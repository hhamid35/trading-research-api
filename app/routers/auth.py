from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..auth import (
    create_access_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from ..db import get_session
from ..deps import get_current_user
from ..models import ApiKey, User
from ..schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreatedOut,
    ApiKeyOut,
    TokenOut,
    UserLogin,
    UserOut,
    UserRegister,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister, session: Session = Depends(get_session)) -> User:
    existing = session.exec(
        select(User).where(User.email == payload.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, session: Session = Depends(get_session)) -> dict:
    user = session.exec(
        select(User).where(User.email == payload.email)
    ).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/api-keys", response_model=ApiKeyCreatedOut, status_code=201)
def create_api_key(
    payload: ApiKeyCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    raw_key, key_hash, key_prefix = generate_api_key()
    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        label=payload.label,
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)
    return {
        "id": api_key.id,
        "label": api_key.label,
        "key_prefix": api_key.key_prefix,
        "created_at": api_key.created_at,
        "last_used_at": api_key.last_used_at,
        "raw_key": raw_key,
    }


@router.get("/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ApiKey]:
    return list(
        session.exec(
            select(ApiKey)
            .where(ApiKey.user_id == user.id)
            .order_by(ApiKey.created_at.desc())
        ).all()
    )


@router.delete("/api-keys/{key_id}", status_code=204)
def delete_api_key(
    key_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    api_key = session.get(ApiKey, key_id)
    if not api_key or api_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key not found")
    session.delete(api_key)
    session.commit()
