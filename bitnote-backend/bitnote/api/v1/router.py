from fastapi import APIRouter

# from bitnote.api.v1.educational_ai.syllabus import router as syllabus_router
# from bitnote.api.v1.educational_ai.roadmap import router as roadmap_router
# from bitnote.api.v1.educational_ai.checklist import router as checklist_router
from bitnote.api.v1.educational_ai.learning_plan import router as learning_plan_router
from .notebooks import router as notebooks_router
from .recall import router as recall_router
from .educational_ai.cell_chat import router as cell_chat_router
from bitnote.contact import router as contact_router

api_router = APIRouter(prefix="/api/v1")

# api_router.include_router(
#     syllabus_router,
#     prefix="/educational-ai",
#     tags=["Educational AI"]
# )

# api_router.include_router(
#     roadmap_router,
#     prefix="/educational-ai",
#     tags=["Educational AI"]
# )

# api_router.include_router(
#     checklist_router,
#     prefix="/educational-ai",
#     tags=["Educational AI"]
# )

api_router.include_router(
    learning_plan_router, prefix="/educational-ai", tags=["Educational AI"]
)

api_router.include_router(notebooks_router)

api_router.include_router(recall_router)

api_router.include_router(contact_router, prefix="/contact", tags=["Contact"])

api_router.include_router(
    cell_chat_router, prefix="/educational-ai", tags=["Educational AI"]
)
