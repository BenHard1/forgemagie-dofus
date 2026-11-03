"""Récupération des équipements via l'API publique DofusDB (https://api.dofusdb.fr).

- Recherche par nom (insensible aux accents), filtrée sur les équipements FM-ables.
- Conversion des effets (characteristic + signe) en lignes de l'outil (min/max).
- Cache local (~/.cache/fmhelper) : un objet déjà consulté reste disponible
  hors ligne, et une recherche déjà faite aussi.

Seule la bibliothèque standard est utilisée (urllib).
"""
from __future__ import annotations

import json
import os
import time
import unicodedata
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from .model import Item, Line

API = "https://api.dofusdb.fr"
USER_AGENT = "fmhelper/1.0 (outil d'aide a la forgemagie)"
CACHE_DIR = os.environ.get("FMHELPER_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "fmhelper"))
CACHE_TTL = 7 * 24 * 3600  # une semaine

# superTypeId DofusDB des équipements qui se forgemagent
EQUIPMENT_SUPERTYPES = {
    1: "Amulette", 2: "Arme", 3: "Anneau", 4: "Ceinture", 5: "Bottes",
    7: "Bouclier", 10: "Chapeau", 11: "Cape",
}

# characteristic DofusDB -> clé de stat de l'outil
CHARACTERISTIC_TO_STAT = {
    1: "pa", 23: "pm", 19: "po", 10: "force", 11: "vitalite", 12: "sagesse",
    13: "chance", 14: "agilite", 15: "intelligence", 16: "dommages", 18: "critique",
    25: "puissance", 26: "invocation", 27: "esquive_pa", 28: "esquive_pm",
    33: "re_pct_terre", 34: "re_pct_feu", 35: "re_pct_eau", 36: "re_pct_air", 37: "re_pct_neutre",
    40: "pods", 44: "initiative", 48: "prospection", 49: "soins", 50: "renvoi",
    54: "re_terre", 55: "re_feu", 56: "re_eau", 57: "re_air", 58: "re_neutre",
    69: "puissance_pieges", 70: "do_pieges", 78: "fuite", 79: "tacle",
    82: "retrait_pa", 83: "retrait_pm", 84: "do_poussee", 85: "re_poussee",
    86: "do_critiques", 87: "re_critiques", 88: "do_terre", 89: "do_feu",
    90: "do_eau", 91: "do_air", 92: "do_neutre",
    120: "pct_do_distance", 121: "pct_re_distance", 122: "pct_do_armes",
    123: "pct_do_sorts", 124: "pct_re_melee", 125: "pct_do_melee",
}

# Effets « malus » connus (repli si l'API /effects est injoignable)
KNOWN_MALUS_EFFECTS = {
    116, 145, 152, 153, 154, 155, 156, 157, 159, 162, 163, 168, 169, 171, 175,
    177, 179, 186, 215, 216, 217, 218, 219, 245, 246, 247, 248, 249,
}


class DofusDBError(RuntimeError):
    pass


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def _cache_path(kind: str, key: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:120]
    return os.path.join(CACHE_DIR, kind, safe + ".json")


def _cache_get(kind: str, key: str, max_age: Optional[float] = CACHE_TTL):
    p = _cache_path(kind, key)
    try:
        if max_age is not None and time.time() - os.path.getmtime(p) > max_age:
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _cache_put(kind: str, key: str, data) -> None:
    p = _cache_path(kind, key)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


def _get(path: str, params: List[tuple], timeout: float = 10.0):
    url = f"{API}{path}?{urllib.parse.urlencode(params, safe='[]$')}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # réseau, HTTP, JSON
        raise DofusDBError(f"DofusDB injoignable : {e}") from e


def _summary(raw: dict) -> dict:
    t = raw.get("type") or {}
    st = (t.get("superType") or {}).get("id", t.get("superTypeId"))
    return {
        "id": raw.get("id"),
        "name": (raw.get("name") or {}).get("fr", "?"),
        "level": raw.get("level", 0),
        "type": ((t.get("name") or {}).get("fr")) or EQUIPMENT_SUPERTYPES.get(st, "?"),
        "superTypeId": st,
    }


def search_items(query: str, limit: int = 30, equipment_only: bool = True) -> List[dict]:
    """Cherche des objets par nom. Renvoie une liste de résumés (id, name, level, type).

    En cas d'échec réseau, renvoie la dernière recherche identique en cache,
    ou les objets déjà consultés dont le nom correspond.
    """
    q = _norm(query)
    if len(q) < 2:
        return []
    key = f"{q}_{limit}_{int(equipment_only)}"
    try:
        data = _get("/items", [("slug.fr[$search]", q), ("$limit", str(min(limit, 50)))])
        raws = data.get("data", [])
        for raw in raws:  # met en cache les objets complets au passage
            if raw.get("id") is not None and raw.get("effects") is not None:
                _cache_put("item", str(raw["id"]), raw)
        out = [_summary(r) for r in raws]
        if equipment_only:
            out = [o for o in out if o["superTypeId"] in EQUIPMENT_SUPERTYPES or o["superTypeId"] is None]
        out.sort(key=lambda o: (-int(o["level"] or 0), o["name"]))
        _cache_put("search", key, out)
        return out
    except DofusDBError:
        cached = _cache_get("search", key, max_age=None)
        if cached is not None:
            return cached
        return [o for o in cached_items() if q in _norm(o["name"])]


def cached_items() -> List[dict]:
    """Résumés des objets présents dans le cache local (mode hors ligne)."""
    d = os.path.join(CACHE_DIR, "item")
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return out
    for n in names:
        try:
            with open(os.path.join(d, n), encoding="utf-8") as f:
                out.append(_summary(json.load(f)))
        except (OSError, ValueError):
            continue
    return out


def get_item_raw(item_id: int) -> dict:
    cached = _cache_get("item", str(item_id), max_age=None)
    if cached is not None:
        return cached
    data = _get("/items", [("id", str(item_id))])
    items = data.get("data", [])
    if not items:
        raise DofusDBError(f"Objet {item_id} introuvable sur DofusDB")
    _cache_put("item", str(item_id), items[0])
    return items[0]


def malus_effects(effect_ids: List[int]) -> set:
    """Identifie les effets négatifs (bonusType = -1) via /effects, avec cache et repli."""
    ids = sorted(set(int(i) for i in effect_ids))
    result = set()
    missing = []
    for i in ids:
        c = _cache_get("effect", str(i), max_age=None)
        if c is None:
            missing.append(i)
        elif c.get("bonusType") == -1:
            result.add(i)
    if missing:
        try:
            params = [(f"id[$in][{n}]", str(i)) for n, i in enumerate(missing[:50])] + [("$limit", "50")]
            for e in _get("/effects", params).get("data", []):
                _cache_put("effect", str(e.get("id")), {"bonusType": e.get("bonusType")})
                if e.get("bonusType") == -1:
                    result.add(int(e["id"]))
        except DofusDBError:
            result |= {i for i in missing if i in KNOWN_MALUS_EFFECTS}
    return result


def item_from_raw(raw: dict, malus: Optional[set] = None) -> Item:
    """Convertit un objet DofusDB en Item de l'outil (valeurs actuelles = jet min)."""
    effects = raw.get("effects") or []
    if malus is None:
        malus = malus_effects([e.get("effectId") for e in effects if e.get("effectId") is not None])
    lines: Dict[str, Line] = {}
    for e in effects:
        stat = CHARACTERISTIC_TO_STAT.get(e.get("characteristic"))
        if stat is None or stat in lines:
            continue  # dégâts d'arme, effets spéciaux, doublons
        lo, hi = int(e.get("from") or 0), int(e.get("to") or 0)
        if hi == 0:
            hi = lo
        lo, hi = min(lo, hi), max(lo, hi)
        if e.get("effectId") in malus:
            lo, hi = -hi, -lo
        lines[stat] = Line(stat=stat, min=lo, max=hi, current=lo)
    name = (raw.get("name") or {}).get("fr", "Objet")
    return Item(name=name, level=int(raw.get("level") or 200), lines=list(lines.values()))


def load_item(item_id: int) -> Item:
    return item_from_raw(get_item_raw(item_id))
