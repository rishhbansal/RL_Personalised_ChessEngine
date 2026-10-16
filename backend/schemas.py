from datetime import datetime
from zoneinfo import ZoneInfo

created_at = datetime.now(ZoneInfo("Asia/Kolkata"))
from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MoveRecord(BaseModel):
    ply: int
    move_san: str
    move_uci: str
    fen_before: str
    fen_after: str
    eval_before: float
    eval_after: float
    is_capture: bool = False
    is_check: bool = False
    by: str  # "player" | "engine"
    explanation: Optional[str] = None
    top_alternatives: list[dict] = []
    style: Optional[dict] = None  


class GameCreate(BaseModel):
    style: dict


class GameResultIn(BaseModel):
    result: str  

class GameSummary(BaseModel):
    id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    result: Optional[str] = None
    num_moves: int
    final_eval: Optional[float] = None
    style: dict


class GameDetail(GameSummary):
    moves: list[MoveRecord]


class StatsResponse(BaseModel):
    total_games: int
    wins: int
    losses: int
    draws: int
    avg_move_swing: float
    timeline: list[dict]
    style: Optional[dict] = None
    games_analyzed: Optional[int] = None
    rationale: Optional[str] = None


class StyleRecommendation(BaseModel):
    style: dict
    games_analyzed: int
    rationale: str