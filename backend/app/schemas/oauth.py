"""OAuth schemas."""

from pydantic import BaseModel

from app.schemas.auth import TokensResponse, UserResponse


class OAuthLinkConfirmRequest(BaseModel):
    """OAuth account linking confirmation request."""

    link_token: str
    email: str
    password: str


class OAuthLinkConfirmResponse(BaseModel):
    """OAuth account linking confirmation response."""

    status: str = "ok"
    message: str = "Account linked successfully"


class OAuthExchangeRequest(BaseModel):
    """Request to exchange an OAuth code for tokens."""

    code: str


class OAuthExchangeResponse(BaseModel):
    """Response from OAuth token exchange."""

    user: UserResponse | None = None
    tokens: TokensResponse | None = None
    mfa_required: bool = False
    mfa_token: str | None = None
    method: str | None = None
