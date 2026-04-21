const TYPE_LABELS = {
  INVOICE: "Fatura",
  PACKING_LIST: "Packing List",
  OTHER: "Outro",
};

export function PageLogTable({ pages }) {
  if (!pages || pages.length === 0) return null;

  return (
    <div className="table-section">
      <h3>Log de classificação por página</h3>
      <table>
        <thead>
          <tr>
            <th>Página</th>
            <th>Tipo</th>
            <th>Confiança</th>
            <th>OCR</th>
            <th>Chars</th>
            <th>Início doc</th>
            <th>Resposta bruta</th>
          </tr>
        </thead>
        <tbody>
          {pages.map((p) => (
            <tr key={p.page_number}>
              <td>{p.page_number}</td>
              <td>
                <span className={`badge ${p.doc_type}`}>
                  {TYPE_LABELS[p.doc_type] ?? p.doc_type}
                </span>
              </td>
              <td>
                <span className={p.confidence < 0.7 ? "low-conf" : ""}>
                  {(p.confidence * 100).toFixed(0)}%
                </span>
              </td>
              <td>
                {p.used_ocr ? <span className="ocr-yes">OCR</span> : ""}
              </td>
              <td>{p.text_length}</td>
              <td>{p.is_doc_start ? <span className="ocr-yes">Sim</span> : ""}</td>
              <td style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>{p.raw_label}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
