import { Chessboard } from "react-chessboard";

interface ChessBoardProps {
  position: string;
  boardWidth?: number;
  onPieceDrop?: (
    sourceSquare: string,
    targetSquare: string,
    piece: string
  ) => boolean;
  onSquareClick?: (
    square: string,
    piece?: string
  ) => void;
  customSquareStyles?: Record<string, React.CSSProperties>;
}

export default function ChessBoard({
  position,
  boardWidth = 600,
  onPieceDrop,
  onSquareClick,
  customSquareStyles,
}: ChessBoardProps) {
  return (
    <Chessboard
      id="RL-Chessboard"
      position={position}
      arePiecesDraggable={false}
      onPieceDrop={onPieceDrop}
      onSquareClick={onSquareClick}
      customSquareStyles={customSquareStyles}
      boardWidth={boardWidth}
    />
  );
}