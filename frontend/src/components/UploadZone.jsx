import { useState, useRef } from "react";

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor"/>
      <polyline points="14,2 14,8 20,8" stroke="currentColor"/>
      <line x1="12" y1="18" x2="12" y2="12" stroke="currentColor"/>
      <polyline points="9,15 12,12 15,15" stroke="currentColor"/>
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

export function UploadZone({ onUpload, loading }) {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  function handleFiles(files) {
    const pdf = Array.from(files).find(f => f.type === "application/pdf" || f.name.endsWith(".pdf"));
    if (pdf) setFile(pdf);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div>
      <div
        className={`upload-zone${dragOver ? " drag-over" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <div className="upload-icon">
          <UploadIcon />
        </div>
        <p>Arraste o PDF aqui ou clique para selecionar</p>
        <p className="hint">Faturas, packing lists, certificados, qualquer PDF consolidado de importação</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={e => handleFiles(e.target.files)}
        />
        {file && (
          <div className="file-selected">{file.name}</div>
        )}
      </div>

      <div className="btn-row">
        <button
          className="btn"
          onClick={() => file && !loading && onUpload(file)}
          disabled={!file || loading}
        >
          {loading ? <><SpinnerIcon /> Enviando...</> : "Processar PDF"}
        </button>
      </div>
    </div>
  );
}
