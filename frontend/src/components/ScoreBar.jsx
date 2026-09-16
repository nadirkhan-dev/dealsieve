import { COMPONENT_GROUPS } from "../constants.js";

// The score as a stack of its parts, so the reason for a number is visible in the table itself.
export default function ScoreBar({ breakdown, pending }) {
  if (pending) return <div className="scorebar scorebar-pending" aria-label="Not scored yet" />;
  return (
    <div className="scorebar" role="img" aria-label={breakdown.map((b) => `${b.label} ${Math.round(b.points)} of ${Math.round(b.max)}`).join(", ")}>
      {breakdown.map((b) => (
        <span
          key={b.key}
          className={`seg seg-${COMPONENT_GROUPS[b.key]} ${b.known ? "" : "seg-unknown"}`}
          style={{ width: `${b.points}%` }}
          title={`${b.label}: ${b.reason}`}
        />
      ))}
    </div>
  );
}
