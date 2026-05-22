from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.schemas import (
    ErrorResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    SessionResponse,
    VerifyRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = auth_header.removeprefix("Bearer ").strip()
    supabase = get_db()

    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        return {"user_id": user.id, "email": user.email}
    except HTTPException:
        raise
    except Exception as e:
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
        expires_at=datetime.fromtimestamp(session.expires_at, tz=timezone.utc)
        if isinstance(session.expires_at, (int, float))
        else datetime.now(timezone.utc),
    )


@router.delete("/session", status_code=204)
async def logout(user: dict = Depends(get_current_user)):
    logger.info("user_logged_out", user_id=user["user_id"])
    return None
