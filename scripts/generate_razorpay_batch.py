import json
import uuid
import random
from datetime import datetime, timezone


OUTPUT_FILE = "razorpay_test_batch.json"
BATCH_SIZE = 100


def generate_payment(index: int) -> dict:
    payment_id = f"pay_demo_{uuid.uuid4().hex[:14]}"
    order_id = f"order_demo_{uuid.uuid4().hex[:14]}"

    amount = random.choice(
        [
            49900,
            99900,
            149900,
            249900,
            499900,
        ]
    )

    return {
        "id": payment_id,
        "entity": "payment",
        "amount": amount,
        "currency": "INR",
        "status": "captured",
        "method": random.choice(
            [
                "upi",
                "card",
                "netbanking",
            ]
        ),
        "order_id": order_id,
        "description": f"RingWatch demo payment {index}",
        "email": f"demo{index}@example.com",
        "contact": f"+9198{index:08d}",
        "created_at": int(
            datetime.now(timezone.utc).timestamp()
        ),
    }


def main():
    payments = [
        generate_payment(index)
        for index in range(1, BATCH_SIZE + 1)
    ]

    payload = {
        "entity": "collection",
        "count": len(payments),
        "items": payments,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            indent=2,
        )

    print(f"Generated {len(payments)} Razorpay-style payments.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()