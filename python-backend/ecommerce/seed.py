from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from .database import init_database, session_scope
from .models import Logistics, LogisticsEvent, Order, RefundRequest


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
    {
        "order_id": "DDN20260004",
        "customer_id": "CUST001",
        "customer_name": "张三",
        "product_name": "便携蓝牙音箱 Mini",
        "amount": Decimal("159.00"),
        "payment_status": "待支付",
        "order_status": "待付款",
        "created_at": datetime(2026, 6, 22, 20, 15),
        "tracking_number": None,
        "refundable": False,
    },
    {
        "order_id": "DDN20260005",
        "customer_id": "CUST004",
        "customer_name": "赵敏",
        "product_name": "智能台灯 L2",
        "amount": Decimal("239.00"),
        "payment_status": "已支付",
        "order_status": "待发货",
        "created_at": datetime(2026, 6, 22, 9, 40),
        "tracking_number": None,
        "refundable": True,
    },
    {
        "order_id": "DDN20260006",
        "customer_id": "CUST005",
        "customer_name": "陈晨",
        "product_name": "降噪头戴耳机 X1",
        "amount": Decimal("699.00"),
        "payment_status": "已支付",
        "order_status": "退款审核中",
        "created_at": datetime(2026, 6, 8, 11, 5),
        "tracking_number": "JD2026060801",
        "refundable": False,
    },
    {
        "order_id": "DDN20260007",
        "customer_id": "CUST006",
        "customer_name": "孙悦",
        "product_name": "运动相机 Action S",
        "amount": Decimal("1299.00"),
        "payment_status": "已支付",
        "order_status": "派送异常",
        "created_at": datetime(2026, 6, 19, 16, 50),
        "tracking_number": "ZTO2026061907",
        "refundable": True,
    },
    {
        "order_id": "DDN20260008",
        "customer_id": "CUST007",
        "customer_name": "周宁",
        "product_name": "人体工学鼠标 M8",
        "amount": Decimal("329.00"),
        "payment_status": "已支付",
        "order_status": "已签收",
        "created_at": datetime(2026, 5, 1, 13, 25),
        "tracking_number": "STO2026050108",
        "refundable": False,
    },
    {
        "order_id": "DDN20260009",
        "customer_id": "CUST008",
        "customer_name": "林晓",
        "product_name": "平板电脑 Pad Air",
        "amount": Decimal("2699.00"),
        "payment_status": "已支付",
        "order_status": "运输异常",
        "created_at": datetime(2026, 6, 17, 8, 55),
        "tracking_number": "EMS2026061709",
        "refundable": True,
    },
    {
        "order_id": "DDN20260010",
        "customer_id": "CUST002",
        "customer_name": "李四",
        "product_name": "家用投影仪 P3",
        "amount": Decimal("1899.00"),
        "payment_status": "已支付",
        "order_status": "已签收",
        "created_at": datetime(2026, 6, 14, 18, 20),
        "tracking_number": "SF2026061410",
        "refundable": True,
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
    {
        "order_id": "DDN20260006",
        "tracking_number": "JD2026060801",
        "carrier": "京东物流",
        "status": "已签收",
        "estimated_delivery": date(2026, 6, 11),
        "latest_event": "商品已由本人签收",
        "events": [
            (datetime(2026, 6, 11, 16, 18), "商品已由本人签收"),
            (datetime(2026, 6, 11, 9, 12), "配送员正在派送"),
            (datetime(2026, 6, 10, 22, 5), "商品到达杭州分拣中心"),
        ],
    },
    {
        "order_id": "DDN20260007",
        "tracking_number": "ZTO2026061907",
        "carrier": "中通快递",
        "status": "派送异常",
        "estimated_delivery": date(2026, 6, 23),
        "latest_event": "收件地址无法联系，快件暂存网点",
        "events": [
            (datetime(2026, 6, 23, 10, 20), "收件地址无法联系，快件暂存网点"),
            (datetime(2026, 6, 23, 8, 15), "快件正在派送"),
            (datetime(2026, 6, 22, 23, 40), "快件到达杭州滨江网点"),
        ],
    },
    {
        "order_id": "DDN20260008",
        "tracking_number": "STO2026050108",
        "carrier": "申通快递",
        "status": "已签收",
        "estimated_delivery": date(2026, 5, 5),
        "latest_event": "订单已签收超过售后期限",
        "events": [
            (datetime(2026, 5, 5, 12, 35), "本人签收"),
            (datetime(2026, 5, 5, 8, 25), "杭州滨江区派件中"),
            (datetime(2026, 5, 4, 18, 45), "快件到达杭州转运中心"),
        ],
    },
    {
        "order_id": "DDN20260009",
        "tracking_number": "EMS2026061709",
        "carrier": "中国邮政 EMS",
        "status": "运输异常",
        "estimated_delivery": date(2026, 6, 24),
        "latest_event": "受天气影响，航班延误，预计晚到 1 天",
        "events": [
            (datetime(2026, 6, 22, 14, 10), "受天气影响，航班延误，预计晚到 1 天"),
            (datetime(2026, 6, 21, 6, 30), "邮件离开广州航空中心"),
            (datetime(2026, 6, 18, 17, 20), "商家已交寄"),
        ],
    },
    {
        "order_id": "DDN20260010",
        "tracking_number": "SF2026061410",
        "carrier": "顺丰速运",
        "status": "已签收",
        "estimated_delivery": date(2026, 6, 17),
        "latest_event": "商品已由前台代收",
        "events": [
            (datetime(2026, 6, 17, 15, 42), "商品已由前台代收"),
            (datetime(2026, 6, 17, 9, 18), "快件正在派送"),
            (datetime(2026, 6, 16, 20, 55), "快件到达杭州转运中心"),
        ],
    },
]

SEED_REFUNDS = [
    {
        "refund_request_id": "RFDEMO0001",
        "order_id": "DDN20260006",
        "reason": "佩戴后夹头，希望退货",
        "amount": Decimal("699.00"),
        "status": "审核中",
        "idempotency_key": "refund:DDN20260006",
        "created_at": datetime(2026, 6, 22, 10, 30),
    }
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
        for values in SEED_REFUNDS:
            session.add(RefundRequest(**values))


if __name__ == "__main__":
    seed_demo_data()
    print("数据库初始化完成。")
