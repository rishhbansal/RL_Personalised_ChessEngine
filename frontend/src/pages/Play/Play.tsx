import { useEffect, useRef, useState } from "react";
import { Chess } from "chess.js";
import type { Square } from "chess.js";
import ChessBoard from "../../components/ChessBoard/ChessBoard";
import GameControls from "../../components/GameControls/GameControls";
import EvalBar from "../../components/EvalBar/EvalBar";
import EvalGraph from "../../components/EvalGraph/EvalGraph";
import MoveHistory from "../../components/MoveHistory/MoveHistory";
import MoveAnalysis from "../../components/MoveAnalysis/MoveAnalysis";
import { getEngineMove } from "../../services/chessApi";
import {
  addMove,
  createGame,
  evaluateFen,
  explainMove,
  finishGame,
  getGameSummary,
  getRecommendedStyle,
} from "../../services/gameApi";
import type { MoveRecord, TopMove } from "../../types/api";
import "./Play.css";

export default function Play() {
  const [game, setGame] = useState(new Chess());
  const [selectedSquare, setSelectedSquare] = useState<Square | null>(null);
  const [legalMoves, setLegalMoves] = useState<Square[]>([]);
  const [paused, setPaused] = useState(false);
  const [style, setStyle] = useState({
    difficulty: 50,
    aggression: 50,
    risk_tolerance: 50,
    positional_tactical: 50,
  });
  const [autoTuning, setAutoTuning] = useState(false);
  const [autoTuneNote, setAutoTuneNote] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>([]);

  const [moves, setMoves] = useState<MoveRecord[]>([]);
  const [evalHistory, setEvalHistory] = useState<{ ply: number; eval: number }[]>([
    { ply: 0, eval: 0 },
  ]);
  const [analysis, setAnalysis] = useState<{
    loading: boolean;
    explanation: string | null;
    moveSan?: string;
    by?: "player" | "engine";
  }>({ loading: false, explanation: null });

  // Game End & Post-Game Coaching Summary
  const [gameOverInfo, setGameOverInfo] = useState<{
    isOver: boolean;
    result: string;
    description: string;
  }>({ isOver: false, result: "", description: "" });
  const [gameSummary, setGameSummary] = useState<string | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const gameIdRef = useRef<string | null>(null);
  const lastEvalRef = useRef(0);
  const moveCountRef = useRef(0);

  useEffect(() => {
    startNewGame();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function startNewGame() {
    setGame(new Chess());
    setHistory([]);
    setSelectedSquare(null);
    setLegalMoves([]);
    setMoves([]);
    setEvalHistory([{ ply: 0, eval: 0 }]);
    setAnalysis({ loading: false, explanation: null });
    setGameOverInfo({ isOver: false, result: "", description: "" });
    setGameSummary(null);
    setSummaryLoading(false);
    lastEvalRef.current = 0;
    moveCountRef.current = 0;

    try {
      const g = await createGame(style);
      gameIdRef.current = g.id;
    } catch (err) {
      console.error("Could not start game session:", err);
      gameIdRef.current = null;
    }
  }

  async function recordMove(record: Omit<MoveRecord, "ply">) {
    moveCountRef.current += 1;
    const full: MoveRecord = { ...record, ply: moveCountRef.current };
    setMoves((prev) => [...prev, full]);
    setEvalHistory((prev) => [...prev, { ply: full.ply, eval: record.eval_after }]);
    lastEvalRef.current = record.eval_after;

    try {
      if (!gameIdRef.current) {
        const g = await createGame(style);
        gameIdRef.current = g.id;
      }
      await addMove(gameIdRef.current, full);
    } catch (err) {
      console.error("Could not save move:", err);
    }
  }

  async function analyzeMove(
    fenBefore: string,
    moveSan: string,
    evalBefore: number,
    evalAfter: number,
    isCapture: boolean,
    isCheck: boolean,
    topAlternatives: TopMove[],
    by: "player" | "engine"
  ) {
    setAnalysis({ loading: true, explanation: null, moveSan, by });
    try {
      const explanation = await explainMove({
        fen_before: fenBefore,
        move_san: moveSan,
        eval_before: evalBefore,
        eval_after: evalAfter,
        is_capture: isCapture,
        is_check: isCheck,
        top_alternatives: topAlternatives,
      });
      setAnalysis({ loading: false, explanation, moveSan, by });
      return explanation;
    } catch (err) {
      console.error("Explain error:", err);
      setAnalysis({ loading: false, explanation: null, moveSan, by });
      return null;
    }
  }

  async function handleGameEnd(finalBoard: Chess, moveHistorySnapshot: MoveRecord[]) {
    let result = "1/2-1/2";
    let desc = "Game ended in a draw";
    if (finalBoard.isCheckmate()) {
      if (finalBoard.turn() === "b") {
        result = "1-0";
        desc = "Checkmate! You win against the AI!";
      } else {
        result = "0-1";
        desc = "Checkmate! The AI wins.";
      }
    } else if (finalBoard.isStalemate()) {
      desc = "Draw by Stalemate!";
    } else if (finalBoard.isThreefoldRepetition()) {
      desc = "Draw by Threefold Repetition!";
    } else if (finalBoard.isInsufficientMaterial()) {
      desc = "Draw by Insufficient Material!";
    }

    setGameOverInfo({ isOver: true, result, description: desc });

    if (gameIdRef.current) {
      try {
        await finishGame(gameIdRef.current, result);
      } catch (err) {
        console.error("Could not finalize game:", err);
      }
    }

    // Identify player errors/blunders (where eval shifted significantly against White)
    const playerErrors: { move_number: number; move_san: string; eval_drop: number; best_alt?: string }[] = [];
    for (let i = 0; i < moveHistorySnapshot.length; i++) {
      const m = moveHistorySnapshot[i];
      if (m.by === "player") {
        const evalDrop = m.eval_before - m.eval_after;
        if (evalDrop > 0.22) {
          playerErrors.push({
            move_number: Math.ceil(m.ply / 2),
            move_san: m.move_san,
            eval_drop: Number(evalDrop.toFixed(2)),
            best_alt: m.top_alternatives?.[0]?.san,
          });
        }
      }
    }

    // Trigger post-game coaching summary via OpenRouter / Groq LLM
    setSummaryLoading(true);
    try {
      const summary = await getGameSummary({
        result,
        player_color: "White",
        total_moves: Math.ceil(moveHistorySnapshot.length / 2),
        player_errors: playerErrors,
      });
      setGameSummary(summary);
    } catch (err) {
      console.error("Game summary error:", err);
      setGameSummary("Match completed! Review move history to examine tactical fluctuations.");
    } finally {
      setSummaryLoading(false);
    }
  }

  async function handleSquareClick(square: string) {
    if (paused || gameOverInfo.isOver) return;

    const board = new Chess(game.fen());
    const clickedPiece = board.get(square as Square);

    if (clickedPiece && clickedPiece.color === board.turn()) {
      const legal = board.moves({ square: square as Square, verbose: true });
      setSelectedSquare(square as Square);
      setLegalMoves(legal.map((m) => m.to));
      return;
    }

    if (!selectedSquare) return;

    const fenBeforePlayerMove = board.fen();
    const move = board.move({ from: selectedSquare, to: square as Square, promotion: "q" });

    setSelectedSquare(null);
    setLegalMoves([]);
    if (!move) return;

    setHistory((prev) => [...prev, game.fen()]);
    setGame(new Chess(board.fen()));

    const evalBefore = lastEvalRef.current;
    let evalAfterPlayer = evalBefore;
    try {
      evalAfterPlayer = await evaluateFen(board.fen());
    } catch (err) {
      console.error("Eval error:", err);
    }

    const isCapture = move.flags.includes("c") || move.flags.includes("e");
    const explanation = await analyzeMove(
      fenBeforePlayerMove,
      move.san,
      evalBefore,
      evalAfterPlayer,
      isCapture,
      board.inCheck(),
      [],
      "player"
    );

    const playerMoveRecord: MoveRecord = {
      ply: moveCountRef.current + 1,
      move_san: move.san,
      move_uci: move.from + move.to + (move.promotion ?? ""),
      fen_before: fenBeforePlayerMove,
      fen_after: board.fen(),
      eval_before: evalBefore,
      eval_after: evalAfterPlayer,
      is_capture: isCapture,
      is_check: board.inCheck(),
      by: "player",
      explanation,
      top_alternatives: [],
    };

    const updatedMovesSnapshot = [...moves, playerMoveRecord];
    await recordMove(playerMoveRecord);

    if (board.isGameOver()) {
      await handleGameEnd(board, updatedMovesSnapshot);
      return;
    }

    try {
      const engineFenBefore = board.fen();
      const response = await getEngineMove({ fen: engineFenBefore, style });
      const engineBoard = new Chess(engineFenBefore);
      engineBoard.move(response.move_uci);
      setGame(new Chess(engineBoard.fen()));

      const engineExplanation = await analyzeMove(
        engineFenBefore,
        response.move_san,
        response.eval_before,
        response.eval_after,
        false,
        response.is_check,
        response.top_moves,
        "engine"
      );

      const engineMoveRecord: MoveRecord = {
        ply: moveCountRef.current + 1,
        move_san: response.move_san,
        move_uci: response.move_uci,
        fen_before: engineFenBefore,
        fen_after: response.fen_after,
        eval_before: response.eval_before,
        eval_after: response.eval_after,
        is_capture: false,
        is_check: response.is_check,
        by: "engine",
        explanation: engineExplanation,
        top_alternatives: response.top_moves,
        style,
      };

      const finalMovesSnapshot = [...updatedMovesSnapshot, engineMoveRecord];
      await recordMove(engineMoveRecord);

      if (response.is_game_over || engineBoard.isGameOver()) {
        await handleGameEnd(engineBoard, finalMovesSnapshot);
      }
    } catch (err) {
      console.error("Engine error:", err);
    }
  }

  function undoMove() {
    if (history.length === 0 || gameOverInfo.isOver) return;
    const previousFen = history[history.length - 1];
    setHistory((prev) => prev.slice(0, -1));
    setGame(new Chess(previousFen));
    setSelectedSquare(null);
    setLegalMoves([]);
  }

  function togglePause() {
    if (gameOverInfo.isOver) return;
    setPaused((prev) => !prev);
  }

  async function handleAutoTune() {
    setAutoTuning(true);
    setAutoTuneNote(null);
    try {
      const rec = await getRecommendedStyle();
      setStyle(rec.style);
      setAutoTuneNote(rec.rationale);
    } catch (err) {
      console.error("Auto-tune error:", err);
      setAutoTuneNote("Couldn't fetch your match history right now — try again in a moment.");
    } finally {
      setAutoTuning(false);
    }
  }

  const squareStyles: Record<string, React.CSSProperties> = {};
  if (selectedSquare) {
    squareStyles[selectedSquare] = {
      background: "radial-gradient(circle, rgba(66,133,244,0.65) 0%, rgba(66,133,244,0.2) 70%)",
      boxShadow: "inset 0 0 0 4px #4285f4",
    };
  }
  legalMoves.forEach((sq) => {
    squareStyles[sq] = {
      background: "radial-gradient(circle, rgba(0,0,0,0.38) 24%, transparent 26%)",
    };
  });

  const currentEval = evalHistory[evalHistory.length - 1]?.eval ?? 0;
  const turnLabel = gameOverInfo.isOver
    ? gameOverInfo.description
    : `${game.turn() === "w" ? "White (You)" : "Black (Engine)"} to move`;

  return (
    <div className="play-shell">
      {/* Prominent Game-Over Status Banner */}
      {gameOverInfo.isOver && (
        <div
          className={`game-over-banner ${
            gameOverInfo.result === "1-0" ? "win" : gameOverInfo.result === "0-1" ? "loss" : "draw"
          }`}
        >
          <div className="game-over-title">
            <span>🏁 GAME OVER — {gameOverInfo.description}</span>
          </div>
          <div className="game-over-sub">
            Result: <strong>{gameOverInfo.result}</strong> · Check the Coach Analysis panel on the right for error review!
          </div>
        </div>
      )}

      <div className="play-topbar">
        <div className="play-turn">{turnLabel}</div>
        <button className="play-newgame-btn" onClick={startNewGame}>
          New Game
        </button>
      </div>

      <div className="play-body">
        <div className="play-col play-col-left">
          <GameControls
            paused={paused}
            style={style}
            onPause={togglePause}
            onUndo={undoMove}
            onReset={startNewGame}
            onStyleChange={setStyle}
            onAutoTune={handleAutoTune}
            autoTuning={autoTuning}
            autoTuneNote={autoTuneNote}
          />
        </div>

        <div className="play-col play-col-center">
          <EvalBar evalScore={currentEval} />
          <div className="board-wrap">
            <ChessBoard
              position={game.fen()}
              boardWidth={680}
              onSquareClick={handleSquareClick}
              customSquareStyles={squareStyles}
            />
            {paused && <div className="pause-overlay">⏸ Game Paused</div>}
            {gameOverInfo.isOver && (
              <div className="board-gameover-overlay">
                <div
                  className={`board-gameover-card ${
                    gameOverInfo.result === "1-0"
                      ? "win"
                      : gameOverInfo.result === "0-1"
                      ? "loss"
                      : "draw"
                  }`}
                >
                  <div className="board-gameover-badge">
                    {gameOverInfo.result === "1-0"
                      ? "🏆 MATCH WON"
                      : gameOverInfo.result === "0-1"
                      ? "🤖 MATCH LOST"
                      : "🤝 DRAW"}
                  </div>
                  <h2 className="board-gameover-winner">
                    {gameOverInfo.result === "1-0"
                      ? "WHITE WINS!"
                      : gameOverInfo.result === "0-1"
                      ? "BLACK WINS!"
                      : "DRAW!"}
                  </h2>
                  <p className="board-gameover-sub">{gameOverInfo.description}</p>
                  <div className="board-gameover-score">
                    {gameOverInfo.result === "1-0"
                      ? "1 — 0"
                      : gameOverInfo.result === "0-1"
                      ? "0 — 1"
                      : "½ — ½"}
                  </div>
                  <button className="board-gameover-btn" onClick={startNewGame}>
                    Play Again
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="play-col play-col-right">
          <MoveHistory moves={moves} />
          <EvalGraph data={evalHistory} />
          <MoveAnalysis
            loading={analysis.loading}
            explanation={analysis.explanation}
            moveSan={analysis.moveSan}
            by={analysis.by}
            gameSummary={gameSummary}
            summaryLoading={summaryLoading}
          />
        </div>
      </div>
    </div>
  );
}