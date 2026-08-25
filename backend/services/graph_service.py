import pandas as pd

from backend.domain.graph import AccountGraph, GraphNode, GraphEdge
from backend.repositories.explainability_repository import ExplainabilityRepository


class GraphService:
    def __init__(self, explainability_repo: ExplainabilityRepository):
        self.explainability_repo = explainability_repo

    async def get_graph_evidence(self, account_id: str) -> dict:
        graph_df = self.explainability_repo.get_graph_evidence()
        row = graph_df[graph_df["account_id"] == account_id]

        if row.empty:
            return {
                "total_graph_links": 0,
                "strongest_edge_type": None,
                "strongest_edge_weight": None,
                "number_of_device_links": 0,
                "number_of_ip_links": 0,
                "number_of_coupon_links": 0,
                "linked_accounts": [],
            }

        row = row.iloc[0]
        linked_accounts = []
        if pd.notna(row["linked_accounts"]) and str(row["linked_accounts"]).strip():
            for rel in str(row["linked_accounts"]).split("|"):
                rel = rel.strip()
                if "->" in rel:
                    edge_type, linked = rel.split("->", 1)
                    linked_accounts.append({
                        "edge_type": edge_type.strip(),
                        "linked_account": linked.strip(),
                    })

        return {
            "total_graph_links": int(row["total_graph_links"]),
            "strongest_edge_type": row["strongest_edge_type"] if pd.notna(row["strongest_edge_type"]) else None,
            "strongest_edge_weight": float(row["strongest_edge_weight"]) if pd.notna(row["strongest_edge_weight"]) else None,
            "number_of_device_links": int(row["number_of_device_links"]),
            "number_of_ip_links": int(row["number_of_ip_links"]),
            "number_of_coupon_links": int(row["number_of_coupon_links"]),
            "linked_accounts": linked_accounts,
        }

    async def get_graph_for_visualization(self, account_id: str) -> AccountGraph:
        graph_evidence = await self.get_graph_evidence(account_id)

        nodes = [GraphNode(id=account_id, label=account_id, is_focus=True)]
        edges = []

        for link in graph_evidence["linked_accounts"]:
            linked = link["linked_account"]
            nodes.append(GraphNode(id=linked, label=linked))
            edges.append(
                GraphEdge(
                    source=account_id,
                    target=linked,
                    edge_type=link["edge_type"],
                    weight=1.0,  # could use strongest_edge_weight if available
                )
            )

        return AccountGraph(account_id=account_id, nodes=nodes, edges=edges)