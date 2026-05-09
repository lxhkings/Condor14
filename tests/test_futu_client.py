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
