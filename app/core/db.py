from dome_core.db import get_db as _get_db

from app.core.config import settings


def get_db():
    return _get_db(url=settings.supabase_url, service_role_key=settings.supabase_service_role_key)


__all__ = ["get_db"]
