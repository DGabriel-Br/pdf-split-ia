const STEPS = [
  { id: "EXTRACT",   statuses: ["QUEUED", "EXTRACTING"], label: "Extração" },
  { id: "CLASSIFY",  statuses: ["CLASSIFYING"],           label: "Classificação" },
  { id: "BUILD",     statuses: ["BUILDING"],              label: "Geração" },
];

function stepState(step, currentStatus) {
  const idx = STEPS.findIndex(s => s.id === step.id);
  const cur = STEPS.findIndex(s => s.statuses.includes(currentStatus));
  if (cur === -1) return "done";
  if (idx < cur) return "done";
  if (idx === cur) return "active";
  return "idle";
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2,6 5,9 10,3"/>
    </svg>
  );
}

export function StatusPoller({ job }) {
  return (
    <div>
      <div className="pipeline">
        {STEPS.map((step) => {
          const state = stepState(step, job.status);
          return (
            <div key={step.id} className={`pipeline-step ${state}`}>
              <div className="step-dot">
                {state === "done" ? <CheckIcon /> : step.id.slice(0, 2)}
              </div>
              <span className="step-label">{step.label}</span>
            </div>
          );
        })}
      </div>

      <div className="progress-section">
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${job.progress}%` }} />
        </div>
        <div className="progress-meta">
          <span className="status-message">{job.message}</span>
          <span className="progress-pct">{job.progress}%</span>
        </div>
      </div>
    </div>
  );
}
