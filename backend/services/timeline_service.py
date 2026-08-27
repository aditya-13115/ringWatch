from typing import Any
import pandas as pd
from backend.repositories.event_repository import EventRepository


class TimelineService:
    def __init__(self, event_repo: EventRepository):
        self.event_repo = event_repo

    async def get_timeline(self, account_id: str) -> list[dict[str, Any]]:
        events = []

        orders = self.event_repo.get_orders_for_account(account_id)
        for _, order in orders.iterrows():
            events.append(
                {
                    "timestamp": order["order_timestamp"],
                    "event": "Order placed",
                    "details": f"Order {order['order_id']}, amount ₹{order['amount']}",
                }
            )
            if pd.notna(order["delivery_timestamp"]):
                events.append(
                    {
                        "timestamp": order["delivery_timestamp"],
                        "event": "Order delivered",
                        "details": f"Order {order['order_id']}",
                    }
                )
            if pd.notna(order["return_timestamp"]) and order["return_flag"]:
                events.append(
                    {
                        "timestamp": order["return_timestamp"],
                        "event": "Return requested",
                        "details": f"Order {order['order_id']}, reason {order['return_reason_code']}",
                    }
                )
            if pd.notna(order["refund_timestamp"]) and order["refund_flag"]:
                events.append(
                    {
                        "timestamp": order["refund_timestamp"],
                        "event": "Refund processed",
                        "details": f"Order {order['order_id']}, amount ₹{order['refund_amount']}",
                    }
                )

        refunds = self.event_repo.get_refunds_for_account(account_id)
        for _, refund in refunds.iterrows():
            # might duplicate; skip if already captured via order
            pass

        disputes = self.event_repo.get_disputes_for_account(account_id)
        for _, dispute in disputes.iterrows():
            events.append(
                {
                    "timestamp": dispute["dispute_created_at"],
                    "event": "Dispute created",
                    "details": f"Reason {dispute['dispute_reason_code']}",
                }
            )

        # Normalize all timestamps to pandas Timestamp before sorting
        for event in events:
            event["timestamp"] = pd.to_datetime(event["timestamp"])

        events.sort(key=lambda x: x["timestamp"])

        return events