import { api } from "../api/client";
import { PageLogTable } from "./PageLogTable";

const LEGACY_KEYS = new Set(["INVOICE", "PACKING_LIST"]);
const NEW_KEY = /^(INVOICE|PACKING_LIST)_\d+$/;

function hasRelevantFiles(outputFiles) {
  return Object.keys(outputFiles ?? {}).some(
    (k) => LEGACY_KEYS.has(k) || NEW_KEY.test(k)
  );
}

export function ResultPanel({ job, jobId, onReset }) {
  const relevant = hasRelevantFiles(job.output_files);

  return (
    <div>
      <p style={{ marginBottom: 20, color: "var(--text-body)", fontWeight: 600 }}>
        Processamento concluído: {job.pages.length} página(s) classificada(s)
      </p>

      {relevant ? (
        <div className="downloads" style={{ marginBottom: 24 }}>
          <a
            href={api.getDownloadAllUrl(jobId)}
            download
            className="download-btn invoice"
            style={{ fontSize: "1rem", padding: "12px 28px" }}
          >
            Baixar faturas e packing lists
          </a>
        </div>
      ) : (
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: 24 }}>
          Nenhuma fatura ou packing list identificada. Verifique o log abaixo.
        </p>
      )}

      <PageLogTable pages={job.pages} />

      <div style={{ marginTop: 24, textAlign: "center" }}>
        <button className="btn secondary" onClick={onReset}>
          Processar outro PDF
        </button>
      </div>
    </div>
  );
}
