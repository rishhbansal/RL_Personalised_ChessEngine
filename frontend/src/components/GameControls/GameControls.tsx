import { Play, Pause, RotateCcw, Undo2, Wand2 } from "lucide-react";
import "./GameControls.css";

export interface EngineStyle {
  difficulty: number;
  aggression: number;
  risk_tolerance: number;
  positional_tactical: number;
}

interface Props {
  paused: boolean;
  style: EngineStyle;
  onPause(): void;
  onUndo(): void;
  onReset(): void;
  onStyleChange(style: EngineStyle): void;
  onAutoTune?(): void;
  autoTuning?: boolean;
  autoTuneNote?: string | null;
}

function eloRange(difficulty: number): number {
  return Math.round(800 + (difficulty / 100) * 1400);
}

function skillLabel(difficulty: number) {
  const elo = eloRange(difficulty);
  if (difficulty < 20) return `Novice (~${elo} Elo)`;
  if (difficulty < 40) return `Beginner (~${elo} Elo)`;
  if (difficulty < 60) return `Intermediate (~${elo} Elo)`;
  if (difficulty < 80) return `Advanced (~${elo} Elo)`;
  return `Master (~${elo} Elo)`;
}

function label(value: number, low: string, mid: string, high: string) {
  if (value < 34) return low;
  if (value > 66) return high;
  return mid;
}

export default function GameControls({
  paused,
  style,
  onPause,
  onUndo,
  onReset,
  onStyleChange,
  onAutoTune,
  autoTuning,
  autoTuneNote,
}: Props) {
  function update(key: keyof EngineStyle, value: number) {
    onStyleChange({ ...style, [key]: value });
  }

  const aggressionLabel = label(style.aggression, "Defensive", "Balanced", "Aggressive");
  const riskLabel = label(style.risk_tolerance, "Cautious", "Moderate", "Bold");
  const styleLabel = label(style.positional_tactical, "Positional", "Mixed", "Tactical");

  return (
    <div className="engine-panel">
      <div className="engine-panel-header">
        <h2>Engine Personality</h2>
        <p>Tune how your opponent plays</p>
      </div>

      <div className="engine-controls-row">
        <button className="icon-btn" onClick={onPause} title={paused ? "Resume" : "Pause"}>
          {paused ? <Play size={18} /> : <Pause size={18} />}
        </button>
        <button className="icon-btn" onClick={onUndo} title="Undo">
          <Undo2 size={18} />
        </button>
        <button className="icon-btn" onClick={onReset} title="New game">
          <RotateCcw size={18} />
        </button>
      </div>

      {onAutoTune && (
        <button className="auto-tune-btn" onClick={onAutoTune} disabled={autoTuning}>
          <Wand2 size={15} />
          {autoTuning ? "Analyzing last 10 games…" : "Auto-Tune from Last 10 Games"}
        </button>
      )}
      {autoTuneNote && <p className="auto-tune-note">{autoTuneNote}</p>}

      <Slider
        label="Difficulty"
        value={style.difficulty}
        valueLabel={skillLabel(style.difficulty)}
        minLabel="Beginner"
        maxLabel="Grandmaster"
        onChange={(v) => update("difficulty", v)}
      />

      <Slider
        label="Aggression"
        value={style.aggression}
        valueLabel={aggressionLabel}
        minLabel="Defensive"
        maxLabel="Aggressive"
        onChange={(v) => update("aggression", v)}
      />

      <Slider
        label="Risk Tolerance"
        value={style.risk_tolerance}
        valueLabel={riskLabel}
        minLabel="Cautious"
        maxLabel="Bold"
        onChange={(v) => update("risk_tolerance", v)}
      />

      <Slider
        label="Positional ↔ Tactical"
        value={style.positional_tactical}
        valueLabel={styleLabel}
        minLabel="Positional"
        maxLabel="Tactical"
        onChange={(v) => update("positional_tactical", v)}
      />

      <div className="engine-summary">
        Expect a {riskLabel.toLowerCase()}, {aggressionLabel.toLowerCase()} opponent playing a{" "}
        {styleLabel.toLowerCase()} style, around level {Math.round(style.difficulty)}/100 (
        {skillLabel(style.difficulty).toLowerCase()}).
      </div>
    </div>
  );
}

interface SliderProps {
  label: string;
  value: number;
  valueLabel: string;
  minLabel: string;
  maxLabel: string;
  onChange(v: number): void;
}

function Slider({ label: name, value, valueLabel, minLabel, maxLabel, onChange }: SliderProps) {
  return (
    <div className="engine-slider">
      <div className="engine-slider-top">
        <span className="engine-slider-label">{name}</span>
        <strong className="engine-slider-value">{valueLabel}</strong>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="engine-slider-bottom">
        <span>{minLabel}</span>
        <span>{maxLabel}</span>
      </div>
    </div>
  );
}