"""OAuth schemas."""

from pydantic import BaseModel


class OAuthLinkConfirmRequest(BaseModel):
    """OAuth account linking confirmation request."""

    link_token: str
    email: str
    password: str


class OAuthLinkConfirmResponse(BaseModel):
    """OAuth account linking confirmation response."""

    status: str = "ok"
    message: str = "Account linked successfully"

