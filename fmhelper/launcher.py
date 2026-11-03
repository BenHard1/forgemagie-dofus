"""Fenêtre de lancement : choisir l'équipement, fixer les stats visées,
voir la liste des runes à acheter, puis lancer le mode live.
"""
from __future__ import annotations

import json
import os
import threading
from typing import List, Optional

from .model import Item, Line
from .planner import click_plan, shopping_list
from .runes import STATS


class Launcher:
    def __init__(self, calibration_path: str = "calibration.json"):
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.cal_path = calibration_path
        self.item: Optional[Item] = None
        self.results: List[dict] = []
        self.rows = []  # (line, var_current, var_target)

        self.root = tk.Tk()
        self.root.title("Aide FM — choix de l'équipement")
        self.root.geometry("760x680")

        # --- recherche ---
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Équipement :").pack(side="left")
        self.v_query = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.v_query, width=40)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda _e: self.search())
        e.focus_set()
        ttk.Button(top, text="Rechercher (DofusDB)", command=self.search).pack(side="left")
        ttk.Button(top, text="Ouvrir un JSON…", command=self.open_json).pack(side="left", padx=4)

        self.lst = tk.Listbox(self.root, height=7)
        self.lst.pack(fill="x", padx=8)
        self.lst.bind("<<ListboxSelect>>", lambda _e: self.pick())
        self.v_status = tk.StringVar(value="Tape le nom d'un équipement puis Entrée.")
        ttk.Label(self.root, textvariable=self.v_status, foreground="#555").pack(anchor="w", padx=8)

        # --- lignes de stats ---
        self.v_title = tk.StringVar()
        ttk.Label(self.root, textvariable=self.v_title, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(8, 0))
        self.grid = ttk.Frame(self.root, padding=(8, 4))
        self.grid.pack(fill="x")

        exo = ttk.Frame(self.root, padding=(8, 0))
        exo.pack(fill="x")
        ttk.Label(exo, text="Ajouter un exo :").pack(side="left")
        self.v_exo = tk.StringVar(value="pa")
        ttk.Combobox(exo, textvariable=self.v_exo, values=["pa", "pm", "po", "invocation", "critique", "dommages"] + sorted(STATS), width=16).pack(side="left", padx=4)
        ttk.Button(exo, text="+ exo", command=self.add_exo).pack(side="left")
        ttk.Label(exo, text="   Reliquat de départ :").pack(side="left")
        self.v_rel = tk.StringVar(value="0")
        ttk.Entry(exo, textvariable=self.v_rel, width=6).pack(side="left")

        act = ttk.Frame(self.root, padding=8)
        act.pack(fill="x")
        ttk.Button(act, text="Calculer les runes", command=self.compute).pack(side="left")
        ttk.Button(act, text="Lire l'objet à l'écran", command=self.read_screen).pack(side="left", padx=4)
        ttk.Button(act, text="Enregistrer…", command=self.save_json).pack(side="left")
        ttk.Button(act, text="Recalibrer", command=self.recalibrate).pack(side="left", padx=4)
        ttk.Button(act, text="Lancer la FM en direct ▶", command=self.go_live).pack(side="right")

        self.out = tk.Text(self.root, height=16, font=("Consolas", 10))
        self.out.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ------------------------------------------------------------------ recherche
    def search(self):
        q = self.v_query.get().strip()
        if len(q) < 2:
            return
        self.v_status.set("Recherche…")

        def work():
            from .dofusdb import search_items

            try:
                res = search_items(q)
                msg = f"{len(res)} résultat(s)." if res else "Aucun équipement trouvé (ou DofusDB hors ligne et rien en cache)."
            except Exception as e:
                res, msg = [], f"Erreur : {e}"
            self.root.after(0, lambda: self._show_results(res, msg))

        threading.Thread(target=work, daemon=True).start()

    def _show_results(self, res, msg):
        self.results = res
        self.lst.delete(0, "end")
        for r in res:
            self.lst.insert("end", f"{r['name']}  —  niv. {r['level']}  ({r['type']})")
        self.v_status.set(msg)

    def pick(self):
        sel = self.lst.curselection()
        if not sel:
            return
        r = self.results[sel[0]]
        self.v_status.set(f"Chargement de {r['name']}…")

        def work():
            from .dofusdb import load_item

            try:
                item = load_item(r["id"])
                self.root.after(0, lambda: self.set_item(item))
                self.root.after(0, lambda: self.v_status.set("Objet chargé. Renseigne ton jet actuel et tes cibles."))
            except Exception as e:
                self.root.after(0, lambda: self.v_status.set(f"Erreur : {e}"))

        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------------ lignes
    def set_item(self, item: Item):
        self.item = item
        self.v_title.set(f"{item.name} (niv. {item.level}) — renseigne le jet actuel et le jet que tu juges acceptable")
        for w in self.grid.winfo_children():
            w.destroy()
        ttk, tk = self.ttk, self.tk
        for c, h in enumerate(["Stat", "Min", "Max", "Actuel", "Cible acceptable", ""]):
            ttk.Label(self.grid, text=h, font=("Segoe UI", 9, "bold")).grid(row=0, column=c, sticky="w", padx=4)
        self.rows = []
        for i, l in enumerate(item.lines, 1):
            vc, vt = tk.StringVar(value=str(l.current)), tk.StringVar(value=str(l.target))
            label = l.info.label + (" (exo)" if l.exo else "")
            ttk.Label(self.grid, text=label).grid(row=i, column=0, sticky="w", padx=4)
            ttk.Label(self.grid, text=str(l.min)).grid(row=i, column=1, padx=4)
            ttk.Label(self.grid, text=str(l.max)).grid(row=i, column=2, padx=4)
            ttk.Entry(self.grid, textvariable=vc, width=7).grid(row=i, column=3, padx=4)
            ttk.Entry(self.grid, textvariable=vt, width=7).grid(row=i, column=4, padx=4)
            ttk.Button(self.grid, text="✕", width=2, command=lambda l=l: self.remove_line(l)).grid(row=i, column=5)
            self.rows.append((l, vc, vt))

    def remove_line(self, line: Line):
        self.sync()
        self.item.lines = [l for l in self.item.lines if l is not line]
        self.set_item(self.item)

    def add_exo(self):
        if not self.item:
            return
        stat = self.v_exo.get().strip()
        if stat not in STATS or self.item.line(stat):
            self.v_status.set("Stat inconnue ou déjà présente.")
            return
        self.sync()
        self.item.lines.append(Line(stat=stat, min=0, max=0, current=0, target=1 if STATS[stat].weight_per_point >= 30 else STATS[stat].powers[0], exo=True))
        self.set_item(self.item)

    def sync(self) -> bool:
        if not self.item:
            return False
        try:
            for l, vc, vt in self.rows:
                l.current = int(vc.get())
                l.target = int(vt.get())
            return True
        except ValueError:
            self.v_status.set("Les valeurs doivent être des nombres entiers.")
            return False

    def reliquat(self) -> float:
        try:
            return float(self.v_rel.get().replace(",", "."))
        except ValueError:
            return 0.0

    # ------------------------------------------------------------------ calcul
    def compute(self):
        if not self.sync():
            return
        item, rel = self.item, self.reliquat()
        self.out.delete("1.0", "end")
        self.out.insert("end", "Calcul en cours (simulation de 200 FM)…\n")

        def work():
            plan = click_plan(item, rel)
            rep = shopping_list(item, rel, runs=200)
            self.root.after(0, lambda: self._show_compute(plan, rep))

        threading.Thread(target=work, daemon=True).start()

    def _show_compute(self, plan, rep):
        o = self.out
        o.delete("1.0", "end")
        o.insert("end", "RUNES À ACHETER\n")
        o.insert("end", f"  {'Rune':28} {'min':>5} {'conseillé':>10} {'prudent':>8}\n")
        for s in rep:
            o.insert("end", f"  {s.rune:28} {s.minimum:>5} {s.median:>10} {s.p90:>8}\n")
        o.insert("end", f"\nFM terminée dans {rep.success_rate:.0%} des simulations (budget {rep.budget} clics).\n")
        o.insert("end", "min = si tout passe · conseillé = médiane · prudent = 9 fois sur 10\n\n")
        o.insert("end", "ORDRE DE CLICS (si tout passe)\n")
        prev, n, rows = None, 0, []
        for r in plan:
            k = (r.rune.name, r.line.stat)
            if k == prev:
                rows[-1][1] += 1
            else:
                rows.append([r, 1])
            prev = k
        for i, (r, n) in enumerate(rows, 1):
            o.insert("end", f"  {i:>2}. {n} x {r.rune.name} sur {r.line.info.label}  ({r.chances})\n")

    # ------------------------------------------------------------------ fichiers
    def open_json(self):
        from tkinter import filedialog

        p = filedialog.askopenfilename(filetypes=[("Objet JSON", "*.json")])
        if p:
            self.set_item(Item.load(p))

    def save_json(self):
        from tkinter import filedialog

        if not self.sync():
            return
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile=f"{self.item.name}.json")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self.item.to_dict(), f, ensure_ascii=False, indent=2)
            self.v_status.set(f"Enregistré : {p}")

    # ------------------------------------------------------------------ écran / live
    def _calibration(self):
        from .ui import Calibration, calibrate

        if os.path.exists(self.cal_path):
            return Calibration.load(self.cal_path)
        from tkinter import messagebox

        if not messagebox.askokcancel("Calibration", "Première utilisation : il faut repérer la fenêtre de FM.\n\n"
                                      "1. Ouvre la fenêtre de FM en jeu avec ton objet, bien visible.\n"
                                      "2. Clique OK : une capture figée de l'écran s'affiche.\n"
                                      "3. Suis les 5 étapes écrites en haut (rectangle autour des stats, puis 4 clics sur les cases).\n\n"
                                      "Clic droit : annuler une étape · Échap : quitter."):
            return None
        try:
            return calibrate(self.cal_path, master=self.root)
        except SystemExit:
            self.v_status.set("Calibration annulée.")
            return None

    def recalibrate(self):
        try:
            os.remove(self.cal_path)
        except OSError:
            pass
        if self._calibration():
            self.v_status.set("Calibration enregistrée.")

    def read_screen(self):
        if not self.item:
            return
        cal = self._calibration()
        if not cal:
            return
        try:
            from .ocr import read_region

            vals = read_region(cal.stats_bbox)
        except Exception as e:
            self.v_status.set(f"Lecture impossible : {e}")
            return
        n = 0
        for l, vc, _vt in self.rows:
            if l.stat in vals:
                vc.set(str(vals[l.stat]))
                n += 1
        self.v_status.set(f"{n} ligne(s) lue(s) à l'écran.")

    def go_live(self):
        if not self.sync():
            return
        cal = self._calibration()
        if not cal:
            return
        from .ui import LiveApp

        item, rel = self.item, self.reliquat()
        self.root.destroy()
        LiveApp(item, cal, reliquat=rel).run()

    def run(self):
        self.root.mainloop()


def main(calibration_path: str = "calibration.json"):
    from .ui import _dpi_aware

    _dpi_aware()
    Launcher(calibration_path).run()
