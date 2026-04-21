import { useState, useRef } from "react";

export function UploadZone({ onUpload, loading }) {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  function handleFiles(files) {
    const pdf = Array.from(files).find((f) => f.type === "application/pdf" || f.name.endsWith(".pdf"));
    if (pdf) setFile(pdf);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  function handleSubmit() {
    if (file && !loading) onUpload(file);
  }

  return (
    <div>
      <div
        className={`upload-zone${dragOver ? " drag-over" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <div className="icon">📄</div>
        <p>Arraste o PDF aqui ou clique para selecionar</p>
        <p className="hint">Faturas, packing lists, certificados, qualquer PDF consolidado</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {file && <p className="file-selected">Selecionado: {file.name}</p>}
      </div>

      <div style={{ textAlign: "center" }}>
        <button
          className="btn"
          onClick={handleSubmit}
          disabled={!file || loading}
        >
          {loading ? "Enviando..." : "Processar PDF"}
        </button>
      </div>
    </div>
  );
}
