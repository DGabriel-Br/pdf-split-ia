const TYPE_LABELS = {
  INVOICE:      "Invoice",
  PACKING_LIST: "Packing List",
  OTHER:        "Other",
};

export function PageLogTable({ pages }) {
  if (!pages || pages.length === 0) return null;

  return (
    <div className="table-section">
      <div className="table-header">
        <h3>Log de classificação</h3>
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
            {pages.map(p => (
              <tr key={p.page_number}>
                <td>{p.page_number}</td>
                <td>
                  <span className={`badge ${p.doc_type}`}>
                    {TYPE_LABELS[p.doc_type] ?? p.doc_type}
                  </span>
                </td>
                <td>
                  <span className={`conf-num${p.confidence < 0.7 ? " low-conf" : ""}`}>
                    {(p.confidence * 100).toFixed(0)}%
                  </span>
                </td>
                <td style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {p.used_ocr    && <span className="tag tag-ocr">OCR</span>}
                  {p.is_doc_start && <span className="tag tag-start">início</span>}
                </td>
                <td>{p.text_length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
