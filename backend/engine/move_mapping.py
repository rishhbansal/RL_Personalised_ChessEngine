
import chess

from .constants import POLICY_SIZE


def build_move_mapping():
    move_to_idx, idx_to_move = {}, []
    directions = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    for from_sq in range(64):
        # Sliding directions (rook + bishop rays -> covers queen/rook/bishop moves)
        for dx, dy in directions:
            for step in range(1, 8):
                to_file = (from_sq % 8) + dx * step
                to_rank = (from_sq // 8) + dy * step
                if 0 <= to_file < 8 and 0 <= to_rank < 8:
                    move = chess.Move(from_sq, to_rank * 8 + to_file)
                    if move not in move_to_idx:
                        move_to_idx[move] = len(idx_to_move)
                        idx_to_move.append(move)

        # Knight moves
        for dx, dy in [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]:
            to_file = (from_sq % 8) + dx
            to_rank = (from_sq // 8) + dy
            if 0 <= to_file < 8 and 0 <= to_rank < 8:
                move = chess.Move(from_sq, to_rank * 8 + to_file)
                if move not in move_to_idx:
                    move_to_idx[move] = len(idx_to_move)
                    idx_to_move.append(move)

        # Promotions
        if (from_sq // 8) == 6:  # white 7th rank
            for dx in [-1, 0, 1]:
                to_file = (from_sq % 8) + dx
                if 0 <= to_file < 8:
                    to_sq = 8 * 7 + to_file
                    for promo in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
                        move = chess.Move(from_sq, to_sq, promotion=promo)
                        if move not in move_to_idx:
                            move_to_idx[move] = len(idx_to_move)
                            idx_to_move.append(move)
        elif (from_sq // 8) == 1:  # black 2nd rank
            for dx in [-1, 0, 1]:
                to_file = (from_sq % 8) + dx
                if 0 <= to_file < 8:
                    to_sq = 0 * 8 + to_file
                    for promo in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
                        move = chess.Move(from_sq, to_sq, promotion=promo)
                        if move not in move_to_idx:
                            move_to_idx[move] = len(idx_to_move)
                            idx_to_move.append(move)

    return move_to_idx, idx_to_move


MOVE_TO_IDX, IDX_TO_MOVE = build_move_mapping()

# NOTE: this mapping produces ~1968 distinct moves, not POLICY_SIZE (4672).
# That's expected and matches the training notebook exactly: POLICY_SIZE is
# just the PolicyHead's output width (with unused headroom), and every move
# this function produces gets a valid index within that range. Do not "fix"
# this to be exactly POLICY_SIZE -- doing so would change indices and break
# compatibility with the trained weights.
assert len(IDX_TO_MOVE) <= POLICY_SIZE, (
    f"Move mapping produced {len(IDX_TO_MOVE)} moves, which exceeds POLICY_SIZE "
    f"({POLICY_SIZE}). This would overflow the policy head's output and break "
    "compatibility with the trained weights -- do not proceed."
)
