from __future__ import annotations

import json
import pickle
from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.core.config import get_settings

EDGE_LABELS = {
    "shares_device": "shared device",
    "shares_phone": "shared phone",
    "shares_payment_instrument": "shared payment instrument",
    "shares_address": "shared address",
    "shares_ip_prefix": "shared IP prefix",
    "shares_coupon": "shared coupon",
}


class RingService:
    """Read and expose the ring-level candidate model artifacts.

    The service intentionally treats ring-level scores as an additional layer over
    the existing account model. Ground-truth labels are never exposed by the API.
    """

    def __init__(self):
        self.settings = get_settings()
        self.model_dir = self.settings.model_dir
        self.candidates_path = self.model_dir / "ring_candidates.csv"
        self.model_path = self.model_dir / "ring_model_lgbm.pkl"
        self.metrics_path = self.model_dir / "ring_metrics.json"
        self.features_path = self.settings.features_graph_path
        self.edges_path = self.settings.account_graph_edges_path

        self._model = None
        self._candidate_cache = None
        self._member_score_cache = None
        self._edges_cache = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        if not self.model_path.exists():
            return None
        with open(self.model_path, "rb") as f:
            self._model = pickle.load(f)
        return self._model

    def _load_candidates(self) -> pd.DataFrame:
        if self._candidate_cache is not None:
            return self._candidate_cache.copy()
        if not self.candidates_path.exists():
            return pd.DataFrame()
        df = pd.read_csv(self.candidates_path)
        for col in ["candidate_id", "member_ids", "source_community_ids"]:
            if col in df.columns:
                df[col] = df[col].fillna("")
        self._candidate_cache = df
        return df.copy()

    def _load_features(self) -> pd.DataFrame:
        if not self.features_path.exists():
            return pd.DataFrame()
        return pd.read_csv(self.features_path, low_memory=False)

    def _load_edges(self) -> pd.DataFrame:
        if self._edges_cache is not None:
            return self._edges_cache.copy()
        if not self.edges_path.exists():
            return pd.DataFrame()
        df = pd.read_csv(self.edges_path, low_memory=False)
        df["account_id_1"] = df["account_id_1"].astype(str)
        df["account_id_2"] = df["account_id_2"].astype(str)
        self._edges_cache = df
        return df.copy()

    @staticmethod
    def _tier(score: float) -> str:
        if score >= 0.85:
            return "CRITICAL"
        if score >= 0.65:
            return "HIGH"
        if score >= 0.45:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _action(tier: str) -> str:
        return {
            "CRITICAL": "Soft-hold refund pending human approval",
            "HIGH": "Route to human investigation/review",
            "MEDIUM": "Require step-up verification before processing refund",
            "LOW": "Monitor — no immediate refund action",
        }[tier]

    def _member_scores(self) -> dict[str, float]:
        if self._member_score_cache is not None:
            return self._member_score_cache

        model = self._load_account_model()
        features = self._load_features()
        if model is None or features.empty:
            self._member_score_cache = {}
            return self._member_score_cache

        cols = list(model.feature_name_)
        missing = [c for c in cols if c not in features.columns]
        if missing:
            self._member_score_cache = {}
            return self._member_score_cache

        proba = model.predict_proba(features[cols])[:, 1]
        ids = features["account_id"].astype(str)
        self._member_score_cache = dict(zip(ids, proba))
        return self._member_score_cache

    def _load_account_model(self):
        path = self.model_dir / "model_lgbm_B_tuned.pkl"
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return pickle.load(f)

    def _score_candidate(self, row: pd.Series) -> float:
        model = self._load_model()
        if model is None:
            return float(row.get("ring_proba", row.get("max_account_risk", 0.0)))
        feature_names = list(model.feature_name_)
        X = pd.DataFrame([{c: row.get(c, 0.0) for c in feature_names}])
        X = X.apply(pd.to_numeric, errors="coerce").fillna(0.0)
        return float(model.predict_proba(X)[:, 1][0])

    def _row_to_summary(self, row: pd.Series) -> dict:
        member_ids = json.loads(row.get("member_ids", "[]") or "[]")
        score = float(row.get("ring_proba", self._score_candidate(row)))
        tier = self._tier(score)
        return {
            "candidate_id": str(row["candidate_id"]),
            "ring_score": score,
            "detected": bool(int(row.get("ring_pred", 0))),
            "risk_tier": tier,
            "recommended_action": self._action(tier),
            "member_count": int(row.get("member_count", len(member_ids))),
            "exposure": float(row.get("ring_total_refund_amount_sum", 0.0)),
            "mean_account_risk": float(row.get("mean_account_risk", 0.0)),
            "max_account_risk": float(row.get("max_account_risk", 0.0)),
            "internal_edge_count": int(row.get("internal_edge_count", 0)),
            "strongest_edge_type": self._strongest_edge_type(member_ids),
            "strongest_edge_weight": self._strongest_edge_weight(member_ids),
            "member_ids": member_ids,
        }

    def _internal_edges(self, member_ids: list[str]) -> pd.DataFrame:
        edges = self._load_edges()
        if edges.empty:
            return edges
        ids = set(member_ids)
        return edges[
            edges["account_id_1"].isin(ids) & edges["account_id_2"].isin(ids)
        ].copy()

    def _strongest_edge_type(self, member_ids: list[str]) -> str | None:
        edges = self._internal_edges(member_ids)
        if edges.empty:
            return None
        row = edges.sort_values("weight", ascending=False).iloc[0]
        return str(row["edge_type"])

    def _strongest_edge_weight(self, member_ids: list[str]) -> float | None:
        edges = self._internal_edges(member_ids)
        if edges.empty:
            return None
        return float(pd.to_numeric(edges["weight"], errors="coerce").max())

    def list_rings(self, limit: int = 25, detected_only: bool = False) -> dict:
        df = self._load_candidates()
        if df.empty:
            return {"rings": [], "total": 0, "detected_count": 0, "model": {}}

        if "ring_proba" not in df.columns:
            df["ring_proba"] = df.apply(self._score_candidate, axis=1)
        if "ring_pred" not in df.columns:
            threshold = self._load_metrics().get("test", {}).get("threshold", 0.5)
            df["ring_pred"] = (df["ring_proba"] >= threshold).astype(int)

        detected_count = int(df["ring_pred"].sum())
        if detected_only:
            df = df[df["ring_pred"] == 1]

        df = df.sort_values("ring_proba", ascending=False).head(max(1, min(limit, 250)))
        rings = [self._row_to_summary(row) for _, row in df.iterrows()]
        metrics = self._load_metrics()
        return {
            "rings": rings,
            "total": int(len(self._load_candidates())),
            "detected_count": detected_count,
            "model": {
                "name": "Ring LightGBM",
                "candidate_seed_threshold": metrics.get("candidate_generation", {}).get(
                    "seed_threshold", 0.70
                ),
                "strong_edge_threshold": metrics.get("candidate_generation", {}).get(
                    "strong_edge_min_weight", 0.70
                ),
                "operating_threshold": metrics.get("test", {}).get("threshold"),
                "test": metrics.get("test", {}),
                "test_ring_coverage": metrics.get("test_ring_coverage", {}),
            },
        }

    def get_ring(self, candidate_id: str) -> dict | None:
        df = self._load_candidates()
        if df.empty:
            return None
        row_df = df[df["candidate_id"].astype(str) == str(candidate_id)]
        if row_df.empty:
            return None
        row = row_df.iloc[0]
        summary = self._row_to_summary(row)
        member_ids = summary["member_ids"]
        scores = self._member_scores()
        members = [
            {
                "account_id": account_id,
                "account_risk": float(scores.get(str(account_id), 0.0)),
                "rank_in_ring": 0,
            }
            for account_id in member_ids
        ]
        members.sort(key=lambda x: x["account_risk"], reverse=True)
        for idx, member in enumerate(members, start=1):
            member["rank_in_ring"] = idx

        edges = self._internal_edges(member_ids)
        edge_counts = (
            edges["edge_type"].value_counts().to_dict() if not edges.empty else {}
        )
        strongest = None
        if not edges.empty:
            e = edges.sort_values("weight", ascending=False).iloc[0]
            strongest = {
                "edge_type": str(e["edge_type"]),
                "label": EDGE_LABELS.get(str(e["edge_type"]), str(e["edge_type"])),
                "weight": float(e["weight"]),
                "source": str(e["account_id_1"]),
                "target": str(e["account_id_2"]),
            }

        summary["members"] = members
        summary["metrics"] = {
            "edge_counts": {str(k): int(v) for k, v in edge_counts.items()},
            "internal_edge_density": float(row.get("internal_edge_density", 0.0)),
            "mean_edge_weight": float(row.get("mean_edge_weight", 0.0)),
            "community_ids": json.loads(row.get("source_community_ids", "[]") or "[]"),
            "strongest_edge": strongest,
        }
        summary["evidence"] = {
            "model_basis": [
                "aggregate account risk",
                "strong relationship density",
                "refund / return behavior aggregates",
                "cross-account relationship counts",
            ],
            "note": "Ring score is a model output for investigation prioritization, not proof of coordinated abuse.",
        }
        return summary

    def _load_metrics(self) -> dict:
        import json as _json

        if not self.metrics_path.exists():
            return {}
        try:
            return _json.loads(self.metrics_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
