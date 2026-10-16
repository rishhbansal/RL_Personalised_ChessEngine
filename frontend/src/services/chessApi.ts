import api from "./api";
import type {
  EngineMoveRequest,
  EngineMoveResponse,
} from "../types/api";

export async function getEngineMove(
  request: EngineMoveRequest
): Promise<EngineMoveResponse> {
  const response = await api.post<EngineMoveResponse>(
    "/engine-move",
    request
  );

  return response.data;
}