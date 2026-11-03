"""Plan de montée de Joaillomage (anneaux, amulettes) de 1 à 200.

Données : Astuces Kamas (2026) et Dofastuces (2015), voir docs/MONTER_JOAILLOMAGE.md.
"""
from __future__ import annotations

from typing import List, Tuple

# (niveau de métier conseillé, objet, niveau de l'objet, runes, étape clé)
JOAILLOMAGE: List[Tuple[str, str, int, str, bool]] = [
    ("1 → 10", "Le Plussain", 1, "Fo, Age (~1 000 runes au total)", True),
    ("10 → 20", "Amulette de l'Aventurier", 5, "Fo, Ine, Cha, Age", True),
    ("9 → 13", "Amulette de Kroquette", 9, "Cha, Cri", False),
    ("13 → 20", "Anneau du Champchamp", 13, "Vi, Cri, Tac", False),
    ("20 → 30", "Amulette du Bouftou", 20, "Fo, Ine, Vi", True),
    ("26 → 31", "Larvamulette", 26, "Pa Vi, Pa Ine, Pa Age", False),
    ("30 → 50", "Passé de Xélor", 30, "Ine, Sa, Vi", True),
    ("50 → 81", "Blopanneau Griotte", 50, "Ine, Pa Ine", True),
    ("59 → 81", "Anneau Merta", 59, "Pa Ine, Pa Age, Cri", False),
    ("81 → 108", "Alliance Feudala", 81, "Ine, Pa Ine, Sa", True),
    ("108 → 128", "Anneau du Dragon Cochon", 108, "Pa Vi, Sa, Pui", True),
    ("128 → 153", "Amulette du Royalmouth", 128, "Pa Ine, Pa Cha, Sa", True),
    ("140 → 153", "Anneau du Mansot Royal", 140, "Pa Vi, Pa Fo, Cri", False),
    ("153 → 168", "Anneau de Cantile", 153, "Pa Fo, Pa Age, Sa", True),
    ("168 → 175", "Anneau des Prophètes", 168, "Pa Ine, Pa Cha, Sa", True),
    ("175 → 190", "Anneau de Guten Tak", 175, "Pa Fo, Pa Cha, Sa", True),
    ("190 → 200", "Anneau de Kolosso", 190, "Pa Vi, Pa Fo, Vi, Fo", True),
]


def print_plan(key_only: bool = False) -> None:
    print("Plan de montée Joaillomage 1 → 200 (règle : niveau de métier >= niveau de l'objet)\n")
    print(f"  {'Métier':10} {'Objet':28} {'Niv.':>4}  Runes")
    for lvl, name, ilvl, runes, key in JOAILLOMAGE:
        if key_only and not key:
            continue
        star = "*" if key else " "
        print(f"{star} {lvl:10} {name:28} {ilvl:>4}  {runes}")
    print("\n* = étape clé. Quantités à partir du niveau 10 : commence avec ~20 runes par ligne,")
    print("note l'XP par clic en jeu, puis achète (XP manquante / XP par clic) runes.")
    print("Détails et sources : docs/MONTER_JOAILLOMAGE.md")
