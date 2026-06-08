from fastapi import APIRouter

from .reports import router as reports_router
from .items import router as items_router
from .trigger import router as trigger_router
from .stats import router as stats_router

api_router = APIRouter(prefix="/api")
api_router.include_router(reports_router)
api_router.include_router(items_router)
api_router.include_router(trigger_router)
api_router.include_router(stats_router)
