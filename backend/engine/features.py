import chess
import numpy as np
import torch

from .constants import HALFKP_DIM, POLICY_SIZE
from .move_mapping import MOVE_TO_IDX

PIECE_TYPES = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]


def board_to_tensor(board: chess.Board) -> torch.Tensor:
    """Encodes board into an 18-plane 8x8 spatial tensor:
    - Planes 0..5: White [P, N, B, R, Q, K]
    - Planes 6..11: Black [P, N, B, R, Q, K]
    - Plane 12: Side to move (1.0 for White, 0.0 for Black)
    - Plane 13: White kingside castling right
    - Plane 14: White queenside castling right
    - Plane 15: Black kingside castling right
    - Plane 16: Black queenside castling right
    - Plane 17: En-passant target square
    """
    planes = np.zeros((18, 8, 8), dtype=np.float32)
    for color in [chess.WHITE, chess.BLACK]:
        for i, ptype in enumerate(PIECE_TYPES):
            plane_idx = (0 if color == chess.WHITE else 6) + i
            for sq in board.pieces(ptype, color):
                row = 7 - (sq // 8)
                col = sq % 8
                planes[plane_idx, row, col] = 1.0

    if board.turn == chess.WHITE:
        planes[12, :, :] = 1.0
    if board.has_kingside_castling_rights(chess.WHITE):
        planes[13, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.WHITE):
        planes[14, :, :] = 1.0
    if board.has_kingside_castling_rights(chess.BLACK):
        planes[15, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.BLACK):
        planes[16, :, :] = 1.0
    if board.ep_square is not None:
        row = 7 - (board.ep_square // 8)
        col = board.ep_square % 8
        planes[17, row, col] = 1.0

    return torch.from_numpy(planes).float()


def board_to_halfkp_features(board: chess.Board, king_color: bool | None = None) -> torch.Tensor:
    """HalfKP feature vector anchored on a specific king (side to move by default).
    Dimension is 64 * 10 * 64 = 40,960.
    """
    if king_color is None:
        king_color = board.turn
    feature_vec = torch.zeros(HALFKP_DIM, dtype=torch.float32)
    king_sq = board.king(king_color)
    if king_sq is None:
        return feature_vec

    for color in [chess.WHITE, chess.BLACK]:
        for i, ptype in enumerate(PIECE_TYPES):
            if ptype == chess.KING:
                continue
            piece_idx_adj = i + (0 if color == chess.WHITE else 5)
            for sq in board.pieces(ptype, color):
                feature_idx = king_sq * 640 + piece_idx_adj * 64 + sq
                feature_vec[feature_idx] = 1.0

    return feature_vec


def board_to_halfkp_sparse_indices(board: chess.Board, king_color: bool | None = None) -> list[int]:
    """Returns list of active feature indices for HalfKP (much faster for batching)."""
    if king_color is None:
        king_color = board.turn
    king_sq = board.king(king_color)
    if king_sq is None:
        return []

    indices = []
    for color in [chess.WHITE, chess.BLACK]:
        for i, ptype in enumerate(PIECE_TYPES):
            if ptype == chess.KING:
                continue
            piece_idx_adj = i + (0 if color == chess.WHITE else 5)
            for sq in board.pieces(ptype, color):
                indices.append(king_sq * 640 + piece_idx_adj * 64 + sq)
    return indices


def board_to_halfkp_both_perspectives(board: chess.Board) -> torch.Tensor:
    """Sum of features anchored on both kings (kept for backward compatibility)."""
    return board_to_halfkp_features(board, chess.WHITE) + board_to_halfkp_features(board, chess.BLACK)


def legal_moves_mask(board: chess.Board) -> torch.Tensor:
    """Binary mask of legal moves against the POLICY_SIZE output space."""
    mask = torch.zeros(POLICY_SIZE, dtype=torch.float32)
    for move in board.legal_moves:
        if move in MOVE_TO_IDX:
            mask[MOVE_TO_IDX[move]] = 1.0
    return mask
