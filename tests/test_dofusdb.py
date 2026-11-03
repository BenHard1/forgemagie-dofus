import pytest

from fmhelper import dofusdb

BOUFTOU = {
    "id": 2411,
    "name": {"fr": "Coiffe du Bouftou"},
    "level": 20,
    "type": {"id": 16, "superTypeId": 10, "name": {"fr": "Chapeau"}, "superType": {"id": 10}},
    "effects": [
        {"from": 16, "to": 20, "characteristic": 10, "effectId": 118},
        {"from": 16, "to": 20, "characteristic": 15, "effectId": 126},
        {"from": 5, "to": 10, "characteristic": 12, "effectId": 156},  # malus Sagesse
        {"from": 1, "to": 0, "characteristic": 1, "effectId": 111},  # PA fixe
        {"from": 10, "to": 20, "characteristic": 0, "effectId": 100},  # dégâts d'arme : ignoré
    ],
}


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(dofusdb, "CACHE_DIR", str(tmp_path))


def test_item_from_raw_with_malus():
    item = dofusdb.item_from_raw(BOUFTOU, malus={156})
    assert item.name == "Coiffe du Bouftou" and item.level == 20
    f = item.line("force")
    assert (f.min, f.max, f.current, f.target) == (16, 20, 16, 20)
    s = item.line("sagesse")
    assert (s.min, s.max) == (-10, -5) and s.is_malus
    pa = item.line("pa")
    assert (pa.min, pa.max) == (1, 1)
    assert len(item.lines) == 4


def test_search_online_then_offline(monkeypatch):
    calls = []

    def fake_get(path, params, timeout=10.0):
        calls.append((path, params))
        return {"data": [BOUFTOU]}

    monkeypatch.setattr(dofusdb, "_get", fake_get)
    res = dofusdb.search_items("Coiffe Bouftou")
    assert res[0]["name"] == "Coiffe du Bouftou" and res[0]["type"] == "Chapeau"
    assert ("slug.fr[$search]", "coiffe bouftou") in calls[0][1]

    def down(*a, **k):
        raise dofusdb.DofusDBError("hors ligne")

    monkeypatch.setattr(dofusdb, "_get", down)
    assert dofusdb.search_items("Coiffe Bouftou")[0]["id"] == 2411  # recherche en cache
    assert dofusdb.search_items("bouf")[0]["id"] == 2411  # objets en cache
    raw = dofusdb.get_item_raw(2411)  # objet en cache
    item = dofusdb.item_from_raw(raw)  # /effects hors ligne : repli sur la liste connue
    assert item.line("sagesse").is_malus


def test_non_equipment_filtered(monkeypatch):
    rune = dict(BOUFTOU, id=1, name={"fr": "Rune Fo"}, type={"superTypeId": 9, "superType": {"id": 9}, "name": {"fr": "Rune"}})
    monkeypatch.setattr(dofusdb, "_get", lambda *a, **k: {"data": [rune, BOUFTOU]})
    assert [r["id"] for r in dofusdb.search_items("bouftou")] == [2411]
