const STEPS = ["Import leads", "Enrich", "Review", "Export"];

export default function StepBar({ current }) {
  return (
    <ol className="steps" aria-label="Progress">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const state = n < current ? "done" : n === current ? "current" : "todo";
        return (
          <li key={label} className={`step step-${state}`} aria-current={state === "current" ? "step" : undefined}>
            <span className="step-num">{state === "done" ? "✓" : n}</span>
            <span className="step-label">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
