from __future__ import annotations

import pytest

from ecommerce.database import configure_database
from ecommerce.context import EcommerceAgentContext, public_context
from ecommerce.seed import seed_demo_data
from ecommerce.services import (
    check_refund_eligibility,
    create_refund,
    query_logistics,
    query_order,
    query_refund,
)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    configure_database(database_url)
    seed_demo_data(reset=True)


def test_query_existing_order():
    result = query_order("DDN20260001")
    assert result["success"] is True
    assert result["order"]["product_name"] == "无线蓝牙耳机 Pro"
    assert result["order"]["amount"] == 299.0


def test_query_missing_order():
    result = query_order("NOT-FOUND")
    assert result["success"] is False


def test_order_ownership_can_be_checked():
    result = query_order("DDN20260001", customer_id="CUST999")
    assert result["success"] is False
    assert result["forbidden"] is True


def test_query_logistics_reads_events_from_database():
    result = query_logistics("DDN20260001")
    assert result["success"] is True
    assert result["logistics"]["status"] == "运输中"
    assert len(result["logistics"]["events"]) == 3


def test_refund_requires_confirmation():
    result = create_refund("DDN20260002", "不想要了", confirmed=False)
    assert result["confirmation_required"] is True


def test_confirmed_refund_requires_server_confirmation_token():
    result = create_refund("DDN20260002", "商品不符合预期", confirmed=True)
    assert result["success"] is False
    assert result["confirmation_required"] is True


def test_confirmed_refund_is_persisted():
    eligibility = check_refund_eligibility("DDN20260002")
    result = create_refund(
        "DDN20260002",
        "商品不符合预期",
        confirmed=True,
        confirmation_token=eligibility["confirmation_token"],
    )
    assert result["success"] is True
    assert result["refund"]["status"] == "审核中"

    stored = query_refund("DDN20260002")
    assert stored["success"] is True
    assert stored["refund"]["refund_request_id"] == result["refund"]["refund_request_id"]


def test_duplicate_refund_returns_original_request():
    eligibility = check_refund_eligibility("DDN20260002")
    first = create_refund(
        "DDN20260002",
        "商品不符合预期",
        confirmed=True,
        confirmation_token=eligibility["confirmation_token"],
    )
    second = create_refund(
        "DDN20260002",
        "重复提交",
        confirmed=True,
        confirmation_token=eligibility["confirmation_token"],
    )
    assert second["success"] is True
    assert second["idempotent"] is True
    assert (
        second["refund"]["refund_request_id"]
        == first["refund"]["refund_request_id"]
    )


def test_closed_order_cannot_refund():
    result = check_refund_eligibility("DDN20260003")
    assert result["eligible"] is False


def test_confirmation_token_is_not_exposed_in_public_context():
    context = EcommerceAgentContext(
        order_id="DDN20260002",
        refund_confirmation_token="server-secret-token",
        pending_refund_confirmation=True,
    )
    snapshot = public_context(context)
    assert "refund_confirmation_token" not in snapshot
    assert snapshot["pending_refund_confirmation"] is True
