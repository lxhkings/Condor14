"""FutuClient 单元测试：验证错误日志与限流器调用。"""

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest
from futu import RET_ERROR, RET_OK

from data_source.futu_client import FutuClient
from data_source.rate_limit import TokenBucket


@pytest.fixture
def fake_ctx():
    return MagicMock()


def _make_client(fake_ctx, **kwargs) -> FutuClient:
    return FutuClient(_ctx=fake_ctx, **kwargs)


def test_option_chain_logs_ret_msg_when_chain_call_fails(fake_ctx, caplog):
    fake_ctx.get_option_chain.return_value = (RET_ERROR, "请求频率超出限制")
    client = _make_client(fake_ctx)
    with caplog.at_level("WARNING", logger="data_source.futu_client"):
        legs = client.option_chain("AAPL", expiration=date(2026, 5, 23), near_spot=200.0)
    assert legs == []
    assert any("请求频率超出限制" in r.message for r in caplog.records)
    assert any("AAPL" in r.message for r in caplog.records)


def test_option_chain_logs_ret_msg_when_snapshot_batch_fails(fake_ctx, caplog):
    chain_df = pd.DataFrame({"code": ["US.AAPL250523C00200000"]})
    fake_ctx.get_option_chain.return_value = (RET_OK, chain_df)
    fake_ctx.get_market_snapshot.return_value = (RET_ERROR, "snapshot quota hit")
    client = _make_client(fake_ctx)
    with caplog.at_level("WARNING", logger="data_source.futu_client"):
        legs = client.option_chain("AAPL", expiration=date(2026, 5, 23), near_spot=200.0)
    assert legs == []
    assert any("snapshot quota hit" in r.message for r in caplog.records)


def test_list_expirations_logs_ret_msg_on_error(fake_ctx, caplog):
    fake_ctx.get_option_expiration_date.return_value = (RET_ERROR, "频率限制")
    client = _make_client(fake_ctx)
    with caplog.at_level("WARNING", logger="data_source.futu_client"):
        result = client.list_expirations("AAPL")
    assert result == []
    assert any("频率限制" in r.message for r in caplog.records)


def test_option_chain_calls_chain_limiter_acquire(fake_ctx):
    chain_df = pd.DataFrame({"code": []})
    fake_ctx.get_option_chain.return_value = (RET_OK, chain_df)
    chain_limiter = MagicMock(spec=TokenBucket)
    exp_limiter = MagicMock(spec=TokenBucket)
    client = _make_client(fake_ctx, chain_limiter=chain_limiter, exp_limiter=exp_limiter)
    client.option_chain("AAPL", expiration=date(2026, 5, 23), near_spot=200.0)
    chain_limiter.acquire.assert_called_once()
    exp_limiter.acquire.assert_not_called()


def test_list_expirations_calls_exp_limiter_acquire(fake_ctx):
    fake_ctx.get_option_expiration_date.return_value = (RET_OK, pd.DataFrame({"strike_time": []}))
    chain_limiter = MagicMock(spec=TokenBucket)
    exp_limiter = MagicMock(spec=TokenBucket)
    client = _make_client(fake_ctx, chain_limiter=chain_limiter, exp_limiter=exp_limiter)
    client.list_expirations("AAPL")
    exp_limiter.acquire.assert_called_once()
    chain_limiter.acquire.assert_not_called()


def test_option_chain_retries_once_on_rate_limit_error(fake_ctx, monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("data_source.futu_client.time.sleep", lambda s: sleeps.append(s))

    chain_df = pd.DataFrame({"code": []})
    fake_ctx.get_option_chain.side_effect = [
        (RET_ERROR, "请求频率超出限制，请稍后重试"),
        (RET_OK, chain_df),
    ]
    client = _make_client(fake_ctx)
    legs = client.option_chain("AAPL", expiration=date(2026, 5, 23), near_spot=200.0)
    assert legs == []  # 链空但接口未失败
    assert fake_ctx.get_option_chain.call_count == 2
    assert sleeps == [30.0]


def test_option_chain_does_not_retry_non_rate_limit_error(fake_ctx, monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("data_source.futu_client.time.sleep", lambda s: sleeps.append(s))
    fake_ctx.get_option_chain.return_value = (RET_ERROR, "auth failed")
    client = _make_client(fake_ctx)
    legs = client.option_chain("AAPL", expiration=date(2026, 5, 23), near_spot=200.0)
    assert legs == []
    assert fake_ctx.get_option_chain.call_count == 1
    assert sleeps == []


def test_option_chain_gives_up_after_one_retry(fake_ctx, monkeypatch):
    monkeypatch.setattr("data_source.futu_client.time.sleep", lambda s: None)
    fake_ctx.get_option_chain.return_value = (RET_ERROR, "频率限制")
    client = _make_client(fake_ctx)
    legs = client.option_chain("AAPL", expiration=date(2026, 5, 23), near_spot=200.0)
    assert legs == []
    assert fake_ctx.get_option_chain.call_count == 2  # 1 次原始 + 1 次重试


def test_list_expirations_retries_once_on_rate_limit(fake_ctx, monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("data_source.futu_client.time.sleep", lambda s: sleeps.append(s))
    fake_ctx.get_option_expiration_date.side_effect = [
        (RET_ERROR, "请求频率超出限制"),
        (RET_OK, pd.DataFrame({"strike_time": ["2026-05-23 00:00:00"]})),
    ]
    client = _make_client(fake_ctx)
    result = client.list_expirations("AAPL")
    assert result == [date(2026, 5, 23)]
    assert sleeps == [30.0]


def test_option_chain_retries_snapshot_on_rate_limit(fake_ctx, monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("data_source.futu_client.time.sleep", lambda s: sleeps.append(s))

    chain_df = pd.DataFrame({"code": ["US.AAPL250523C00200000"]})
    fake_ctx.get_option_chain.return_value = (RET_OK, chain_df)
    snap_df = pd.DataFrame({
        "option_type": ["CALL"], "option_strike_price": [200.0],
        "bid_price": [1.0], "ask_price": [1.5], "last_price": [1.2],
        "prev_close_price": [1.1], "option_implied_volatility": [30.0],
        "option_delta": [0.5], "option_open_interest": [500], "volume": [100],
    })
    fake_ctx.get_market_snapshot.side_effect = [
        (RET_ERROR, "获取市场快照频率太高，请求失败"),
        (RET_OK, snap_df),
    ]
    client = _make_client(fake_ctx)
    legs = client.option_chain("AAPL", expiration=date(2026, 5, 23))
    assert len(legs) == 1
    assert fake_ctx.get_market_snapshot.call_count == 2
    assert sleeps == [30.0]


def test_option_chain_calls_snapshot_limiter_acquire(fake_ctx):
    chain_df = pd.DataFrame({"code": ["US.AAPL250523C00200000"]})
    snap_df = pd.DataFrame({
        "option_type": ["CALL"], "option_strike_price": [200.0],
        "bid_price": [1.0], "ask_price": [1.5], "last_price": [1.2],
        "prev_close_price": [1.1], "option_implied_volatility": [30.0],
        "option_delta": [0.5], "option_open_interest": [500], "volume": [100],
    })
    fake_ctx.get_option_chain.return_value = (RET_OK, chain_df)
    fake_ctx.get_market_snapshot.return_value = (RET_OK, snap_df)
    snapshot_limiter = MagicMock(spec=TokenBucket)
    client = _make_client(fake_ctx, snapshot_limiter=snapshot_limiter)
    client.option_chain("AAPL", expiration=date(2026, 5, 23))
    snapshot_limiter.acquire.assert_called_once()


def test_option_exercise_prob_returns_latest(fake_ctx):
    df = pd.DataFrame({
        "timestamp_str": ["2026-06-05", "2026-06-04"],
        "security_price": [311.2, 310.3],
        "strike_probability": [92.9, 94.8],  # row 0 = latest (API sorts desc)
    })
    fake_ctx.get_option_exercise_probability.return_value = (RET_OK, df)
    client = _make_client(fake_ctx)
    assert client.option_exercise_prob("US.AAPL260702C260000") == 92.9


def test_option_exercise_prob_none_on_error(fake_ctx):
    fake_ctx.get_option_exercise_probability.return_value = (RET_ERROR, "频率限制")
    client = _make_client(fake_ctx)
    assert client.option_exercise_prob("US.AAPL260702C260000") is None


def test_option_exercise_prob_none_on_empty(fake_ctx):
    fake_ctx.get_option_exercise_probability.return_value = (RET_OK, pd.DataFrame())
    client = _make_client(fake_ctx)
    assert client.option_exercise_prob("US.AAPL260702C260000") is None


def test_option_volatility_returns_points(fake_ctx):
    df = pd.DataFrame({
        "timestamp_str": ["2026-05-21", "2026-05-22"],  # API sorts ascending
        "implied_volatility": [32.8, 26.7],
        "history_volatility": [21.9, 22.0],
    })
    fake_ctx.get_option_volatility.return_value = (RET_OK, df)
    client = _make_client(fake_ctx)
    pts = client.option_volatility("US.AAPL281215C320000", window=1, hv_days=30)
    assert [p.iv for p in pts] == [32.8, 26.7]
    assert pts[-1].hv == 22.0
    assert pts[0].date == date(2026, 5, 21)


def test_option_volatility_none_on_error(fake_ctx):
    fake_ctx.get_option_volatility.return_value = (RET_ERROR, "频率限制")
    client = _make_client(fake_ctx)
    assert client.option_volatility("US.AAPL281215C320000", window=1) is None


def test_option_volatility_none_on_empty(fake_ctx):
    fake_ctx.get_option_volatility.return_value = (RET_OK, pd.DataFrame())
    client = _make_client(fake_ctx)
    assert client.option_volatility("US.AAPL281215C320000", window=1) is None


def test_option_chain_populates_leg_code(fake_ctx):
    chain_df = pd.DataFrame({"code": ["US.AAPL260523C00200000"]})
    snap_df = pd.DataFrame([{
        "code": "US.AAPL260523C00200000",
        "option_type": "CALL",
        "option_strike_price": 200.0,
        "bid_price": 2.0, "ask_price": 2.1, "last_price": 2.05,
        "prev_close_price": 2.0,
        "option_implied_volatility": 40.0,
        "option_delta": 0.3,
        "option_open_interest": 1000, "volume": 500,
    }])
    fake_ctx.get_option_chain.return_value = (RET_OK, chain_df)
    fake_ctx.get_market_snapshot.return_value = (RET_OK, snap_df)
    client = _make_client(fake_ctx)
    legs = client.option_chain("AAPL", expiration=date(2026, 5, 23), near_spot=200.0)
    assert len(legs) == 1
    assert legs[0].code == "US.AAPL260523C00200000"


def test_option_chain_preserves_raw_quotes_on_collapse(fake_ctx):
    # 宽价差 (0.1/2.0, spread 190%>30%) 触发 collapse
    chain_df = pd.DataFrame({"code": ["US.AAPL250523P00200000"]})
    snap_df = pd.DataFrame({
        "option_type": ["PUT"], "option_strike_price": [200.0],
        "bid_price": [0.10], "ask_price": [2.00], "last_price": [1.0],
        "prev_close_price": [1.0], "option_implied_volatility": [30.0],
        "option_delta": [-0.5], "option_gamma": [0.02], "option_vega": [0.1],
        "option_theta": [-0.05], "option_rho": [0.01],
        "option_open_interest": [500], "option_net_open_interest": ["N/A"],
        "volume": [100], "bid_vol": [40], "ask_vol": [60], "price_spread": [1.90],
    })
    fake_ctx.get_option_chain.return_value = (RET_OK, chain_df)
    fake_ctx.get_market_snapshot.return_value = (RET_OK, snap_df)
    client = _make_client(fake_ctx)
    legs = client.option_chain("AAPL", expiration=date(2026, 5, 23))
    assert len(legs) == 1
    leg = legs[0]
    # collapse 改写 bid/ask -> mid
    assert leg.quote_collapsed is True
    assert leg.bid == leg.ask  # mid
    # 真实值保留
    assert leg.raw_bid == 0.10
    assert leg.raw_ask == 2.00
    # snapshot 全字段袋，bid_price 仍是真实原值，希腊值齐
    assert leg.snapshot["bid_price"] == 0.10
    assert leg.snapshot["ask_price"] == 2.00
    assert leg.snapshot["bid_vol"] == 40
    assert leg.snapshot["ask_vol"] == 60
    assert leg.snapshot["option_gamma"] == 0.02
    # 'N/A' 安全透传，不崩
    assert leg.snapshot["option_net_open_interest"] == "N/A"
