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

const STATUS_DETAILS = {
  QUEUED:      "O arquivo está na fila de processamento.",
  EXTRACTING:  "Lendo texto e estrutura de cada página.",
  CLASSIFYING: "A IA está analisando o conteúdo de cada página.",
  BUILDING:    "Separando e compactando os arquivos de saída.",
};

const DOC_LINE_WIDTHS = [88, 72, 92, 55, 80, 65, 78, 45];

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
    <svg viewBox="0 0 12 12" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2,6 5,9 10,3"/>
    </svg>
  );
}

function ScannerVisual({ progress }) {
  const r    = 68;
  const circ = 2 * Math.PI * r;
  return (
    <div className="scanner-visual" aria-hidden="true">
      <div className="scanner-wrap">
        <svg className="scanner-ring" viewBox="0 0 160 160" fill="none">
          <circle cx="80" cy="80" r={r} stroke="var(--border)" strokeWidth="2" />
          <circle
            cx="80" cy="80" r={r}
            stroke="var(--accent-mid)"
            strokeWidth="2.5"
            strokeDasharray={`${(progress / 100) * circ} ${circ}`}
            strokeLinecap="round"
            style={{
              transform: 'rotate(-90deg)',
              transformOrigin: '80px 80px',
              transition: 'stroke-dasharray 0.6s cubic-bezier(0.4,0,0.2,1)',
            }}
          />
        </svg>

        <div className="scanner-doc">
          <div className="scanner-doc-header" />
          <div className="scanner-doc-body">
            {DOC_LINE_WIDTHS.map((w, i) => (
              <div
                key={i}
                className="scanner-line"
                style={{ width: `${w}%`, animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
          <div className="scanner-beam" />
        </div>
      </div>
    </div>
  );
}

export function StatusPoller({ job }) {
  const title  = STATUS_TITLES[job.status]  ?? "Processando";
  const detail = STATUS_DETAILS[job.status] ?? "";

  return (
    <div className="status-poller">
      <div className="status-poller-inner">

        <div className="status-poller-left">
          <div className="status-poller-header">
            <div className="status-live-badge">
              <span className="status-live-dot" />
              Em processamento
            </div>
            <h2 className="status-poller-title">{title}</h2>
            <p className="status-poller-detail">{detail}</p>
          </div>

          <div className="pipeline">
            {STEPS.map((step, i) => {
              const state  = stepState(step, job.status);
              const isLast = i === STEPS.length - 1;
              return (
                <div key={step.id} className={`pipeline-step ${state}`}>
                  <div className="step-dot-col">
                    <div className="step-dot">
                      {state === "done" ? <CheckIcon /> : step.number}
                    </div>
                    {!isLast && <div className="step-connector" />}
                  </div>
                  <div className="step-info">
                    <span className="step-label">{step.label}</span>
                    {state === "active" && (
                      <span className="step-active-tag">Em andamento</span>
                    )}
                  </div>
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

        <ScannerVisual progress={job.progress} />
      </div>
    </div>
  );
}
