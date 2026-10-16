export interface StyleParams {
  difficulty: number;
  aggression: number;
  risk_tolerance: number;
  positional_tactical: number;
}

export interface EngineMoveRequest {
  fen: string;
  style: StyleParams;
}

export interface TopMove {
  san: string;
  uci: string;
  visits: number;
  value: number;
}

export interface EngineMoveResponse {
  move_uci: string;
  move_san: string;
  fen_after: string;
  eval_before: number;
  eval_after: number;
  is_check: boolean;
  is_checkmate: boolean;
  is_game_over: boolean;
  top_moves: TopMove[];
}
export interface AuthUser {
  id: string;
  email: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}
export interface MoveRecord {
  ply: number;
  move_san: string;
  move_uci: string;
  fen_before: string;
  fen_after: string;
  eval_before: number;
  eval_after: number;
  is_capture: boolean;
  is_check: boolean;
  by: "player" | "engine";
  explanation?: string | null;
  top_alternatives: TopMove[];
  style?: StyleParams | null;
}

export interface GameSummary {
  id: string;
  started_at: string;
  ended_at?: string | null;
  result?: string | null;
  num_moves: number;
  final_eval?: number | null;
  style: StyleParams;
}

export interface GameDetail extends GameSummary {
  moves: MoveRecord[];
}

export interface StatsResponse {
  total_games: number;
  wins: number;
  losses: number;
  draws: number;
  avg_move_swing: number;
  timeline: { date: string; eval: number }[];
}

export interface ExplainRequest {
  fen_before: string;
  move_san: string;
  eval_before: number;
  eval_after: number;
  is_capture: boolean;
  is_check: boolean;
  top_alternatives: TopMove[];
}

export interface ExplainResponse {
  explanation: string;
}

export interface EvaluateResponse {
  eval: number;
}
export interface StyleRecommendation {
  style: StyleParams;
  games_analyzed: number;
  rationale: string;
}