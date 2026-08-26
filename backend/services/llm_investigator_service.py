import json
import re
from datetime import datetime, timezone
from typing import Any
import time
import pandas as pd
from groq import AsyncGroq

from backend.core.config import get_settings
from backend.core.concurrency import LLM_SEMAPHORE
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
        self.executed_tools: set[str] = set()

    async def investigate(self, account_id: str) -> dict:
        async with LLM_SEMAPHORE:
            self.executed_tools.clear()
            start_time = time.perf_counter()
            try:
                return await self._run_investigation(account_id, start_time)
            except Exception as exc:
                try:
                    return await self._fallback_deterministic(
                        account_id,
                        error=str(exc),
                        start_time=start_time,
                    )
                except Exception as fallback_exc:
                    return {
                        "account_id": account_id,
                        "source": "deterministic",
                        "summary": "Investigation unavailable.",
                        "key_findings": [],
                        "evidence_gaps": [],
                        "uncertainties": [],
                        "confidence": "LOW",
                        "tool_calls": [],
                        "recommended_action": "Monitor",
                        "action_source": "deterministic_policy",
                        "error": str(fallback_exc),
                        "duration_seconds": round(time.perf_counter() - start_time, 2),
                        "completion_summary": None,
                    }

    async def _run_investigation(self, account_id: str, start_time: float) -> dict:
        if not self.settings.groq_api_key:
            return await self._fallback_deterministic(
                account_id, 
                error="Groq API key not configured",
                start_time=start_time,
            )

        # ----------------------------------------------------------------
        # Define tools for Groq
        # ----------------------------------------------------------------
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
                    "name": "get_account_timeline",
                    "description": "Get the order/return/refund/dispute timeline for an account.",
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

        # ----------------------------------------------------------------
        # Step 1: Pre-execute essential tools deterministically
        # ----------------------------------------------------------------
        tool_calls_log = []

        # 1. Related accounts
        related_result = await self._execute_tool(
            "get_related_accounts", {"account_id": account_id}
        )
        tool_calls_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": "get_related_accounts",
                "args": {"account_id": account_id},
                "result_summary": self._summarize_tool_result(
                    "get_related_accounts", related_result
                ),
            }
        )
        self.executed_tools.add("get_related_accounts")

        # 2. Shared attributes for related accounts
        related_ids = related_result.get("linked_accounts", [])
        shared_result = await self._execute_tool(
            "get_shared_attributes", {"account_ids": related_ids}
        )
        tool_calls_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": "get_shared_attributes",
                "args": {"account_ids": related_ids},
                "result_summary": self._summarize_tool_result(
                    "get_shared_attributes",
                    shared_result,
                ),
            }
        )
        self.executed_tools.add("get_shared_attributes")

        # 3. Evidence availability
        evidence_result = await self._execute_tool(
            "check_evidence_availability", {"account_id": account_id}
        )
        tool_calls_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": "check_evidence_availability",
                "args": {"account_id": account_id},
                "result_summary": self._summarize_tool_result(
                    "check_evidence_availability",
                    evidence_result,
                ),
            }
        )
        self.executed_tools.add("check_evidence_availability")

        # 4. Financial exposure
        exposure_result = await self._execute_tool(
            "calculate_financial_exposure", {"account_id": account_id}
        )
        tool_calls_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": "calculate_financial_exposure",
                "args": {"account_id": account_id},
                "result_summary": self._summarize_tool_result(
                    "calculate_financial_exposure",
                    exposure_result,
                ),
            }
        )
        self.executed_tools.add("calculate_financial_exposure")

        # 5. Account timeline
        timeline_result = await self._execute_tool(
            "get_account_timeline", {"account_id": account_id}
        )
        tool_calls_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": "get_account_timeline",
                "args": {"account_id": account_id},
                "result_summary": self._summarize_tool_result(
                    "get_account_timeline",
                    timeline_result,
                ),
            }
        )
        self.executed_tools.add("get_account_timeline")

        # 6. Merchant policy
        policy_result = await self._execute_tool(
            "get_merchant_policy", {"category": "default"}
        )
        tool_calls_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": "get_merchant_policy",
                "args": {"category": "default"},
                "result_summary": self._summarize_tool_result(
                    "get_merchant_policy",
                    policy_result,
                ),
            }
        )
        self.executed_tools.add("get_merchant_policy")

        # ----------------------------------------------------------------
        # Step 2: Build evidence packet and prompt
        # ----------------------------------------------------------------
        evidence_packet = {
            "account_id": account_id,
            "related_accounts": related_result,
            "shared_attributes": shared_result,
            "evidence": evidence_result,
            "financial_exposure": exposure_result,
            "timeline": timeline_result,
            "merchant_policy": policy_result,
        }

        system_prompt = (
            "You are an AI investigator for RingWatch, a post-delivery refund/return abuse detection system.\n"
            "You have already been provided with core investigation evidence.\n"
            "You may call additional tools if you need more information.\n"
            "After investigation, produce a JSON object with the following structure:\n"
            "{\n"
            '  "summary": "...",\n'
            '  "key_findings": ["...", "..."],\n'
            '  "evidence_gaps": ["..."],\n'
            '  "uncertainties": ["..."],\n'
            '  "confidence": "LOW|MEDIUM|HIGH"\n'
            "}\n"
            "Rules:\n"
            "- Do not invent facts.\n"
            "- Do not treat model score as calibrated probability.\n"
            "- Do not make final financial decisions.\n"
            "- Use only the provided evidence and tool outputs.\n"
            "- The final action is determined by the system's deterministic policy, not by you.\n"
            "- Use ₹ for Indian Rupees. Do not use $ or USD.\n"
            "- If has_dispute_at_cutoff is false, describe evidence gaps as "
            "'not yet applicable' rather than 'missing'.\n"
            "- Return ONLY the JSON object, no additional text.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Core evidence:\n{json.dumps(evidence_packet)}",
            },
        ]

        # ----------------------------------------------------------------
        # Step 3: Call Groq with tools (optional additional tools)
        # ----------------------------------------------------------------
        final_content = None

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

                        if function_name in self.executed_tools:
                            # Skip duplicate optional tool call
                            continue

                        self.executed_tools.add(function_name)

                        tool_result = await self._execute_tool(function_name, arguments)
                        tool_calls_log.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "tool": function_name,
                                "args": arguments,
                                "result_summary": self._summarize_tool_result(
                                    function_name,
                                    tool_result,
                                ),
                            }
                        )

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(tool_result),
                            }
                        )

                    # Final call with JSON response format (no tools)
                    final_response = await self.client.chat.completions.create(
                        model=self.settings.groq_model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=0.2,
                        max_tokens=1024,
                    )
                    final_content = final_response.choices[0].message.content
                else:
                    # No tool calls, but we can still request JSON
                    # However, we cannot use response_format with tools present, so we just take content
                    final_content = message.content

                break

            except Exception as exc:
                if attempt == self.settings.llm_max_retries:
                    return await self._fallback_deterministic(
                        account_id, 
                        error=f"LLM error: {exc}",
                        start_time=start_time,
                    )
                continue

        if final_content is None:
            return await self._fallback_deterministic(
                account_id, 
                error="No LLM response",
                start_time=start_time,
            )

        # ----------------------------------------------------------------
        # Step 4: Parse structured output
        # ----------------------------------------------------------------
        parsed = self._extract_json_from_text(final_content)
        if parsed is None:
            summary = final_content.strip()
            key_findings = []
            evidence_gaps = []
            uncertainties = []
            confidence = "LOW"
        else:
            summary = parsed.get("summary", "").strip()
            key_findings = parsed.get("key_findings", [])
            evidence_gaps = parsed.get("evidence_gaps", [])
            uncertainties = parsed.get("uncertainties", [])
            confidence = parsed.get("confidence", "LOW")

        # Normalize lists (handle string input)
        if isinstance(key_findings, str):
            key_findings = [key_findings]
        if isinstance(evidence_gaps, str):
            evidence_gaps = [evidence_gaps]
        if isinstance(uncertainties, str):
            uncertainties = [uncertainties]

        # Ensure lists contain only strings, converting if necessary
        key_findings = [str(item) for item in key_findings]
        evidence_gaps = [str(item) for item in evidence_gaps]
        uncertainties = [str(item) for item in uncertainties]

        # ----------------------------------------------------------------
        # Step 5: Deterministic action
        # ----------------------------------------------------------------
        action = await self.action_service.get_action(account_id)

        # ----------------------------------------------------------------
        # Step 6: Investigation duration + completion summary
        # ----------------------------------------------------------------
        end_time = time.perf_counter()
        duration_seconds = end_time - start_time

        completion_summary = {
            "tools_executed": len(tool_calls_log),
            "graph_links_found": len(
                related_result.get("linked_accounts", [])
            ),
            "financial_exposure": exposure_result.get(
                "potential_exposure", 0
            ),
            "evidence_fields_checked": len(
                evidence_result.get("fields", {})
            ),
            "llm_confidence": confidence,
            "duration_seconds": round(duration_seconds, 2),
        }


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
            "duration_seconds": completion_summary["duration_seconds"],
            "completion_summary": completion_summary,
        }

        await self._save_investigation_audit(result, success=True)
        return result

    def _extract_json_from_text(self, text: str) -> dict | None:
        """Robustly extract a JSON object from possibly messy text."""
        if not text:
            return None

        # Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find first '{' and last '}', attempt parse
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start : end + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Regex fallback
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _summarize_tool_result(self, tool_name: str, result: Any) -> str:
        if tool_name == "get_related_accounts":
            return f"{len(result.get('linked_accounts', []))} linked accounts"

        if tool_name == "get_shared_attributes":
            total = sum(len(v) for v in result.values())
            return f"{total} shared attributes across categories"

        if tool_name == "check_evidence_availability":
            fields = result.get("fields", {})
            # If no dispute, return that
            if not result.get("has_dispute_at_cutoff", False):
                return "no dispute at cutoff"
            available = sum(1 for v in fields.values() if v is True or v == "AVAILABLE")
            missing = sum(1 for v in fields.values() if v is False or v == "MISSING")
            return f"{available} available, {missing} missing"

        if tool_name == "calculate_financial_exposure":
            return (
                f"GMV ₹{result.get('gross_order_value', 0):,.0f}, "
                f"refund ₹{result.get('refund_amount', 0):,.0f}, "
                f"exposure ₹{result.get('potential_exposure', 0):,.0f}"
            )

        if tool_name == "get_account_timeline":
            events = result.get("events", [])
            return f"{len(events)} timeline events"

        if tool_name == "get_merchant_policy":
            return result.get("policy", "")

        return str(result)[:200]

    async def _execute_tool(self, function_name: str, args: dict) -> Any:
        # ... (same as before, but ensure native types)
        # We'll keep the existing implementation, but make sure to cast to native types.
        pass

    # The _execute_tool implementation is unchanged except for the numerical casts.
    # For brevity, we assume it's already correct; we'll provide the complete method below.

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

            features = self.feature_repo.get_features()
            for account_id in account_ids:
                row = features[features["account_id"] == account_id]
                if not row.empty:
                    row = row.iloc[0]
                    for entity in [
                        "shared_device_count",
                        "shared_address_count",
                        "shared_phone_count",
                        "shared_instrument_count",
                    ]:
                        count = row.get(entity, 0)
                        if count > 0:
                            shared_attrs[
                                entity.replace("shared_", "").replace("_count", "")
                            ].append(
                                {
                                    "account_id": account_id,
                                    "count": int(count),
                                }
                            )
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
                return {
                    "gross_order_value": 0.0,
                    "refund_amount": 0.0,
                    "potential_exposure": 0.0,
                }
            total_amount = float(row.iloc[0].get("total_amount", 0) or 0)
            total_refund_amount = float(row.iloc[0].get("total_refund_amount", 0) or 0)
            potential_exposure = total_amount - total_refund_amount
            return {
                "gross_order_value": total_amount,
                "refund_amount": total_refund_amount,
                "potential_exposure": potential_exposure,
            }

        elif function_name == "get_account_timeline":
            orders = self.event_repo.get_orders_for_account(args["account_id"])
            events = []
            for _, order in orders.iterrows():
                events.append(
                    {
                        "timestamp": str(order["order_timestamp"]),
                        "event": "Order placed",
                        "details": f"Amount ₹{float(order['amount'])}",
                    }
                )
                if pd.notna(order["delivery_timestamp"]):
                    events.append(
                        {
                            "timestamp": str(order["delivery_timestamp"]),
                            "event": "Order delivered",
                            "details": "",
                        }
                    )
                if pd.notna(order["return_timestamp"]) and order["return_flag"]:
                    events.append(
                        {
                            "timestamp": str(order["return_timestamp"]),
                            "event": "Return requested",
                            "details": f"Reason: {order['return_reason_code']}",
                        }
                    )
                if pd.notna(order["refund_timestamp"]) and order["refund_flag"]:
                    events.append(
                        {
                            "timestamp": str(order["refund_timestamp"]),
                            "event": "Refund processed",
                            "details": f"Amount ₹{float(order['refund_amount'])}",
                        }
                    )
            return {"events": events}

        elif function_name == "get_merchant_policy":
            category = args.get("category", "default")
            policies = {
                "fashion": "Manual review required for refunds over ₹5000",
                "electronics": "Proof of delivery and return condition required",
                "default": "Standard refund policy: verify return reason before processing",
            }
            return {"policy": policies.get(category, policies["default"])}

        else:
            raise ValueError(f"Unknown tool: {function_name}")

    async def _save_investigation_audit(
        self,
        result: dict,
        success: bool = True,
    ):
        """Append a detailed investigation record."""
        audit_dir = self.explainability_repo.explainability_dir
        audit_path = audit_dir / "investigation_audit_log.csv"

        try:
            df = pd.read_csv(audit_path)
        except FileNotFoundError:
            df = pd.DataFrame()
        except Exception:
            df = pd.DataFrame()

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_id": result["account_id"],
            "model_version": "LightGBM_Model_B",
            "proba": None,
            "rank": None,
            "risk_tier": None,
            "top_k_flag": True,
            "action_recommended": result["recommended_action"],
            "case_report_generated": True,
            "investigation_source": result["source"],
            "tool_calls": json.dumps(result.get("tool_calls", [])),
            "summary": result.get("summary", ""),
            "action_source": result.get(
                "action_source",
                "deterministic_policy",
            ),
        }

        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        df.to_csv(audit_path, index=False)

    async def _fallback_deterministic(self,account_id: str,error: str = "",start_time: float | None = None,) -> dict:
        report = self.explainability_repo.get_reports()
        row = report[report["account_id"] == account_id]

        case_report = (
            str(row.iloc[0]["case_report_text"])
            if not row.empty
            else ""
        )

        action = await self.action_service.get_action(account_id)

        # Calculate investigation duration
        if start_time is not None:
            duration_seconds = round(
                time.perf_counter() - start_time,
                2,
            )
        else:
            duration_seconds = 0.0

        completion_summary = {
            "tools_executed": 0,
            "graph_links_found": 0,
            "financial_exposure": 0,
            "evidence_fields_checked": 0,
            "llm_confidence": "LOW",
            "duration_seconds": duration_seconds,
        }

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
            "duration_seconds": duration_seconds,
            "completion_summary": completion_summary,
        }

        await self._save_investigation_audit(
            result,
            success=False,
        )

        return result