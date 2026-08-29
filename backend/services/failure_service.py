import random
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
    Failure-handling demonstration service.

    Razorpay flow:
        Razorpay Test API
            -> fetch up to 100 payments
            -> preserve original records
            -> return/display original records
            -> STOP

    Scripted failure-demo flow:
        Synthetic batch
            -> generate 100 records
            -> inject 10 controlled faults
            -> validate
            -> quarantine invalid records
            -> process 90 valid records

    IMPORTANT:
    Real Razorpay Test Mode records are never fault-injected,
    modified, quarantined, or sent to model inference by the
    Razorpay fetch endpoint.
    """

    RAZORPAY_URL = "https://api.razorpay.com/v1/payments"
    BATCH_SIZE = 100
    FAULT_INJECTION_COUNT = 10

    async def simulate_malformed_batch(self) -> dict:
        return await self.ingest_synthetic_razorpay_batch()

    async def ingest_razorpay_batch(self) -> dict:
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        batch_id = (
            f"RP-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        started_at = datetime.now(timezone.utc).isoformat()

        payments = await self._fetch_razorpay_payments()

        if not payments:
            raise RuntimeError(
                "Razorpay returned no payments. "
                "Create Test Mode payments before fetching the batch."
            )

        # Razorpay fetch endpoint:
        # - does not generate synthetic records
        # - does not inject faults
        # - does not validate
        # - does not quarantine
        # - does not call model inference
        #
        # It only returns the original Razorpay Test Mode records.

        payments = payments[: self.BATCH_SIZE]

        completed_at = datetime.now(timezone.utc).isoformat()

        audit_trail = [
            self._audit(
                "Batch fetched from Razorpay",
                f"{len(payments)} original Test Mode payments fetched",
                request_id,
                batch_id,
            )
        ]

        return {
            "status": "RAZORPAY_FETCH_SUCCESS",
            "source": "razorpay",
            "environment": "test",

            "batch_id": batch_id,
            "request_id": request_id,

            "started_at": started_at,
            "completed_at": completed_at,

            "batch_size": len(payments),

            # No failure handling is performed on the Razorpay tab.
            "malformed_rows": 0,
            "quarantined": 0,
            "valid_processed": 0,
            "human_review_routed": 0,

            # IMPORTANT:
            # Frontend displays this directly.
            "payments": payments,

            "quarantined_records": [],

            "audit_trail": audit_trail,

            "safety": {
                "malformed_entered_investigation_pipeline": False,
                "quarantined_before_model_inference": False,
                "human_review_required": False,
                "sent_to_model_inference": False,
                "original_razorpay_data_preserved": True,
            },

            "fault_injection": {
                "enabled": False,
                "count": 0,
                "description": (
                    "Fault injection is disabled for the live "
                    "Razorpay Test API fetch."
                ),
            },
        }

    async def _fetch_razorpay_payments(
        self,
    ) -> list[dict[str, Any]]:

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
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

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
    def _urlopen_json(
        request: Request,
    ) -> dict[str, Any]:

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
        Create a separate working copy for fault injection.

        The original Razorpay payment is never modified.
        """

        original_record = dict(payment)
        working_record = dict(payment)

        if index < self.FAULT_INJECTION_COUNT:
            working_record["_ringwatch_demo_fault"] = True

            # Deliberately corrupt different fields so the demo
            # represents realistic data-quality failures.
            fault_type = index % 4

            if fault_type == 0:
                working_record["_ringwatch_original_field"] = "amount"
                working_record["amount"] = None

            elif fault_type == 1:
                working_record["_ringwatch_original_field"] = "currency"
                working_record["currency"] = None

            elif fault_type == 2:
                working_record["_ringwatch_original_field"] = "status"
                working_record["status"] = None

            else:
                working_record["_ringwatch_original_field"] = "id"
                working_record["id"] = None

        else:
            working_record["_ringwatch_demo_fault"] = False

        # Keep the original Razorpay record attached so the
        # quarantine report can show what actually arrived.
        working_record["_ringwatch_original_input"] = original_record

        return working_record

    @staticmethod
    def _validate_payment(
        record: dict[str, Any],
    ) -> dict[str, Any]:

        errors: list[dict[str, str]] = []

        payment_id = record.get("id")

        if not payment_id or not isinstance(payment_id, str):
            errors.append(
                {
                    "field": "id",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Payment ID is missing or invalid.",
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

        if not currency or not isinstance(currency, str):
            errors.append(
                {
                    "field": "currency",
                    "code": "MISSING_CURRENCY",
                    "message": "Currency is missing or invalid.",
                }
            )

        status = record.get("status")

        if not status or not isinstance(status, str):
            errors.append(
                {
                    "field": "status",
                    "code": "MISSING_STATUS",
                    "message": "Payment status is missing or invalid.",
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

        original_record = record.get(
        "_ringwatch_original_input",
        record,
        )


        return {
            "row_number": row_number,
            "record_id": record.get("id"),
            "status": "QUARANTINED",
            "action": "HUMAN_REVIEW",
            "request_id": request_id,
            "batch_id": batch_id,
            "failed_fields": validation["errors"],
            "original_input": {
            "id": original_record.get("id"),
            "entity": original_record.get("entity"),
            "amount": original_record.get("amount"),
            "currency": original_record.get("currency"),
            "status": original_record.get("status"),
            "method": original_record.get("method"),
            "order_id": original_record.get("order_id"),
            "description": original_record.get("description"),
            "email": FailureDemoService._mask_email(
                original_record.get("email")
            ),
            "contact": FailureDemoService._mask_contact(
                original_record.get("contact")
            ),
            "notes": {
                "address": (original_record.get("notes") or {}).get("address"),
            },
        },
        "validated_input": {
            "amount": record.get("amount"),
        },
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
    def _mask_email(
        value: Any,
    ) -> str | None:

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
    def _mask_contact(
        value: Any,
    ) -> str | None:

        if not value or not isinstance(value, str):
            return None

        digits = "".join(
            ch for ch in value
            if ch.isdigit()
        )

        if len(digits) < 4:
            return "***"

        return f"***{digits[-4:]}"

    async def ingest_synthetic_razorpay_batch(
        self,
    ) -> dict:

        request_id = f"req_{uuid.uuid4().hex[:12]}"

        batch_id = (
            f"RP-DEMO-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        started_at = datetime.now(timezone.utc).isoformat()

        payments = [
            self._generate_synthetic_payment(index)
            for index in range(
                1,
                self.BATCH_SIZE + 1,
            )
        ]

        audit_trail = [
            self._audit(
                "Synthetic Razorpay batch generated",
                f"{len(payments)} payments",
                request_id,
                batch_id,
            )
        ]

        working_batch = [
            self._inject_demo_fault(
                payment,
                index,
            )
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

        audit_trail.extend(
            [
                self._audit(
                    "Validation completed",
                    f"{malformed_count} records failed validation",
                    request_id,
                    batch_id,
                ),
                self._audit(
                    "Quarantined",
                    f"{malformed_count} records",
                    request_id,
                    batch_id,
                ),
                self._audit(
                    "Human review routed",
                    f"{malformed_count} records",
                    request_id,
                    batch_id,
                ),
                self._audit(
                    "Valid rows processed",
                    f"{valid_count} records",
                    request_id,
                    batch_id,
                ),
            ]
        )

        return {
            "status": "GRACEFUL_FAILURE_HANDLED",
            "source": "razorpay_style_synthetic",
            "environment": "demo",
            "batch_id": batch_id,
            "request_id": request_id,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),

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
                    f"{min(self.FAULT_INJECTION_COUNT, len(working_batch))} "
                    "synthetic Razorpay-style records were deliberately "
                    "corrupted after ingestion."
                ),
            },
        }

    @staticmethod
    def _generate_synthetic_payment(
        index: int,
    ) -> dict[str, Any]:

        return {
            "id": f"pay_demo_{uuid.uuid4().hex[:14]}",
            "entity": "payment",
            "amount": random.choice(
                [
                    49900,
                    99900,
                    149900,
                    249900,
                    499900,
                ]
            ),
            "currency": "INR",
            "status": "captured",
            "method": random.choice(
                [
                    "upi",
                    "card",
                    "netbanking",
                ]
            ),
            "order_id": (
                f"order_demo_{uuid.uuid4().hex[:14]}"
            ),
            "description": (
                f"RingWatch synthetic payment {index}"
            ),
            "email": (
                f"demo{index}@example.com"
            ),
            "contact": (
                f"+9198{index:08d}"
            ),
        }