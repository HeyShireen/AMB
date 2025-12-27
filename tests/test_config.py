from amb_bot.config import get_settings


def test_settings_loads_defaults():
    settings = get_settings()
    assert settings.monthly_budget == 200
    assert settings.stop_loss_pct == 0.10
    assert settings.take_profit_pct == 0.15
