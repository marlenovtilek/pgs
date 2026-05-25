from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.spot_events import router as spot_events_router
from app.api.v1.spots import router as spots_router
from app.api.v1.zones import router as zones_router
from app.api.v1.display import router as display_router


router = APIRouter()
router.include_router(health_router)
router.include_router(spot_events_router)
router.include_router(spots_router)
router.include_router(zones_router)
router.include_router(display_router)