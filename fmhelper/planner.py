"""Choix de la prochaine rune, plan de clics et liste d'achats.

Stratégie (consensus des guides, voir docs/REGLES_FORGEMAGIE.md) :
1. Remonter d'abord les lignes légères et les malus (malus = moitié prix).
2. Monter toutes les lignes progressivement plutôt qu'une seule à 100 %.
3. Choisir le rang de rune (base / Pa / Ra) selon l'écart restant et la règle
   du x20 : la plus grosse rune qui ne dépasse pas la cible, sauf si la valeur
   actuelle dépasse 20 x sa puissance (alors on préfère monter d'un rang).
4. Garder les lignes lourdes (PA, PM, PO, Invo) et les exos/overs pour la fin,
   quand le reliquat est le plus grand ; ne tenter un over/exo lourd que si
   le reliquat couvre le poids de la rune.
"""
from __future__ import annotations

import copy
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model import EC, SC, SN, ForgeSession, Item, Line, rune_weight_on_line
from .probability import Chances, estimate
from .runes import Rune, runes_for

HEAVY_WEIGHT = 30  # poids à partir duquel une ligne est « lourde »


@dataclass
class Recommendation:
    line: Line
    rune: Rune
    chances: Chances
    reason: str
    line_index: int
    covered_by_reliquat: bool = False

    def __str__(self) -> str:
        cov = " (couvert par le reliquat)" if self.covered_by_reliquat else ""
        return f"{self.rune.name} sur {self.line.info.label} [{self.chances}]{cov} — {self.reason}"


def choose_tier(line: Line) -> Optional[Rune]:
    """Choisit la rune (base/Pa/Ra) à poser sur une ligne pour aller vers sa cible."""
    gap = line.target - line.current
    if gap <= 0:
        return None
    runes = sorted(runes_for(line.stat), key=lambda r: r.power)
    over_allowed = line.target > line.max
    limit = line.target if over_allowed else min(line.target, line.max if line.max > 0 else line.target)
    fitting = [r for r in runes if line.current + r.power <= limit]
    if not fitting:
        # Écart plus petit que la plus petite rune : on accepte de dépasser
        # légèrement si on reste sous le plafond d'over.
        smallest = runes[0]
        if line.current + smallest.power <= line.cap():
            return smallest
        return None
    # La plus grosse rune qui rentre : c'est aussi celle qui respecte le mieux
    # la règle du x20 (valeur actuelle <= 20 x puissance).
    best = fitting[-1]
    return best


def _priority(line: Line, rune: Rune) -> tuple:
    heavy = rune.weight >= HEAVY_WEIGHT
    over_or_exo = line.exo or line.current + rune.power > max(line.max, 0)
    span = max(line.target - line.min, 1)
    progress = (line.current - line.min) / span
    return (
        2 if (heavy and over_or_exo) else (1 if (heavy or over_or_exo) else 0),
        0 if line.is_malus else 1,  # malus à moitié prix d'abord
        round(progress, 3),
        line.wpp,
    )


def recommend(session: ForgeSession, force_heavy: bool = False) -> Optional[Recommendation]:
    """Renvoie la prochaine rune à poser.

    Un over/exo lourd (PA, PM, PO, Invo...) n'est proposé que si le reliquat
    couvre le poids de la rune, sauf si force_heavy=True : sans reliquat, chaque
    échec (99 % du temps) fait sauter des lignes de l'objet.
    """
    item = session.item
    best = None
    for idx, line in enumerate(item.lines):
        rune = choose_tier(line)
        if rune is None:
            continue
        heavy_risky = rune.weight >= HEAVY_WEIGHT and (line.exo or line.current + rune.power > max(line.max, 0))
        covered = session.reliquat >= rune_weight_on_line(rune, line) - 1e-9
        if heavy_risky and not covered and not force_heavy:
            continue
        key = _priority(line, rune)
        if heavy_risky and covered:
            # Reliquat suffisant : on tente l'exo/over lourd tout de suite, avant que
            # les SN des autres runes n'entament le reliquat.
            key = (-1,) + key[1:]
        if best is None or key < best[0]:
            best = (key, idx, line, rune, covered, heavy_risky)
    if best is None:
        return None
    _, idx, line, rune, covered, heavy_risky = best
    ch = estimate(item, line, rune)
    if line.exo:
        reason = "exo : ligne absente du jet, à tenter en dernier"
    elif line.current + rune.power > max(line.max, 0):
        reason = "over : au-delà du jet max"
    elif line.is_malus:
        reason = "malus : la rune coûte moitié poids"
    else:
        reason = f"ligne la moins avancée ({line.current}/{line.target})"
    if heavy_risky and not covered:
        reason += " — ATTENTION : le reliquat ne couvre pas cette rune, un échec fera sauter d'autres lignes"
    return Recommendation(line, rune, ch, reason, idx, covered)


def pending_heavy(session: ForgeSession) -> List[Line]:
    """Lignes over/exo lourdes en attente faute de reliquat suffisant."""
    out = []
    for line in session.item.lines:
        rune = choose_tier(line)
        if rune is None:
            continue
        heavy = rune.weight >= HEAVY_WEIGHT and (line.exo or line.current + rune.power > max(line.max, 0))
        if heavy and session.reliquat < rune_weight_on_line(rune, line) - 1e-9:
            out.append(line)
    return out


def click_plan(item: Item, reliquat: float = 0.0, max_steps: int = 500, force_heavy: bool = False) -> List[Recommendation]:
    """Ordre de clics théorique si chaque rune passe (utile pour préparer la FM)."""
    s = ForgeSession(copy.deepcopy(item), reliquat)
    plan = []
    for _ in range(max_steps):
        rec = recommend(s, force_heavy)
        if rec is None:
            break
        plan.append(rec)
        rec.line.current += rec.rune.power
    return plan


# ---------------------------------------------------------------------------
# Simulation Monte-Carlo pour estimer la liste d'achats
# ---------------------------------------------------------------------------

def _apply_loss(session: ForgeSession, rune: Rune, protect: Line, rng: random.Random) -> None:
    """Applique une perte de poids `rune.weight` (modèle communautaire).

    Ordre : reliquat, puis overs/exos, puis lignes de poids proche de la rune.
    """
    need = rune.weight
    if session.reliquat > 0:
        take = min(session.reliquat, need)
        session.reliquat -= take
        need -= take
    if need <= 1e-9:
        return
    item = session.item
    cands = [l for l in item.lines if l is not protect and l.current > l.min and l.current > 0]
    if not cands:
        return
    overs = [l for l in cands if l.exo or l.current > l.max]
    pool = overs or cands
    # Les lignes dont le poids par rune de base est proche de la rune sont visées en priorité
    pool.sort(key=lambda l: (abs(l.wpp - rune.weight), rng.random()))
    target = pool[0]
    pts = max(1, int(round(need / target.wpp)))
    pts = min(pts, target.current)
    target.current -= pts
    lost_w = pts * target.wpp
    if lost_w > need:
        session.reliquat += lost_w - need


def simulate(item: Item, reliquat: float = 0.0, runs: int = 300, seed: int = 1, max_clicks: int = 2000,
             force_heavy: bool = False) -> Dict:
    rng = random.Random(seed)
    totals: List[Counter] = []
    for _ in range(runs):
        s = ForgeSession(copy.deepcopy(item), reliquat)
        used: Counter = Counter()
        for _ in range(max_clicks):
            rec = recommend(s, force_heavy)
            if rec is None:
                break
            line, rune = rec.line, rec.rune
            used[rune.name] += 1
            ch = rec.chances
            x = rng.random()
            if x < ch.sc:
                line.current += rune.power
            elif x < ch.sc + ch.sn:
                line.current += rune.power
                _apply_loss(s, rune, line, rng)
            else:
                _apply_loss(s, rune, line, rng)
            # un exo lourd raté : on abandonne après 150 essais (budget)
            if line.exo and used[rune.name] > 150 and line.current < line.target:
                line.target = line.current
        totals.append(used)
    names = sorted({n for c in totals for n in c})
    summary = {}
    for n in names:
        vals = sorted(c.get(n, 0) for c in totals)
        summary[n] = {
            "mediane": vals[len(vals) // 2],
            "p90": vals[int(len(vals) * 0.9) - 1 if len(vals) > 1 else 0],
        }
    return summary


@dataclass
class ShoppingLine:
    rune: str
    minimum: int
    median: int
    p90: int


def shopping_list(item: Item, reliquat: float = 0.0, runs: int = 300, force_heavy: bool = False) -> List[ShoppingLine]:
    plan = click_plan(item, reliquat, force_heavy=force_heavy)
    minimum = Counter(r.rune.name for r in plan)
    sim = simulate(item, reliquat, runs=runs, force_heavy=force_heavy)
    out = []
    for name in sorted(set(minimum) | set(sim)):
        out.append(ShoppingLine(name, minimum.get(name, 0), sim.get(name, {}).get("mediane", 0), sim.get(name, {}).get("p90", 0)))
    out.sort(key=lambda s: -s.median)
    return out
