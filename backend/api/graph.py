from fastapi import APIRouter, Depends, HTTPException

from backend.schemas.graph import AccountGraphResponse, GraphNodeSchema, GraphEdgeSchema
from backend.services.graph_service import GraphService
from backend.dependencies import get_graph_service

router = APIRouter(prefix="/accounts", tags=["graph"])


@router.get("/{account_id}/graph", response_model=AccountGraphResponse)
async def get_account_graph(
    account_id: str,
    graph_service: GraphService = Depends(get_graph_service),
):
    try:
        graph = await graph_service.get_graph_for_visualization(account_id)
        return AccountGraphResponse(
            account_id=graph.account_id,
            nodes=[GraphNodeSchema(**n.__dict__) for n in graph.nodes],
            edges=[GraphEdgeSchema(**e.__dict__) for e in graph.edges],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))