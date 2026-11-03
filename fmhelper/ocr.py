"""Lecture de la fenêtre de forgemagie par capture d'écran + OCR.

Lecture seule : on capture une zone de l'écran (mss) et on la passe à
Tesseract (pytesseract). Aucune interaction avec le client du jeu.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .runes import match_stat

_LINE_RE = re.compile(r"^\s*([+\-−–]?)\s*(\d{1,4})\s*(%?)\s*(.+?)\s*$")


def parse_lines(text: str) -> List[Tuple[str, int]]:
    """Transforme le texte OCR en liste (clé de stat, valeur).

    Accepte « 245 Vitalité », « +12 Force », « -5 Sagesse », « 8% Résistance Feu ».
    Les lignes non reconnues sont ignorées.
    """
    out = []
    for raw in text.splitlines():
        raw = raw.replace("|", " ").strip()
        if not raw:
            continue
        m = _LINE_RE.match(raw)
        if not m:
            continue
        sign, num, pct, label = m.groups()
        label = re.sub(r"[^\w%' \-àâäéèêëîïôöùûüç]", " ", label, flags=re.I).strip()
        if pct:
            label = "% " + label
        key = match_stat(label)
        if key is None:
            continue
        val = int(num)
        if sign in ("-", "−", "–"):
            val = -val
        out.append((key, val))
    return out


def values_dict(pairs: List[Tuple[str, int]]) -> Dict[str, int]:
    d: Dict[str, int] = {}
    for k, v in pairs:
        d.setdefault(k, v)  # première occurrence
    return d


def grab(bbox: Tuple[int, int, int, int]):
    """Capture la zone (left, top, width, height) et renvoie une image PIL."""
    import mss
    from PIL import Image

    left, top, width, height = bbox
    with (mss.MSS() if hasattr(mss, "MSS") else mss.mss()) as sct:
        shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
        return Image.frombytes("RGB", shot.size, shot.rgb)


def preprocess(img, scale: int = 2, invert: Optional[bool] = None):
    """Agrandit, passe en niveaux de gris et binarise (texte clair sur fond sombre en jeu)."""
    from PIL import ImageOps

    g = ImageOps.grayscale(img)
    g = g.resize((g.width * scale, g.height * scale))
    if invert is None:
        hist = g.histogram()
        dark = sum(hist[:128]) > sum(hist[128:])
        invert = dark
    if invert:
        g = ImageOps.invert(g)
    return g.point(lambda p: 255 if p > 150 else 0)


def find_tesseract() -> Optional[str]:
    """Cherche tesseract : PATH, puis emplacements d'installation Windows habituels."""
    import os
    import shutil

    p = shutil.which("tesseract")
    if p:
        return p
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        cand = os.path.join(base, "Tesseract-OCR", "tesseract.exe")
        if base and os.path.exists(cand):
            return cand
    return None


def read_region(bbox, lang: str = "fra", tesseract_cmd: Optional[str] = None) -> Dict[str, int]:
    import pytesseract

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        found = find_tesseract()
        if found:
            pytesseract.pytesseract.tesseract_cmd = found
    img = preprocess(grab(bbox))
    text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
    return values_dict(parse_lines(text))
