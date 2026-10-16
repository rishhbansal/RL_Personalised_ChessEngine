import glob
import logging
import os

import chess
import torch

from .constants import DEVICE
from .mcts import StyleParams, mcts_search
from .models import NNUE, PolicyHead
from .move_mapping import MOVE_TO_IDX

logger = logging.getLogger("engine_manager")

WEIGHTS_DIR = os.environ.get("WEIGHTS_DIR", os.path.join(os.path.dirname(__file__), "weights"))
NNUE_PATH = os.path.join(WEIGHTS_DIR, "nnue_distilled.pth")
POLICY_PATH = os.path.join(WEIGHTS_DIR, "policy_distilled.pth")

_nnue = None
_policy = None


def find_latest_checkpoint(pattern: str) -> str | None:
    matches = glob.glob(os.path.join(WEIGHTS_DIR, pattern))
    if not matches:
        return None
    matches.sort(key=os.path.getmtime, reverse=True)
    return matches[0]


def resolve_model_paths() -> tuple[str | None, str | None]:
    # Check primary default paths first
    nnue_candidate = NNUE_PATH if os.path.exists(NNUE_PATH) else None
    policy_candidate = POLICY_PATH if os.path.exists(POLICY_PATH) else None

    # Search alternative common names
    if not nnue_candidate:
        for candidate_name in ["nnue_modern_distilled.pth", "nnue_supervised.pth", "nnue_modern_chunk*.pth", "nnue_*.pth"]:
            found = find_latest_checkpoint(candidate_name)
            if found:
                nnue_candidate = found
                break

    if not policy_candidate:
        for candidate_name in ["policy_distilled.pth", "policy_after_chunk*.pth", "policy_supervised.pth", "policy_rl_*.pth", "policy_*.pth"]:
            found = find_latest_checkpoint(candidate_name)
            if found:
                policy_candidate = found
                break

    return nnue_candidate, policy_candidate


def load_models(allow_random_fallback: bool = True):
    """Idempotent model loader with smart checkpoint discovery and fallback."""
    global _nnue, _policy
    if _nnue is not None and _policy is not None:
        return

    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    nnue_path, policy_path = resolve_model_paths()

    nnue = NNUE().to(DEVICE)
    policy = PolicyHead().to(DEVICE)

    if nnue_path and policy_path:
        logger.info(f"Loading weights:\n  NNUE: {nnue_path}\n  Policy: {policy_path}")
        nnue.load_state_dict(torch.load(nnue_path, map_location=DEVICE))
        policy.load_state_dict(torch.load(policy_path, map_location=DEVICE))
        print(f"Loaded model weights from {nnue_path} and {policy_path}")
    else:
        if allow_random_fallback:
            print(
                f"[WARNING] Model weights not found in {WEIGHTS_DIR}. "
                "Initialized fresh models for development/testing. "
                "Train or copy weights into backend/engine/weights/ to play with full strength."
            )
        else:
            raise FileNotFoundError(
                f"Missing model weights in {WEIGHTS_DIR}. Please train checkpoints and save to {WEIGHTS_DIR}."
            )

    nnue.eval()
    policy.eval()
    _nnue, _policy = nnue, policy


def _require_models():
    if _nnue is None or _policy is None:
        load_models()
    return _nnue, _policy


def evaluate_fen(fen: str) -> float:
    """Returns NNUE evaluation in [-1, 1] from the perspective of the side to move."""
    from .features import board_to_halfkp_features

    nnue, _ = _require_models()
    board = chess.Board(fen)
    with torch.no_grad():
        feat = board_to_halfkp_features(board).unsqueeze(0).to(DEVICE)
        v = nnue(feat).item()
    return v


def evaluate_fen_white_pov(fen: str) -> float:
    """Normalized evaluation from White's perspective [-1, 1] (suitable for UI eval bars)."""
    board = chess.Board(fen)
    v = evaluate_fen(fen)
    return v if board.turn == chess.WHITE else -v


def best_move_for_fen(fen: str, style: StyleParams):
    """Runs MCTS search from given FEN and returns chosen move with candidate metadata."""
    nnue, policy = _require_models()
    board = chess.Board(fen)

    if board.is_game_over():
        return None

    move, visit_probs, root = mcts_search(board, nnue, policy, style, temperature=style.play_temperature)

    candidates = sorted(root.children.items(), key=lambda kv: kv[1].N, reverse=True)[:3]
    top_moves = [
        {
            "san": board.san(m),
            "uci": m.uci(),
            "visits": child.N,
            # Q is stored from child perspective; mover perspective is -child.Q
            "value": round(-child.Q if child.N > 0 else 0.0, 3),
        }
        for m, child in candidates
    ]

    san = board.san(move)
    eval_before = evaluate_fen_white_pov(fen)

    board.push(move)
    eval_after = evaluate_fen_white_pov(board.fen())

    return {
        "move_uci": move.uci(),
        "move_san": san,
        "fen_after": board.fen(),
        "eval_before": round(eval_before, 3),
        "eval_after": round(eval_after, 3),
        "is_check": board.is_check(),
        "is_checkmate": board.is_checkmate(),
        "is_game_over": board.is_game_over(),
        "top_moves": top_moves,
    }
