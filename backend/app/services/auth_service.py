import logging

from sqlalchemy.orm import Session

from app.auth.jwt import hash_password, verify_password
from app.exceptions import ConflictError, NotFoundError
from app.models.user import User

logger = logging.getLogger(__name__)


def create_user(db: Session, email: str, password: str, full_name: str | None) -> User:
    if db.query(User).filter(User.email == email).first():
        raise ConflictError("A user with this email already exists")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created user id=%s", user.id)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User")
    return user
