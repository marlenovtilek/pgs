from fastapi import APIRouter, Depends

from app.api.dependencies import require_api_token
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.spot_events import router as spot_events_router
from app.api.v1.spots import router as spots_router
from app.api.v1.zones import router as zones_router
from app.api.v1.display import router as display_router


router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(require_api_token)])

router.include_router(auth_router)
router.include_router(health_router)
protected_router.include_router(spot_events_router)
protected_router.include_router(spots_router)
protected_router.include_router(zones_router)
protected_router.include_router(display_router)
router.include_router(protected_router)
