import uuid
from datetime import datetime, timezone


class FailureDemoService:
    async def simulate_malformed_batch(self) -> dict:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        audit_trail = [
            {
                "timestamp": now,
                "event": "Batch received",
                "details": "100 rows",
                "request_id": request_id,
            },
            {
                "timestamp": now,
                "event": "Malformed address detected",
                "details": "5 rows",
                "request_id": request_id,
            },
            {
                "timestamp": now,
                "event": "Quarantined",
                "details": "5 rows",
                "request_id": request_id,
            },
            {
                "timestamp": now,
                "event": "Human review routed",
                "details": "5 rows",
                "request_id": request_id,
            },
            {
                "timestamp": now,
                "event": "Valid rows processed",
                "details": "95 rows",
                "request_id": request_id,
            },
        ]

        return {
            "status": "GRACEFUL_FAILURE_HANDLED",
            "batch_size": 100,
            "malformed_rows": 5,
            "quarantined": 5,
            "valid_processed": 95,
            "human_review_routed": 5,
            "request_id": request_id,
            "audit_trail": audit_trail,
        }
