import api from "./api";
import type {
  EvaluateResponse,
  ExplainRequest,
  ExplainResponse,
  GameDetail,
  GameSummary,
  MoveRecord,
  StatsResponse,
  StyleParams,
  StyleRecommendation,
} from "../types/api";


export async function evaluateFen(fen: string): Promise<number> {
  const res = await api.post<EvaluateResponse>("/evaluate", { fen });
  return res.data.eval;
}

export async function explainMove(req: ExplainRequest): Promise<string> {
  const res = await api.post<ExplainResponse>("/explain", req);
  return res.data.explanation;
}

export async function getGameSummary(req: {
  result: string;
  player_color?: string;
  total_moves?: number;
  player_errors?: { move_number: number; move_san: string; eval_drop: number; best_alt?: string }[];
}): Promise<string> {
  const res = await api.post<{ summary: string }>("/game-summary", req);
  return res.data.summary;
}

export async function createGame(style: StyleParams): Promise<GameSummary> {
  const res = await api.post<GameSummary>("/games", { style });
  return res.data;
}

export async function addMove(gameId: string, move: MoveRecord): Promise<void> {
  await api.post(`/games/${gameId}/moves`, move);
}

export async function finishGame(gameId: string, result: string): Promise<void> {
  await api.post(`/games/${gameId}/finish`, { result });
}

export async function listGames(): Promise<GameSummary[]> {
  const res = await api.get<GameSummary[]>("/games");
  return res.data;
}

export async function getGame(gameId: string): Promise<GameDetail> {
  const res = await api.get<GameDetail>(`/games/${gameId}`);
  return res.data;
}

export async function getStats(): Promise<StatsResponse> {
  const res = await api.get<StatsResponse>("/stats");
  return res.data;
}
export async function getRecommendedStyle(): Promise<StyleRecommendation> {
  const res = await api.get<StyleRecommendation>("/games/recommend-style");
  return res.data;
}