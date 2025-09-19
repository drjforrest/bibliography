from fastapi import APIRouter
from .search_spaces_routes import router as search_spaces_router
from .documents_routes import router as documents_router
from .chats_routes import router as chats_router
from .papers_routes import router as papers_router
from .annotations_routes import router as annotations_router
from .semantic_search_routes import router as semantic_search_router
from .dashboard_routes import router as dashboard_router
from .devonthink_sync_routes import router as devonthink_router

router = APIRouter()

router.include_router(search_spaces_router)
router.include_router(documents_router)
router.include_router(chats_router)
router.include_router(papers_router)
router.include_router(annotations_router)
router.include_router(semantic_search_router)
router.include_router(dashboard_router)
router.include_router(devonthink_router)
