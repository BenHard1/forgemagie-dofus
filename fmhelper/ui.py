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
from .alerts import ALERT_COLOR, OUTCOME_COLORS, detect_alerts, tier_chances
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
    reliquat_bbox: Optional[Tuple[int, int, int, int]] = None  # zone « reliquat : N » du jeu

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
        rb = d.get("reliquat_bbox")
        return cls(tuple(d["stats_bbox"]), tuple(d["cell0"]), tuple(d["col_dx"]), int(d["row_dy"]),
                   int(d.get("radius", 18)), tuple(rb) if rb else None)


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

STEPS = [
    "Étape 1/6 — Maintiens le clic gauche et trace un rectangle autour de la colonne « Effets / Carac. » "
    "(valeur + nom de chaque stat, de la 1re à la dernière ligne). Pas les colonnes Min / Max.",
    "Étape 2/6 — Clique au centre de la 1re case de rune de la 1re ligne (la case sans titre, juste à gauche de « Pa »).",
    "Étape 3/6 — Clique au centre de la case « Pa » de la 1re ligne.",
    "Étape 4/6 — Clique au centre de la case « Ra » de la 1re ligne.",
    "Étape 5/6 — Clique au centre de la 1re case de rune de la 2e ligne.",
    "Étape 6/6 — Trace un rectangle autour du texte « reliquat : … » en haut de la fenêtre.",
]
RECT_STEPS = (0, 5)
HELP = "Clic droit : annuler la dernière étape   ·   Échap : quitter sans enregistrer"


def _grab_screen(point: Optional[Tuple[int, int]] = None):
    """Capture l'écran qui contient `point` (la souris), sinon l'écran principal."""
    import mss
    from PIL import Image

    with (mss.MSS() if hasattr(mss, "MSS") else mss.mss()) as sct:
        mon = dict(sct.monitors[1])
        if point is not None:
            for m in sct.monitors[1:]:
                if m["left"] <= point[0] < m["left"] + m["width"] and m["top"] <= point[1] < m["top"] + m["height"]:
                    mon = dict(m)
                    break
        shot = sct.grab(mon)
        return mon, Image.frombytes("RGB", shot.size, shot.rgb)


def calibrate(path: str = "calibration.json", master=None) -> Calibration:
    """Affiche une capture (figée) de l'écran principal et demande 5 repères.

    master : fenêtre Tk existante (fenêtre de lancement). Sans elle, une
    fenêtre Tk est créée. On n'ouvre jamais deux Tk() à la fois : l'image de la
    capture serait rattachée à la mauvaise fenêtre et l'écran resterait gris.
    Les coordonnées sont converties en pixels réels de l'écran, même avec une
    mise à l'échelle Windows (125 %, 150 %...).
    """
    _dpi_aware()
    import time
    import tkinter as tk

    from PIL import ImageTk

    own_root = master is None
    if own_root:
        root = tk.Tk()
        root.withdraw()
    else:
        root = master
        root.withdraw()
        root.update()
        time.sleep(0.4)  # laisse la fenêtre de lancement disparaître avant la capture

    mon, img = _grab_screen(root.winfo_pointerxy())
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    # Fenêtre posée sur l'écran capturé (écran où se trouve la souris)
    win.geometry(f"{mon['width']}x{mon['height']}+{mon['left']}+{mon['top']}")
    win.attributes("-topmost", True)
    win.update_idletasks()
    sw, sh = max(win.winfo_width(), 1), max(win.winfo_height(), 1)
    if (sw, sh) == (1, 1):
        sw, sh = mon["width"], mon["height"]
    # Échelle entre les pixels Tk et les pixels réels capturés (mise à l'échelle Windows)
    fx, fy = img.width / sw, img.height / sh
    shown = img if (fx, fy) == (1, 1) else img.resize((sw, sh))
    photo = ImageTk.PhotoImage(shown, master=win)
    cv = tk.Canvas(win, width=sw, height=sh, highlightthickness=0, cursor="crosshair")
    cv.pack(fill="both", expand=True)
    cv.create_image(0, 0, image=photo, anchor="nw")
    cv.image = photo  # garde une référence

    box = cv.create_rectangle(10, 10, 10, 10, fill="#000000", outline="#00ff66", width=2)
    banner = cv.create_text(24, 20, anchor="nw", text=STEPS[0], fill="#00ff66", font=("Segoe UI", 16, "bold"), width=sw - 60)
    helpt = cv.create_text(24, 60, anchor="nw", text=HELP, fill="#ffffff", font=("Segoe UI", 11))

    def place_banner():
        x0, y0, x1, y1 = cv.bbox(banner)
        cv.coords(helpt, 24, y1 + 6)
        hx0, hy0, hx1, hy1 = cv.bbox(helpt)
        cv.coords(box, 12, 10, max(x1, hx1) + 12, hy1 + 10)

    place_banner()
    state: Dict = {"step": 0, "start": None, "rect": None, "rects": [], "pts": [], "marks": [], "done": False}
    ox, oy = mon["left"], mon["top"]

    def real(x, y):
        return int(round(x * fx)) + ox, int(round(y * fy)) + oy

    def set_step(n):
        state["step"] = n
        if n >= len(STEPS):
            state["done"] = True
            win.destroy()
            return
        cv.itemconfig(banner, text=STEPS[n])
        place_banner()

    def on_press(e):
        if state["step"] in RECT_STEPS:
            if state["rect"]:
                cv.delete(state["rect"])
            state["start"] = (e.x, e.y)
            state["rect"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#00ff66", width=3)

    def on_drag(e):
        if state["step"] in RECT_STEPS and state["rect"]:
            x0, y0 = state["start"]
            cv.coords(state["rect"], x0, y0, e.x, e.y)

    def on_release(e):
        n = state["step"]
        if n in RECT_STEPS:
            if not state["start"]:
                return
            x0, y0 = state["start"]
            if abs(e.x - x0) < 10 or abs(e.y - y0) < 6:
                cv.itemconfig(banner, text=STEPS[n] + "  (rectangle trop petit, recommence)")
                return
            l, t = real(min(x0, e.x), min(y0, e.y))
            r, b = real(max(x0, e.x), max(y0, e.y))
            state["bbox" if n == 0 else "rbox"] = (l, t, r - l, b - t)
            state["rects"].append(state["rect"])
            state["rect"] = None
            state["start"] = None
        else:
            state["pts"].append(real(e.x, e.y))
            state["marks"].append(cv.create_oval(e.x - 8, e.y - 8, e.x + 8, e.y + 8, outline="#00ff66", width=3))
        set_step(n + 1)

    def undo(_e=None):
        n = state["step"]
        if n == 0:
            return
        prev = n - 1
        if prev in RECT_STEPS:
            if state["rects"]:
                cv.delete(state["rects"].pop())
        elif state["pts"]:
            state["pts"].pop()
            cv.delete(state["marks"].pop())
        set_step(prev)

    cv.bind("<ButtonPress-1>", on_press)
    cv.bind("<B1-Motion>", on_drag)
    cv.bind("<ButtonRelease-1>", on_release)
    cv.bind("<ButtonPress-3>", undo)
    win.bind("<Escape>", lambda e: win.destroy())
    win.update()
    win.lift()
    win.focus_force()
    try:
        win.grab_set()  # tous les clics vont à la fenêtre de calibration
    except tk.TclError:
        pass
    root.wait_window(win)
    if own_root:
        root.destroy()
    else:
        root.deiconify()

    if not state["done"]:
        raise SystemExit("Calibration annulée.")
    rune0, pa0, ra0, rune1 = state["pts"]
    cal = Calibration(
        stats_bbox=state["bbox"],
        cell0=rune0,
        col_dx=(pa0[0] - rune0[0], ra0[0] - pa0[0]),
        row_dy=rune1[1] - rune0[1],
        radius=max(10, min(30, abs(rune1[1] - rune0[1]) // 2 - 2)),
        reliquat_bbox=state.get("rbox"),
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
            # Couvre tous les écrans (bureau virtuel) : le jeu peut être sur un 2e écran
            self.ox, self.oy, sw, sh = 0, 0, self.win.winfo_screenwidth(), self.win.winfo_screenheight()
            try:
                import mss

                with (mss.MSS() if hasattr(mss, "MSS") else mss.mss()) as sct:
                    v = sct.monitors[0]
                    self.ox, self.oy, sw, sh = v["left"], v["top"], v["width"], v["height"]
            except Exception:
                pass
            self.win.geometry(f"{sw}x{sh}+{self.ox}+{self.oy}")
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
            # Exclut l'overlay des captures d'écran (Windows 10 2004+) : l'OCR ne lit
            # jamais nos propres textes (SC 47 %...) par-dessus la fenêtre de FM.
            WDA_EXCLUDEFROMCAPTURE = 0x11
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def show(self, x: int, y: int, r: int, color: str = "#00e676", label: str = "",
             extras: Optional[List[Tuple[int, int, str]]] = None, alert: str = ""):
        """Cadre sur la rune à cliquer, texte à côté, petites étiquettes sur les autres cases
        (Windows) et bandeau d'alerte."""
        if self.full:
            x, y = x - self.ox, y - self.oy
            extras = [(ex - self.ox, ey - self.oy, t) for ex, ey, t in (extras or [])]
            self.cv.delete("all")
            self.cv.create_oval(x - r, y - r, x + r, y + r, outline=color, width=5)
            if label:
                self.cv.create_text(x + r + 8, y, text=label, fill=color, anchor="w", font=("Segoe UI", 11, "bold"))
            for ex, ey, txt in extras or []:
                self.cv.create_text(ex, ey + r + 2, text=txt, fill="#ffffff", anchor="n", font=("Segoe UI", 8))
            if alert:
                self._banner(x, y - 3 * r, alert)
            self.win.lift()
            return
        t = 5
        rects = [(x - r, y - r, 2 * r, t), (x - r, y + r - t, 2 * r, t), (x - r, y - r, t, 2 * r), (x + r - t, y - r, t, 2 * r)]
        for b, (bx, by, w, h) in zip(self.bars, rects):
            b.configure(bg=color)
            b.withdraw()  # certains gestionnaires de fenêtres ignorent un déplacement de fenêtre visible
            b.geometry(f"{w}x{h}+{bx}+{by}")
            b.deiconify()
            b.lift()
        self.bars[0].update_idletasks()

    def _banner(self, x: int, y: int, text: str):
        tid = self.cv.create_text(x, max(y, 20), text=text, fill="#ffffff", anchor="s", font=("Segoe UI", 13, "bold"), width=500)
        x0, y0, x1, y1 = self.cv.bbox(tid)
        rid = self.cv.create_rectangle(x0 - 8, y0 - 6, x1 + 8, y1 + 6, fill="#ff1744", outline="")
        self.cv.tag_lower(rid, tid)

    def alert_only(self, x: int, y: int, text: str):
        if self.full:
            x, y = x - self.ox, y - self.oy
            self.cv.delete("all")
            self._banner(x, y, text)
            self.win.lift()

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
    def __init__(self, item: Item, cal: Calibration, reliquat: float = 0.0, interval_ms: int = 100,
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
        self.last_outcome = None
        self.alerts: List[str] = []
        self.go_back = False
        self.synced = False
        self.zero_reads = 0
        self.prev_sig = None
        self.done_sig = None
        self.read_info = "En attente de la première lecture"
        from concurrent.futures import ThreadPoolExecutor

        self.pool = ThreadPoolExecutor(max_workers=1)

        self.root = tk.Tk()
        self.root.title("Aide FM — lecture seule")
        self.root.attributes("-topmost", True)
        self.root.geometry("+20+20")
        self.overlay = Overlay(self.root)

        self.v_rec = tk.StringVar()
        self.v_state = tk.StringVar()
        self.v_last = tk.StringVar()
        self.v_chances = tk.StringVar()
        self.v_alert = tk.StringVar()
        self.v_read = tk.StringVar(value="En attente de la première lecture de l'écran…")
        tk.Label(self.root, text=item.name, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        self.alert_frame = tk.Frame(self.root, bg=ALERT_COLOR)
        tk.Label(self.alert_frame, textvariable=self.v_alert, bg=ALERT_COLOR, fg="white", font=("Segoe UI", 11, "bold"),
                 wraplength=330, justify="left").pack(side="left", padx=6, pady=4)
        tk.Button(self.alert_frame, text="OK", command=self.clear_alerts).pack(side="right", padx=6)
        tk.Button(self.alert_frame, text="Changer d'objet", command=self.back).pack(side="right")
        self.anchor = tk.Label(self.root, textvariable=self.v_rec, fg="#0a7d32", font=("Segoe UI", 11, "bold"), wraplength=380, justify="left")
        self.anchor.pack(anchor="w", padx=8)
        tk.Label(self.root, textvariable=self.v_chances, font=("Consolas", 10), justify="left").pack(anchor="w", padx=8)
        tk.Label(self.root, text="Chances estimées avec la formule DoFocus (approximation, pas la formule officielle).",
                 fg="#888", font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        tk.Label(self.root, textvariable=self.v_state, font=("Consolas", 10), justify="left").pack(anchor="w", padx=8)
        tk.Label(self.root, textvariable=self.v_last, fg="#555", wraplength=380, justify="left").pack(anchor="w", padx=8)
        tk.Label(self.root, textvariable=self.v_read, fg="#888", font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        bar = tk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=6)
        tk.Button(bar, text="Pause", command=self.toggle).pack(side="left")
        tk.Button(bar, text="Reliquat −1", command=lambda: self.adj(-1)).pack(side="left")
        tk.Button(bar, text="+1", command=lambda: self.adj(1)).pack(side="left")
        tk.Button(bar, text="=0", command=lambda: self.adj(None)).pack(side="left")
        tk.Button(bar, text="Liste d'achats", command=self.show_shopping).pack(side="left")
        tk.Button(bar, text="Resynchroniser", command=lambda: self.resync()).pack(side="left")
        tk.Button(bar, text="⟵ Changer d'objet", command=self.back).pack(side="right")
        self.refresh()

    # -- actions --
    def toggle(self):
        self.paused = not self.paused
        if self.paused:
            self.overlay.hide()

    def back(self):
        """Arrête le suivi en direct et revient à la fenêtre de choix de l'équipement."""
        self.go_back = True
        self.paused = True
        try:
            self.overlay.hide()
        finally:
            self.root.destroy()

    def clear_alerts(self):
        self.alerts = []
        self.alert_frame.pack_forget()
        self.refresh()

    def raise_alerts(self, alerts: List[str]):
        if not alerts:
            return
        self.alerts = alerts
        self.v_alert.set("⚠ " + "\n⚠ ".join(alerts))
        self.alert_frame.pack(fill="x", padx=8, pady=4, before=self.anchor)

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
        """Relit l'écran, met à jour l'état et la recommandation.

        Se replanifie toujours (finally) : une erreur ponctuelle ne doit jamais
        arrêter le suivi. Les erreurs sont affichées et écrites dans fmhelper_erreur.log.
        """
        try:
            if not self.paused:
                self._read_and_update()
        except Exception as e:
            import traceback

            self.v_last.set(f"Erreur pendant le suivi (le suivi continue) : {e}")
            try:
                with open("fmhelper_erreur.log", "a", encoding="utf-8") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
            except OSError:
                pass
        finally:
            self.root.after(self.interval, self.tick)

    def _read(self, img=None) -> Optional[Dict[str, int]]:
        from . import ocr

        try:
            vals = ocr.ocr_stats(img, lang=self.lang, tesseract_cmd=self.tess) if img is not None else \
                ocr.read_region(self.cal.stats_bbox, lang=self.lang, tesseract_cmd=self.tess)
        except Exception as e:  # OCR indisponible : on continue sans planter
            msg = str(e)
            if "traineddata" in msg or "Failed loading language" in msg:
                msg = ("langue française de Tesseract absente. Réinstalle Tesseract en cochant "
                       "« French » (Additional language data), ou vérifie ta connexion pour le téléchargement automatique.")
            self.v_last.set(f"Lecture écran impossible : {msg}")
            return None
        if ocr.LANG_NOTE:
            self.v_last.set(ocr.LANG_NOTE)
            ocr.LANG_NOTE = ""
        try:
            with open("fmhelper_ocr_derniere_lecture.txt", "w", encoding="utf-8") as f:
                f.write(ocr.LAST_TEXT)
        except OSError:
            pass
        # On ne garde que les lignes de l'objet (le bruit d'OCR ne crée pas de fausses lignes)
        known = {k: v for k, v in vals.items() if self.session.item.line(k)}
        self.read_info = f"Lecture {time.strftime('%H:%M:%S')} : {len(known)}/{len(self.session.item.lines)} lignes reconnues"
        self.v_read.set(self.read_info)
        if not known:
            self.zero_reads += 1
            if self.zero_reads >= 3:
                self.v_last.set("Aucune ligne de l'objet reconnue : la zone lue ne montre pas la fenêtre de FM "
                                "(fenêtre déplacée, autre écran, ou une fenêtre passe devant). Vérifie que la fenêtre "
                                "de FM est visible, sinon reviens en arrière et clique sur « Recalibrer ».")
        else:
            self.zero_reads = 0
        return known

    def _read_game_reliquat(self) -> Optional[float]:
        if not self.cal.reliquat_bbox:
            return None
        try:
            from .ocr import read_reliquat

            return read_reliquat(self.cal.reliquat_bbox, tesseract_cmd=self.tess)
        except Exception:
            return None

    def _read_and_update(self):
        """Capture (rapide) à chaque tick ; OCR seulement quand l'image a changé
        puis est restée stable un tick (fin de l'animation du jeu)."""
        from . import ocr

        img = ocr.grab(self.cal.stats_bbox)
        sig = ocr.image_signature(img)
        if sig == self.done_sig:
            # rien de neuf à l'écran : on montre juste que la surveillance tourne
            self.v_read.set(f"{self.read_info} · surveillance {time.strftime('%H:%M:%S')}")
            return
        if sig != self.prev_sig:
            self.prev_sig = sig  # l'écran bouge encore : on attend un tick
            return
        # Image stable et nouvelle : OCR des stats et du reliquat en parallèle
        rel_future = None
        if self.cal.reliquat_bbox:
            rel_img = ocr.grab(self.cal.reliquat_bbox)
            rel_future = self.pool.submit(ocr.ocr_reliquat, rel_img, self.tess)
        vals = self._read(img)
        game_rel = None
        if rel_future is not None:
            try:
                game_rel = rel_future.result(timeout=5)
            except Exception:
                game_rel = None
        self.done_sig = sig
        if not vals or len(vals) < max(1, len(self.session.item.lines) // 2):
            return
        self.last_read = vals
        self.row_order = [k for k in (self.ocr_order() or vals.keys())]
        if not self.synced:
            self.resync(vals, game_rel)
            return
        rune = self.rec.rune if self.rec else None
        before = self.session.item.values()
        obs = self.session.observe(vals, rune=rune)
        if obs is None:
            return
        if game_rel is not None:  # le jeu affiche le vrai reliquat : il remplace l'estimation
            obs.reliquat_after = game_rel
            self.session.reliquat = game_rel
            if obs.ambiguous and obs.rune is not None and abs(obs.reliquat_before - game_rel) < 1e-6:
                obs.outcome, obs.ambiguous, obs.note = "SC", False, ""
        self.log(obs)
        self.last_outcome = obs.outcome
        self.v_last.set(f"Dernier coup : {obs.outcome} {obs.rune.name if obs.rune else ''} — reliquat {obs.reliquat_after:g}. {obs.note}")
        self.refresh()
        self.raise_alerts(detect_alerts(before, self.session, obs, target_reached=self.rec is None))
        self.refresh()

    def ocr_order(self) -> List[str]:
        """Ordre des lignes à l'écran, d'après le dernier texte lu."""
        from . import ocr

        order = []
        for k, _v in ocr.parse_lines(ocr.LAST_TEXT):
            if self.session.item.line(k) and k not in order:
                order.append(k)
        return order

    def resync(self, vals: Optional[Dict[str, int]] = None, game_rel: Optional[float] = None):
        """Prend les valeurs lues comme état de départ, sans compter de coup."""
        if vals is None:
            vals = self._read() or {}
            game_rel = self._read_game_reliquat()
            self.done_sig = None
        for k, v in vals.items():
            l = self.session.item.line(k)
            if l is not None:
                l.current = v
        self.synced = bool(vals)
        if game_rel is not None:
            self.session.reliquat = game_rel
        if vals:
            self.last_read = vals
            self.v_last.set("Jet synchronisé avec l'écran. Tu peux cliquer sur la rune entourée.")
        self.refresh()

    def refresh(self):
        s = self.session
        self.rec = recommend(s)
        lines = [f"{l.info.label[:22]:22} {l.current:>5} / {l.target:<5}" for l in s.item.lines]
        self.v_state.set("\n".join(lines) + f"\nReliquat estimé : {s.reliquat:g}")
        alert = " · ".join(self.alerts)
        bx, by = self.cal.stats_bbox[0] + self.cal.stats_bbox[2] // 2, self.cal.stats_bbox[1]
        if self.rec is None:
            self.v_rec.set("Objet terminé selon tes cibles 🎉")
            self.v_chances.set("")
            self.overlay.hide()
            if alert and not self.paused:
                self.overlay.alert_only(bx, by, alert)
            return
        self.v_rec.set(f"➜ {self.rec}")
        line = self.rec.line
        tiers = tier_chances(s.item, line)
        self.v_chances.set("\n".join(
            f"{'➜' if r.tier == self.rec.rune.tier else ' '} {r.name:20} SC {c.sc:4.0%}  SN {c.sn:4.0%}  EC {c.ec:4.0%}"
            + ("  (over)" if line.current + r.power > max(line.max, 0) else "")
            for r, c in tiers))
        if self.paused:
            return
        if line.stat in self.row_order and not line.exo:
            row = self.row_order.index(line.stat)
            x, y = self.cal.cell(row, self.rec.rune.tier)
            ch = self.rec.chances
            label = f"{self.rec.rune.name}  SC {ch.sc:.0%} · SN {ch.sn:.0%} · EC {ch.ec:.0%}"
            extras = []
            for r, c in tiers:
                if r.tier != self.rec.rune.tier:
                    ex, ey = self.cal.cell(row, r.tier)
                    extras.append((ex, ey, f"SC {c.sc:.0%}"))
            self.overlay.show(x, y, self.cal.radius, color=OUTCOME_COLORS.get(self.last_outcome, "#00e676"),
                              label=label, extras=extras, alert=alert)
        else:
            self.overlay.hide()
            if alert:
                self.overlay.alert_only(bx, by, alert)
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

    def run(self) -> bool:
        """Lance la boucle. Renvoie True si l'utilisateur a demandé à changer d'objet."""
        self.root.after(self.interval, self.tick)
        self.root.mainloop()
        return self.go_back
