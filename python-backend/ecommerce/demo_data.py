from __future__ import annotations

from copy import deepcopy


ORDERS = {
    "DDN20260001": {
        "order_id": "DDN20260001",
        "customer_id": "CUST001",
        "customer_name": "张三",
        "product_name": "无线蓝牙耳机 Pro",
        "amount": 299.00,
        "payment_status": "已支付",
        "order_status": "运输中",
        "created_at": "2026-06-18 10:30",
        "tracking_number": "SF1234567890",
        "refundable": True,
    },
    "DDN20260002": {
        "order_id": "DDN20260002",
        "customer_id": "CUST002",
        "customer_name": "李四",
        "product_name": "智能运动手环",
        "amount": 199.00,
        "payment_status": "已支付",
        "order_status": "已签收",
        "created_at": "2026-06-10 15:20",
        "tracking_number": "YT9876543210",
        "refundable": True,
    },
    "DDN20260003": {
        "order_id": "DDN20260003",
        "customer_id": "CUST003",
        "customer_name": "王五",
        "product_name": "机械键盘 K87",
        "amount": 459.00,
        "payment_status": "退款完成",
        "order_status": "已关闭",
        "created_at": "2026-05-20 09:15",
        "tracking_number": None,
        "refundable": False,
    },
}


LOGISTICS = {
    "SF1234567890": {
        "carrier": "顺丰速运",
        "status": "运输中",
        "estimated_delivery": "2026-06-22",
        "latest_event": "快件已到达杭州转运中心",
        "events": [
            "2026-06-21 08:40 快件已到达杭州转运中心",
            "2026-06-20 19:10 快件已从上海分拨中心发出",
            "2026-06-19 12:30 商家已发货",
        ],
    },
    "YT9876543210": {
        "carrier": "圆通速递",
        "status": "已签收",
        "estimated_delivery": "2026-06-13",
        "latest_event": "本人签收，感谢使用圆通速递",
        "events": [
            "2026-06-13 14:25 本人签收",
            "2026-06-13 09:05 杭州西湖区派件中",
            "2026-06-12 21:15 快件已到达杭州转运中心",
        ],
    },
}


REFUND_REQUESTS: dict[str, dict] = {}


def get_order_record(order_id: str) -> dict | None:
    order = ORDERS.get(order_id.upper())
    return deepcopy(order) if order else None


def get_logistics_record(tracking_number: str) -> dict | None:
    record = LOGISTICS.get(tracking_number.upper())
    return deepcopy(record) if record else None

