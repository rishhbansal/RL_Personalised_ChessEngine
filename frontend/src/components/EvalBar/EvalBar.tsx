import "./EvalBar.css";

interface Props {
  evalScore: number; // -1..1, positive = White ahead
}

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v));
}

function describe(evalScore: number): string {
  if (Math.abs(evalScore) < 0.05) return "Equal";
  const side = evalScore > 0 ? "White" : "Black";
  const mag = Math.abs(evalScore);
  if (mag > 0.6) return `${side} winning`;
  if (mag > 0.25) return `${side} better`;
  return `${side} ahead`;
}

export default function EvalBar({ evalScore }: Props) {
  const clamped = clamp(evalScore, -1, 1);
  const whitePercent = ((clamped + 1) / 2) * 100;

  return (
    <div className="eval-bar">
      <div className="eval-bar-track">
        <div className="eval-bar-white" style={{ height: `${whitePercent}%` }} />
      </div>
      <span className="eval-bar-label">{describe(clamped)}</span>
    </div>
  );
}