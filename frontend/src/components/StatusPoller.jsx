function progressLabel(progress) {
  if (progress <= 5)  return "Iniciando...";
  if (progress <= 79) return `Classificando páginas (${progress}%)`;
  if (progress <= 89) return "Gerando arquivos de saída...";
  if (progress <= 99) return "Finalizando...";
  return "Concluído";
}

export function StatusPoller({ job }) {
  return (
    <div className="progress-section">
      <p className="progress-label">{progressLabel(job.progress)}</p>
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${job.progress}%` }}
        />
      </div>
      <p className="progress-percent">{job.progress}%</p>
      {job.message && <p className="status-message">{job.message}</p>}
    </div>
  );
}
