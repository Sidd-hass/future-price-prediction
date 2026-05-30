from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from alert_logic import AlertEngine

class DummyConfig:
    BASIS_THRESHOLD = 2.0
    SPREAD_MIN = 0.0
    SPREAD_MAX = 0.2
    BREACH_COUNT_THRESHOLD = 5
    COOLDOWN_MINUTES = 15
    WATCHLIST = ["RELIANCE", "TCS"]


def test_condition_both_true():
    engine = AlertEngine(DummyConfig())
    # basis=2.5, spread=0.1 -> True
    assert engine.check_conditions(2.5, 0.1) is True


def test_condition_basis_not_met():
    engine = AlertEngine(DummyConfig())
    # basis=1.5, spread=0.1 -> False
    assert engine.check_conditions(1.5, 0.1) is False


def test_condition_spread_too_high():
    engine = AlertEngine(DummyConfig())
    # basis=2.5, spread=0.5 -> False
    assert engine.check_conditions(2.5, 0.5) is False


def test_condition_spread_negative():
    engine = AlertEngine(DummyConfig())
    # basis=2.5, spread=-0.1 -> False
    assert engine.check_conditions(2.5, -0.1) is False


def test_noise_filter_fires_on_nth_tick():
    engine = AlertEngine(DummyConfig())
    # simulate 5 ticks, assert True only on tick 5
    # Let's send 4 ticks that meet conditions, expect False
    for _ in range(4):
        assert engine.noise_filter("RELIANCE", 2.5, 0.1) is False
    # On the 5th tick, expect True
    assert engine.noise_filter("RELIANCE", 2.5, 0.1) is True


def test_noise_filter_resets_on_false():
    engine = AlertEngine(DummyConfig())
    # send 3 true ticks then 1 false
    for _ in range(3):
        assert engine.noise_filter("RELIANCE", 2.5, 0.1) is False
        
    # False tick
    assert engine.noise_filter("RELIANCE", 1.5, 0.1) is False
    
    # Counter should reset to 0
    assert engine.breach_counter["RELIANCE"] == 0


def test_cooldown_blocks_immediate_relalert():
    engine = AlertEngine(DummyConfig())
    engine.record_alert("RELIANCE")
    assert engine.is_cooldown_active("RELIANCE") is True


class MockDateTime:
    _now = datetime(2026, 5, 27, 10, 0, 0)
    
    @classmethod
    def now(cls):
        return cls._now


@patch('alert_logic.datetime', MockDateTime)
def test_cooldown_allows_after_expiry():
    engine = AlertEngine(DummyConfig())
    
    # Set the initial time
    MockDateTime._now = datetime(2026, 5, 27, 10, 0, 0)
    engine.record_alert("RELIANCE")
    
    # Verify cooldown is initially active
    assert engine.is_cooldown_active("RELIANCE") is True
    
    # Advance time by 16 minutes
    MockDateTime._now = datetime(2026, 5, 27, 10, 16, 0)
    assert engine.is_cooldown_active("RELIANCE") is False


def test_should_alert_full_flow():
    engine = AlertEngine(DummyConfig())
    # 5 ticks pass noise filter, cooldown not active -> should return True on 5th tick
    for _ in range(4):
        assert engine.should_alert("RELIANCE", 2.5, 0.1) is False
        
    assert engine.should_alert("RELIANCE", 2.5, 0.1) is True
