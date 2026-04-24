const TYPE_LABELS = {
  INVOICE:      "Invoice",
  PACKING_LIST: "Packing List",
  OTHER:        "Other",
};

const ALL_TYPES = ["INVOICE", "PACKING_LIST", "OTHER"];

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
                      <select
                        className={`type-select${changed ? " changed" : ""}`}
                        value={currentType}
                        onChange={e => onTypeChange(p.page_number, e.target.value)}
                      >
                        {ALL_TYPES.map(t => (
                          <option key={t} value={t}>{TYPE_LABELS[t]}</option>
                        ))}
                      </select>
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
