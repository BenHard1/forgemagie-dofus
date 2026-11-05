"""Point d'entrée : python -m fmhelper <commande>.

Sans commande : ouvre la fenêtre de choix de l'équipement (recherche DofusDB,
stats visées, liste des runes, puis FM en direct).

Commandes :
  gui                   même chose que sans commande
  plan ITEM.json        ordre de clics théorique + liste d'achats estimée
  calibrate             repère la fenêtre de FM à l'écran (une fois par résolution)
  live ITEM.json        lit l'écran en continu et entoure en vert la rune à cliquer
  progression           plan de montée Joaillomage 1 → 200
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


def cmd_gui(a):
    from .launcher import main as launcher_main

    launcher_main(a.calibration)


def cmd_item(a):
    import json

    from .dofusdb import load_item, search_items

    res = search_items(a.recherche)
    if not res:
        sys.exit("Aucun équipement trouvé.")
    for i, r in enumerate(res[:15], 1):
        print(f"  {i:>2}. {r['name']} — niv. {r['level']} ({r['type']})")
    pick = res[0]
    if len(res) > 1 and sys.stdin.isatty():
        n = input("Numéro de l'objet [1] : ").strip()
        pick = res[int(n) - 1] if n else res[0]
    item = load_item(pick["id"])
    out = a.out or f"{pick['name']}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(item.to_dict(), f, ensure_ascii=False, indent=2)
    print("Objet enregistré dans", out, "— modifie current / target puis lance : python -m fmhelper plan", repr(out))


def cmd_stats(a):
    for k, s in STATS.items():
        powers = "/".join(str(p) for p in s.powers)
        print(f"  {k:18} {s.label:24} poids/pt {s.weight_per_point:<5g} runes +{powers}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="fmhelper", description="Aide à la décision pour la forgemagie Dofus (lecture seule).")
    sub = p.add_subparsers(dest="cmd")

    sg = sub.add_parser("gui", help="fenêtre de choix de l'équipement (par défaut)")
    sg.add_argument("--calibration", default="calibration.json")
    sg.set_defaults(func=cmd_gui)

    sd = sub.add_parser("item", help="crée un JSON d'objet depuis DofusDB")
    sd.add_argument("recherche")
    sd.add_argument("--out")
    sd.set_defaults(func=cmd_item)

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
    sl.add_argument("--interval", type=int, default=100, help="ms entre deux captures (l'OCR ne tourne que si l'écran change)")
    sl.add_argument("--tesseract", help="chemin de tesseract.exe si non trouvé")
    sl.add_argument("--lang", default="fra")
    sl.set_defaults(func=cmd_live)

    sj = sub.add_parser("progression", help="plan de montée Joaillomage 1 → 200")
    sj.add_argument("--essentiel", action="store_true", help="seulement les étapes clés")
    sj.set_defaults(func=lambda a: __import__("fmhelper.progression", fromlist=["print_plan"]).print_plan(a.essentiel))

    ss = sub.add_parser("stats", help="clés de caractéristiques")
    ss.set_defaults(func=cmd_stats)

    a = p.parse_args(argv)
    if a.cmd is None:
        a = p.parse_args(["gui"])
    a.func(a)


def _main_with_error_report():
    """Lancé sans console (pyw) : une erreur est écrite dans fmhelper_erreur.log et affichée."""
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback

        msg = traceback.format_exc()
        try:
            with open("fmhelper_erreur.log", "w", encoding="utf-8") as f:
                f.write(msg)
        except OSError:
            pass
        if sys.stderr is None or not sys.stderr.isatty():
            try:
                import tkinter as tk
                from tkinter import messagebox

                r = tk.Tk()
                r.withdraw()
                messagebox.showerror("Aide FM — erreur", msg[-1500:] + "\n\n(copie dans fmhelper_erreur.log)")
            except Exception:
                pass
        raise


if __name__ == "__main__":
    _main_with_error_report()
