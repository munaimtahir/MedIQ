"""OAuth/OIDC utilities and provider adapters."""

import json
import secrets
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import jwt
from jose.exceptions import JWTError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis_client
from app.models.oauth import OAuthProvider

logger = get_logger(__name__)

# OIDC metadata cache (in-memory with TTL)
_jwks_cache: dict[str, dict[str, Any]] = {}  # {cache_key: {"jwks": {...}, "expires_at": timestamp}}


class OAuthProviderAdapter:
    """Base class for OAuth provider adapters."""

    def __init__(self, provider: OAuthProvider):
        self.provider = provider

    def get_authorize_url(self, state: str, nonce: str, redirect_uri: str) -> str:
        """Generate authorization URL."""
        raise NotImplementedError

    def get_token_endpoint(self) -> str:
        """Get token endpoint URL."""
        raise NotImplementedError

    def get_jwks_uri(self) -> str:
        """Get JWKS URI for token validation."""
        raise NotImplementedError

    def get_issuer(self) -> str:
        """Get expected issuer."""
        raise NotImplementedError

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        raise NotImplementedError

    async def validate_id_token(self, id_token: str, nonce: str, client_id: str) -> dict[str, Any]:
        """Validate and decode id_token."""
        raise NotImplementedError


class GoogleOAuthAdapter(OAuthProviderAdapter):
    """Google OAuth/OIDC adapter."""

    def __init__(self):
        super().__init__(OAuthProvider.GOOGLE)
        self.client_id = settings.OAUTH_GOOGLE_CLIENT_ID
        self.client_secret = settings.OAUTH_GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.OAUTH_GOOGLE_REDIRECT_URI

    def get_authorize_url(self, state: str, nonce: str, redirect_uri: str | None = None) -> str:
        """Generate Google authorization URL."""
        # Validate redirect URI
        redirect_uri = self._validate_redirect_uri(redirect_uri) or self.redirect_uri
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def get_token_endpoint(self) -> str:
        return "https://oauth2.googleapis.com/token"

    def get_jwks_uri(self) -> str:
        return "https://www.googleapis.com/oauth2/v3/certs"

    def get_issuer(self) -> str:
        return "https://accounts.google.com"

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.get_token_endpoint(),
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri or self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    async def validate_id_token(self, id_token: str, nonce: str, client_id: str) -> dict[str, Any]:
        """Validate Google id_token."""
        from jose import jwk

        # Get JWKS
        jwks = await self._get_jwks()
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")

        # Find the key
        key = None
        for jwk_key in jwks.get("keys", []):
            if jwk_key.get("kid") == kid:
                key = jwk.construct(jwk_key)
                break

        if not key:
            raise ValueError("Key not found in JWKS")

        # Decode and verify
        try:
            payload = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=client_id,
                issuer=self.get_issuer(),
            )
            # Verify nonce
            if payload.get("nonce") != nonce:
                raise ValueError("Nonce mismatch")
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid id_token: {e}") from e

    async def _get_jwks(self) -> dict:
        """Get JWKS (cached with TTL)."""
        cache_key = "jwks:google"
        now = datetime.now(timezone.utc).timestamp()

        # Check cache
        if cache_key in _jwks_cache:
            cached = _jwks_cache[cache_key]
            expires_at = cached.get("expires_at", 0)
            if now < expires_at:
                return cached["jwks"]

        # Fetch fresh JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(self.get_jwks_uri())
            response.raise_for_status()
            jwks = response.json()

        # Cache with TTL
        expires_at = now + settings.JWKS_CACHE_TTL_SECONDS
        _jwks_cache[cache_key] = {"jwks": jwks, "expires_at": expires_at}
        return jwks


class MicrosoftOAuthAdapter(OAuthProviderAdapter):
    """Microsoft OAuth/OIDC adapter."""

    def __init__(self):
        super().__init__(OAuthProvider.MICROSOFT)
        self.client_id = settings.OAUTH_MICROSOFT_CLIENT_ID
        self.client_secret = settings.OAUTH_MICROSOFT_CLIENT_SECRET
        self.redirect_uri = settings.OAUTH_MICROSOFT_REDIRECT_URI
        self.tenant = "common"  # Can be made configurable

    def get_authorize_url(self, state: str, nonce: str, redirect_uri: str | None = None) -> str:
        """Generate Microsoft authorization URL."""
        # Validate redirect URI
        redirect_uri = self._validate_redirect_uri(redirect_uri) or self.redirect_uri
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "response_mode": "query",
        }
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/authorize?{urlencode(params)}"

    def get_token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"

    def get_jwks_uri(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant}/discovery/v2.0/keys"

    def get_issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant}/v2.0"

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.get_token_endpoint(),
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri or self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    async def validate_id_token(self, id_token: str, nonce: str, client_id: str) -> dict[str, Any]:
        """Validate Microsoft id_token."""
        from jose import jwk

        # Get JWKS
        jwks = await self._get_jwks()
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")

        # Find the key
        key = None
        for jwk_key in jwks.get("keys", []):
            if jwk_key.get("kid") == kid:
                key = jwk.construct(jwk_key)
                break

        if not key:
            raise ValueError("Key not found in JWKS")

        # Decode and verify
        try:
            payload = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=client_id,
                # Microsoft issuer can vary by tenant, so we check prefix
                options={"verify_iss": False},  # We'll verify manually
            )
            # Verify issuer pattern
            issuer = payload.get("iss", "")
            if not issuer.startswith("https://login.microsoftonline.com/"):
                raise ValueError("Invalid issuer")
            # Verify nonce
            if payload.get("nonce") != nonce:
                raise ValueError("Nonce mismatch")
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid id_token: {e}") from e

    async def _get_jwks(self) -> dict:
        """Get JWKS (cached with TTL)."""
        cache_key = "jwks:microsoft"
        now = datetime.now(timezone.utc).timestamp()

        # Check cache
        if cache_key in _jwks_cache:
            cached = _jwks_cache[cache_key]
            expires_at = cached.get("expires_at", 0)
            if now < expires_at:
                return cached["jwks"]

        # Fetch fresh JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(self.get_jwks_uri())
            response.raise_for_status()
            jwks = response.json()

        # Cache with TTL
        expires_at = now + settings.JWKS_CACHE_TTL_SECONDS
        _jwks_cache[cache_key] = {"jwks": jwks, "expires_at": expires_at}
        return jwks


def get_provider_adapter(provider: str) -> OAuthProviderAdapter:
    """Get OAuth provider adapter."""
    provider_enum = OAuthProvider(provider.upper())
    if provider_enum == OAuthProvider.GOOGLE:
        return GoogleOAuthAdapter()
    elif provider_enum == OAuthProvider.MICROSOFT:
        return MicrosoftOAuthAdapter()
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def generate_oauth_state() -> str:
    """Generate secure OAuth state."""
    return secrets.token_urlsafe(32)


def generate_oauth_nonce() -> str:
    """Generate secure OAuth nonce."""
    return secrets.token_urlsafe(32)


def store_oauth_state(state: str, nonce: str, provider: str) -> None:
    """Store OAuth state and nonce in Redis."""
    redis_client = get_redis_client()
    if not redis_client:
        raise ValueError("Redis not available for OAuth state storage")

    data = {
        "nonce": nonce,
        "provider": provider,
        "created_at": str(datetime.now(timezone.utc)),
    }
    redis_client.setex(
        f"oauth:state:{state}",
        settings.OAUTH_STATE_TTL,
        json.dumps(data),
    )


def get_oauth_state(state: str) -> dict[str, Any] | None:
    """Get and delete OAuth state from Redis (one-time use)."""
    redis_client = get_redis_client()
    if not redis_client:
        return None

    key = f"oauth:state:{state}"
    data = redis_client.get(key)
    if data:
        redis_client.delete(key)  # One-time use - delete immediately after fetch
        return json.loads(data)
    return None


def create_oauth_link_token(provider: str, provider_subject: str, email: str) -> str:
    """Create a link token for OAuth account linking."""
    import secrets

    redis_client = get_redis_client()
    if not redis_client:
        raise ValueError("Redis not available for OAuth link token storage")

    link_token = secrets.token_urlsafe(32)
    data = {
        "provider": provider,
        "provider_subject": provider_subject,
        "email": email,
        "created_at": str(datetime.now(timezone.utc)),
    }
    redis_client.setex(
        f"oauth:link:{link_token}",
        settings.OAUTH_LINK_TTL,
        json.dumps(data),
    )
    return link_token


def get_oauth_link_token(link_token: str) -> dict[str, Any] | None:
    """Get and delete OAuth link token from Redis (one-time use)."""
    redis_client = get_redis_client()
    if not redis_client:
        return None

    key = f"oauth:link:{link_token}"
    data = redis_client.get(key)
    if data:
        redis_client.delete(key)  # One-time use
        return json.loads(data)
    return None

