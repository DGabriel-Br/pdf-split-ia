import { useState, useEffect } from "react";
import { api } from "./api/client";
import { useJobPoller } from "./hooks/useJobPoller";
import { UploadZone } from "./components/UploadZone";
import { StatusPoller } from "./components/StatusPoller";
import { ResultPanel } from "./components/ResultPanel";

const PROCESSING_STATUSES = ["QUEUED", "EXTRACTING", "CLASSIFYING", "BUILDING"];

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  );
}

function useDarkMode() {
  const [dark, setDark] = useState(() => localStorage.getItem("theme") === "dark");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  return [dark, () => setDark((d) => !d)];
}

export default function App() {
  const [dark, toggleDark] = useDarkMode();
  const [jobId, setJobId] = useState(null);
  const [jobState, setJobState] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [pollerError, setPollerError] = useState(null);

  useJobPoller(jobId, setJobState, setPollerError);

  async function handleUpload(file) {
    setUploading(true);
    setUploadError(null);
    try {
      const { job_id } = await api.uploadPdf(file);
      setJobId(job_id);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const networkFail = !err?.response;
      setUploadError(
        detail ?? (networkFail ? "Sem resposta do servidor. Verifique sua conexão." : "Erro ao enviar arquivo.")
      );
    } finally {
      setUploading(false);
    }
  }

  function handleReset() {
    setJobId(null);
    setJobState(null);
    setUploadError(null);
    setPollerError(null);
  }

  const isProcessing = jobState && PROCESSING_STATUSES.includes(jobState.status);
  const isDone = jobState?.status === "DONE";
  const isError = jobState?.status === "ERROR";

  return (
    <>
      <header className="app-header">
        <img src="/logo-brasiliense.webp" alt="Brasiliense" className="header-logo" />
        <button className="theme-toggle" onClick={toggleDark} title="Alternar tema">
          {dark ? <SunIcon /> : <MoonIcon />}
        </button>
      </header>

      <main className="app-main">
        <div className="app-column">

          {/* Estado de upload: sem card, o upload-layout é o container visual */}
          {!jobId && (
            <>
              {uploadError && (
                <div className="card" style={{ marginBottom: 16 }}>
                  <div className="error-box" style={{ marginBottom: 0 }}>{uploadError}</div>
                </div>
              )}
              <UploadZone onUpload={handleUpload} loading={uploading} />
            </>
          )}

          {/* Estado com job ativo: card padrão */}
          {jobId && (
            <div className="card">
              {pollerError && (
                <div className="error-box">
                  {pollerError}
                  <br />
                  <button className="btn secondary" style={{ marginTop: 14 }} onClick={handleReset}>
                    Reiniciar
                  </button>
                </div>
              )}

              {isError && (
                <div className="error-box">
                  {jobState.error || jobState.message}
                  <br />
                  <button className="btn secondary" style={{ marginTop: 14 }} onClick={handleReset}>
                    Tentar novamente
                  </button>
                </div>
              )}

              {!jobState && !pollerError && (
                <div className="status-message" style={{ padding: "24px 0", textAlign: "center", color: "var(--text-3)" }}>
                  Aguardando servidor...
                </div>
              )}

              {isProcessing && <StatusPoller job={jobState} />}

              {isDone && (
                <ResultPanel job={jobState} jobId={jobId} onReset={handleReset} />
              )}
            </div>
          )}

        </div>
      </main>
    </>
  );
}
