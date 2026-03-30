from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from .auth import decode_access_token, hash_api_key
from .db import get_session
from .models import ApiKey, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials

    # Try JWT first
    subject = decode_access_token(token)
    if subject:
        user = session.get(User, UUID(subject))
        if user and user.is_active:
            return user

    # Try API key
    key_hash = hash_api_key(token)
    api_key = session.exec(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    ).first()
    if api_key:
        user = session.get(User, api_key.user_id)
        if user and user.is_active:
            from .models import utcnow

            api_key.last_used_at = utcnow()
            session.add(api_key)
            session.commit()
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User | None:
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, session)
    except HTTPException:
        return None
