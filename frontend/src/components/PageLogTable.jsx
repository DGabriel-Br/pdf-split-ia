import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";

const TYPE_LABELS = {
  INVOICE:      "Invoice",
  PACKING_LIST: "Packing List",
  OTHER:        "Other",
};

const ALL_TYPES = ["INVOICE", "PACKING_LIST", "OTHER"];

const TYPE_DOT_COLOR = {
  INVOICE:      "var(--accent-mid)",
  PACKING_LIST: "#14B8A6",
  OTHER:        "var(--amber)",
};

function ChevronIcon() {
  return (
    <svg width="9" height="9" viewBox="0 0 9 9" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="1.5,3 4.5,6 7.5,3"/>
    </svg>
  );
}

function CheckSmIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 11 11" fill="none" stroke="currentColor"
      strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2,5.5 4.5,8 9.5,2.5"/>
    </svg>
  );
}

function TypeSelect({ value, onChange, changed }) {
  const [open, setOpen]   = useState(false);
  const [pos,  setPos]    = useState({ top: 0, left: 0 });
  const btnRef            = useRef(null);
  const dropRef           = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onOutside(e) {
      const inBtn  = btnRef.current?.contains(e.target);
      const inDrop = dropRef.current?.contains(e.target);
      if (!inBtn && !inDrop) setOpen(false);
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, [open]);

  function handleToggle() {
    if (!open && btnRef.current) {
      const r = btnRef.current.getBoundingClientRect();
      setPos({ top: r.bottom + 6, left: r.left });
    }
    setOpen(o => !o);
  }

  function handleKeyDown(e) {
    if (e.key === "Escape") setOpen(false);
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleToggle(); }
  }

  return (
    <div className={`type-select-wrap${changed ? " changed" : ""}`}>
      <button
        ref={btnRef}
        type="button"
        className={`type-select-btn ${value}`}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {TYPE_LABELS[value] ?? value}
        <ChevronIcon />
      </button>

      {open && createPortal(
        <div
          ref={dropRef}
          className="type-select-dropdown"
          role="listbox"
          style={{ position: "fixed", top: pos.top, left: pos.left }}
        >
          {ALL_TYPES.map(type => {
            const selected = type === value;
            return (
              <button
                key={type}
                type="button"
                role="option"
                aria-selected={selected}
                className={`type-select-option${selected ? " selected" : ""}`}
                onClick={() => { onChange(type); setOpen(false); }}
              >
                <span className="type-select-dot" style={{ background: TYPE_DOT_COLOR[type] }} />
                <span className="type-select-label">{TYPE_LABELS[type]}</span>
                <span className="type-select-check">{selected && <CheckSmIcon />}</span>
              </button>
            );
          })}
        </div>,
        document.body
      )}
    </div>
  );
}

export function PageLogTable({ pages, pageTypes, onTypeChange }) {
  if (!pages || pages.length === 0) return null;

  const editable = typeof onTypeChange === "function";

  return (
    <div className="table-section">
      <div className="table-header">
        <h3>{editable ? "Revise a classificação" : "Log de classificação"}</h3>
        {editable && (
          <span className="table-hint">Altere o tipo de qualquer página antes de gerar os PDFs.</span>
        )}
      </div>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Pág.</th>
              <th>Tipo</th>
              <th>Confiança</th>
              <th>Flags</th>
              <th>Chars</th>
            </tr>
          </thead>
          <tbody>
            {pages.map(p => {
              const currentType = pageTypes ? pageTypes[p.page_number] : p.doc_type;
              const changed = pageTypes && currentType !== p.doc_type;
              return (
                <tr key={p.page_number} data-changed={changed ? "true" : undefined}>
                  <td>{p.page_number}</td>
                  <td>
                    {editable ? (
                      <TypeSelect
                        value={currentType}
                        changed={changed}
                        onChange={newType => onTypeChange(p.page_number, newType)}
                      />
                    ) : (
                      <span className={`badge ${currentType}`}>
                        {TYPE_LABELS[currentType] ?? currentType}
                      </span>
                    )}
                  </td>
                  <td>
                    <span className={`conf-num${p.confidence < 0.7 ? " low-conf" : ""}`}>
                      {(p.confidence * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {p.used_ocr     && <span className="tag tag-ocr">OCR</span>}
                      {p.is_doc_start && <span className="tag tag-start">início</span>}
                    </div>
                  </td>
                  <td>{p.text_length}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
