from dome_core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api import auth
from app.core.config import settings
from app.core.limiter import RateLimitMiddleware
from app.core.logging import setup_logging
from app.core.sentry import init_sentry

init_sentry()
setup_logging()

app = FastAPI(
    title="Dome Auth Service",
    description="Cross-subdomain authentication gateway for the DOME portfolio.",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
)

origins = [o.strip() for o in settings.allowed_origins.split(",")]

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware, environment=settings.environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RequestIDMiddleware)

app.include_router(auth.router)


@app.api_route("/api/v1/health", methods=["GET", "HEAD"], tags=["health"])
async def health_check():
    return {"status": "ok"}


@app.api_route("/api/v1/ready", methods=["GET", "HEAD"], tags=["health"])
async def readiness_check():
    supabase_status = "ok"
    try:
        from app.core.db import get_db

        get_db().auth.get_user("__readiness_probe__")
    except Exception as e:
        err_str = str(e).lower()
        if "invalid" in err_str or "expired" in err_str or "token" in err_str:
            supabase_status = "ok"
        else:
            supabase_status = "unavailable"
    return {"status": "ok", "supabase": supabase_status}
