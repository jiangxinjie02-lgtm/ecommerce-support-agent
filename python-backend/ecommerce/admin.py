from __future__ import annotations

import argparse
import sys

from sqlalchemy import func, select

from .database import database_health, session_scope
from .models import Logistics, Order, RefundRequest
from .seed import seed_demo_data


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def show_stats() -> None:
    seed_demo_data()
    with session_scope() as session:
        order_count = session.scalar(select(func.count()).select_from(Order))
        logistics_count = session.scalar(select(func.count()).select_from(Logistics))
        refund_count = session.scalar(select(func.count()).select_from(RefundRequest))
    health = database_health()
    print(f"数据库：{health['dialect']} / {health['status']}")
    print(f"订单：{order_count}")
    print(f"物流：{logistics_count}")
    print(f"退款申请：{refund_count}")


def list_orders() -> None:
    seed_demo_data()
    with session_scope() as session:
        orders = session.scalars(select(Order).order_by(Order.created_at.desc())).all()
        for order in orders:
            print(
                f"{order.order_id} | {order.customer_name} | {order.product_name} | "
                f"CNY {order.amount} | {order.order_status}"
            )


def list_refunds() -> None:
    seed_demo_data()
    with session_scope() as session:
        refunds = session.scalars(
            select(RefundRequest).order_by(RefundRequest.created_at.desc())
        ).all()
        if not refunds:
            print("暂无退款申请")
            return
        for refund in refunds:
            print(
                f"{refund.refund_request_id} | {refund.order_id} | "
                f"CNY {refund.amount} | {refund.status} | {refund.reason}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="电商售后 Agent 数据库管理工具")
    parser.add_argument(
        "command",
        choices=["init", "reset", "stats", "orders", "refunds"],
    )
    args = parser.parse_args()

    if args.command == "init":
        seed_demo_data()
        print("数据库初始化完成")
    elif args.command == "reset":
        seed_demo_data(reset=True)
        print("数据库已重置并写入演示数据")
    elif args.command == "stats":
        show_stats()
    elif args.command == "orders":
        list_orders()
    elif args.command == "refunds":
        list_refunds()


if __name__ == "__main__":
    main()
