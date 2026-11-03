from fmhelper.alerts import OUTCOME_COLORS, detect_alerts, tier_chances
from fmhelper.model import EC, SN, ForgeSession, Item
from fmhelper.runes import rune_by_tier


def make():
    return Item.from_dict({"name": "t", "level": 200, "lines": [
        {"stat": "force", "min": 1, "max": 100, "current": 50},
        {"stat": "pa", "min": 1, "max": 1, "current": 1}]})


def test_tier_chances_all_tiers():
    it = make()
    tc = tier_chances(it, it.line("force"))
    assert [r.tier for r, _ in tc] == ["base", "pa", "ra"]
    assert tc[2][1].sc > tc[0][1].sc  # x14 : la rune de base est pénalisée à 50 de Force


def test_alert_pa_lost_and_reliquat():
    s = ForgeSession(make())
    before = s.item.values()
    obs = s.observe({"force": 60, "pa": 0}, rune=rune_by_tier("force", "ra"))
    al = detect_alerts(before, s, obs, target_reached=False)
    assert obs.outcome == SN and any("PA" in a for a in al)
    # un SN absorbé par un reliquat trop petit l'épuise
    s.reliquat = 5
    before = s.item.values()
    obs = s.observe({"force": 70, "pa": 0}, rune=rune_by_tier("force", "ra"))
    assert obs.outcome == SN and s.reliquat == 0
    assert any("Reliquat épuisé" in a for a in detect_alerts(before, s, obs, False))


def test_alert_target():
    s = ForgeSession(make())
    assert detect_alerts(s.item.values(), s, None, target_reached=True)[0].startswith("Cible atteinte")
    assert OUTCOME_COLORS[EC] != OUTCOME_COLORS[SN]
