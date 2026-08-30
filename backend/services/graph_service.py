import pandas as pd

from backend.core.config import get_settings
from backend.domain.graph import AccountGraph, GraphNode, GraphEdge
from backend.repositories.explainability_repository import ExplainabilityRepository

EDGE_WEIGHTS = {
    "shares_device": 1.0,
    "shares_phone": 1.0,
    "shares_payment_instrument": 1.0,
    "shares_address": 0.7,
    "shares_ip_prefix": 0.3,
    "shares_coupon": 0.2,
}

EDGE_LABELS = {
    "shares_device": "shared device",
    "shares_phone": "shared phone",
    "shares_payment_instrument": "shared payment instrument",
    "shares_address": "shared address",
    "shares_ip_prefix": "shared IP prefix",
    "shares_coupon": "shared coupon",
}


class GraphService:
    def __init__(self, explainability_repo: ExplainabilityRepository):
        self.explainability_repo = explainability_repo
        self.settings = get_settings()
        self._communities = self._load_communities()

    def _load_communities(self) -> dict[str, int | str]:
        path = self.settings.communities_path
        if not path.exists():
            return {}
        try:
            df = pd.read_csv(path, usecols=["account_id", "community_id"])
            df["account_id"] = df["account_id"].astype(str)
            return dict(zip(df["account_id"], df["community_id"]))
        except Exception:
            return {}

    def _community_id(self, account_id: str):
        return self._communities.get(str(account_id))

    async def get_graph_evidence(self, account_id: str) -> dict:
        graph_df = self.explainability_repo.get_graph_evidence()
        row = graph_df[graph_df["account_id"].astype(str) == str(account_id)]

        if row.empty:
            return {
                "total_graph_links": 0,
                "strongest_edge_type": None,
                "strongest_edge_weight": None,
                "strongest_edge_target": None,
                "strongest_edge_explanation": None,
                "number_of_device_links": 0,
                "number_of_ip_links": 0,
                "number_of_coupon_links": 0,
                "linked_accounts": [],
                "community_id": self._community_id(account_id),
            }

        row = row.iloc[0]
        linked_accounts = []
        if pd.notna(row["linked_accounts"]) and str(row["linked_accounts"]).strip():
            for rel in str(row["linked_accounts"]).split("|"):
                rel = rel.strip()
                if "->" in rel:
                    edge_type, linked = rel.split("->", 1)
                    linked_accounts.append(
                        {
                            "edge_type": edge_type.strip(),
                            "linked_account": linked.strip(),
                        }
                    )

        strongest_type = (
            row["strongest_edge_type"] if pd.notna(row["strongest_edge_type"]) else None
        )
        strongest_weight = (
            float(row["strongest_edge_weight"])
            if pd.notna(row["strongest_edge_weight"])
            else None
        )

        strongest_target = None
        if strongest_type:
            for link in linked_accounts:
                if link["edge_type"] == strongest_type:
                    strongest_target = link["linked_account"]
                    break

        strongest_explanation = None
        if strongest_type and strongest_weight is not None:
            label = EDGE_LABELS.get(str(strongest_type), str(strongest_type))
            if strongest_target:
                strongest_explanation = (
                    f"Strongest configured relationship is a {label} link to "
                    f"{strongest_target} (weight {strongest_weight:.2f}). "
                    "The weight is an evidence-prioritization heuristic, not proof of abuse."
                )
            else:
                strongest_explanation = (
                    f"Strongest configured relationship is {label} "
                    f"(weight {strongest_weight:.2f}). The weight is an "
                    "evidence-prioritization heuristic, not proof of abuse."
                )

        return {
            "total_graph_links": int(row["total_graph_links"]),
            "strongest_edge_type": strongest_type,
            "strongest_edge_weight": strongest_weight,
            "strongest_edge_target": strongest_target,
            "strongest_edge_explanation": strongest_explanation,
            "number_of_device_links": int(row["number_of_device_links"]),
            "number_of_ip_links": int(row["number_of_ip_links"]),
            "number_of_coupon_links": int(row["number_of_coupon_links"]),
            "linked_accounts": linked_accounts,
            "community_id": self._community_id(account_id),
        }

    async def get_graph_for_visualization(self, account_id: str) -> AccountGraph:
        graph_evidence = await self.get_graph_evidence(account_id)

        nodes = [
            GraphNode(
                id=account_id,
                label=account_id,
                is_focus=True,
                community_id=graph_evidence.get("community_id"),
            )
        ]
        edges = []

        for link in graph_evidence["linked_accounts"]:
            linked = link["linked_account"]
            nodes.append(
                GraphNode(
                    id=linked,
                    label=linked,
                    community_id=self._community_id(linked),
                )
            )
            edges.append(
                GraphEdge(
                    source=account_id,
                    target=linked,
                    edge_type=link["edge_type"],
                    weight=float(EDGE_WEIGHTS.get(link["edge_type"], 0.0)),
                )
            )

        return AccountGraph(account_id=account_id, nodes=nodes, edges=edges)

    async def get_overview_graph(self) -> AccountGraph:
        """Build an overview graph containing flagged accounts and direct relationships."""
        actions_df = self.explainability_repo.get_actions()
        flagged_ids = actions_df["account_id"].astype(str).tolist()

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_nodes: set[str] = set()

        for account_id in flagged_ids:
            if account_id not in seen_nodes:
                nodes.append(
                    GraphNode(
                        id=account_id,
                        label=account_id,
                        is_focus=True,
                        community_id=self._community_id(account_id),
                    )
                )
                seen_nodes.add(account_id)

            evidence = await self.get_graph_evidence(account_id)
            for link in evidence["linked_accounts"]:
                linked = link["linked_account"]
                if linked not in seen_nodes:
                    nodes.append(
                        GraphNode(
                            id=linked,
                            label=linked,
                            community_id=self._community_id(linked),
                        )
                    )
                    seen_nodes.add(linked)

                edges.append(
                    GraphEdge(
                        source=account_id,
                        target=linked,
                        edge_type=link["edge_type"],
                        weight=float(EDGE_WEIGHTS.get(link["edge_type"], 0.0)),
                    )
                )

        return AccountGraph(account_id="overview", nodes=nodes, edges=edges)
