import { useState, useRef } from "react";

function SpinnerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="16" height="16" style={{ animation: "spin 0.8s linear infinite" }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="40 20"/>
    </svg>
  );
}

function SelectIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="16" height="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17,8 12,3 7,8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  );
}

function PdfSplitIllustration() {
  return (
    <svg width="400" height="256" viewBox="0 0 185 118" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Documento PDF de origem */}
      <rect x="4" y="10" width="62" height="82" rx="6" fill="#D4EDFA" stroke="#7ACEF0" strokeWidth="1.5"/>
      <path d="M52 10 L66 24 L52 24 Z" fill="#7ACEF0"/>
      <rect x="12" y="20" width="28" height="11" rx="3" fill="#009EDF"/>
      <text x="26" y="29" textAnchor="middle" fontFamily="monospace" fontSize="6.5" fontWeight="700" fill="white">PDF</text>
      <rect x="12" y="38" width="36" height="2.5" rx="1.25" fill="#7ACEF0"/>
      <rect x="12" y="44" width="30" height="2.5" rx="1.25" fill="#7ACEF0"/>
      <rect x="12" y="50" width="38" height="2.5" rx="1.25" fill="#7ACEF0"/>
      <rect x="12" y="56" width="26" height="2.5" rx="1.25" fill="#7ACEF0"/>
      <rect x="12" y="62" width="34" height="2.5" rx="1.25" fill="#7ACEF0"/>
      <rect x="12" y="68" width="28" height="2.5" rx="1.25" fill="#7ACEF0"/>
      <rect x="12" y="74" width="32" height="2.5" rx="1.25" fill="#7ACEF0"/>
      <rect x="12" y="80" width="22" height="2.5" rx="1.25" fill="#7ACEF0"/>

      {/* Seta de divisão */}
      <line x1="68" y1="51" x2="90" y2="51" stroke="#009EDF" strokeWidth="2" strokeLinecap="round"/>
      <line x1="90" y1="51" x2="90" y2="31" stroke="#009EDF" strokeWidth="2" strokeLinecap="round"/>
      <line x1="90" y1="31" x2="104" y2="31" stroke="#009EDF" strokeWidth="2" strokeLinecap="round"/>
      <polyline points="101,28 104,31 101,34" stroke="#009EDF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      <line x1="90" y1="51" x2="90" y2="71" stroke="#009EDF" strokeWidth="2" strokeLinecap="round"/>
      <line x1="90" y1="71" x2="104" y2="71" stroke="#009EDF" strokeWidth="2" strokeLinecap="round"/>
      <polyline points="101,68 104,71 101,74" stroke="#009EDF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>

      {/* Invoice */}
      <rect x="106" y="8" width="72" height="46" rx="6" fill="#D4EDFA" stroke="#7ACEF0" strokeWidth="1.5"/>
      <path d="M162 8 L178 24 L162 24 Z" fill="#7ACEF0"/>
      <rect x="115" y="17" width="38" height="10" rx="3" fill="#009EDF"/>
      <text x="134" y="25" textAnchor="middle" fontFamily="monospace" fontSize="6" fontWeight="700" fill="white">INVOICE</text>
      <rect x="115" y="32" width="42" height="2" rx="1" fill="#7ACEF0"/>
      <rect x="115" y="37" width="34" height="2" rx="1" fill="#7ACEF0"/>
      <rect x="115" y="42" width="40" height="2" rx="1" fill="#7ACEF0"/>
      <rect x="115" y="47" width="28" height="2" rx="1" fill="#7ACEF0"/>

      {/* Packing List */}
      <rect x="106" y="64" width="72" height="46" rx="6" fill="#E0F5F1" stroke="#99D6CE" strokeWidth="1.5"/>
      <path d="M162 64 L178 80 L162 80 Z" fill="#99D6CE"/>
      <rect x="115" y="73" width="38" height="10" rx="3" fill="#14B8A6"/>
      <text x="134" y="81" textAnchor="middle" fontFamily="monospace" fontSize="5.5" fontWeight="700" fill="white">PKG LIST</text>
      <rect x="115" y="88" width="42" height="2" rx="1" fill="#99D6CE"/>
      <rect x="115" y="93" width="34" height="2" rx="1" fill="#99D6CE"/>
      <rect x="115" y="98" width="40" height="2" rx="1" fill="#99D6CE"/>
      <rect x="115" y="103" width="28" height="2" rx="1" fill="#99D6CE"/>
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
    <div
      className={`upload-layout${dragOver ? " drag-over" : ""}`}
      onDragOver={e => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <div className="upload-layout-left">
        <div>
          <h1 className="upload-title">Separação inteligente de documentos</h1>
          <p className="upload-desc">
            Arraste o PDF do pré-alerta ou selecione um arquivo. A IA identifica faturas, packing lists e outros documentos automaticamente.
          </p>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          style={{ display: "none" }}
          onChange={e => handleFiles(e.target.files)}
        />

        {file && <div className="file-selected">{file.name}</div>}

        <div className="upload-actions">
          {!file ? (
            <button className="btn" onClick={() => inputRef.current?.click()} disabled={loading}>
              <SelectIcon /> Selecionar arquivo
            </button>
          ) : (
            <>
              <button className="btn" onClick={() => !loading && onUpload(file)} disabled={loading}>
                {loading ? <><SpinnerIcon /> Enviando...</> : "Processar PDF"}
              </button>
              <button className="btn secondary" onClick={() => inputRef.current?.click()} disabled={loading}>
                Trocar arquivo
              </button>
            </>
          )}
        </div>
      </div>

      <div className="upload-layout-right" aria-hidden="true">
        <div className="upload-illustration-wrap">
          <PdfSplitIllustration />
        </div>
      </div>
    </div>
  );
}
