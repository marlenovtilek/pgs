from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.admin import setup_admin
from app.api.router import api_router
from app.core.config import settings

# Importing the metrics module registers the counters on the default registry
# so they are exported even before the first event is handled.
from app.core import metrics  # noqa: F401


app = FastAPI(title=settings.app_name, debug=settings.debug)
setup_admin(app)
app.include_router(api_router)


@app.get("/metrics", include_in_schema=False)
def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
