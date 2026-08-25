from pathlib import Path
import pandas as pd


class EventRepository:
    def __init__(self, data_dir: Path):
        self.orders = pd.read_csv(
            data_dir / "orders.csv",
            parse_dates=[
                "order_timestamp",
                "delivery_timestamp",
                "return_timestamp",
                "refund_timestamp",
            ],
        )
        self.refunds = pd.read_csv(
            data_dir / "refunds.csv",
            parse_dates=["refund_timestamp"],
        )
        self.disputes = pd.read_csv(
            data_dir / "disputes.csv",
            parse_dates=["dispute_created_at"],
        )

    def get_orders_for_account(self, account_id: str) -> pd.DataFrame:
        return self.orders[self.orders["account_id"] == account_id].copy()

    def get_refunds_for_account(self, account_id: str) -> pd.DataFrame:
        return self.refunds[self.refunds["account_id"] == account_id].copy()

    def get_disputes_for_account(self, account_id: str) -> pd.DataFrame:
        return self.disputes[self.disputes["account_id"] == account_id].copy()
