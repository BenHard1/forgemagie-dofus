"""Base de données des runes de forgemagie.

Chaque caractéristique a un *poids par point* (aussi appelé densité) et une
liste de runes disponibles (rune de base, Pa, Ra) avec leur puissance (le
nombre de points ajoutés). Le poids d'une rune = puissance x poids par point.

Sources (voir docs/REGLES_FORGEMAGIE.md) : JeuxOnLine, Dofus Fashionista,
Gamosaurus, Huzounet. Les valeurs sont celles de Dofus 2.x / Dofus 3 au moment
de la rédaction ; vérifie la « densité » affichée au survol d'une rune en jeu
si un doute existe et corrige ce fichier si besoin.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Plafond de poids d'une ligne en over / exo (règle des 101).
OVER_WEIGHT_CAP = 101.0


@dataclass(frozen=True)
class Rune:
    stat: str  # clé de la caractéristique
    tier: str  # "base", "pa" ou "ra"
    name: str  # nom en jeu
    power: int  # points ajoutés

    @property
    def weight(self) -> float:
        return round(self.power * STATS[self.stat].weight_per_point, 4)


@dataclass(frozen=True)
class StatInfo:
    key: str
    label: str  # libellé affiché en jeu (français)
    weight_per_point: float
    rune_abbr: str  # abréviation utilisée dans le nom de la rune
    powers: Tuple[int, ...]  # puissances disponibles (base, pa, ra)
    aliases: Tuple[str, ...] = ()
    special_name: Optional[str] = None  # nom spécial (Ga Pa, Ga Pme...)

    def runes(self) -> List[Rune]:
        tiers = ("base", "pa", "ra")
        out = []
        for tier, power in zip(tiers, self.powers):
            if self.special_name:
                name = f"Rune {self.special_name}"
            elif tier == "base":
                name = f"Rune {self.rune_abbr}"
            else:
                name = f"Rune {tier.capitalize()} {self.rune_abbr}"
            out.append(Rune(self.key, tier, name, power))
        return out

    @property
    def over_cap_points(self) -> int:
        """Nombre de points max qu'une ligne en over/exo peut atteindre (101 de poids)."""
        return int(OVER_WEIGHT_CAP / self.weight_per_point + 1e-9)


def _s(key, label, wpp, abbr, powers, aliases=(), special=None):
    return StatInfo(key, label, wpp, abbr, tuple(powers), tuple(aliases), special)


_ALL = [
    _s("vitalite", "Vitalité", 0.2, "Vi", (5, 15, 50), ("vita", "vie")),
    _s("initiative", "Initiative", 0.1, "Ini", (10, 30, 100), ("ini",)),
    _s("pods", "Pods", 0.25, "Pod", (10, 30, 100), ("pod",)),
    _s("force", "Force", 1, "Fo", (1, 3, 10), ("fo",)),
    _s("intelligence", "Intelligence", 1, "Ine", (1, 3, 10), ("intel", "ine")),
    _s("chance", "Chance", 1, "Cha", (1, 3, 10), ("cha",)),
    _s("agilite", "Agilité", 1, "Age", (1, 3, 10), ("agi", "age")),
    _s("sagesse", "Sagesse", 3, "Sa", (1, 3, 10), ("sa",)),
    _s("puissance", "Puissance", 2, "Pui", (1, 3, 10), ("pui",)),
    _s("prospection", "Prospection", 3, "Prospe", (1, 3), ("pp", "prospe")),
    _s("tacle", "Tacle", 4, "Tac", (1, 3)),
    _s("fuite", "Fuite", 4, "Fui", (1, 3)),
    _s("retrait_pa", "Retrait PA", 7, "Ret Pa", (1, 3)),
    _s("retrait_pm", "Retrait PM", 7, "Ret Pme", (1, 3)),
    _s("esquive_pa", "Esquive PA", 7, "Ré Pa", (1, 3)),
    _s("esquive_pm", "Esquive PM", 7, "Ré Pme", (1, 3)),
    _s("soins", "Soins", 10, "So", (1,), ("soin",)),
    _s("critique", "Critique", 10, "Cri", (1,), ("% critique", "coups critiques")),
    _s("dommages", "Dommages", 20, "Do", (1,), ("do",)),
    _s("do_neutre", "Dommages Neutre", 5, "Do Neutre", (1, 3)),
    _s("do_terre", "Dommages Terre", 5, "Do Terre", (1, 3)),
    _s("do_feu", "Dommages Feu", 5, "Do Feu", (1, 3)),
    _s("do_eau", "Dommages Eau", 5, "Do Eau", (1, 3)),
    _s("do_air", "Dommages Air", 5, "Do Air", (1, 3)),
    _s("do_critiques", "Dommages Critiques", 5, "Do Cri", (1, 3)),
    _s("do_poussee", "Dommages Poussée", 5, "Do Pou", (1, 3)),
    _s("do_pieges", "Dommages Pièges", 5, "Do Pi", (1, 3)),
    _s("puissance_pieges", "Puissance Pièges", 2, "Pi Per", (1, 3, 10)),
    _s("renvoi", "Renvoie dommages", 5, "Ré Ren", (1,), ("renvoi",)),
    _s("re_neutre", "Résistance Neutre", 2, "Ré Neutre", (1, 3)),
    _s("re_terre", "Résistance Terre", 2, "Ré Terre", (1, 3)),
    _s("re_feu", "Résistance Feu", 2, "Ré Feu", (1, 3)),
    _s("re_eau", "Résistance Eau", 2, "Ré Eau", (1, 3)),
    _s("re_air", "Résistance Air", 2, "Ré Air", (1, 3)),
    _s("re_critiques", "Résistance Critiques", 2, "Ré Cri", (1, 3)),
    _s("re_poussee", "Résistance Poussée", 2, "Ré Pou", (1, 3)),
    _s("re_pct_neutre", "% Résistance Neutre", 6, "Ré Per Neutre", (1,)),
    _s("re_pct_terre", "% Résistance Terre", 6, "Ré Per Terre", (1,)),
    _s("re_pct_feu", "% Résistance Feu", 6, "Ré Per Feu", (1,)),
    _s("re_pct_eau", "% Résistance Eau", 6, "Ré Per Eau", (1,)),
    _s("re_pct_air", "% Résistance Air", 6, "Ré Per Air", (1,)),
    _s("pct_do_armes", "% Dommages d'armes", 15, "Per Do Arme", (1,)),
    _s("pct_do_sorts", "% Dommages aux sorts", 15, "Per Do Sort", (1,)),
    _s("pct_do_melee", "% Dommages mêlée", 15, "Per Do Mel", (1,)),
    _s("pct_do_distance", "% Dommages distance", 15, "Per Do Dis", (1,)),
    _s("pct_re_melee", "% Résistance mêlée", 15, "Per Ré Mel", (1,)),
    _s("pct_re_distance", "% Résistance distance", 15, "Per Ré Dis", (1,)),
    _s("invocation", "Invocation", 30, "Invo", (1,), ("invocations",)),
    _s("po", "Portée", 51, "Po", (1,), ("po",)),
    _s("pm", "PM", 90, "Pme", (1,), ("pme",), special="Ga Pme"),
    _s("pa", "PA", 100, "Pa", (1,), (), special="Ga Pa"),
]

STATS: Dict[str, StatInfo] = {s.key: s for s in _ALL}


def runes_for(stat: str) -> List[Rune]:
    return STATS[stat].runes()


def rune_by_tier(stat: str, tier: str) -> Optional[Rune]:
    for r in runes_for(stat):
        if r.tier == tier:
            return r
    return None


def _norm(text: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.replace("'", " ").split())


def match_stat(label: str, cutoff: float = 0.75) -> Optional[str]:
    """Retrouve la clé d'une caractéristique à partir d'un libellé (OCR, saisie).

    Tolérant aux accents et aux petites erreurs d'OCR.
    """
    import difflib

    n = _norm(label)
    if not n:
        return None
    table = {}
    for s in _ALL:
        table[_norm(s.label)] = s.key
        table[_norm(s.key.replace("_", " "))] = s.key
        for a in s.aliases:
            table[_norm(a)] = s.key
    if n in table:
        return table[n]
    best = difflib.get_close_matches(n, list(table), n=1, cutoff=cutoff)
    return table[best[0]] if best else None
