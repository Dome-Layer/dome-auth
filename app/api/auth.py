from __future__ import annotations

from datetime import datetime, timezone

from dome_core.auth import AuthError, make_supabase_fallback, verify_jwt
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.schemas import (
    ErrorResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    RefreshRequest,
    SessionResponse,
    VerifyRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _supabase_for_fallback():
    """Service-role client for the network fallback, or None if unconfigured."""
    try:
        return get_db()
    except Exception:
        return None


# Used only when local JWKS verification can't reach a signing key (DA-005).
_network_fallback = make_supabase_fallback(_supabase_for_fallback)


def get_current_user(request: Request) -> dict:
    """Verify the Supabase access token locally (dome-core verify_jwt) with a
    live get_user fallback. Returns a dict with 'user_id' and 'email'."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        principal = verify_jwt(
            token, supabase_url=settings.supabase_url, network_fallback=_network_fallback
        )
        return {"user_id": principal.user_id, "email": principal.email}
    except AuthError as e:
        logger.warning("auth_verification_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


@router.post(
    "/magic-link",
    response_model=MagicLinkResponse,
    responses={400: {"model": ErrorResponse}},
)
async def request_magic_link(body: MagicLinkRequest):
    supabase = get_db()

    try:
        supabase.auth.sign_in_with_otp(
            {
                "email": body.email,
                "options": {"email_redirect_to": settings.get_auth_callback_url()},
            }
        )
    except Exception as e:
        logger.error("magic_link_send_failed", email_domain=body.email.split("@")[1], error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to send magic link: {e}")

    return MagicLinkResponse(
        message="Magic link sent. Check your email.",
        expires_in_minutes=60,
    )


@router.post(
    "/verify",
    response_model=SessionResponse,
    responses={401: {"model": ErrorResponse}},
)
async def verify_token(body: VerifyRequest):
    supabase = get_db()

    try:
        session_response = supabase.auth.verify_otp({"token": body.token, "type": "magiclink"})
        session = session_response.session
        user = session_response.user
        if session is None or user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("token_verification_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return SessionResponse(
        user_id=user.id,
        email=user.email,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_at=datetime.fromtimestamp(session.expires_at, tz=timezone.utc)
        if isinstance(session.expires_at, (int, float))
        else datetime.now(timezone.utc),
    )


@router.delete("/session", status_code=204)
async def logout(request: Request, user: dict = Depends(get_current_user)):
    # Revoke the server-side session (refresh tokens) via the service-role admin
    # API. NOTE: the access-token JWT is stateless and stays valid until its ~1h
    # expiry — this ends the renewable session, not the current access token.
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    try:
        get_db().auth.admin.sign_out(token)
        logger.info("user_logged_out", user_id=user["user_id"], revoked=True)
    except Exception as e:
        logger.warning("logout_revoke_failed", user_id=user["user_id"], error=str(e))
    return None


@router.post(
    "/refresh",
    response_model=SessionResponse,
    responses={401: {"model": ErrorResponse}},
)
async def refresh_session(body: RefreshRequest):
    """Rotate an access+refresh token pair from a valid refresh token.

    Supabase rotates the refresh token on each use, invalidating the previous
    one. Returns a fresh SessionResponse."""
    supabase = get_db()

    try:
        session_response = supabase.auth.refresh_session(body.refresh_token)
        session = session_response.session
        user = session_response.user
        if session is None or user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("token_refresh_failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    return SessionResponse(
        user_id=user.id,
        email=user.email,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_at=datetime.fromtimestamp(session.expires_at, tz=timezone.utc)
        if isinstance(session.expires_at, (int, float))
        else datetime.now(timezone.utc),
    )
