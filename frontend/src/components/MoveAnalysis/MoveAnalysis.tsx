import "./MoveAnalysis.css";

interface Props {
  loading: boolean;
  explanation: string | null;
  moveSan?: string;
  by?: "player" | "engine";
  gameSummary?: string | null;
  summaryLoading?: boolean;
}

export default function MoveAnalysis({
  loading,
  explanation,
  moveSan,
  by,
  gameSummary,
  summaryLoading,
}: Props) {
  return (
    <div className="move-analysis">
      <h3>
        Coach Analysis
        {moveSan && (
          <span className={`badge ${by}`}>
            {by === "engine" ? "Engine" : "You"}: {moveSan}
          </span>
        )}
      </h3>

      {/* Per-move live coach feedback */}
      {loading && <p className="move-analysis-loading">Coach evaluating move…</p>}
      {!loading && explanation && <p className="move-analysis-text">{explanation}</p>}
      {!loading && !explanation && !gameSummary && (
        <p className="move-analysis-empty">Make a move to receive real-time coach feedback.</p>
      )}

      {/* Post-game Coaching Summary & Error Review */}
      {summaryLoading && (
        <div className="game-summary-box">
          <h4 className="summary-title">Generating Post-Game Error Review…</h4>
          <p className="move-analysis-loading">Analyzing mistakes and missed opportunities with coach LLM…</p>
        </div>
      )}

      {!summaryLoading && gameSummary && (
        <div className="game-summary-box">
          <h4 className="summary-title">Post-Game Coach Error Summary</h4>
          <div className="summary-content">
            {gameSummary.split("\n").map((line, idx) => (
              <p key={idx} className="summary-paragraph">
                {line}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}