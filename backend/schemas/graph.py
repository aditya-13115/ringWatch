from pydantic import BaseModel


class GraphNodeSchema(BaseModel):
    id: str
    label: str
    is_focus: bool = False
    community_id: int | str | None = None


class GraphEdgeSchema(BaseModel):
    source: str
    target: str
    edge_type: str
    weight: float


class AccountGraphResponse(BaseModel):
    account_id: str
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
