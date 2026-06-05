from fastapi import FastAPI

from app.admin import setup_admin
from app.api.router import api_router
from app.core.config import settings


app = FastAPI(title=settings.app_name, debug=settings.debug)
setup_admin(app)
app.include_router(api_router)
