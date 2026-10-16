import { useEffect, useState } from "react";
import { listGames, getGame } from "../../services/gameApi";
import type { GameDetail, GameSummary } from "../../types/api";
import EvalGraph from "../../components/EvalGraph/EvalGraph";
import MoveHistory from "../../components/MoveHistory/MoveHistory";
import "./Analysis.css";

const Analysis = () => {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [selected, setSelected] = useState<GameDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listGames()
      .then((loaded) => {
        setGames(loaded);
        if (loaded.length > 0) {
          openGame(loaded[0].id);
        }
      })
      .catch((err) => console.error("Failed to load games:", err))
      .finally(() => setLoading(false));
  }, []);

  async function openGame(id: string) {
    try {
      setSelected(await getGame(id));
    } catch (err) {
      console.error("Failed to load game:", err);
    }
  }

  function formatResult(res?: string | null) {
    if (res === "1-0") return "🏆 White Won (1-0)";
    if (res === "0-1") return "🤖 Black Won (0-1)";
    if (res === "1/2-1/2") return "🤝 Draw (½-½)";
    return "⏳ Finished / Saved";
  }

  return (
    <div className="analysis-page">
      <h1>Match History & Analysis</h1>

      <div className="analysis-layout">
        <div className="analysis-game-list">
          {loading && <p className="dim">Loading games…</p>}
          {!loading && games.length === 0 && (
            <p className="dim">No games played yet. Play a few moves on the Play page first!</p>
          )}
          {games.map((g, idx) => (
            <button
              key={g.id}
              className={`analysis-game-item ${selected?.id === g.id ? "active" : ""}`}
              onClick={() => openGame(g.id)}
            >
              <span className="date">
                Match #{games.length - idx} · {new Date(g.started_at).toLocaleString()}
              </span>
              <span className="dim">
                {formatResult(g.result)} · {g.num_moves} plies
              </span>
            </button>
          ))}
        </div>

        <div className="analysis-detail">
          {!selected && (
            <p className="dim">Select a game on the left to review its evaluation graph, moves, and coach notes.</p>
          )}
          {selected && (
            <>
              <EvalGraph
                data={[
                  { ply: 0, eval: 0 },
                  ...selected.moves.map((m, i) => ({ ply: i + 1, eval: m.eval_after })),
                ]}
              />
              <MoveHistory moves={selected.moves} />
              <div className="analysis-explanations">
                <h3>Coach Notes</h3>
                {selected.moves.filter((m) => m.explanation).length === 0 && (
                  <p className="dim">No move-level commentary recorded for this match.</p>
                )}
                {selected.moves
                  .filter((m) => m.explanation)
                  .map((m) => (
                    <div className="analysis-note" key={m.ply}>
                      <span className={`badge ${m.by}`}>
                        {Math.ceil(m.ply / 2)}
                        {m.by === "player" ? "." : "..."} {m.move_san}
                      </span>
                      <p>{m.explanation}</p>
                    </div>
                  ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Analysis;