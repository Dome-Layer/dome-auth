from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MagicLinkRequest(BaseModel):
    email: str = Field(
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
        max_length=254,
    )


class MagicLinkResponse(BaseModel):
    message: str
    expires_in_minutes: int


class VerifyRequest(BaseModel):
    token: str


class SessionResponse(BaseModel):
    user_id: str
    email: str
    access_token: str
    expires_at: datetime


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
