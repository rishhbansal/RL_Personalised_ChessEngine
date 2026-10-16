"""Monte Carlo Tree Search (PUCT) guided by NNUE evaluation and Policy networks.

Implements the AlphaZero search framework adapted for chess:
- PUCT selection with correct parent-perspective Q-value inversion:
  Q(s, a) = -child.Q (since child.Q is evaluated from the opponent's turn).
- Root Dirichlet noise for balanced exploration during self-play.
- Fast tree expansion with legal move masking and heuristic style priors.
- Temperature-controlled move selection (argmax for play, sampling for self-play).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import chess
import numpy as np
import torch
import torch.nn.functional as F

from .constants import DEVICE, POLICY_SIZE
from .features import board_to_halfkp_features, board_to_tensor, legal_moves_mask
from .move_mapping import MOVE_TO_IDX


@dataclass
class StyleParams:
    difficulty: float = 50.0            # 0 (Novice ~800 Elo) to 100 (Grandmaster ~2200 Elo)
    aggression: float = 50.0            # 0 (Passive defense) to 100 (Hyper-aggressive attacks & checks)
    risk_tolerance: float = 50.0        # 0 (Risk-averse solid) to 100 (Gambits, sacrifices & high variance)
    positional_tactical: float = 50.0   # 0 (Positional quiet maneuvering) to 100 (Sharp tactical complications)

    @property
    def estimated_elo(self) -> int:
        """Translates difficulty setting 0-100 into standard chess Elo rating."""
        # 0 -> 800 Elo (Novice), 50 -> 1500 Elo (Intermediate), 100 -> 2200+ Elo (Master)
        return int(800 + (self.difficulty / 100.0) * 1400)

    @property
    def num_simulations(self) -> int:
        # Scale search depth with difficulty:
        # Novice: 15-30 sims (short horizon, occasional tactical misses)
        # Master: 250-400 sims (deep tactical calculation)
        base = int(15 + ((self.difficulty / 100.0) ** 1.3) * 385)
        return max(10, min(500, base))

    @property
    def c_puct(self) -> float:
        # Exploration factor: higher risk tolerance explores unconventional lines
        base = 1.1 + (self.difficulty / 100.0) * 0.4
        return base * (0.75 + (self.risk_tolerance / 100.0) * 0.5)

    @property
    def dirichlet_weight(self) -> float:
        # High risk tolerance injects more exploration noise
        return 0.02 + (self.risk_tolerance / 100.0) * 0.35

    @property
    def tactical_bias(self) -> float:
        # 0.0 = prioritize positional heuristics, 1.0 = sharp raw tactical calculation
        return self.positional_tactical / 100.0

    @property
    def play_temperature(self) -> float:
        # At lower difficulty (<50), use slight sampling temperature so the engine occasionally
        # plays plausible sub-optimal moves like an intermediate human player rather than robotic argmax.
        if self.difficulty < 25:
            return 0.85
        elif self.difficulty < 50:
            return 0.45
        elif self.difficulty < 75:
            return 0.15
        return 0.0  # Competitive greedy argmax at advanced / expert levels


class MCTSNode:
    __slots__ = ("board", "parent", "move", "children", "N", "W", "Q", "P")

    def __init__(self, board: chess.Board, parent: MCTSNode | None = None, move: chess.Move | None = None):
        self.board = board
        self.parent = parent
        self.move = move
        self.children: dict[chess.Move, MCTSNode] = {}
        self.N: int = 0
        self.W: float = 0.0
        self.Q: float = 0.0
        self.P: float = 0.0

    def is_leaf(self) -> bool:
        return len(self.children) == 0


def _positional_heuristic_priors(board: chess.Board, legal_moves: list[chess.Move]) -> dict[chess.Move, float]:
    center = {chess.D4, chess.E4, chess.D5, chess.E5}
    scores = {}
    for move in legal_moves:
        score = 1.0
        if move.to_square in center:
            score += 1.5
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            back_ranks = {0, 1, 6, 7}
            if (move.from_square // 8) in back_ranks and (move.to_square // 8) not in back_ranks:
                score += 1.0  # Minor piece development
        if board.is_castling(move):
            score += 2.0
        scores[move] = score
    total = sum(scores.values()) or 1.0
    return {m: s / total for m, s in scores.items()}


def _tactical_prior_boost(board: chess.Board, move: chess.Move, aggression: float) -> float:
    boost = 1.0
    if board.is_capture(move):
        boost += 0.6 * (aggression / 100.0)
    board.push(move)
    gives_check = board.is_check()
    board.pop()
    if gives_check:
        boost += 0.5 * (aggression / 100.0)
    return boost


@torch.no_grad()
def _evaluate_and_expand(node: MCTSNode, nnue_net, policy_net, style: StyleParams, is_root: bool) -> float:
    board = node.board
    board_t = board_to_tensor(board).unsqueeze(0).to(DEVICE)
    halfkp = board_to_halfkp_features(board).unsqueeze(0).to(DEVICE)

    # Value from perspective of node.board.turn in [-1.0, 1.0]
    v = float(nnue_net(halfkp).item())
    
    # Policy logits
    logits = policy_net(board_t).squeeze(0)
    mask = legal_moves_mask(board).to(DEVICE)
    
    # Use -1e4 rather than -1e9 to avoid half-precision NaN / overflow
    masked_logits = logits.masked_fill(mask == 0, -1e4)
    probs = F.softmax(masked_logits, dim=-1)

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return v

    heuristic_priors = None
    if style.tactical_bias < 0.999:
        heuristic_priors = _positional_heuristic_priors(board, legal_moves)

    raw_priors = {}
    for move in legal_moves:
        if move in MOVE_TO_IDX:
            idx = MOVE_TO_IDX[move]
            p = float(probs[idx].item())
        else:
            p = 1e-5
            
        if heuristic_priors is not None and move in heuristic_priors:
            p = style.tactical_bias * p + (1.0 - style.tactical_bias) * heuristic_priors[move]
            
        p *= _tactical_prior_boost(board, move, style.aggression)
        raw_priors[move] = max(p, 1e-8)

    total_prior = sum(raw_priors.values()) or 1.0
    for move in legal_moves:
        child_board = board.copy()
        child_board.push(move)
        child = MCTSNode(child_board, parent=node, move=move)
        child.P = raw_priors[move] / total_prior
        node.children[move] = child

    # Apply Dirichlet noise to root priors for exploration
    if is_root and node.children and style.dirichlet_weight > 0:
        moves = list(node.children.keys())
        noise = np.random.dirichlet([0.3] * len(moves))
        eps = style.dirichlet_weight
        for m, n_val in zip(moves, noise):
            node.children[m].P = (1.0 - eps) * node.children[m].P + eps * float(n_val)

    return v


def mcts_search(
    root_board: chess.Board,
    nnue_net,
    policy_net,
    style: StyleParams | None = None,
    num_simulations: int | None = None,
    c_puct: float | None = None,
    temperature: float = 0.0,
    add_noise: bool = True,
):
    """Executes PUCT MCTS search from the given root board.
    
    Args:
        root_board: Current chess board state
        nnue_net: Trained value evaluation network (predicts [-1, 1])
        policy_net: Trained policy network (predicts move logits)
        style: Style parameters (difficulty, aggression, etc.)
        num_simulations: Override simulation count if provided
        c_puct: Override exploration constant if provided
        temperature: Action selection temperature (0.0 for argmax, 1.0 for self-play)
        add_noise: Whether to add Dirichlet noise at root
    
    Returns:
        tuple: (best_move, visit_probs_array, root_node)
    """
    if style is None:
        style = StyleParams()

    sims = num_simulations if num_simulations is not None else style.num_simulations
    c_val = c_puct if c_puct is not None else style.c_puct

    root = MCTSNode(root_board.copy())

    if root.board.is_game_over(claim_draw=True):
        legal = list(root_board.legal_moves)
        fallback = random.choice(legal) if legal else chess.Move.null()
        return fallback, np.zeros(POLICY_SIZE, dtype=np.float32), root

    # 1. Expand root first
    v_root = _evaluate_and_expand(root, nnue_net, policy_net, style, is_root=add_noise)
    root.N = 1
    root.W = v_root
    root.Q = v_root

    if not root.children:
        legal = list(root_board.legal_moves)
        fallback = random.choice(legal) if legal else chess.Move.null()
        return fallback, np.zeros(POLICY_SIZE, dtype=np.float32), root

    # 2. Run MCTS simulations
    for _ in range(sims):
        node = root
        path = [root]

        # Selection: traverse until reaching an unexpanded node or terminal state
        while not node.is_leaf() and not node.board.is_game_over(claim_draw=True):
            sum_N = sum(c.N for c in node.children.values())
            sqrt_sum_N = math.sqrt(max(1, sum_N))

            best_score = -float("inf")
            best_child = None

            for move, child in node.children.items():
                # CORRECTED PUCT VALUE EQUATION:
                # child.Q is evaluated from child.board.turn's POV (the opponent).
                # Therefore, from the current player's POV at node, Q = -child.Q!
                if child.N > 0:
                    q_val = -child.Q
                else:
                    # First-Play Urgency (FPU): unvisited child starts slightly below parent
                    q_val = -node.Q - 0.1

                u = c_val * child.P * sqrt_sum_N / (1.0 + child.N)
                score = q_val + u

                if score > best_score:
                    best_score = score
                    best_child = child

            if best_child is None:
                break

            node = best_child
            path.append(node)

        # Evaluation & Expansion
        if not node.board.is_game_over(claim_draw=True):
            v = _evaluate_and_expand(node, nnue_net, policy_net, style, is_root=False)
        else:
            result = node.board.result(claim_draw=True)
            if result == "1-0":
                # White won. Positive if side to move at node is White, negative if Black
                v = 1.0 if node.board.turn == chess.WHITE else -1.0
            elif result == "0-1":
                # Black won. Positive if side to move at node is Black, negative if White
                v = 1.0 if node.board.turn == chess.BLACK else -1.0
            else:
                v = 0.0

        # Backpropagation:
        # leaf gets v (from leaf's perspective).
        # Its parent gets -v (action taken by parent led to leaf, so good for leaf means bad for parent).
        for n in reversed(path):
            n.N += 1
            n.W += v
            n.Q = n.W / n.N
            v = -v

    # 3. Action selection
    total_visits = sum(c.N for c in root.children.values())
    if total_visits == 0:
        legal = list(root_board.legal_moves)
        chosen = random.choice(legal)
        return chosen, np.zeros(POLICY_SIZE, dtype=np.float32), root

    visit_probs = np.zeros(POLICY_SIZE, dtype=np.float32)
    for move, child in root.children.items():
        if move in MOVE_TO_IDX:
            visit_probs[MOVE_TO_IDX[move]] = float(child.N) / float(total_visits)

    if temperature <= 0.01:
        # Greedy selection (competitive play / testing)
        best_move = max(root.children.items(), key=lambda x: x[1].N)[0]
    else:
        # Stochastic selection with temperature (RL self-play exploration)
        moves = list(root.children.keys())
        counts = np.array([float(root.children[m].N) for m in moves], dtype=np.float64)
        if temperature != 1.0:
            counts = counts ** (1.0 / temperature)
        norm_probs = counts / (counts.sum() or 1.0)
        best_move = random.choices(moves, weights=norm_probs, k=1)[0]

    return best_move, visit_probs, root
