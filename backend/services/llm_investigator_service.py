import json
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from groq import AsyncGroq

from backend.core.config import get_settings
from backend.core.concurrency import LLM_SEMAPHORE
from backend.core.exceptions import LLMServiceError
from backend.repositories.explainability_repository import ExplainabilityRepository
from backend.repositories.feature_repository import FeatureRepository
from backend.repositories.event_repository import EventRepository
from backend.services.action_service import ActionService


class LLMInvestigatorService:
    def __init__(
        self,
        explainability_repo: ExplainabilityRepository,
        feature_repo: FeatureRepository,
        event_repo: EventRepository,
        action_service: ActionService,
    ):
        self.explainability_repo = explainability_repo
        self.feature_repo = feature_repo
        self.event_repo = event_repo
        self.action_service = action_service
        self.settings = get_settings()
        self.client = AsyncGroq(api_key=self.settings.groq_api_key)

    async def investigate(self, account_id: str) -> dict:
        async with LLM_SEMAPHORE:
            try:
                return await self._run_groq_investigation(account_id)
            except Exception as exc:
                # Fallback to deterministic investigation
                return await self._fallback_deterministic(account_id, error=str(exc))

    async def _run_groq_investigation(self, account_id: str) -> dict:
        if not self.settings.groq_api_key:
            return await self._fallback_deterministic(account_id, error="Groq API key not configured")

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_related_accounts",
                    "description": "Get accounts related to the given account via graph edges.",
                    "parameters": {
                        "type": "object",
                        "properties": {"account_id": {"type": "string"}},
                        "required": ["account_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_shared_attributes",
                    "description": "Get shared entities (device, address, phone, instrument) for a set of account IDs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            }
                        },
                        "required": ["account_ids"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_evidence_availability",
                    "description": "Check which Razorpay evidence fields are available/missing for an account.",
                    "parameters": {
                        "type": "object",
                        "properties": {"account_id": {"type": "string"}},
                        "required": ["account_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_financial_exposure",
                    "description": "Calculate gross order value, refunds, pending refunds, and potential exposure for an account.",
                    "parameters": {
                        "type": "object",
                        "properties": {"account_id": {"type": "string"}},
                        "required": ["account_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_merchant_policy",
                    "description": "Get the merchant's refund/dispute policy for a given category.",
                    "parameters": {
                        "type": "object",
                        "properties": {"category": {"type": "string"}},
                        "required": ["category"],
                    },
                },
            },
        ]

        system_prompt = (
            "You are an investigator assistant for RingWatch, a post-delivery "
            "refund/return abuse detection system for merchants. "
            "Use the provided tools to gather information about the flagged account. "
            "Then produce a concise investigation report with key findings, evidence gaps, "
            "uncertainties, and a recommended action from the allowed list: "
            "LOW, MEDIUM, HIGH, CRITICAL. "
            "Do not invent facts. Only use tool outputs. "
            "Do not treat model score as calibrated probability. "
            "Do not make final financial decisions. The final action is determined by the system."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Investigate account {account_id}."},
        ]

        tool_calls_log = []

        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.settings.groq_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=1024,
                )
                message = response.choices[0].message
                messages.append(message)

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)

                        tool_result = await self._execute_tool(
                            function_name, arguments
                        )

                        tool_calls_log.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "tool": function_name,
                                "args": arguments,
                                "result_summary": str(tool_result)[:200],
                            }
                        )

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(tool_result),
                            }
                        )

                    final_response = await self.client.chat.completions.create(
                        model=self.settings.groq_model,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=1024,
                    )
                    final_message = final_response.choices[0].message.content

                    # Attempt to parse structured JSON; if fails, treat as plain text
                    try:
                        parsed = json.loads(final_message)
                        summary = parsed.get("summary", final_message)
                        key_findings = parsed.get("key_findings", [])
                        evidence_gaps = parsed.get("evidence_gaps", [])
                        uncertainties = parsed.get("uncertainties", [])
                        confidence = parsed.get("confidence", "LOW")
                    except json.JSONDecodeError:
                        summary = final_message
                        key_findings = []
                        evidence_gaps = []
                        uncertainties = []
                        confidence = "LOW"

                    # Deterministic action from action service
                    action = await self.action_service.get_action(account_id)

                    result = {
                        "account_id": account_id,
                        "source": "llm",
                        "summary": summary,
                        "key_findings": key_findings,
                        "evidence_gaps": evidence_gaps,
                        "uncertainties": uncertainties,
                        "confidence": confidence,
                        "tool_calls": tool_calls_log,
                        "recommended_action": action.action_description,
                        "action_source": "deterministic_policy",
                    }

                    # Save audit
                    await self._save_investigation_audit(result, success=True)
                    return result

                else:
                    # No tool calls, just content
                    content = message.content
                    try:
                        parsed = json.loads(content)
                        summary = parsed.get("summary", content)
                        key_findings = parsed.get("key_findings", [])
                        evidence_gaps = parsed.get("evidence_gaps", [])
                        uncertainties = parsed.get("uncertainties", [])
                        confidence = parsed.get("confidence", "LOW")
                    except json.JSONDecodeError:
                        summary = content
                        key_findings = []
                        evidence_gaps = []
                        uncertainties = []
                        confidence = "LOW"

                    action = await self.action_service.get_action(account_id)

                    result = {
                        "account_id": account_id,
                        "source": "llm",
                        "summary": summary,
                        "key_findings": key_findings,
                        "evidence_gaps": evidence_gaps,
                        "uncertainties": uncertainties,
                        "confidence": confidence,
                        "tool_calls": tool_calls_log,
                        "recommended_action": action.action_description,
                        "action_source": "deterministic_policy",
                    }
                    await self._save_investigation_audit(result, success=True)
                    return result

            except Exception as exc:
                if attempt == self.settings.llm_max_retries:
                    return await self._fallback_deterministic(account_id, error=str(exc))
                continue

        return await self._fallback_deterministic(account_id, error="Max retries exceeded")

    async def _execute_tool(self, function_name: str, args: dict) -> Any:
        if function_name == "get_related_accounts":
            graph_evidence = self.explainability_repo.get_graph_evidence()
            row = graph_evidence[graph_evidence["account_id"] == args["account_id"]]
            if row.empty:
                return {"linked_accounts": []}
            linked = row.iloc[0]["linked_accounts"]
            if pd.isna(linked):
                return {"linked_accounts": []}
            accounts = []
            for rel in str(linked).split("|"):
                rel = rel.strip()
                if "->" in rel:
                    _, linked_account = rel.split("->", 1)
                    accounts.append(linked_account.strip())
            return {"linked_accounts": accounts}

        elif function_name == "get_shared_attributes":
            account_ids = args.get("account_ids", [])
            shared_attrs = {"device": [], "address": [], "phone": [], "instrument": []}
            if not account_ids:
                return shared_attrs

            # Use graph edges to find shared entities
            # This is a simplification: use explainability repo's graph_evidence or feature repo
            # We'll leverage the feature repository to get shared counts
            features = self.feature_repo.get_features()
            for account_id in account_ids:
                row = features[features["account_id"] == account_id]
                if not row.empty:
                    row = row.iloc[0]
                    for entity in ["shared_device_count", "shared_address_count",
                                   "shared_phone_count", "shared_instrument_count"]:
                        count = row.get(entity, 0)
                        if count > 0:
                            shared_attrs[entity.replace("shared_", "").replace("_count", "")].append({
                                "account_id": account_id,
                                "count": int(count)
                            })
            return shared_attrs

        elif function_name == "check_evidence_availability":
            evidence_df = self.explainability_repo.get_evidence()
            row = evidence_df[evidence_df["account_id"] == args["account_id"]]
            if row.empty:
                return {"has_dispute_at_cutoff": False, "fields": {}}
            return {
                "has_dispute_at_cutoff": bool(row.iloc[0]["has_dispute_at_cutoff"]),
                "fields": {
                    field: row.iloc[0][field]
                    for field in [
                        "proof_of_service",
                        "explanation_letter",
                        "refund_confirmation",
                        "access_activity_log",
                        "refund_cancellation_policy",
                        "terms_and_conditions",
                    ]
                },
            }

        elif function_name == "calculate_financial_exposure":
            features = self.feature_repo.get_features()
            row = features[features["account_id"] == args["account_id"]]
            if row.empty:
                return {"gross_order_value": 0, "refund_amount": 0, "potential_exposure": 0}
            total_amount = row.iloc[0].get("total_amount", 0)
            total_refund_amount = row.iloc[0].get("total_refund_amount", 0)
            potential_exposure = total_amount - total_refund_amount
            return {
                "gross_order_value": total_amount,
                "refund_amount": total_refund_amount,
                "potential_exposure": potential_exposure,
            }

        elif function_name == "get_merchant_policy":
            # In a real system, this would query a policy table.
            # For now, return a deterministic policy based on category.
            category = args.get("category", "default")
            policies = {
                "fashion": "Manual review required for refunds over ₹5000",
                "electronics": "Proof of delivery and return condition required",
                "default": "Standard refund policy: verify return reason before processing",
            }
            return {"policy": policies.get(category, policies["default"])}

        else:
            raise ValueError(f"Unknown tool: {function_name}")

    async def _save_investigation_audit(self, result: dict, success: bool = True):
        # Append to existing audit log or create new record
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_id": result["account_id"],
            "model_version": "LightGBM_Model_B",
            "proba": result.get("proba", None),
            "rank": result.get("rank", None),
            "risk_tier": result.get("risk_tier", None),
            "top_k_flag": True,
            "action_recommended": result["recommended_action"],
            "case_report_generated": True,
            "investigation_source": result["source"],
            "tool_calls": result.get("tool_calls", []),
            "summary": result.get("summary", ""),
            "action_source": result.get("action_source", "deterministic_policy"),
        }

        # Save to a new file or existing audit CSV (append)
        try:
            audit_path = self.explainability_repo.audit_path
            df = pd.read_csv(audit_path)
            df = pd.concat([df, pd.DataFrame([audit_entry])], ignore_index=True)
            df.to_csv(audit_path, index=False)
        except Exception:
            # If fails, just log
            pass

    async def _fallback_deterministic(self, account_id: str, error: str = "") -> dict:
        report = self.explainability_repo.get_reports()
        row = report[report["account_id"] == account_id]
        case_report = str(row.iloc[0]["case_report_text"]) if not row.empty else ""

        action = await self.action_service.get_action(account_id)

        result = {
            "account_id": account_id,
            "source": "deterministic",
            "summary": case_report.split("\n")[0] if case_report else "",
            "key_findings": [],
            "evidence_gaps": [],
            "uncertainties": [],
            "confidence": "LOW",
            "tool_calls": [],
            "recommended_action": action.action_description,
            "action_source": "deterministic_policy",
            "error": error,
        }

        # Save audit as fallback
        await self._save_investigation_audit(result, success=False)
        return result