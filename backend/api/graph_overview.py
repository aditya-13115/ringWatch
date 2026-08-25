from fastapi import APIRouter, Depends
from backend.schemas.graph import AccountGraphResponse, GraphNodeSchema, GraphEdgeSchema
from backend.services.graph_service import GraphService
from backend.dependencies import get_graph_service

router = APIRouter(prefix="/graph", tags=["graph-overview"])


@router.get("/overview", response_model=AccountGraphResponse)
async def get_graph_overview(
    graph_service: GraphService = Depends(get_graph_service),
):
    overview = await graph_service.get_overview_graph()
    return overview
