from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import User, create_db_and_tables, get_async_session
from app.schemas import UserCreate, UserRead, UserUpdate


from app.routes import router as crud_router
from app.routes.devonthink_sync_routes import router as devonthink_router
# TODO: Enhanced RAG routes temporarily disabled due to deprecated langchain.chains.RetrievalQA
# from app.routes.enhanced_rag_routes import router as enhanced_rag_router
from app.routes.automated_ingestion_routes import router as automated_ingestion_router
from app.routes.admin_routes import router as admin_router
from app.routes.clerk_routes import router as clerk_router
from app.config import config

from app.users import SECRET, auth_backend, fastapi_users, current_active_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Not needed if you setup a migration system like Alembic
    await create_db_and_tables()
    yield


app = FastAPI(
    lifespan=lifespan,
    redirect_slashes=False,  # Disable automatic trailing slash redirects to preserve CORS headers
)

# Add CORS middleware
# Explicitly allow production frontend domain
allowed_origins = [
    "https://library.counterforce-hero.tech",
    "https://api.counterforce-hero.tech",
    "http://localhost:3000",
    "http://localhost:8501",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8501",
]

# Note: Cannot use allow_credentials=True with allow_origins=["*"]
# So we explicitly list origins instead
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

if config.AUTH_TYPE == "GOOGLE":
    from app.users import google_oauth_client

    app.include_router(
        fastapi_users.get_oauth_router(
            google_oauth_client, auth_backend, SECRET, is_verified_by_default=True
        ),
        prefix="/auth/google",
        tags=["auth"],
    )

app.include_router(clerk_router, tags=["clerk"])
app.include_router(crud_router, prefix="/api/v1", tags=["crud"])
app.include_router(devonthink_router, prefix="/devonthink", tags=["devonthink"])
# TODO: Enhanced RAG router temporarily disabled - see import comment above
# app.include_router(enhanced_rag_router, tags=["enhanced-rag"])
app.include_router(automated_ingestion_router, tags=["automated-ingestion"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/verify-token")
async def authenticated_route(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return {"message": "Token is valid"}
