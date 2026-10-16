import "./MoveHistory.css";
import type { MoveRecord } from "../../types/api";

interface Props {
  moves: MoveRecord[];
}

export default function MoveHistory({ moves }: Props) {
  const rows: { num: number; white?: MoveRecord; black?: MoveRecord }[] = [];
  moves.forEach((m, i) => {
    const num = Math.floor(i / 2) + 1;
    if (i % 2 === 0) rows.push({ num, white: m });
    else rows[rows.length - 1].black = m;
  });

  return (
    <div className="move-history">
      <h3>Move History</h3>
      <div className="move-history-list">
        {rows.length === 0 && <p className="move-history-empty">No moves yet</p>}
        {rows.map((r) => (
          <div className="move-row" key={r.num}>
            <span className="move-num">{r.num}.</span>
            <span className="move-san white">{r.white?.move_san ?? ""}</span>
            <span className="move-san black">{r.black?.move_san ?? ""}</span>
          </div>
        ))}
      </div>
    </div>
  );
}