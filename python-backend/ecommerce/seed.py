from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from .database import init_database, session_scope
from .models import Logistics, LogisticsEvent, Order


SEED_ORDERS = [
    {
        "order_id": "DDN20260001",
        "customer_id": "CUST001",
        "customer_name": "张三",
        "product_name": "无线蓝牙耳机 Pro",
        "amount": Decimal("299.00"),
        "payment_status": "已支付",
        "order_status": "运输中",
        "created_at": datetime(2026, 6, 18, 10, 30),
        "tracking_number": "SF1234567890",
        "refundable": True,
    },
    {
        "order_id": "DDN20260002",
        "customer_id": "CUST002",
        "customer_name": "李四",
        "product_name": "智能运动手环",
        "amount": Decimal("199.00"),
        "payment_status": "已支付",
        "order_status": "已签收",
        "created_at": datetime(2026, 6, 10, 15, 20),
        "tracking_number": "YT9876543210",
        "refundable": True,
    },
    {
        "order_id": "DDN20260003",
        "customer_id": "CUST003",
        "customer_name": "王五",
        "product_name": "机械键盘 K87",
        "amount": Decimal("459.00"),
        "payment_status": "退款完成",
        "order_status": "已关闭",
        "created_at": datetime(2026, 5, 20, 9, 15),
        "tracking_number": None,
        "refundable": False,
    },
]

SEED_LOGISTICS = [
    {
        "order_id": "DDN20260001",
        "tracking_number": "SF1234567890",
        "carrier": "顺丰速运",
        "status": "运输中",
        "estimated_delivery": date(2026, 6, 22),
        "latest_event": "快件已到达杭州转运中心",
        "events": [
            (datetime(2026, 6, 21, 8, 40), "快件已到达杭州转运中心"),
            (datetime(2026, 6, 20, 19, 10), "快件已从上海分拨中心发出"),
            (datetime(2026, 6, 19, 12, 30), "商家已发货"),
        ],
    },
    {
        "order_id": "DDN20260002",
        "tracking_number": "YT9876543210",
        "carrier": "圆通速递",
        "status": "已签收",
        "estimated_delivery": date(2026, 6, 13),
        "latest_event": "本人签收，感谢使用圆通速递",
        "events": [
            (datetime(2026, 6, 13, 14, 25), "本人签收"),
            (datetime(2026, 6, 13, 9, 5), "杭州西湖区派件中"),
            (datetime(2026, 6, 12, 21, 15), "快件已到达杭州转运中心"),
        ],
    },
]


def seed_demo_data(reset: bool = False) -> None:
    init_database(drop_existing=reset)
    with session_scope() as session:
        exists = session.scalar(select(Order.order_id).limit(1))
        if exists:
            return
        for values in SEED_ORDERS:
            session.add(Order(**values))
        session.flush()
        for values in SEED_LOGISTICS:
            logistics_values = values.copy()
            events = logistics_values.pop("events")
            logistics = Logistics(**logistics_values)
            logistics.events = [
                LogisticsEvent(event_time=event_time, description=description)
                for event_time, description in events
            ]
            session.add(logistics)


if __name__ == "__main__":
    seed_demo_data()
    print("数据库初始化完成。")
