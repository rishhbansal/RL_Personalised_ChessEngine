import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import "./EvalGraph.css";

interface Props {
  data: { ply: number; eval: number }[];
}

function describe(evalScore: number): { text: string; color: string } {
  if (Math.abs(evalScore) < 0.05) return { text: "Equal position", color: "#94a3b8" };
  const side = evalScore > 0 ? "White" : "Black";
  const mag = Math.abs(evalScore);
  const color = evalScore > 0 ? "#34d399" : "#f87171";
  if (mag > 0.6) return { text: `${side} is winning`, color };
  if (mag > 0.25) return { text: `${side} is better`, color };
  return { text: `${side} slightly ahead`, color };
}

export default function EvalGraph({ data }: Props) {
  const current = data.length ? data[data.length - 1].eval : 0;
  const status = describe(current);
  const lineColor = current >= 0 ? "#34d399" : "#f87171";

  return (
    <div className="eval-graph">
      <div className="eval-graph-header">
        <h3>Evaluation</h3>
        <span className="eval-graph-status" style={{ color: status.color }}>
          {status.text}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={150}>
        {/* 1. Changed left margin from -24 to 0 */}
<AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
  <defs>
    <linearGradient id="evalFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={lineColor} stopOpacity={0.5} />
      <stop offset="100%" stopColor={lineColor} stopOpacity={0.02} />
    </linearGradient>
  </defs>
  <XAxis dataKey="ply" stroke="#64748b" fontSize={11} tickLine={false} />
  
  {/* 2. Changed stroke color to #cbd5e1 for distinct readability */}
  <YAxis
    domain={[-1, 1]}
    stroke="#cbd5e1" 
    fontSize={11}
    tickLine={false}
    width={44}
    ticks={[-1, 0, 1]}
    tickFormatter={(v) => (v > 0 ? "White" : v < 0 ? "Black" : "Equal")}
  />
  
  <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
  <Tooltip
    contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
    labelStyle={{ color: "#94a3b8" }}
    formatter={(value) => [describe(Number(value)).text, "Position"]}
    labelFormatter={(label) => `Move ${label}`}
  />
  <Area type="monotone" dataKey="eval" stroke={lineColor} strokeWidth={2} fill="url(#evalFill)" />
</AreaChart>

      </ResponsiveContainer>
    </div>
  );
}