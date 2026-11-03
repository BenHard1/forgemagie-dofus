"""Point d'entrée : python -m fmhelper <commande>.

Commandes :
  plan ITEM.json        ordre de clics théorique + liste d'achats estimée
  calibrate             repère la fenêtre de FM à l'écran (une fois par résolution)
  live ITEM.json        lit l'écran en continu et entoure en vert la rune à cliquer
  stats                 liste des clés de caractéristiques utilisables dans ITEM.json
"""
from __future__ import annotations

import argparse
import sys

from .model import Item
from .planner import click_plan, shopping_list
from .probability import estimate
from .runes import STATS


def _parse_current(s: str):
    out = {}
    for part in filter(None, (p.strip() for p in s.split(","))):
        k, v = part.split("=")
        out[k.strip()] = int(v)
    return out


def cmd_plan(a):
    item = Item.load(a.item)
    for k, v in _parse_current(a.current or "").items():
        l = item.line(k)
        if l is None:
            sys.exit(f"Ligne inconnue sur l'objet : {k}")
        l.current = v
    print(f"== {item.name} (niv. {item.level}) — reliquat de départ {a.reliquat:g} ==\n")
    print("Ordre de clics conseillé (si chaque rune passe) :")
    plan = click_plan(item, a.reliquat, force_heavy=a.forcer_exo)
    prev = None
    count = 0
    rows = []
    for rec in plan:
        key = (rec.rune.name, rec.line.stat)
        if key == prev:
            count += 1
            rows[-1] = (rows[-1][0], count, rows[-1][2])
        else:
            count = 1
            rows.append((rec, 1, str(rec.chances)))
        prev = key
    for i, (rec, n, ch) in enumerate(rows, 1):
        print(f"  {i:>2}. {n} x {rec.rune.name:<22} sur {rec.line.info.label:<20} ({ch} au 1er clic)")
    print("\nListe d'achats estimée (simulation de", a.runs, "FM) :")
    print(f"  {'Rune':28} {'min':>5} {'médiane':>8} {'p90':>6}")
    rep = shopping_list(item, a.reliquat, runs=a.runs, force_heavy=a.forcer_exo, budget=a.budget)
    for s in rep:
        print(f"  {s.rune:28} {s.minimum:>5} {s.median:>8} {s.p90:>6}")
    print(f"\nFM terminée dans {rep.success_rate:.0%} des simulations (budget {rep.budget} clics).")
    if rep.success_rate < 0.5:
        print("Objectif très dur : vise un jet un peu sous le max (--current / \"target\" dans le JSON),")
        print("ou monte les lignes ensemble avant de finir les derniers points.")
    from .model import ForgeSession
    from .planner import pending_heavy

    waiting = pending_heavy(ForgeSession(item, a.reliquat)) if not a.forcer_exo else []
    if waiting:
        names = ", ".join(l.info.label for l in waiting)
        print(f"\nEn attente de reliquat (non planifié) : {names}. Crée du reliquat d'abord")
        print("(faire sauter une grosse ligne avec une petite rune), ou relance avec --forcer-exo.")
    print("\nmin = si tout passe ; médiane/p90 = avec échecs, simulés avec la formule de difficulté DoFocus.")
    print("Formule reconstituée à partir de 225 896 clics, pas publiée par Ankama : une approximation.")


def cmd_calibrate(a):
    from .ui import calibrate

    cal = calibrate(a.out)
    print("Calibration enregistrée dans", a.out, ":", cal)


def cmd_live(a):
    from .ui import Calibration, LiveApp

    item = Item.load(a.item)
    cal = Calibration.load(a.calibration)
    LiveApp(item, cal, reliquat=a.reliquat, interval_ms=a.interval, tesseract_cmd=a.tesseract, lang=a.lang).run()


def cmd_stats(a):
    for k, s in STATS.items():
        powers = "/".join(str(p) for p in s.powers)
        print(f"  {k:18} {s.label:24} poids/pt {s.weight_per_point:<5g} runes +{powers}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="fmhelper", description="Aide à la décision pour la forgemagie Dofus (lecture seule).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("plan", help="ordre de clics et liste d'achats")
    sp.add_argument("item")
    sp.add_argument("--current", help="valeurs actuelles, ex. 'vitalite=230,force=40'")
    sp.add_argument("--reliquat", type=float, default=0.0)
    sp.add_argument("--runs", type=int, default=300)
    sp.add_argument("--budget", type=int, default=400, help="clics max par FM simulée")
    sp.add_argument("--forcer-exo", action="store_true", help="planifier les exos/overs lourds même sans reliquat")
    sp.set_defaults(func=cmd_plan)

    sc = sub.add_parser("calibrate", help="repérer la fenêtre de FM")
    sc.add_argument("--out", default="calibration.json")
    sc.set_defaults(func=cmd_calibrate)

    sl = sub.add_parser("live", help="overlay en temps réel")
    sl.add_argument("item")
    sl.add_argument("--calibration", default="calibration.json")
    sl.add_argument("--reliquat", type=float, default=0.0)
    sl.add_argument("--interval", type=int, default=400, help="ms entre deux lectures")
    sl.add_argument("--tesseract", help="chemin de tesseract.exe si non trouvé")
    sl.add_argument("--lang", default="fra")
    sl.set_defaults(func=cmd_live)

    ss = sub.add_parser("stats", help="clés de caractéristiques")
    ss.set_defaults(func=cmd_stats)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
