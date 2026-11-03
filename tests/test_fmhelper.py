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


def test_choose_tier_biggest_fitting():
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


def test_probability_floor_and_palier():
    it = item(vitalite=301)
    low = estimate(it, it.line("vitalite"), rune_by_tier("vitalite", "base"))
    it.line("vitalite").current = 345
    high = estimate(it, it.line("vitalite"), rune_by_tier("vitalite", "base"))
    assert low.sc > high.sc >= 0.02
    assert abs(low.sc + low.sn + low.ec - 1) < 1e-3
