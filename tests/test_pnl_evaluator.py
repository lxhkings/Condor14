import pytest

from math_engine.pnl_evaluator import Settlement, evaluate_settlement


def test_close_inside_short_strikes_is_won():
    s = evaluate_settlement(
        underlying_close=215.0,
        short_call=230.0, short_put=200.0,
        wing_width=5.0, net_credit=1.50,
    )
    assert s == Settlement(
        status="won", breached_side=None, final_pnl_per_spread=150.0,
    )


def test_close_at_short_call_is_won_inclusive():
    s = evaluate_settlement(
        underlying_close=230.0,
        short_call=230.0, short_put=200.0,
        wing_width=5.0, net_credit=1.50,
    )
    assert s.status == "won"


def test_close_at_short_put_is_won_inclusive():
    s = evaluate_settlement(
        underlying_close=200.0,
        short_call=230.0, short_put=200.0,
        wing_width=5.0, net_credit=1.50,
    )
    assert s.status == "won"


def test_close_above_long_call_is_max_loss_upper():
    # Breach: 240 - 230 = 10, capped at wing_width=5
    # P&L per spread = (1.50 - 5.00) * 100 = -350.0
    s = evaluate_settlement(
        underlying_close=240.0,
        short_call=230.0, short_put=200.0,
        wing_width=5.0, net_credit=1.50,
    )
    assert s.status == "lost"
    assert s.breached_side == "upper"
    assert s.final_pnl_per_spread == pytest.approx(-350.0)


def test_close_above_short_call_partial_loss():
    # 232 between short and long call: breach = 2, capped 2
    # P&L = (1.50 - 2.00) * 100 = -50.0
    s = evaluate_settlement(
        underlying_close=232.0,
        short_call=230.0, short_put=200.0,
        wing_width=5.0, net_credit=1.50,
    )
    assert s.status == "lost"
    assert s.breached_side == "upper"
    assert s.final_pnl_per_spread == pytest.approx(-50.0)


def test_close_below_short_put_partial_loss():
    # 198 below short put 200: breach = 2, capped 2
    # P&L = (1.50 - 2.00) * 100 = -50.0
    s = evaluate_settlement(
        underlying_close=198.0,
        short_call=230.0, short_put=200.0,
        wing_width=5.0, net_credit=1.50,
    )
    assert s.status == "lost"
    assert s.breached_side == "lower"
    assert s.final_pnl_per_spread == pytest.approx(-50.0)


def test_close_below_long_put_is_max_loss_lower():
    s = evaluate_settlement(
        underlying_close=190.0,
        short_call=230.0, short_put=200.0,
        wing_width=5.0, net_credit=1.50,
    )
    assert s.status == "lost"
    assert s.breached_side == "lower"
    assert s.final_pnl_per_spread == pytest.approx(-350.0)
