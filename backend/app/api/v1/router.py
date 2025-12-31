"""API v1 router - includes all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, mfa, oauth

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(oauth.router, prefix="/auth/oauth", tags=["OAuth"])
api_router.include_router(mfa.router, prefix="/auth/mfa", tags=["MFA"])

