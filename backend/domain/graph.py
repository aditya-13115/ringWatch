from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    label: str
    is_focus: bool = False
    community_id: int | str | None = None


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str
    weight: float


@dataclass
class AccountGraph:
    account_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
