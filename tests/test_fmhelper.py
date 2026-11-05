import copy

from fmhelper.model import EC, SC, SN, ForgeSession, Item, Line, rune_weight_on_line
from fmhelper.ocr import parse_lines, values_dict
from fmhelper.planner import choose_tier, click_plan, recommend
from fmhelper.probability import estimate
from fmhelper.runes import STATS, match_stat, rune_by_tier


def item(**cur):
    it = Item.from_dict({
        "name": "Test", "level": 200,
        "lines": [
            {"stat": "vitalite", "min": 301, "max": 350, "current": 320},
            {"stat": "force", "min": 61, "max": 80, "current": 70},
            {"stat": "po", "min": 1, "max": 1, "current": 1},
        ],
    })
    for k, v in cur.items():
        it.line(k).current = v
    return it


def test_rune_weights():
    assert rune_by_tier("vitalite", "ra").weight == 10
    assert rune_by_tier("force", "pa").weight == 3
    assert rune_by_tier("pa", "base").name == "Rune Ga Pa"
    assert rune_by_tier("pa", "base").weight == 100
    assert STATS["vitalite"].over_cap_points == 505
    assert STATS["sagesse"].over_cap_points == 33


def test_match_stat_ocr_tolerant():
    assert match_stat("Vitalite") == "vitalite"
    assert match_stat("Intelligenee") == "intelligence"
    assert match_stat("% Résistance Feu") == "re_pct_feu"
    assert match_stat("Résistance Feu") == "re_feu"
    assert match_stat("PA") == "pa"
    assert match_stat("blabla xyz") is None


def test_parse_lines():
    txt = "+320 Vitalité\n 70 Force\n-5 Sagesse\n8% Résistance Feu\n1 Portée\nbruit"
    d = values_dict(parse_lines(txt))
    assert d == {"vitalite": 320, "force": 70, "sagesse": -5, "re_pct_feu": 8, "po": 1}


def test_sn_creates_reliquat_when_heavy_line_drops():
    # Do Feu (poids 5) fait sauter la PO (poids 51) : reliquat 46 (exemple Gamosaurus)
    it = Item.from_dict({"name": "t", "level": 200, "lines": [
        {"stat": "do_feu", "min": 1, "max": 10, "current": 5},
        {"stat": "po", "min": 1, "max": 1, "current": 1}]})
    s = ForgeSession(it)
    obs = s.observe({"do_feu": 6, "po": 0}, rune=rune_by_tier("do_feu", "base"))
    assert obs.outcome == SN
    assert s.reliquat == 46


def test_sc_keeps_reliquat():
    s = ForgeSession(item())
    obs = s.observe({"vitalite": 370, "force": 70, "po": 1}, rune=rune_by_tier("vitalite", "ra"))
    assert obs.outcome == SC and s.reliquat == 0


def test_sn_absorbed_by_reliquat_is_ambiguous():
    s = ForgeSession(item(), reliquat=20)
    obs = s.observe({"vitalite": 370, "force": 70, "po": 1}, rune=rune_by_tier("vitalite", "ra"))
    assert obs.outcome == SN and obs.ambiguous and s.reliquat == 10


def test_ec_consumes():
    s = ForgeSession(item())
    # EC Ra Vi (10) : perte de 10 Force
    obs = s.observe({"vitalite": 320, "force": 60, "po": 1}, rune=rune_by_tier("vitalite", "ra"))
    assert obs.outcome == EC and s.reliquat == 0
    # EC Fo (1) qui fait sauter la PO (51) : reliquat 50
    obs = s.observe({"vitalite": 320, "force": 60, "po": 0}, rune=rune_by_tier("force", "base"))
    assert obs.outcome == EC and s.reliquat == 50


def test_other_rune_than_recommended_is_deduced():
    s = ForgeSession(item())
    obs = s.observe({"vitalite": 320, "force": 73, "po": 1}, rune=rune_by_tier("vitalite", "ra"))
    assert obs.rune.stat == "force" and obs.rune.tier == "pa"


def test_malus_half_price():
    l = Line("sagesse", -10, -5, current=-9)
    assert rune_weight_on_line(rune_by_tier("sagesse", "base"), l) == 1.5
    l.current = -1
    assert rune_weight_on_line(rune_by_tier("sagesse", "base"), l) == 3


def test_choose_tier_biggest_fitting():  # sans objet : la plus grosse rune qui rentre
    it = item(vitalite=300)
    assert choose_tier(it.line("vitalite")).tier == "ra"
    it.line("vitalite").current = 330
    assert choose_tier(it.line("vitalite")).tier == "pa"
    it.line("vitalite").current = 350
    assert choose_tier(it.line("vitalite")) is None


def test_plan_reaches_targets():
    it = item(vitalite=301, force=61)
    plan = click_plan(it)
    final = copy.deepcopy(it)
    for r in plan:
        final.line(r.line.stat).current += r.rune.power
    assert final.line("vitalite").current >= 350
    assert final.line("force").current == 80


def test_heavy_exo_needs_reliquat():
    it = Item.from_dict({"name": "t", "level": 200, "lines": [
        {"stat": "force", "min": 1, "max": 10, "current": 10}], "exos": {"pa": 1}})
    assert recommend(ForgeSession(it)) is None
    rec = recommend(ForgeSession(it, reliquat=150))
    assert rec.rune.name == "Rune Ga Pa"
    assert rec.chances.sc == 0.01 and rec.chances.sn == 0


def one_line(cur, level=200, extra=None):
    d = {"name": "t", "level": level, "lines": [{"stat": "force", "min": 1, "max": 100, "current": cur}]}
    if extra:
        d["lines"] += extra
    return Item.from_dict(d)


def test_formula_easy_click():
    it = one_line(50)
    ch = estimate(it, it.line("force"), rune_by_tier("force", "ra"))
    assert ch.difficulty == 5
    assert (ch.sc, ch.sn, ch.ec) == (0.475, 0.5, 0.025)


def test_formula_palier_80():
    it = one_line(78)  # 78 + 10 = 88 >= 80 % du max
    ch = estimate(it, it.line("force"), rune_by_tier("force", "ra"))
    assert ch.difficulty == 50 and ch.sc == 0.25


def test_formula_over_and_floor():
    it = one_line(95)  # 95 + 10 = 105 : over de 5 points de poids
    ch = estimate(it, it.line("force"), rune_by_tier("force", "ra"))
    assert ch.difficulty == 5 + 45 + 65 + 4 * 5
    assert ch.sc == 0.02  # plancher


def test_formula_x14():
    it = one_line(40)  # 40 / 1 = x40 avec une rune Fo : +12 x 26
    ch = estimate(it, it.line("force"), rune_by_tier("force", "base"))
    assert ch.difficulty == 5 + 12 * 26 and ch.sc == 0.02
    it = one_line(15)  # x15 : +12
    ch = estimate(it, it.line("force"), rune_by_tier("force", "base"))
    assert ch.difficulty == 17


def test_formula_low_level():
    it = one_line(50, level=150)
    ch = estimate(it, it.line("force"), rune_by_tier("force", "ra"))
    assert ch.difficulty == -15 and ch.sc == 0.575 and abs(ch.sc + ch.sn + ch.ec - 1) < 1e-9


def test_formula_quality_and_exo_pa():
    perfect = [{"stat": "vitalite", "min": 100, "max": 200, "current": 200}]
    it = one_line(50, extra=perfect)
    assert estimate(it, it.line("force"), rune_by_tier("force", "ra")).difficulty == 65
    it = one_line(50, extra=[{"stat": "vitalite", "min": 100, "max": 200, "current": 100}])
    assert estimate(it, it.line("force"), rune_by_tier("force", "ra")).difficulty == 5
    it = one_line(50, extra=[{"stat": "vitalite", "min": 100, "max": 200, "current": 100}])
    it.lines.append(Line("pa", 0, 0, current=1, exo=True))
    assert estimate(it, it.line("force"), rune_by_tier("force", "ra")).difficulty == 65


def test_choose_tier_prefers_bigger_rune_past_x14():
    it = one_line(40)
    assert choose_tier(it.line("force"), it).tier == "ra"


def test_resolve_lang_fallbacks(monkeypatch, tmp_path):
    import pytesseract
    from fmhelper import ocr

    monkeypatch.setattr(ocr, "_LANG_CACHE", {})
    monkeypatch.setattr(ocr, "user_tessdata_dir", lambda: str(tmp_path))
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "osd"])
    # téléchargement OK -> fra depuis le dossier utilisateur
    def fake_dl(lang, d, timeout=30.0):
        (tmp_path / f"{lang}.traineddata").write_bytes(b"x" * 200_000)
        return True
    monkeypatch.setattr(ocr, "_download_lang", fake_dl)
    lang, extra = ocr.resolve_lang("fra")
    assert lang == "fra" and str(tmp_path) in extra
    # téléchargement impossible -> anglais
    monkeypatch.setattr(ocr, "_LANG_CACHE", {})
    monkeypatch.setattr(ocr, "user_tessdata_dir", lambda: str(tmp_path / "vide"))
    monkeypatch.setattr(ocr, "_download_lang", lambda *a, **k: False)
    assert ocr.resolve_lang("fra") == ("eng", "")
    # fra déjà installée
    monkeypatch.setattr(ocr, "_LANG_CACHE", {})
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "fra"])
    assert ocr.resolve_lang("fra") == ("fra", "")


def test_parse_lines_with_trailing_noise():
    txt = "312 Vitalité SC 47% 12\n64 Force Pa Ra\n8% Résistance Feu 3 2 1"
    d = values_dict(parse_lines(txt))
    assert d == {"vitalite": 312, "force": 64, "re_pct_feu": 8}


def test_parse_real_fm_table_lines():
    from fmhelper.ocr import parse_reliquat

    txt = ("Min Max Effets / Carac. Modif. Pa Ra\n101 150 ® 131 Vitalité 7)\n21 30 # 30 Puissance 34 44\n"
           "Ÿ 21 Sagesse\n6 8 Dommages Neutre\n& 7 Dommages Feu se\n1 1 © 1 Portée 681\n-10 -10 % -10 Tacle\n")
    d = values_dict(parse_lines(txt))
    assert d == {"vitalite": 131, "puissance": 30, "sagesse": 21, "do_neutre": 8, "do_feu": 7, "po": 1, "tacle": -10}
    assert parse_reliquat(" 1\n") == 1.0 and parse_reliquat("12,5") == 12.5 and parse_reliquat("—") is None


def test_default_budget_by_item():
    from fmhelper.planner import default_budget

    small = Item.from_dict({"name": "t", "level": 20, "lines": [{"stat": "force", "min": 1, "max": 20}]})
    assert default_budget(small) == 400
    high = Item.from_dict({"name": "t", "level": 200, "lines": [{"stat": "force", "min": 1, "max": 80}]})
    assert default_budget(high) == 1500
    heavy = Item.from_dict({"name": "t", "level": 200, "lines": [{"stat": "force", "min": 1, "max": 80},
                                                               {"stat": "pa", "min": 1, "max": 1},
                                                               {"stat": "sagesse", "min": 31, "max": 80}]})
    assert default_budget(heavy) == 2500
