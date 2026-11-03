"""Lecture de la fenêtre de forgemagie par capture d'écran + OCR.

Lecture seule : on capture une zone de l'écran (mss) et on la passe à
Tesseract (pytesseract). Aucune interaction avec le client du jeu.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .runes import match_stat

_NUM_RE = re.compile(r"([+\-−–]?)\s?(\d{1,4})")
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}")


def parse_lines(text: str) -> List[Tuple[str, int]]:
    """Transforme le texte OCR en liste (clé de stat, valeur).

    Accepte « 245 Vitalité », « +12 Force », « -5 Sagesse », « 8% Résistance Feu »,
    et les lignes du tableau de FM « 101 150 ♥ 131 Vitalité -1 7 » (Min, Max,
    valeur, stat, Modif., quantités de runes) : la valeur retenue est le
    dernier nombre placé juste avant le nom de la stat.
    Les lignes non reconnues sont ignorées.
    """
    out = []
    for raw in text.splitlines():
        raw = raw.replace("|", " ").strip()
        if not raw:
            continue
        w = _WORD_RE.search(raw)
        if not w:
            continue
        nums = [m for m in _NUM_RE.finditer(raw, 0, w.start())]
        if not nums:
            continue
        m = nums[-1]
        sign, num = m.group(1), m.group(2)
        between = raw[m.end():w.start()]
        pct = "%" in between
        label = raw[w.start():]
        label = re.sub(r"[^\w%' \-àâäéèêëîïôöùûüç]", " ", label, flags=re.I).strip()
        if pct:
            label = "% " + label
        key = match_stat(label)
        if key is None:
            # Texte parasite après le nom de la stat (Modif., quantités de runes…) :
            # on raccourcit le libellé par la fin jusqu'à reconnaître une stat.
            words = label.split()
            for n in range(len(words) - 1, 0, -1):
                key = match_stat(" ".join(words[:n]), cutoff=0.85)
                if key:
                    break
        if key is None:
            continue
        val = int(num)
        if sign in ("-", "−", "–"):
            val = -val
        out.append((key, val))
    return out


def parse_reliquat(text: str) -> Optional[float]:
    """Lit « reliquat : 12 » (ou juste « 12 »)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)", text.replace(" ", ""))
    return float(m.group(1).replace(",", ".")) if m else None


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
    """Prépare l'image pour Tesseract (texte coloré sur fond sombre en jeu).

    On garde la composante la plus claire de chaque pixel (le texte vert, rouge
    ou blanc ressort pareil), on agrandit, puis on inverse pour avoir du texte
    noir sur fond blanc et on binarise.
    """
    from PIL import ImageChops, ImageOps

    r, g, b = img.convert("RGB").split()
    v = ImageChops.lighter(ImageChops.lighter(r, g), b)
    v = v.resize((v.width * scale, v.height * scale))
    if invert is None:
        hist = v.histogram()
        invert = sum(hist[:128]) > sum(hist[128:])
    if invert:
        v = ImageOps.invert(v)
        return v.point(lambda p: 255 if p > 140 else 0)
    return v.point(lambda p: 255 if p > 115 else 0)


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


TESSDATA_URL = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/{lang}.traineddata"
_LANG_CACHE: Dict[str, Tuple[str, str]] = {}  # lang demandée -> (lang utilisée, config --tessdata-dir)
LANG_NOTE = ""  # message à afficher (langue de repli, téléchargement…)


def user_tessdata_dir() -> str:
    import os

    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "fmhelper", "tessdata")


def _download_lang(lang: str, dest_dir: str, timeout: float = 30.0) -> bool:
    """Télécharge {lang}.traineddata (tessdata_fast, ~1 à 4 Mo) dans un dossier utilisateur."""
    import os
    import urllib.request

    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"{lang}.traineddata")
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(TESSDATA_URL.format(lang=lang), headers={"User-Agent": "fmhelper"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
            f.write(r.read())
        if os.path.getsize(tmp) < 100_000:
            os.remove(tmp)
            return False
        os.replace(tmp, dest)
        return True
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def resolve_lang(lang: str = "fra") -> Tuple[str, str]:
    """Trouve une langue OCR utilisable : (langue, options).

    1. la langue demandée si Tesseract l'a déjà ;
    2. sinon, elle est téléchargée une fois dans %LOCALAPPDATA%\\fmhelper\\tessdata ;
    3. sinon, repli sur l'anglais (les libellés sont reconnus sans accents, ça marche bien).
    """
    global LANG_NOTE
    import os
    import shutil

    import pytesseract

    if lang in _LANG_CACHE:
        return _LANG_CACHE[lang]
    try:
        installed = set(pytesseract.get_languages(config=""))
    except Exception:
        installed = set()
    if lang in installed:
        res = (lang, "")
    else:
        udir = user_tessdata_dir()
        have = os.path.exists(os.path.join(udir, f"{lang}.traineddata")) or _download_lang(lang, udir)
        if have:
            # le dossier utilisateur doit aussi contenir osd/eng si on veut s'y limiter : on y copie eng
            src_eng = None
            try:
                exe = shutil.which(pytesseract.pytesseract.tesseract_cmd) or pytesseract.pytesseract.tesseract_cmd
                cand = os.path.join(os.path.dirname(exe), "tessdata", "eng.traineddata")
                src_eng = cand if os.path.exists(cand) else None
            except Exception:
                pass
            if src_eng and not os.path.exists(os.path.join(udir, "eng.traineddata")):
                try:
                    shutil.copy(src_eng, udir)
                except OSError:
                    pass
            res = (lang, f'--tessdata-dir "{udir}"')
            LANG_NOTE = f"Langue OCR « {lang} » installée dans {udir}."
        elif "eng" in installed:
            res = ("eng", "")
            LANG_NOTE = (f"Langue OCR « {lang} » absente et téléchargement impossible : lecture en anglais. "
                         "Pour de meilleurs résultats, réinstalle Tesseract en cochant French.")
        else:
            res = (lang, "")  # laissera Tesseract afficher son erreur
    _LANG_CACHE[lang] = res
    return res


def read_region(bbox, lang: str = "fra", tesseract_cmd: Optional[str] = None) -> Dict[str, int]:
    import pytesseract

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        found = find_tesseract()
        if found:
            pytesseract.pytesseract.tesseract_cmd = found
    use_lang, extra = resolve_lang(lang)
    img = preprocess(grab(bbox))
    text = pytesseract.image_to_string(img, lang=use_lang, config=f"--psm 6 {extra}".strip())
    global LAST_TEXT
    LAST_TEXT = text
    return values_dict(parse_lines(text))


LAST_TEXT = ""  # dernier texte brut lu (diagnostic)


def read_reliquat(bbox, tesseract_cmd: Optional[str] = None) -> Optional[float]:
    """Lit le reliquat affiché par le jeu (« reliquat : N »)."""
    import pytesseract

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    img = preprocess(grab(bbox), scale=3)
    text = pytesseract.image_to_string(img, config="--psm 7 -c tessedit_char_whitelist=0123456789.,:reliquatRELIQUAT")
    return parse_reliquat(text.split(":")[-1])
