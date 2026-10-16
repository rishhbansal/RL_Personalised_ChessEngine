from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from database import users_collection
from schemas import LoginRequest, TokenResponse, UserResponse
from security import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_DUMMY_HASH = hash_password("not-a-real-password-used-only-for-timing")


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = await users_collection.find_one({"email": payload.email})

    if user:
        password_ok = verify_password(payload.password, user["hashed_password"])
    else:
        verify_password(payload.password, _DUMMY_HASH)
        password_ok = False

    if not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    user_id = str(user["_id"])
    token = create_access_token(subject=user_id)
    return TokenResponse(access_token=token, user=UserResponse(id=user_id, email=user["email"]))


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        user = None

    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return UserResponse(id=str(user["_id"]), email=user["email"])


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserResponse = Depends(get_current_user)):
    return current_user