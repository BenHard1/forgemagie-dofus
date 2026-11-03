"""Alertes et estimations affichées pendant la FM en direct (logique pure, testable)."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .model import EC, SC, SN, ForgeSession, Item, Line, Observation
from .probability import Chances, estimate
from .runes import Rune, runes_for

# Couleur du cadre selon l'issue du dernier coup
OUTCOME_COLORS = {None: "#00e676", SC: "#00e676", SN: "#ffd600", EC: "#ff1744"}
ALERT_COLOR = "#ff1744"

HEAVY_NATURAL = ("pa", "pm", "po")


def tier_chances(item: Item, line: Line) -> List[Tuple[Rune, Chances]]:
    """Chances SC/SN/EC de chaque rang de rune (Rune, Pa, Ra) sur une ligne."""
    return [(r, estimate(item, line, r)) for r in runes_for(line.stat)]


def detect_alerts(before: Dict[str, int], session: ForgeSession, obs: Optional[Observation],
                  target_reached: bool) -> List[str]:
    """Situations où il faut s'arrêter et regarder.

    - cible atteinte ;
    - une ligne lourde naturelle (PA, PM, PO) vient de baisser ;
    - le reliquat vient de tomber à 0.
    """
    alerts: List[str] = []
    if target_reached:
        alerts.append("Cible atteinte : l'objet est terminé selon tes cibles.")
    for l in session.item.lines:
        if l.stat in HEAVY_NATURAL and not l.exo and l.current < before.get(l.stat, l.current):
            alerts.append(f"Ligne {l.info.label} sautée ({before[l.stat]} → {l.current}).")
    if obs is not None and obs.reliquat_before > 0 and obs.reliquat_after <= 0:
        alerts.append("Reliquat épuisé : les prochains SN/EC toucheront les lignes de l'objet.")
    return alerts
