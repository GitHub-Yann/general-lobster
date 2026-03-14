from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def safe_hash_password(password: str) -> str:
    """bcrypt 最大支持 72 字节，需要截断"""
    return pwd_context.hash(password.encode('utf-8')[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 验证时也截断
    return pwd_context.verify(plain_password.encode('utf-8')[:72], hashed_password)

def get_user(username: str):
    # 延迟初始化 USERS_DB，避免模块导入时哈希
    if not hasattr(get_user, "_users_db"):
        get_user._users_db = {
            "admin": {
                "username": "admin",
                "hashed_password": safe_hash_password("admin123"),
                "disabled": False,
            }
        }
    if username in get_user._users_db:
        return get_user._users_db[username]
    return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception
