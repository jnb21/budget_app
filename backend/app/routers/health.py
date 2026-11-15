"""HTTP layer for the health check: GET /health.

A router only deals with HTTP: which URL, which status code, what the JSON
looks like. The decision itself comes from the service.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.dependencies import get_health_service
from app.services.health_service import HealthService

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """The JSON body. Only these two fields are ever sent."""

    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "The database is unavailable"}},
)
def health(
    response: Response,
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    result = service.check()
    if result.status != "ok":
        # 503 Service Unavailable: "temporary problem, try again later".
        # Monitoring tools and load balancers read the code, not the body.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status=result.status, database=result.database)
