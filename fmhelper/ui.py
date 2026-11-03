"""Interface : calibration, overlay (cercle vert) et panneau de contrôle.

Tout est en lecture seule : l'outil regarde l'écran et dessine par-dessus, il ne
clique jamais à ta place et n'interagit pas avec le client Dofus.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

from .model import ForgeSession, Item
from .planner import recommend, shopping_list

TIER_COL = {"base": 0, "pa": 1, "ra": 2}


def _dpi_aware():
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


@dataclass
class Calibration:
    """Positions à l'écran (pixels physiques).

    stats_bbox : zone (left, top, width, height) contenant les lignes de stats.
    cell0 : centre de la case « Rune » de la 1re ligne.
    col_dx : décalage horizontal entre colonnes Rune -> Pa -> Ra.
    row_dy : décalage vertical entre deux lignes.
    """

    stats_bbox: Tuple[int, int, int, int]
    cell0: Tuple[int, int]
    col_dx: Tuple[int, int]
    row_dy: int
    radius: int = 18

    def cell(self, row: int, tier: str) -> Tuple[int, int]:
        x, y = self.cell0
        col = TIER_COL.get(tier, 0)
        dx = 0 if col == 0 else sum(self.col_dx[:col])
        return x + dx, y + row * self.row_dy

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Calibration":
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls(tuple(d["stats_bbox"]), tuple(d["cell0"]), tuple(d["col_dx"]), int(d["row_dy"]), int(d.get("radius", 18)))


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

STEPS = [
    "1/5 — Trace un rectangle (clic-glisser) autour des LIGNES DE STATS de l'objet dans la fenêtre de FM.",
    "2/5 — Clique au centre de la case « Rune » (rune de base) de la 1re ligne.",
    "3/5 — Clique au centre de la case « Pa » de la 1re ligne.",
    "4/5 — Clique au centre de la case « Ra » de la 1re ligne.",
    "5/5 — Clique au centre de la case « Rune » de la 2e ligne.",
]


def calibrate(path: str = "calibration.json") -> Calibration:
    """Affiche une capture plein écran et demande 5 repères à l'utilisateur."""
    _dpi_aware()
    import tkinter as tk

    import mss
    from PIL import Image, ImageTk

    with (mss.MSS() if hasattr(mss, "MSS") else mss.mss()) as sct:
        mon = sct.monitors[1]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.rgb)

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    cv = tk.Canvas(root, highlightthickness=0, cursor="crosshair")
    cv.pack(fill="both", expand=True)
    photo = ImageTk.PhotoImage(img)
    cv.create_image(0, 0, image=photo, anchor="nw")
    banner = cv.create_text(20, 20, anchor="nw", text=STEPS[0], fill="#00ff66", font=("Segoe UI", 18, "bold"))
    cv.create_text(20, 55, anchor="nw", text="Échap pour annuler", fill="#ffffff", font=("Segoe UI", 12))

    state: Dict = {"step": 0, "start": None, "rect": None, "pts": []}
    ox, oy = mon["left"], mon["top"]

    def on_press(e):
        if state["step"] == 0:
            state["start"] = (e.x, e.y)
            state["rect"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#00ff66", width=2)

    def on_drag(e):
        if state["step"] == 0 and state["rect"]:
            x0, y0 = state["start"]
            cv.coords(state["rect"], x0, y0, e.x, e.y)

    def on_release(e):
        if state["step"] == 0:
            x0, y0 = state["start"]
            l, t = min(x0, e.x), min(y0, e.y)
            w, h = abs(e.x - x0), abs(e.y - y0)
            if w < 10 or h < 10:
                return
            state["bbox"] = (l + ox, t + oy, w, h)
        else:
            state["pts"].append((e.x + ox, e.y + oy))
            cv.create_oval(e.x - 6, e.y - 6, e.x + 6, e.y + 6, outline="#00ff66", width=3)
        state["step"] += 1
        if state["step"] >= len(STEPS):
            root.destroy()
        else:
            cv.itemconfig(banner, text=STEPS[state["step"]])

    cv.bind("<ButtonPress-1>", on_press)
    cv.bind("<B1-Motion>", on_drag)
    cv.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()

    if state["step"] < len(STEPS):
        raise SystemExit("Calibration annulée.")
    rune0, pa0, ra0, rune1 = state["pts"]
    cal = Calibration(
        stats_bbox=state["bbox"],
        cell0=rune0,
        col_dx=(pa0[0] - rune0[0], ra0[0] - pa0[0]),
        row_dy=rune1[1] - rune0[1],
    )
    cal.save(path)
    return cal


# ---------------------------------------------------------------------------
# Overlay
# ---------------------------------------------------------------------------

class Overlay:
    """Surbrillance toujours au premier plan, qui laisse passer les clics.

    Windows : fenêtre plein écran transparente (couleur clé) + style
    WS_EX_TRANSPARENT, on y dessine un cercle vert et le nom de la rune.
    Autres systèmes : quatre fines barres vertes forment un cadre autour de la
    case (pas besoin de transparence ; les clics passent à l'intérieur du cadre).
    """

    KEY = "#ff00fe"  # couleur rendue transparente

    def __init__(self, root):
        import tkinter as tk

        self.tk = tk
        self.full = sys.platform == "win32"
        if self.full:
            self.win = tk.Toplevel(root)
            self.win.overrideredirect(True)
            self.win.attributes("-topmost", True)
            sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
            self.win.geometry(f"{sw}x{sh}+0+0")
            self.win.configure(bg=self.KEY)
            self.win.attributes("-transparentcolor", self.KEY)
            self.cv = tk.Canvas(self.win, bg=self.KEY, highlightthickness=0)
            self.cv.pack(fill="both", expand=True)
            self.win.update_idletasks()
            self._click_through()
        else:
            self.bars = []
            for _ in range(4):
                b = tk.Toplevel(root)
                b.overrideredirect(True)
                b.attributes("-topmost", True)
                b.configure(bg="#00e676")
                b.withdraw()
                self.bars.append(b)

    def _click_through(self):
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
            GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT = -20, 0x80000, 0x20
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception:
            pass

    def show(self, x: int, y: int, r: int, color: str = "#00e676", label: str = ""):
        if self.full:
            self.cv.delete("all")
            self.cv.create_oval(x - r, y - r, x + r, y + r, outline=color, width=4)
            if label:
                self.cv.create_text(x + r + 8, y, text=label, fill=color, anchor="w", font=("Segoe UI", 11, "bold"))
            self.win.lift()
            return
        t = 4
        rects = [(x - r, y - r, 2 * r, t), (x - r, y + r - t, 2 * r, t), (x - r, y - r, t, 2 * r), (x + r - t, y - r, t, 2 * r)]
        for b, (bx, by, w, h) in zip(self.bars, rects):
            b.withdraw()  # certains gestionnaires de fenêtres ignorent un déplacement de fenêtre visible
            b.geometry(f"{w}x{h}+{bx}+{by}")
            b.deiconify()
            b.lift()
        self.bars[0].update_idletasks()

    def hide(self):
        if self.full:
            self.cv.delete("all")
        else:
            for b in self.bars:
                b.withdraw()


# ---------------------------------------------------------------------------
# Mode live
# ---------------------------------------------------------------------------

class LiveApp:
    def __init__(self, item: Item, cal: Calibration, reliquat: float = 0.0, interval_ms: int = 400,
                 log_path: str = "historique_fm.csv", tesseract_cmd: Optional[str] = None, lang: str = "fra"):
        _dpi_aware()
        import tkinter as tk

        self.tk = tk
        self.session = ForgeSession(item, reliquat)
        self.cal = cal
        self.interval = interval_ms
        self.log_path = log_path
        self.tess = tesseract_cmd
        self.lang = lang
        self.paused = False
        self.last_read: Optional[Dict[str, int]] = None
        self.row_order: List[str] = [l.stat for l in item.lines]
        self.rec = None

        self.root = tk.Tk()
        self.root.title("Aide FM — lecture seule")
        self.root.attributes("-topmost", True)
        self.root.geometry("+20+20")
        self.overlay = Overlay(self.root)

        self.v_rec = tk.StringVar()
        self.v_state = tk.StringVar()
        self.v_last = tk.StringVar()
        tk.Label(self.root, text=item.name, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        tk.Label(self.root, textvariable=self.v_rec, fg="#0a7d32", font=("Segoe UI", 11, "bold"), wraplength=380, justify="left").pack(anchor="w", padx=8)
        tk.Label(self.root, textvariable=self.v_state, font=("Consolas", 10), justify="left").pack(anchor="w", padx=8)
        tk.Label(self.root, textvariable=self.v_last, fg="#555", wraplength=380, justify="left").pack(anchor="w", padx=8)
        bar = tk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=6)
        tk.Button(bar, text="Pause", command=self.toggle).pack(side="left")
        tk.Button(bar, text="Reliquat −1", command=lambda: self.adj(-1)).pack(side="left")
        tk.Button(bar, text="+1", command=lambda: self.adj(1)).pack(side="left")
        tk.Button(bar, text="=0", command=lambda: self.adj(None)).pack(side="left")
        tk.Button(bar, text="Liste d'achats", command=self.show_shopping).pack(side="left")
        self.refresh()

    # -- actions --
    def toggle(self):
        self.paused = not self.paused
        if self.paused:
            self.overlay.hide()

    def adj(self, d):
        self.session.reliquat = 0.0 if d is None else max(0.0, self.session.reliquat + d)
        self.refresh()

    def show_shopping(self):
        tk = self.tk
        top = tk.Toplevel(self.root)
        top.title("Liste d'achats (estimation)")
        txt = tk.Text(top, width=60, height=20, font=("Consolas", 10))
        txt.pack()
        txt.insert("end", f"{'Rune':28} {'min':>5} {'médiane':>8} {'p90':>6}\n")
        rep = shopping_list(self.session.item, self.session.reliquat, runs=150)
        for s in rep:
            txt.insert("end", f"{s.rune:28} {s.minimum:>5} {s.median:>8} {s.p90:>6}\n")
        txt.insert("end", f"\nFM terminée dans {rep.success_rate:.0%} des simulations (budget {rep.budget} clics).\n")

    # -- boucle --
    def tick(self):
        if not self.paused:
            try:
                from .ocr import read_region

                vals = read_region(self.cal.stats_bbox, lang=self.lang, tesseract_cmd=self.tess)
            except Exception as e:  # OCR indisponible : on continue sans planter
                self.v_last.set(f"Lecture écran impossible : {e}")
                vals = None
            if vals:
                known = [k for k in vals if self.session.item.line(k)]
                stable = vals == self.last_read
                self.last_read = vals
                if stable and len(known) >= max(1, len(self.session.item.lines) // 2):
                    self.row_order = list(vals.keys())
                    rune = self.rec.rune if self.rec else None
                    obs = self.session.observe(vals, rune=rune)
                    if obs:
                        self.log(obs)
                        self.v_last.set(f"Dernier coup : {obs.outcome} {obs.rune.name if obs.rune else ''} — reliquat {obs.reliquat_after:g}. {obs.note}")
                    self.refresh()
        self.root.after(self.interval, self.tick)

    def refresh(self):
        s = self.session
        self.rec = recommend(s)
        lines = [f"{l.info.label[:22]:22} {l.current:>5} / {l.target:<5}" for l in s.item.lines]
        self.v_state.set("\n".join(lines) + f"\nReliquat estimé : {s.reliquat:g}")
        if self.rec is None:
            self.v_rec.set("Objet terminé selon tes cibles 🎉")
            self.overlay.hide()
            return
        self.v_rec.set(f"➜ {self.rec}")
        if self.paused:
            return
        stat = self.rec.line.stat
        if stat in self.row_order and not self.rec.line.exo:
            row = self.row_order.index(stat)
            x, y = self.cal.cell(row, self.rec.rune.tier)
            self.overlay.show(x, y, self.cal.radius, label=self.rec.rune.name)
        else:
            self.overlay.hide()
            self.v_rec.set(self.v_rec.get() + "\n(Exo : glisse la rune depuis l'inventaire dans la case de rune.)")

    def log(self, obs):
        new = not os.path.exists(self.log_path)
        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            if new:
                w.writerow(["horodatage", "rune", "issue", "delta_poids", "reliquat_avant", "reliquat_apres", "sc_estime", "ambigu"])
            sc = self.rec.chances.sc if self.rec else ""
            w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), obs.rune.name if obs.rune else "", obs.outcome,
                        obs.delta_weight, obs.reliquat_before, obs.reliquat_after, sc, obs.ambiguous])

    def run(self):
        self.root.after(self.interval, self.tick)
        self.root.mainloop()
