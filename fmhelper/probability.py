"""Estimation des chances SC / SN / EC d'une rune.

ATTENTION : Ankama n'a jamais publié la formule officielle. Ce module implémente
un modèle *estimatif* construit à partir des règles communautaires listées dans
docs/REGLES_FORGEMAGIE.md (vidéo DoFocus, Fashionista, Gamosaurus, Huzounet) :

- palier des 80 % : tant que la ligne reste sous 80 % de son max après la rune,
  les chances sont bonnes ; au-delà elles baissent jusqu'au max, puis
  fortement en over ;
- règle du x20 : une rune passe bien tant que la valeur de la ligne reste
  sous ~20 fois la puissance de la rune (+1 jusqu'à 20, +3 jusqu'à 60, +10
  jusqu'à 200) ;
- plancher de 2 % : le SC ne descend jamais sous 2 % pour une rune normale ;
- exo lourd (PA, PM, PO, Invo… poids >= 30 sur une ligne absente) : SC 1 %,
  pas de SN ;
- plus l'objet est proche de son poids max, plus c'est dur ;
- objets sous le niveau 170 : chances plus favorables (facteur réglable).

Tous les coefficients sont dans PARAMS pour pouvoir les recalibrer à partir de
ton propre historique (fichier CSV écrit par l'outil en mode live).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .model import Item, Line
from .runes import Rune

PARAMS: Dict[str, float] = {
    "base_sc": 0.66,  # SC max théorique sur une ligne basse
    "palier": 0.80,  # palier des 80 %
    "sc_at_max": 0.30,  # SC quand la rune amène la ligne pile au max
    "sc_over": 0.10,  # SC de départ pour un over (décroît avec le poids d'over)
    "x20_penalty": 0.55,  # multiplicateur si la valeur dépasse 20 x puissance
    "item_weight_factor": 0.25,  # pénalité max liée au remplissage de l'objet
    "low_level_bonus": 1.15,  # objets < 170
    "low_level_threshold": 170,
    "floor": 0.02,  # plancher de 2 %
    "exo_heavy_sc": 0.01,  # exo PA/PM/PO/Invo
    "exo_heavy_weight": 30,  # poids à partir duquel un exo est « lourd »
    "sn_share": 0.65,  # part de SN dans (1 - SC)
}


@dataclass
class Chances:
    sc: float
    sn: float
    ec: float

    @property
    def passes(self) -> float:
        """Probabilité que la rune passe (SC + SN)."""
        return self.sc + self.sn

    def __str__(self) -> str:
        return f"SC {self.sc:.0%} · SN {self.sn:.0%} · EC {self.ec:.0%}"


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def estimate(item: Item, line: Line, rune: Rune, params: Dict[str, float] = PARAMS) -> Chances:
    p = params
    after = line.current + rune.power
    # Exo lourd : ligne absente du jet et rune de poids >= 30
    if (line.exo or line.max <= 0 and not line.is_malus) and line.current <= 0 and rune.weight >= p["exo_heavy_weight"]:
        sc = p["exo_heavy_sc"]
        return Chances(sc, 0.0, 1 - sc)

    ref_max = max(line.max, 1)
    if line.is_malus:
        ratio = 0.0  # remonter un malus est facile
    else:
        ratio = after / ref_max

    if ratio <= p["palier"]:
        sc = p["base_sc"]
    elif ratio <= 1.0:
        t = (ratio - p["palier"]) / (1 - p["palier"])
        sc = p["base_sc"] + t * (p["sc_at_max"] - p["base_sc"])
    else:
        over_w = line.over_points(after) * line.wpp
        sc = p["sc_over"] * (1 - over_w / 101.0)

    if line.current > 20 * rune.power:
        sc *= p["x20_penalty"]

    mw = item.max_weight()
    if mw > 0:
        fill = _clamp(item.positive_weight() / mw, 0, 1.3)
        sc *= 1 - p["item_weight_factor"] * fill / 1.3

    if item.level < p["low_level_threshold"]:
        sc *= p["low_level_bonus"]

    sc = _clamp(sc, p["floor"], 0.95)
    sn = (1 - sc) * p["sn_share"]
    ec = 1 - sc - sn
    return Chances(round(sc, 4), round(sn, 4), round(ec, 4))
