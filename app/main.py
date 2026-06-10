from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.admin import setup_admin
from app.api.router import api_router
from app.core.config import settings

# Importing the metrics module registers the counters on the default registry
# so they are exported even before the first event is handled.
from app.core import metrics  # noqa: F401


app = FastAPI(title=settings.app_name, debug=settings.debug)
setup_admin(app)
app.include_router(api_router)
app.mount("/metrics", make_asgi_app())
