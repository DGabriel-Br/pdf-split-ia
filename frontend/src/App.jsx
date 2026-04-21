import { useState, useEffect } from "react";
import { api } from "./api/client";
import { useJobPoller } from "./hooks/useJobPoller";
import { UploadZone } from "./components/UploadZone";
import { StatusPoller } from "./components/StatusPoller";
import { ResultPanel } from "./components/ResultPanel";

const PROCESSING_STATUSES = ["QUEUED", "EXTRACTING", "CLASSIFYING", "BUILDING"];

function useDarkMode() {
  const [dark, setDark] = useState(
    () => localStorage.getItem("theme") === "dark"
  );

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

  useJobPoller(jobId, setJobState);

  async function handleUpload(file) {
    setUploading(true);
    setUploadError(null);
    try {
      const { job_id } = await api.uploadPdf(file);
      setJobId(job_id);
    } catch (err) {
      setUploadError(
        err?.response?.data?.detail ?? "Erro ao enviar arquivo. Verifique o backend."
      );
    } finally {
      setUploading(false);
    }
  }

  function handleReset() {
    setJobId(null);
    setJobState(null);
    setUploadError(null);
  }

  const isProcessing = jobState && PROCESSING_STATUSES.includes(jobState.status);
  const isDone = jobState?.status === "DONE";
  const isError = jobState?.status === "ERROR";

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h1>PDF Split IA</h1>
          <button className="theme-toggle" onClick={toggleDark} title="Alternar tema">
            {dark ? "☀️" : "🌙"}
          </button>
        </div>
        <p className="subtitle">
          Separação automática de documentos de importação usando inteligência artificial
        </p>

        {uploadError && <div className="error-box">{uploadError}</div>}
        {isError && (
          <div className="error-box">
            Erro no processamento: {jobState.error || jobState.message}
            <br />
            <button className="btn secondary" style={{ marginTop: 12 }} onClick={handleReset}>
              Tentar novamente
            </button>
          </div>
        )}

        {!jobId && !isError && (
          <UploadZone onUpload={handleUpload} loading={uploading} />
        )}

        {isProcessing && <StatusPoller job={jobState} />}

        {isDone && (
          <ResultPanel job={jobState} jobId={jobId} onReset={handleReset} />
        )}
      </div>
    </div>
  );
}
