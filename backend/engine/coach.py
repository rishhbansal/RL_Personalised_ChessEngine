"""Natural-language explanation layer using OpenRouter (with fallback to Groq or rule-based analysis).

Supports:
1. Per-move explanation: Analyzes specific tactical choices and eval shifts.
2. Game summary: Analyzes player errors, blunders, missed opportunities, and provides key takeaways.
"""
import os
import httpx

SYSTEM_PROMPT = """You are an encouraging and insightful chess coach analyzing a player's moves.
Base your analysis on the evaluation numbers, move played, and candidate alternatives provided.
Keep explanations concise (2-4 clear sentences), plain language, and constructive.
Do not use raw engine terms like 'MCTS', 'NNUE', 'visit counts' or 'FEN' — speak in chess concepts.
"""

SUMMARY_PROMPT = """You are an expert chess coach reviewing a recently completed match.
You will be provided with:
1. The game result and who played which color.
2. Total moves played.
3. A list of key moments and errors/blunders where the evaluation swung noticeably against the human player.

Your task:
Provide a clear, engaging post-game summary with:
- Performance Verdict: A short summary of how the player performed.
- Critical Errors & Mistakes: Identify the main mistakes or blunders from the list and explain what went wrong.
- Practical Advice: 2 actionable takeaways for the player to practice and improve their game.

Keep it structured, insightful, and under 180 words.
"""


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    # 1. Check for OpenRouter API Key
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "RL Chess Agent",
            }
            payload = {
                "model": os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 400,
                "temperature": 0.5,
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    print(f"[OpenRouter API Error] {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[OpenRouter Exception] {e}")

    # 2. Check for Groq API Key
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=400,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Groq Exception] {e}")

    return ""


def explain_move(
    fen_before: str,
    move_san: str,
    eval_before: float,
    eval_after: float,
    is_capture: bool,
    is_check: bool,
    top_alternatives: list[dict],
) -> str:
    alt_lines = "\n".join(
        f"- {a['san']} (score: {a['value']}, visits: {a['visits']})"
        for a in top_alternatives
    ) or "- none recorded"

    user_prompt = f"""Position before the move (FEN): {fen_before}
Move played: {move_san}
Capture: {is_capture} | Gives check: {is_check}
Eval before (White POV, -1 to +1 scale): {eval_before:.3f}
Eval after (White POV, -1 to +1 scale): {eval_after:.3f}
Top alternative moves considered:
{alt_lines}

Explain this move concisely."""

    llm_resp = _call_llm(SYSTEM_PROMPT, user_prompt)
    if llm_resp:
        return llm_resp

    # Fallback heuristic explanation if no API key is provided
    diff = eval_after - eval_before
    if abs(diff) < 0.08:
        return f"{move_san} is a solid, balanced move keeping the position steady."
    elif diff > 0.25:
        return f"{move_san} is a strong positional/tactical improvement, shifting the balance in White's favor."
    elif diff < -0.25:
        alt_msg = f" Alternatives like {top_alternatives[0]['san']} were stronger." if top_alternatives else ""
        return f"{move_san} gives up ground and allows counterplay.{alt_msg}"
    else:
        return f"{move_san} maintains active play on the board."


def summarize_game(
    result: str,
    player_color: str,
    total_moves: int,
    player_errors: list[dict],
) -> str:
    """Produces comprehensive post-game coaching review focusing on player errors."""
    error_lines = []
    for err in player_errors:
        error_lines.append(
            f"- Move {err.get('move_number', '?')}: Played {err.get('move_san', '?')} "
            f"(Eval dropped by {err.get('eval_drop', 0):.2f}). Best alternative: {err.get('best_alt', 'N/A')}"
        )
    errors_text = "\n".join(error_lines) if error_lines else "No significant blunders recorded! Played with high accuracy."

    user_prompt = f"""Match Summary:
- Result: {result}
- Human played as: {player_color}
- Total moves: {total_moves}
- Notable Player Mistakes / Blunders:
{errors_text}

Provide the post-game error review and advice for the human player."""

    llm_resp = _call_llm(SUMMARY_PROMPT, user_prompt)
    if llm_resp:
        return llm_resp

    # Fallback coaching summary
    num_errors = len(player_errors)
    if num_errors == 0:
        return f"Impressive performance! You played a clean game ({result}) with high accuracy across {total_moves} moves and avoided major tactical blunders."
    elif num_errors <= 2:
        top_err = player_errors[0]
        return f"Solid effort! You fought well throughout {total_moves} moves. The key turning point was around move {top_err.get('move_number', '')} ({top_err.get('move_san', '')}), which cost valuable positional momentum. Keeping pieces coordinated under pressure will take your game to the next level."
    else:
        return f"Tough match! The engine capitalized on {num_errors} critical errors, particularly around moves {', '.join(str(e.get('move_number', '')) for e in player_errors[:3])}. Focus on checking undefended pieces and calculating king safety before committing to tactical trades."