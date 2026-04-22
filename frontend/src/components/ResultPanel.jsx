import { api } from "../api/client";
import { PageLogTable } from "./PageLogTable";

const LEGACY_KEYS = new Set(["INVOICE", "PACKING_LIST"]);
const NEW_KEY = /^(INVOICE|PACKING_LIST)_\d+$/;

function hasRelevantFiles(outputFiles) {
  return Object.keys(outputFiles ?? {}).some(
    k => LEGACY_KEYS.has(k) || NEW_KEY.test(k)
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20,6 9,17 4,12"/>
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7,10 12,15 17,10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  );
}

export function ResultPanel({ job, jobId, onReset }) {
  const relevant = hasRelevantFiles(job.output_files);

  return (
    <div>
      <div className="result-header">
        <div className="result-checkmark">
          <CheckIcon />
        </div>
        <div>
          <div className="result-title">Processamento concluído</div>
          <div className="result-sub">{job.pages.length} páginas classificadas</div>
        </div>
      </div>

      {relevant ? (
        <div className="download-block">
          <a
            href={api.getDownloadAllUrl(jobId)}
            download
            className="download-btn"
          >
            <DownloadIcon />
            Baixar faturas e packing lists
          </a>
        </div>
      ) : (
        <p style={{ color: "var(--text-3)", fontSize: "0.88rem", marginBottom: 24 }}>
          Nenhuma fatura ou packing list identificada. Verifique o log abaixo.
        </p>
      )}

      <hr className="divider" />

      <PageLogTable pages={job.pages} />

      <div className="btn-row" style={{ marginTop: 28 }}>
        <button className="btn secondary" onClick={onReset}>
          Processar outro PDF
        </button>
      </div>
    </div>
  );
}
