from __future__ import annotations

from uuid import uuid4

from .demo_data import REFUND_REQUESTS, get_logistics_record, get_order_record


def query_order(order_id: str) -> dict:
    order = get_order_record(order_id)
    if not order:
        return {"success": False, "message": f"未找到订单 {order_id}"}
    return {"success": True, "order": order}


def query_logistics(order_id: str) -> dict:
    order_result = query_order(order_id)
    if not order_result["success"]:
        return order_result

    order = order_result["order"]
    tracking_number = order.get("tracking_number")
    if not tracking_number:
        return {"success": False, "message": "该订单暂无物流信息"}

    logistics = get_logistics_record(tracking_number)
    if not logistics:
        return {"success": False, "message": f"未找到运单 {tracking_number}"}

    return {
        "success": True,
        "order_id": order_id.upper(),
        "tracking_number": tracking_number,
        "logistics": logistics,
    }


def check_refund_eligibility(order_id: str) -> dict:
    order_result = query_order(order_id)
    if not order_result["success"]:
        return order_result

    order = order_result["order"]
    if not order["refundable"]:
        return {
            "success": False,
            "eligible": False,
            "message": "该订单当前状态不支持再次退款",
        }

    return {
        "success": True,
        "eligible": True,
        "message": "订单满足退款申请条件，提交前需要用户明确确认",
        "order": order,
    }


def create_refund(order_id: str, reason: str, confirmed: bool) -> dict:
    eligibility = check_refund_eligibility(order_id)
    if not eligibility.get("eligible"):
        return eligibility
    if not confirmed:
        return {
            "success": False,
            "confirmation_required": True,
            "message": "退款属于高风险操作，请用户明确回复确认退款后再提交",
        }

    request_id = f"RF{uuid4().hex[:8].upper()}"
    request = {
        "refund_request_id": request_id,
        "order_id": order_id.upper(),
        "reason": reason,
        "status": "审核中",
    }
    REFUND_REQUESTS[request_id] = request
    return {"success": True, "refund": request}

