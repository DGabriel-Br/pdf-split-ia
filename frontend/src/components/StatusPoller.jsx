const STEPS = [
  { id: "EXTRACT",  number: 1, statuses: ["QUEUED", "EXTRACTING"], label: "Extração" },
  { id: "CLASSIFY", number: 2, statuses: ["CLASSIFYING"],           label: "Classificação" },
  { id: "BUILD",    number: 3, statuses: ["BUILDING"],              label: "Geração" },
];

const STATUS_TITLES = {
  QUEUED:      "Preparando processamento",
  EXTRACTING:  "Extraindo páginas do PDF",
  CLASSIFYING: "Identificando documentos com IA",
  BUILDING:    "Gerando arquivos separados",
};

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
    <svg viewBox="0 0 12 12" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2,6 5,9 10,3"/>
    </svg>
  );
}

export function StatusPoller({ job }) {
  const title = STATUS_TITLES[job.status] ?? "Processando";

  return (
    <div className="status-poller">
      <div className="status-poller-header">
        <h2 className="status-poller-title">{title}</h2>
      </div>

      <div className="pipeline">
        {STEPS.map((step) => {
          const state = stepState(step, job.status);
          return (
            <div key={step.id} className={`pipeline-step ${state}`}>
              <div className="step-dot">
                {state === "done" ? <CheckIcon /> : step.number}
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
