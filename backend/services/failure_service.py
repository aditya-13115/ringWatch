import asyncio
import base64
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from backend.core.config import get_settings

settings = get_settings()

key_id = settings.razorpay_key_id
key_secret = settings.razorpay_key_secret

class FailureDemoService:
    """
    Razorpay-backed ingestion and failure-handling demo.

    Flow:
        Razorpay Test API
            -> fetch 100 payments
            -> normalize
            -> controlled demo fault injection on 10 records
            -> validate
            -> quarantine invalid records
            -> process valid records

    IMPORTANT:
    The 10 malformed records are deliberately fault-injected AFTER
    receiving the real Razorpay batch. They are not claimed to be
    malformed records originally returned by Razorpay.
    """

    RAZORPAY_URL = "https://api.razorpay.com/v1/payments"
    BATCH_SIZE = 100
    FAULT_INJECTION_COUNT = 10

    async def simulate_malformed_batch(self) -> dict:
        return await self.ingest_razorpay_batch()

    async def ingest_razorpay_batch(self) -> dict:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        batch_id = f"RP-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6].upper()}"
        started_at = datetime.now(timezone.utc).isoformat()

        payments = await self._fetch_razorpay_payments()

        if not payments:
            raise RuntimeError(
                "Razorpay returned no payments. Create Test Mode payments "
                "before running the failure demo."
            )

        # Razorpay permits up to 100 payments per request.
        # We process the returned batch as-is.
        payments = payments[: self.BATCH_SIZE]

        audit_trail: list[dict[str, Any]] = []

        audit_trail.append(
            self._audit(
                "Batch received from Razorpay",
                f"{len(payments)} payments",
                request_id,
                batch_id,
            )
        )

        # Fault injection is deterministic for the demo:
        # first 10 records are deliberately made invalid.
        working_batch = [
            self._inject_demo_fault(payment, index)
            for index, payment in enumerate(payments)
        ]

        processed_records: list[dict[str, Any]] = []
        quarantined_records: list[dict[str, Any]] = []

        for index, record in enumerate(working_batch):
            validation = self._validate_payment(record)

            if not validation["valid"]:
                quarantined_records.append(
                    self._build_quarantine_record(
                        record=record,
                        row_number=index + 1,
                        validation=validation,
                        request_id=request_id,
                        batch_id=batch_id,
                    )
                )
            else:
                processed_records.append(
                    self._build_processed_record(
                        record=record,
                        row_number=index + 1,
                        request_id=request_id,
                        batch_id=batch_id,
                    )
                )

        malformed_count = len(quarantined_records)
        valid_count = len(processed_records)

        audit_trail.append(
            self._audit(
                "Validation completed",
                f"{malformed_count} records failed validation",
                request_id,
                batch_id,
            )
        )

        audit_trail.append(
            self._audit(
                "Quarantined",
                f"{malformed_count} records",
                request_id,
                batch_id,
            )
        )

        audit_trail.append(
            self._audit(
                "Human review routed",
                f"{malformed_count} records",
                request_id,
                batch_id,
            )
        )

        audit_trail.append(
            self._audit(
                "Valid rows processed",
                f"{valid_count} records",
                request_id,
                batch_id,
            )
        )

        completed_at = datetime.now(timezone.utc).isoformat()

        return {
            "status": (
                "GRACEFUL_FAILURE_HANDLED"
                if malformed_count > 0
                else "SUCCESS"
            ),
            "source": "razorpay",
            "environment": "test",
            "batch_id": batch_id,
            "request_id": request_id,
            "started_at": started_at,
            "completed_at": completed_at,

            "batch_size": len(working_batch),
            "malformed_rows": malformed_count,
            "quarantined": len(quarantined_records),
            "valid_processed": valid_count,
            "human_review_routed": len(quarantined_records),

            "processed_records": processed_records,
            "quarantined_records": quarantined_records,

            "audit_trail": audit_trail,

            "safety": {
                "malformed_entered_investigation_pipeline": False,
                "quarantined_before_model_inference": True,
                "human_review_required": malformed_count > 0,
            },

            "fault_injection": {
                "enabled": True,
                "count": min(
                    self.FAULT_INJECTION_COUNT,
                    len(working_batch),
                ),
                "description": (
                    "Ten records are deliberately corrupted after "
                    "Razorpay ingestion to demonstrate quarantine handling."
                ),
            },
        }

    async def _fetch_razorpay_payments(self) -> list[dict[str, Any]]:
        
        if not key_id or not key_secret:
            raise RuntimeError(
                "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured."
            )

        query = urlencode(
            {
                "count": self.BATCH_SIZE,
                "skip": 0,
            }
        )

        url = f"{self.RAZORPAY_URL}?{query}"

        token = base64.b64encode(
            f"{key_id}:{key_secret}".encode("utf-8")
        ).decode("ascii")

        request = Request(
            url,
            headers={
                "Authorization": f"Basic {token}",
                "Accept": "application/json",
                "User-Agent": "RingWatch/1.0",
            },
            method="GET",
        )

        try:
            response = await asyncio.to_thread(
                self._urlopen_json,
                request,
            )
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")

            raise RuntimeError(
                f"Razorpay API returned HTTP {exc.code}: {body}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Could not reach Razorpay API: {exc.reason}"
            ) from exc

        except Exception as exc:
            raise RuntimeError(
                f"Razorpay API request failed: {exc}"
            ) from exc

        items = response.get("items", [])

        if not isinstance(items, list):
            raise RuntimeError(
                "Unexpected Razorpay response: 'items' is not a list."
            )

        return items

    @staticmethod
    def _urlopen_json(request: Request) -> dict[str, Any]:
        with urlopen(request, timeout=20) as response:
            import json

            return json.loads(
                response.read().decode("utf-8")
            )

    def _inject_demo_fault(
        self,
        payment: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        """
        Fault injection happens AFTER Razorpay ingestion.

        This guarantees a deterministic 90/10 demo without claiming
        that Razorpay returned malformed data.

        We copy the payment before modifying it.
        """
        record = dict(payment)

        if index < self.FAULT_INJECTION_COUNT:
            record["_ringwatch_demo_fault"] = True
            record["_ringwatch_original_field"] = "notes.address"

            notes = dict(record.get("notes") or {})

            # Deliberately corrupt the address field.
            notes["address"] = None

            record["notes"] = notes

        else:
            record["_ringwatch_demo_fault"] = False

        return record

    @staticmethod
    def _validate_payment(
        record: dict[str, Any],
    ) -> dict[str, Any]:
        errors: list[dict[str, str]] = []

        payment_id = record.get("id")

        if not payment_id:
            errors.append(
                {
                    "field": "id",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Payment ID is missing.",
                }
            )

        amount = record.get("amount")

        if not isinstance(amount, (int, float)) or amount <= 0:
            errors.append(
                {
                    "field": "amount",
                    "code": "INVALID_AMOUNT",
                    "message": "Payment amount must be a positive number.",
                }
            )

        currency = record.get("currency")

        if not currency:
            errors.append(
                {
                    "field": "currency",
                    "code": "MISSING_CURRENCY",
                    "message": "Currency is missing.",
                }
            )

        notes = record.get("notes") or {}

        # This is the demo's data-quality rule.
        address = notes.get("address")

        if address is None or not isinstance(address, str) or not address.strip():
            errors.append(
                {
                    "field": "notes.address",
                    "code": "INVALID_ADDRESS",
                    "message": "Address is missing or invalid.",
                }
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    @staticmethod
    def _build_quarantine_record(
        record: dict[str, Any],
        row_number: int,
        validation: dict[str, Any],
        request_id: str,
        batch_id: str,
    ) -> dict[str, Any]:
        notes = record.get("notes") or {}

        # Do not expose payment credentials or sensitive payment data.
        safe_input = {
            "id": record.get("id"),
            "entity": record.get("entity"),
            "amount": record.get("amount"),
            "currency": record.get("currency"),
            "status": record.get("status"),
            "method": record.get("method"),
            "order_id": record.get("order_id"),
            "description": record.get("description"),
            "email": FailureDemoService._mask_email(
                record.get("email")
            ),
            "contact": FailureDemoService._mask_contact(
                record.get("contact")
            ),
            "notes": {
                "address": notes.get("address"),
            },
        }

        return {
            "row_number": row_number,
            "record_id": record.get("id"),
            "status": "QUARANTINED",
            "action": "HUMAN_REVIEW",
            "request_id": request_id,
            "batch_id": batch_id,
            "failed_fields": validation["errors"],
            "original_input": safe_input,
            "fault_injected": bool(
                record.get("_ringwatch_demo_fault")
            ),
            "quarantine_reason": (
                validation["errors"][0]["message"]
                if validation["errors"]
                else "Validation failure"
            ),
        }

    @staticmethod
    def _build_processed_record(
        record: dict[str, Any],
        row_number: int,
        request_id: str,
        batch_id: str,
    ) -> dict[str, Any]:
        return {
            "row_number": row_number,
            "record_id": record.get("id"),
            "status": "PROCESSED",
            "request_id": request_id,
            "batch_id": batch_id,
            "amount": record.get("amount"),
            "currency": record.get("currency"),
            "payment_status": record.get("status"),
            "method": record.get("method"),
        }

    @staticmethod
    def _audit(
        event: str,
        details: str,
        request_id: str,
        batch_id: str,
    ) -> dict[str, str]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details,
            "request_id": request_id,
            "batch_id": batch_id,
        }

    @staticmethod
    def _mask_email(value: Any) -> str | None:
        if not value or not isinstance(value, str):
            return None

        if "@" not in value:
            return "***"

        name, domain = value.split("@", 1)

        if len(name) <= 2:
            masked_name = "*" * len(name)
        else:
            masked_name = name[0] + "***" + name[-1]

        return f"{masked_name}@{domain}"

    @staticmethod
    def _mask_contact(value: Any) -> str | None:
        if not value or not isinstance(value, str):
            return None

        digits = "".join(ch for ch in value if ch.isdigit())

        if len(digits) < 4:
            return "***"

        return f"***{digits[-4:]}"