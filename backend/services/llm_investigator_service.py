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
        # ----------------------------------------------------------------
        # Build an explicit authoritative financial packet.
        #
        # IMPORTANT:
        # The LLM must NOT calculate, reconcile, or infer monetary values.
        # Every financial value shown to the investigator comes directly
        # from the deterministic order data.
        # ----------------------------------------------------------------

        authoritative_financials = {
            "gross_order_value": float(exposure_result.get("gross_order_value", 0.0)),
            "refund_amount": float(exposure_result.get("refund_amount", 0.0)),
            "potential_exposure": float(exposure_result.get("potential_exposure", 0.0)),
        }

        evidence_packet = {
            "account_id": account_id,
            "related_accounts": related_result,
            "shared_attributes": shared_result,
            "evidence": evidence_result,
            # AUTHORITATIVE FINANCIAL DATA.
            #
            # These values must be treated as immutable facts.
            "financial_exposure": authoritative_financials,
            # The timeline is evidence only.
            # The LLM must not recompute totals from it.
            "timeline": timeline_result,
            "merchant_policy": policy_result,
            # Explicit instruction for the model to avoid financial
            # reconciliation hallucinations.
            "financial_rules": {
                "financial_values_are_authoritative": True,
                "do_not_recalculate_financial_values": True,
                "do_not_sum_refunds_from_timeline": True,
                "do_not_compare_timeline_totals_against_financial_exposure": True,
                "do_not_report_financial_discrepancies": True,
                "do_not_infer_missing_refunds": True,
                "do_not_infer_extra_refunds": True,
                "do_not_create_new_monetary_values": True,
            },
        }

        system_prompt = (
            "You are an AI investigator for RingWatch, a post-delivery "
            "refund/return abuse detection system.\n"
            "\n"
            "You have already been provided with authoritative deterministic "
            "investigation evidence.\n"
            "You may call additional tools if necessary.\n"
            "\n"
            "Your job is to explain the evidence, identify relevant patterns, "
            "describe uncertainties, and summarize the investigation.\n"
            "\n"
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "summary": "...",\n'
            '  "key_findings": ["...", "..."],\n'
            '  "evidence_gaps": ["..."],\n'
            '  "uncertainties": ["..."],\n'
            '  "confidence": "LOW|MEDIUM|HIGH"\n'
            "}\n"
            "\n"
            "RULES:\n"
            "\n"
            "1. Do not invent facts.\n"
            "2. Do not treat the model score as a calibrated probability.\n"
            "3. Do not make final financial decisions.\n"
            "4. The final action is determined by the deterministic policy "
            "engine, not by you.\n"
            "5. Use only the provided evidence and tool outputs.\n"
            "6. Use ₹ for Indian Rupees.\n"
            "\n"
            "FINANCIAL DATA RULES — VERY IMPORTANT:\n"
            "7. The financial_exposure object is authoritative.\n"
            "8. Never recalculate gross order value.\n"
            "9. Never recalculate total refunds.\n"
            "10. Never recalculate potential exposure.\n"
            "11. Never sum refund amounts from the timeline.\n"
            "12. Never compare timeline refund amounts against "
            "financial_exposure.refund_amount.\n"
            "13. Never report a financial discrepancy based on your own "
            "arithmetic.\n"
            "14. Never invent, estimate, approximate, round, subtract, "
            "add, or derive a new monetary amount.\n"
            "15. If discussing financial values, copy the exact value from "
            "financial_exposure or directly quote an individual amount "
            "already present in the evidence.\n"
            "16. Do not state that the financial data is inconsistent merely "
            "because the timeline contains individual transactions.\n"
            "17. The timeline is chronological evidence. It is NOT an input "
            "for calculating financial totals.\n"
            "18. If the financial_exposure values and timeline appear to "
            "contain different representations, trust financial_exposure "
            "and do not report a discrepancy.\n"
            "\n"
            "EVIDENCE RULES:\n"
            "19. If has_dispute_at_cutoff is false, describe evidence gaps "
            "as 'not yet applicable' rather than 'missing'.\n"
            "20. Distinguish between total refund amount and individual "
            "refund transactions.\n"
            "21. Do not claim that a merchant verified a return reason unless "
            "the evidence explicitly proves that verification occurred.\n"
            "22. Do not claim that shared attributes prove fraud. Describe "
            "them as signals, relationships, or possible coordinated activity "
            "unless stronger evidence exists.\n"
            "23. Do not claim future events are known.\n"
            "24. Confidence must reflect the quality and completeness of "
            "the available evidence, not simply the risk score.\n"
            "\n"
            "25. Return ONLY the JSON object. No markdown. No explanation "
            "outside the JSON object."
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

        # -------------------------------------------------------------
        # Validate AI-generated monetary claims against authoritative
        # evidence. The LLM is not allowed to invent monetary values.
        # -------------------------------------------------------------

        authoritative_amounts = {
            round(
                float(exposure_result.get("gross_order_value", 0.0)),
                2,
            ),
            round(
                float(exposure_result.get("refund_amount", 0.0)),
                2,
            ),
            round(
                float(exposure_result.get("potential_exposure", 0.0)),
                2,
            ),
        }

        # Also allow individual order/refund amounts appearing in the
        # authoritative timeline.
        for event in timeline_result.get("events", []):
            details = str(event.get("details", ""))

            for match in re.findall(
                r"₹\s*([0-9]+(?:\.[0-9]+)?)",
                details,
            ):
                try:
                    authoritative_amounts.add(round(float(match), 2))
                except ValueError:
                    pass

        monetary_claim_pattern = re.compile(r"₹\s*([0-9]+(?:\.[0-9]+)?)")

        generated_texts = [
            summary,
            *key_findings,
            *evidence_gaps,
            *uncertainties,
        ]

        invalid_monetary_claim = False

        for generated_text in generated_texts:
            for match in monetary_claim_pattern.findall(str(generated_text)):
                try:
                    amount = round(float(match), 2)

                    if amount not in authoritative_amounts:
                        invalid_monetary_claim = True
                        break

                except ValueError:
                    continue

            if invalid_monetary_claim:
                break

        if invalid_monetary_claim:
            # Remove only unsupported monetary statements.
            # Do not destroy an otherwise useful investigation.
            key_findings = [
                finding
                for finding in key_findings
                if not monetary_claim_pattern.search(str(finding))
            ]

            evidence_gaps = [
                gap
                for gap in evidence_gaps
                if not monetary_claim_pattern.search(str(gap))
            ]

            uncertainties = [
                uncertainty
                for uncertainty in uncertainties
                if not monetary_claim_pattern.search(str(uncertainty))
            ]

            # If the summary itself contains an unsupported monetary claim,
            # replace only that summary with a neutral statement.
            if monetary_claim_pattern.search(str(summary)):
                summary = (
                    "The investigation identified relevant account, "
                    "graph, evidence, and policy signals. "
                    "Authoritative financial values are shown separately "
                    "from the AI-generated investigation narrative."
                )

            # Do NOT automatically downgrade confidence just because an
            # unsupported monetary sentence was removed. Confidence should
            # reflect the remaining evidence.

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
            "graph_links_found": len(related_result.get("linked_accounts", [])),
            "financial_exposure": exposure_result.get("potential_exposure", 0),
            "evidence_fields_checked": len(evidence_result.get("fields", {})),
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
            # Keep the authoritative financial calculation separate
            # from AI-generated prose.
            "financial_exposure": {
                "gross_order_value": float(
                    exposure_result.get(
                        "gross_order_value",
                        0.0,
                    )
                ),
                "refund_amount": float(
                    exposure_result.get(
                        "refund_amount",
                        0.0,
                    )
                ),
                "potential_exposure": float(
                    exposure_result.get(
                        "potential_exposure",
                        0.0,
                    )
                ),
            },
            # Action comes exclusively from deterministic policy.
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
            orders = self.event_repo.get_orders_for_account(args["account_id"])

            if orders.empty:
                return {
                    "gross_order_value": 0.0,
                    "refund_amount": 0.0,
                    "potential_exposure": 0.0,
                }

            # Authoritative financial values come from the actual order data.
            gross_order_value = float(
                pd.to_numeric(
                    orders["amount"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

            refund_amount = 0.0

            if "refund_flag" in orders.columns and "refund_amount" in orders.columns:
                refund_mask = orders["refund_flag"].fillna(False).astype(bool)

                refund_amount = float(
                    pd.to_numeric(
                        orders.loc[refund_mask, "refund_amount"],
                        errors="coerce",
                    )
                    .fillna(0)
                    .sum()
                )

            potential_exposure = max(
                0.0,
                gross_order_value - refund_amount,
            )

            return {
                "gross_order_value": gross_order_value,
                "refund_amount": refund_amount,
                "potential_exposure": potential_exposure,
            }

        elif function_name == "get_account_timeline":
            orders = self.event_repo.get_orders_for_account(args["account_id"])

            events = []

            for _, order in orders.iterrows():
                order_id = str(order["order_id"])

                events.append(
                    {
                        "timestamp": str(order["order_timestamp"]),
                        "event": "Order placed",
                        "details": (
                            f"Order {order_id}, "
                            f"amount ₹{float(order['amount']):.2f}"
                        ),
                        "order_id": order_id,
                        "amount": float(order["amount"]),
                        "financial_role": "individual_order_transaction",
                    }
                )

                if pd.notna(order["delivery_timestamp"]):
                    events.append(
                        {
                            "timestamp": str(order["delivery_timestamp"]),
                            "event": "Order delivered",
                            "details": f"Order {order_id}",
                        }
                    )

                if pd.notna(order["return_timestamp"]) and bool(order["return_flag"]):
                    events.append(
                        {
                            "timestamp": str(order["return_timestamp"]),
                            "event": "Return requested",
                            "details": (
                                f"Order {order_id}, "
                                f"reason {order['return_reason_code']}"
                            ),
                        }
                    )

                if pd.notna(order["refund_timestamp"]) and bool(order["refund_flag"]):
                    events.append(
                        {
                            "timestamp": str(order["refund_timestamp"]),
                            "event": "Refund processed",
                            "details": (
                                f"Order {order_id}, "
                                f"amount ₹{float(order['refund_amount']):.2f}"
                            ),
                            "order_id": order_id,
                            "amount": float(order["refund_amount"]),
                            "financial_role": "individual_refund_transaction",
                        }
                    )

            # Keep chronology deterministic.
            events.sort(key=lambda event: pd.to_datetime(event["timestamp"]))

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
        """
        Persist every LLM investigation into the live audit log.

        This is separate from the model prediction audit rows.

        A prediction row tells us:
            model -> score -> risk tier -> action

        An investigation row tells us:
            LLM -> tools -> findings -> confidence -> action
        """

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_id": result.get(
                "account_id",
                "",
            ),
            # The investigation is performed AFTER the ensemble score.
            # Keep the model identity explicit.
            "model_version": "Ensemble_LGBM_B_GNN",
            # Investigation rows do not generate a new prediction.
            "proba": None,
            "rank": None,
            # Risk tier comes from the prediction/action system.
            "risk_tier": None,
            "recommended_action": None,
            # This is the field consumed by the API/frontend.
            "action_recommended": result.get(
                "recommended_action",
                "",
            ),
            "top_k_flag": False,
            "case_report_generated": True,
            # ---------------------------------------------------------
            # LLM investigation information
            # ---------------------------------------------------------
            "investigation_source": result.get(
                "source",
                "llm",
            ),
            "tool_calls": json.dumps(
                result.get("tool_calls", []),
                default=str,
            ),
            "summary": result.get(
                "summary",
                "",
            ),
            "action_source": result.get(
                "action_source",
                "deterministic_policy",
            ),
            "error": (result.get("error", "") if not success else ""),
        }

        # Use the repository's append method so the existing prediction
        # rows and newly generated investigation rows coexist safely.
        self.explainability_repo.append_audit_record(entry)

    async def _fallback_deterministic(
        self,
        account_id: str,
        error: str = "",
        start_time: float | None = None,
    ) -> dict:
        report = self.explainability_repo.get_reports()
        row = report[report["account_id"] == account_id]

        case_report = str(row.iloc[0]["case_report_text"]) if not row.empty else ""

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

        # Get authoritative financial data for the fallback path too.
        try:
            orders = self.event_repo.get_orders_for_account(account_id)

            if not orders.empty:
                gross_order_value = float(
                    pd.to_numeric(
                        orders["amount"],
                        errors="coerce",
                    )
                    .fillna(0)
                    .sum()
                )

                if (
                    "refund_flag" in orders.columns
                    and "refund_amount" in orders.columns
                ):
                    refund_mask = orders["refund_flag"].fillna(False).astype(bool)

                    refund_amount = float(
                        pd.to_numeric(
                            orders.loc[refund_mask, "refund_amount"],
                            errors="coerce",
                        )
                        .fillna(0)
                        .sum()
                    )
                else:
                    refund_amount = 0.0

                potential_exposure = max(
                    0.0,
                    gross_order_value - refund_amount,
                )
            else:
                gross_order_value = 0.0
                refund_amount = 0.0
                potential_exposure = 0.0

        except Exception:
            gross_order_value = 0.0
            refund_amount = 0.0
            potential_exposure = 0.0

        result = {
            "account_id": account_id,
            "source": "deterministic",
            "summary": (case_report.split("\n")[0] if case_report else ""),
            "key_findings": [],
            "evidence_gaps": [],
            "uncertainties": [],
            "confidence": "LOW",
            "tool_calls": [],
            "financial_exposure": {
                "gross_order_value": gross_order_value,
                "refund_amount": refund_amount,
                "potential_exposure": potential_exposure,
            },
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
