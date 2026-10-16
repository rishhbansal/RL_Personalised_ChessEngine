import os
from datetime import datetime
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
created_at = datetime.now(ZoneInfo("Asia/Kolkata"))
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

import chess
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import router as auth_router
from database import db, ensure_indexes, games_collection
from engine.engine_manager import best_move_for_fen, evaluate_fen_white_pov, load_models
from engine.mcts import StyleParams
from engine.coach import explain_move, summarize_game
from schemas import (
    GameCreate,
    GameDetail,
    GameResultIn,
    GameSummary,
    MoveRecord,
    StatsResponse,
    StyleRecommendation,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.on_event("startup")
def _startup():
    # Fails loudly and immediately if weights are missing, rather than on
    # the first request a user makes.
    load_models()


@app.on_event("startup")
async def _startup_db():
    await ensure_indexes()


class StyleParamsIn(BaseModel):
    difficulty: float = 50.0
    aggression: float = 50.0
    risk_tolerance: float = 50.0
    positional_tactical: float = 50.0


class EngineMoveRequest(BaseModel):
    fen: str
    style: StyleParamsIn = StyleParamsIn()


class EvaluateRequest(BaseModel):
    fen: str


class ExplainRequest(BaseModel):
    fen_before: str
    move_san: str
    eval_before: float
    eval_after: float
    is_capture: bool = False
    is_check: bool = False
    top_alternatives: list[dict] = []



async def get_demo_user_id(x_demo_user: str | None = Header(default=None)) -> str:
    if not x_demo_user:
        return "demo-default"
    return x_demo_user.strip().lower()


def _clamp(v: float, lo: float = 0, hi: float = 100) -> int:
    return int(round(max(lo, min(hi, v))))


@app.get("/api/test-db")
async def test_db():
    collections = await db.list_collection_names()

    return {
        "status": "connected",
        "database": "rl_chess",
        "collections": collections
    }


@app.post("/api/evaluate")
def evaluate(req: EvaluateRequest):
    try:
        chess.Board(req.fen)
    except ValueError:
        raise HTTPException(400, "Invalid FEN")
    return {"eval": round(evaluate_fen_white_pov(req.fen), 3)}


@app.post("/api/engine-move")
def engine_move(req: EngineMoveRequest):
    try:
        board = chess.Board(req.fen)
    except ValueError:
        raise HTTPException(400, "Invalid FEN")

    if board.is_game_over():
        raise HTTPException(400, "Game is already over")

    style = StyleParams(**req.style.dict())
    result = best_move_for_fen(req.fen, style)
    if result is None:
        raise HTTPException(400, "No legal moves available")
    return result


class GameSummaryRequest(BaseModel):
    result: str
    player_color: str = "White"
    total_moves: int = 0
    player_errors: list[dict] = []


@app.post("/api/game-summary")
def get_game_summary(req: GameSummaryRequest):
    try:
        summary_text = summarize_game(
            result=req.result,
            player_color=req.player_color,
            total_moves=req.total_moves,
            player_errors=req.player_errors,
        )
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"summary": summary_text}


@app.post("/api/explain")
def explain(req: ExplainRequest):
    try:
        text = explain_move(
            fen_before=req.fen_before,
            move_san=req.move_san,
            eval_before=req.eval_before,
            eval_after=req.eval_after,
            is_capture=req.is_capture,
            is_check=req.is_check,
            top_alternatives=req.top_alternatives,
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"explanation": text}


# ---------------------------------------------------------------------------
# Game persistence (MongoDB) — powers the Analysis and Dashboard pages.

async def _get_owned_game(game_id: str, user_id: str):
    try:
        oid = ObjectId(game_id)
    except InvalidId:
        raise HTTPException(400, "Invalid game id")
    game = await games_collection.find_one({"_id": oid})
    if game is None:
        raise HTTPException(404, "Game not found")
    return oid, game


def _to_summary(g: dict) -> GameSummary:
    moves = g.get("moves", [])
    return GameSummary(
        id=str(g["_id"]),
        started_at=g["started_at"],
        ended_at=g.get("ended_at"),
        result=g.get("result"),
        num_moves=len(moves),
        final_eval=(moves[-1]["eval_after"] if moves else None),
        style=g.get("style", {}),
    )


@app.post("/api/games", response_model=GameSummary)
async def create_game(payload: GameCreate, user_id: str = Depends(get_demo_user_id)):
    now = datetime.now(IST)
    doc = {
        "user_id": user_id,
        "style": payload.style,
        "moves": [],
        "result": None,
        "started_at": now,
        "updated_at": now,
        "ended_at": None,
    }
    res = await games_collection.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _to_summary(doc)


@app.post("/api/games/{game_id}/moves")
async def add_move(
    game_id: str, move: MoveRecord, user_id: str = Depends(get_demo_user_id)
):
    oid, _ = await _get_owned_game(game_id, user_id)
    await games_collection.update_one(
        {"_id": oid},
        {"$push": {"moves": move.dict()}, "$set": {"updated_at": datetime.now(IST)}},
    )
    return {"status": "ok"}


@app.post("/api/games/{game_id}/finish")
async def finish_game(
    game_id: str, payload: GameResultIn, user_id: str = Depends(get_demo_user_id)
):
    oid, _ = await _get_owned_game(game_id, user_id)
    now = datetime.now(IST)
    await games_collection.update_one(
        {"_id": oid},
        {"$set": {"result": payload.result, "ended_at": now, "updated_at": now}},
    )
    return {"status": "ok"}


@app.get("/api/games", response_model=list[GameSummary])
async def list_games(user_id: str = Depends(get_demo_user_id)):
    cursor = games_collection.find({"user_id": user_id}).sort("started_at", -1)
    user_games = await cursor.to_list(length=200)
    played_games = [g for g in user_games if len(g.get("moves", [])) > 0]

    # Fallback: if user logged in with a different email, still surface all local played games
    if not played_games:
        all_cursor = games_collection.find({}).sort("started_at", -1)
        all_games = await all_cursor.to_list(length=200)
        played_games = [g for g in all_games if len(g.get("moves", [])) > 0]

    return [_to_summary(g) for g in played_games]


MAX_STEP = 12.0
CONFIDENCE_GAMES = 10.0


def _confidence(n: int) -> float:
    """How much we trust the sample. Ramps 0 -> 1 as games played -> CONFIDENCE_GAMES."""
    return min(n / CONFIDENCE_GAMES, 1.0)


def _step_toward(current: float, target: float, confidence: float) -> int:
    """Move `current` toward `target`, bounded to +/-MAX_STEP * confidence."""
    target = max(0.0, min(100.0, target))
    delta = target - current
    capped = max(-MAX_STEP, min(MAX_STEP, delta)) * confidence
    return _clamp(current + capped)


def _skill_label(difficulty: float) -> str:
    if difficulty < 20:
        return "Novice"
    if difficulty < 40:
        return "Beginner"
    if difficulty < 60:
        return "Intermediate"
    if difficulty < 80:
        return "Advanced"
    return "Expert"


@app.get("/api/games/recommend-style", response_model=StyleRecommendation)
async def recommend_style(user_id: str = Depends(get_demo_user_id)):
    cursor = games_collection.find({"user_id": user_id}).sort("started_at", -1).limit(20)
    games = await cursor.to_list(length=20)
    games = [g for g in games if len(g.get("moves", [])) > 0][:10]

    if not games:
        all_cursor = games_collection.find({}).sort("started_at", -1).limit(20)
        all_games = await all_cursor.to_list(length=20)
        games = [g for g in all_games if len(g.get("moves", [])) > 0][:10]

    default_style = {
        "difficulty": 50.0,
        "aggression": 50.0,
        "risk_tolerance": 50.0,
        "positional_tactical": 50.0,
    }

    finished = [g for g in games if g.get("result")]
    if not finished:
        return StyleRecommendation(
            style=default_style,
            games_analyzed=0,
            rationale="Not enough finished games yet — play a few to unlock auto-tuning.",
        )

    current_style = games[0].get("style") or default_style
    current = {k: float(current_style.get(k, default_style[k])) for k in default_style}

    # Player is always White in this app.
    wins = sum(1 for g in finished if g["result"] == "1-0")
    losses = sum(1 for g in finished if g["result"] == "0-1")
    win_rate = wins / len(finished)
    confidence = _confidence(len(finished))

    player_moves = [
        m for g in games for m in g.get("moves", []) if m.get("by") == "player"
    ]

    if player_moves:
        capture_rate = sum(1 for m in player_moves if m.get("is_capture")) / len(player_moves)
        check_rate = sum(1 for m in player_moves if m.get("is_check")) / len(player_moves)
        # Clamp per-move swing before averaging so one blunder/brilliancy
        # doesn't dominate the average and yank risk_tolerance around.
        avg_swing = sum(
            min(abs(m["eval_after"] - m["eval_before"]), 1.5) for m in player_moves
        ) / len(player_moves)
    else:
        capture_rate = check_rate = avg_swing = 0.0

   
    target_difficulty = 50 + (win_rate - 0.5) * 60
    target_aggression = (capture_rate + check_rate) / 2 * 120
    target_risk_tolerance = (avg_swing / 1.5) * 100
    target_positional_tactical = capture_rate * 150

    difficulty = _step_toward(current["difficulty"], target_difficulty, confidence)
    aggression = _step_toward(current["aggression"], target_aggression, confidence)
    risk_tolerance = _step_toward(current["risk_tolerance"], target_risk_tolerance, confidence)
    positional_tactical = _step_toward(
        current["positional_tactical"], target_positional_tactical, confidence
    )

    style = {
        "difficulty": difficulty,
        "aggression": aggression,
        "risk_tolerance": risk_tolerance,
        "positional_tactical": positional_tactical,
    }

    if win_rate >= 0.6:
        form = "winning most of your recent games"
    elif win_rate <= 0.35:
        form = "finding your recent games tough"
    else:
        form = "playing evenly"

    rationale = (
        f"Based on your last {len(finished)} games ({wins}W-{losses}L, {form}), "
        f"the engine is nudged to difficulty {difficulty}/100 ({_skill_label(difficulty)}) with "
        f"{'a tactical' if positional_tactical > 55 else 'a positional'} lean matching your play style."
    )

    return StyleRecommendation(style=style, games_analyzed=len(finished), rationale=rationale)


@app.get("/api/games/{game_id}", response_model=GameDetail)
async def get_game(game_id: str, user_id: str = Depends(get_demo_user_id)):
    _, game = await _get_owned_game(game_id, user_id)
    summary = _to_summary(game)
    return GameDetail(**summary.dict(), moves=game.get("moves", []))


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(user_id: str = Depends(get_demo_user_id)):
    cursor = games_collection.find({"user_id": user_id}).sort("started_at", 1)
    games = await cursor.to_list(length=1000)

    total = len(games)
    wins = sum(1 for g in games if g.get("result") == "1-0")
    losses = sum(1 for g in games if g.get("result") == "0-1")
    draws = sum(1 for g in games if g.get("result") == "1/2-1/2")

    swings = [
        abs(m["eval_after"] - m["eval_before"])
        for g in games
        for m in g.get("moves", [])
        if m.get("by") == "player"
    ]
    avg_swing = round(sum(swings) / len(swings), 4) if swings else 0.0

    activity = Counter()

    for g in games:
        day = g["started_at"].strftime("%d %b")
        activity[day] += 1

    timeline = [
        {
            "date": day,
            "games": count,
        }
        for day, count in activity.items()
    ]

    return StatsResponse(
        total_games=total,
        wins=wins,
        losses=losses,
        draws=draws,
        avg_move_swing=avg_swing,
        timeline=timeline,
    )


@app.get("/")
def root():
    return {"message": "Hello from app.py"}