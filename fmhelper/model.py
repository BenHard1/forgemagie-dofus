"""Modèle d'un objet en cours de forgemagie et suivi du reliquat (puits)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .runes import OVER_WEIGHT_CAP, STATS, Rune


@dataclass
class Line:
    """Une ligne de caractéristique de l'objet.

    min/max : jet théorique (pour un malus, min et max sont négatifs).
    exo : True si la ligne n'existe pas sur le jet théorique (min = max = 0).
    target : valeur visée par le joueur (par défaut le max du jet).
    """

    stat: str
    min: int
    max: int
    current: int = 0
    target: Optional[int] = None
    exo: bool = False

    def __post_init__(self):
        if self.stat not in STATS:
            raise ValueError(f"Caractéristique inconnue : {self.stat}")
        if self.min > self.max:
            self.min, self.max = self.max, self.min
        if self.target is None:
            self.target = self.max

    @property
    def info(self):
        return STATS[self.stat]

    @property
    def wpp(self) -> float:
        return STATS[self.stat].weight_per_point

    @property
    def is_malus(self) -> bool:
        return self.max < 0

    def weight(self, value: Optional[int] = None) -> float:
        v = self.current if value is None else value
        return v * self.wpp

    def cap(self) -> int:
        """Valeur maximale atteignable (jet max, ou 101 de poids pour un over/exo)."""
        if self.max <= 0 and not self.exo:
            return 0 if self.is_malus else self.max
        return max(self.max, self.info.over_cap_points)

    def over_points(self, value: Optional[int] = None) -> int:
        v = self.current if value is None else value
        return max(0, v - max(self.max, 0))


@dataclass
class Item:
    name: str
    level: int
    lines: List[Line] = field(default_factory=list)

    def line(self, stat: str) -> Optional[Line]:
        for l in self.lines:
            if l.stat == stat:
                return l
        return None

    def total_weight(self) -> float:
        return sum(l.current * l.wpp for l in self.lines)

    def positive_weight(self) -> float:
        return sum(max(l.current, 0) * l.wpp for l in self.lines)

    def max_weight(self) -> float:
        return sum(max(l.max, 0) * l.wpp for l in self.lines if not l.exo)

    def values(self) -> Dict[str, int]:
        return {l.stat: l.current for l in self.lines}

    # --- (dé)sérialisation -------------------------------------------------
    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        lines = []
        for ld in d.get("lines", []):
            lines.append(
                Line(
                    stat=ld["stat"],
                    min=int(ld.get("min", 0)),
                    max=int(ld.get("max", 0)),
                    current=int(ld.get("current", ld.get("max", 0))),
                    target=ld.get("target"),
                    exo=bool(ld.get("exo", False)),
                )
            )
        for stat, tgt in (d.get("exos") or {}).items():
            lines.append(Line(stat=stat, min=0, max=0, current=0, target=int(tgt), exo=True))
        return cls(name=d.get("name", "Objet"), level=int(d.get("level", 200)), lines=lines)

    @classmethod
    def load(cls, path: str) -> "Item":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level,
            "lines": [
                {
                    "stat": l.stat,
                    "min": l.min,
                    "max": l.max,
                    "current": l.current,
                    "target": l.target,
                    "exo": l.exo,
                }
                for l in self.lines
            ],
        }


def rune_weight_on_line(rune: Rune, line: Line) -> float:
    """Poids effectif d'une rune sur une ligne.

    Règle « malus à moitié prix » : une rune qui réduit un malus coûte la moitié
    de son poids, sauf pour le passage de -1 à 0 (communauté : Gamosaurus,
    DoFocus).
    """
    w = rune.weight
    if line.current < 0 and line.current != -1 and line.current + rune.power <= 0:
        return w / 2
    return w


# Issues possibles d'une rune
SC, SN, EC = "SC", "SN", "EC"


@dataclass
class Observation:
    outcome: str
    rune: Optional[Rune]
    delta_weight: float
    reliquat_before: float
    reliquat_after: float
    ambiguous: bool = False
    note: str = ""


class ForgeSession:
    """Suit l'état d'une FM : valeurs de l'objet et estimation du reliquat.

    Conservation utilisée (communauté) :
    - SC : la rune passe sans perte, le reliquat ne bouge pas.
    - SN : la rune passe ; une perte égale au poids de la rune est prise d'abord
      sur le reliquat, puis sur les lignes. Si une ligne qui saute pèse plus que
      nécessaire, l'excédent va dans le reliquat. Donc reliquat' = reliquat - ΔW.
    - EC : la rune ne passe pas et la perte a lieu quand même :
      reliquat' = reliquat - ΔW - poids(rune).
    où ΔW est la variation du poids total de l'objet.
    """

    def __init__(self, item: Item, reliquat: float = 0.0):
        self.item = item
        self.reliquat = float(reliquat)
        self.history: List[Observation] = []

    def snapshot(self) -> Dict[str, int]:
        return self.item.values()

    def observe(self, new_values: Dict[str, int], rune: Optional[Rune] = None) -> Optional[Observation]:
        """Met à jour l'état à partir de nouvelles valeurs lues (OCR ou saisie).

        rune : la rune posée si on la connaît (sinon déduite de la ligne qui a monté,
        ou None si rien n'a monté = échec sur une rune inconnue).
        Renvoie None si rien n'a changé.
        """
        old = self.snapshot()
        changed = {k: v for k, v in new_values.items() if k in old and old[k] != v}
        new_lines = [k for k in new_values if k not in old]
        if not changed and not new_lines:
            return None

        before_w = self.item.total_weight()
        for k in new_lines:  # exo apparu
            self.item.lines.append(Line(stat=k, min=0, max=0, current=0, exo=True))
            old[k] = 0
        for k, v in new_values.items():
            l = self.item.line(k)
            if l is not None:
                l.current = v
        dW = self.item.total_weight() - before_w

        increased = [k for k in new_values if new_values[k] > old.get(k, 0)]
        decreased = [k for k in new_values if new_values[k] < old.get(k, 0)]

        if rune is not None and increased and rune.stat not in increased:
            rune = None  # le joueur a posé une autre rune que celle prévue
        if rune is None and increased:
            # Déduire la rune de la ligne qui a monté
            k = increased[0]
            gain = new_values[k] - old[k]
            from .runes import runes_for

            cands = runes_for(k)
            rune = min(cands, key=lambda r: abs(r.power - gain))

        r_before = self.reliquat
        ambiguous = False
        note = ""
        passed = rune is not None and rune.stat in increased
        if passed:
            if decreased:
                outcome = SN
                self.reliquat = self.reliquat - dW
            else:
                # Pas de perte visible : SC, ou SN absorbé par le reliquat.
                if self.reliquat >= rune.weight - 1e-9:
                    outcome = SN
                    ambiguous = True
                    self.reliquat -= rune.weight
                    note = "SC ou SN absorbé par le reliquat : hypothèse prudente (SN)."
                elif self.reliquat > 1e-9:
                    outcome = SN
                    ambiguous = True
                    note = "Reliquat partiel : hypothèse SN, reliquat consommé."
                    self.reliquat = 0.0
                else:
                    outcome = SC
        else:
            outcome = EC
            w = rune.weight if rune is not None else 0.0
            self.reliquat = self.reliquat - dW - w
            if rune is None:
                ambiguous = True
                note = "Rune inconnue sur un échec : reliquat approximatif."
        self.reliquat = max(0.0, round(self.reliquat, 3))
        obs = Observation(outcome, rune, round(dW, 3), r_before, self.reliquat, ambiguous, note)
        self.history.append(obs)
        return obs
