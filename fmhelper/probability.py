"""Chances SC / SN / EC d'une rune : formule de la « difficulté ».

Formule reconstituée par DoFocus (vidéo « J'ai CRACKÉ le secret de la
forgemagie DOFUS », 225 896 clics analysés). Ankama ne l'a pas publiée : c'est
une approximation très proche des données, pas le code du jeu.

    difficulté = 5
               + 45                      si la ligne dépasse 80 % de son max
               + 65 + 4 x poids d'over   si la ligne passe au-dessus de son max
               + 12 x (multiplicateur - 14)  si la ligne vaut plus de 14 x la puissance de la rune
               - 20                      si l'objet est sous le niveau 170
               + 0 à 60                  selon la qualité globale de l'objet
                                         (60 d'office avec un exo PA/PM/PO)

    SC = (100 - difficulté) / 2, jamais sous 2 % (sauf exo PA/PM/PO)
    SN = 50 % (dans la plupart des cas)
    EC = le reste

Points encore incertains, réglables dans PARAMS :
- la forme exacte de la courbe de qualité globale (la vidéo dit seulement
  « presque rien pour un objet moyen, jusqu'à +60 presque parfait ») ;
- si le palier des 80 % et le x14 se mesurent avant ou après la rune ;
- la part exacte de SN dans les cas extrêmes ;
- les chances d'un exo PA/PM/PO (≈ 1 % selon la communauté).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .model import Item, Line
from .runes import Rune

HEAVY_EXO_STATS = ("pa", "pm", "po")

PARAMS: Dict[str, float] = {
    "base": 5,
    "palier": 0.80,
    "palier_cost": 45,
    "over_cost": 65,
    "over_per_weight": 4,
    "mult_start": 14,
    "mult_cost": 12,
    "low_level_threshold": 170,
    "low_level_bonus": 20,
    "quality_max": 60,
    "quality_exponent": 3,  # courbe de qualité : 60 x q^3 (incertain)
    "floor": 0.02,
    "sn": 0.50,
    "exo_heavy_sc": 0.01,
    "exo_heavy_weight": 30,
    "palier_after_rune": 1,  # 1 : palier/over mesurés sur la valeur après la rune
}


@dataclass
class Chances:
    sc: float
    sn: float
    ec: float
    difficulty: float = 0.0

    @property
    def passes(self) -> float:
        """Probabilité que la rune passe (SC + SN)."""
        return self.sc + self.sn

    def __str__(self) -> str:
        return f"SC {self.sc:.0%} · SN {self.sn:.0%} · EC {self.ec:.0%}"


def item_quality(item: Item, exclude: Line = None) -> float:
    """Qualité globale de 0 (lignes au min) à 1 (jet parfait), pondérée par le poids.

    Un exo PA/PM/PO présent sur l'objet le rend « parfait » (règle de l'exo PA).
    """
    for l in item.lines:
        if l.exo and l.stat in HEAVY_EXO_STATS and l.current > 0:
            return 1.0
    num = den = 0.0
    for l in item.lines:
        if l is exclude or l.exo or l.max <= 0:
            continue
        w = max(l.max, 1) * l.wpp
        span = l.max - l.min
        q = 1.0 if span <= 0 else (l.current - l.min) / span
        num += w * max(0.0, min(1.0, q))
        den += w
    return num / den if den else 0.0


def difficulty(item: Item, line: Line, rune: Rune, p: Dict[str, float] = PARAMS) -> float:
    value = line.current + rune.power if p["palier_after_rune"] else line.current
    d = p["base"]
    if not line.is_malus and line.max > 0:
        if value >= p["palier"] * line.max:
            d += p["palier_cost"]
    over_w = line.over_points(value) * line.wpp
    if over_w > 0:
        d += p["over_cost"] + p["over_per_weight"] * over_w
    if rune.power > 0 and line.current > 0:
        mult = int(line.current // rune.power)
        if mult > p["mult_start"]:
            d += p["mult_cost"] * (mult - p["mult_start"])
    if item.level < p["low_level_threshold"]:
        d -= p["low_level_bonus"]
    d += p["quality_max"] * item_quality(item, exclude=line) ** p["quality_exponent"]
    return d


def estimate(item: Item, line: Line, rune: Rune, params: Dict[str, float] = PARAMS) -> Chances:
    p = params
    absent = line.exo or (line.max <= 0 and not line.is_malus)
    if absent and line.current <= 0 and (rune.stat in HEAVY_EXO_STATS or rune.weight >= p["exo_heavy_weight"]):
        sc = p["exo_heavy_sc"]
        return Chances(sc, 0.0, round(1 - sc, 4), difficulty=float("inf"))
    d = difficulty(item, line, rune, p)
    sc = (100 - d) / 2 / 100
    sc = max(p["floor"], min(1.0, sc))
    sn = min(p["sn"], 1 - sc)
    ec = max(0.0, 1 - sc - sn)
    return Chances(round(sc, 4), round(sn, 4), round(ec, 4), difficulty=d)
