from ecommerce.services import (
    check_refund_eligibility,
    create_refund,
    query_logistics,
    query_order,
)


def test_query_existing_order():
    result = query_order("DDN20260001")
    assert result["success"] is True
    assert result["order"]["product_name"] == "无线蓝牙耳机 Pro"


def test_query_missing_order():
    result = query_order("NOT-FOUND")
    assert result["success"] is False


def test_query_logistics():
    result = query_logistics("DDN20260001")
    assert result["success"] is True
    assert result["logistics"]["status"] == "运输中"


def test_refund_requires_confirmation():
    result = create_refund("DDN20260002", "不想要了", confirmed=False)
    assert result["confirmation_required"] is True


def test_confirmed_refund_is_created():
    eligibility = check_refund_eligibility("DDN20260002")
    assert eligibility["eligible"] is True
    result = create_refund("DDN20260002", "商品不符合预期", confirmed=True)
    assert result["success"] is True
    assert result["refund"]["status"] == "审核中"
