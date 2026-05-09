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
