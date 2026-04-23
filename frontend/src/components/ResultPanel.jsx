import { useState } from "react";
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

function SpinnerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="16" height="16" style={{ animation: "spin 0.8s linear infinite" }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="40 20"/>
    </svg>
  );
}

function initTypes(pages) {
  return Object.fromEntries(pages.map(p => [p.page_number, p.doc_type]));
}

export function ResultPanel({ job, jobId, onReset }) {
  const [pageTypes, setPageTypes]     = useState(() => initTypes(job.pages));
  const [savedTypes, setSavedTypes]   = useState(() => initTypes(job.pages));
  const [outputFiles, setOutputFiles] = useState(job.output_files);
  const [rebuilding, setRebuilding]   = useState(false);
  const [rebuildError, setRebuildError] = useState(null);

  const changedCount = Object.entries(pageTypes).filter(
    ([num, type]) => type !== savedTypes[num]
  ).length;

  const isDirty = changedCount > 0;

  function handleTypeChange(pageNumber, newType) {
    setPageTypes(prev => ({ ...prev, [pageNumber]: newType }));
    setRebuildError(null);
  }

  async function handleRebuild() {
    setRebuilding(true);
    setRebuildError(null);
    try {
      const intKeys = Object.fromEntries(
        Object.entries(pageTypes).map(([k, v]) => [parseInt(k, 10), v])
      );
      const updated = await api.reclassify(jobId, intKeys);
      const newTypes = initTypes(updated.pages);
      setPageTypes(newTypes);
      setSavedTypes(newTypes);
      setOutputFiles(updated.output_files);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const networkFail = !err?.response;
      setRebuildError(
        detail ?? (networkFail ? "Sem resposta do servidor." : "Erro ao regenerar PDFs.")
      );
    } finally {
      setRebuilding(false);
    }
  }

  const canDownload = hasRelevantFiles(outputFiles);
  const correctionLabel = changedCount === 1
    ? "1 correção pendente"
    : `${changedCount} correções pendentes`;

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

      <PageLogTable
        pages={job.pages}
        pageTypes={pageTypes}
        onTypeChange={handleTypeChange}
      />

      {rebuildError && (
        <div className="error-box" style={{ marginTop: 12 }}>{rebuildError}</div>
      )}

      <div className="actions-block">
        {isDirty && (
          <button className="btn" onClick={handleRebuild} disabled={rebuilding}>
            {rebuilding
              ? <><SpinnerIcon /> Gerando PDFs...</>
              : `Aplicar ${correctionLabel} e gerar PDFs`}
          </button>
        )}

        {canDownload ? (
          <div className="download-block">
            <a href={api.getDownloadAllUrl(jobId)} download className="download-btn">
              <DownloadIcon />
              Baixar faturas e packing lists
            </a>
          </div>
        ) : (
          !isDirty && (
            <p style={{ color: "var(--text-3)", fontSize: "0.88rem" }}>
              Nenhuma fatura ou packing list identificada. Corrija a classificação acima se necessário.
            </p>
          )
        )}
      </div>

      <hr className="divider" />

      <div className="btn-row" style={{ marginTop: 28 }}>
        <button className="btn secondary" onClick={onReset}>
          Processar outro PDF
        </button>
      </div>
    </div>
  );
}
