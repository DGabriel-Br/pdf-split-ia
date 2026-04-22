import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
});

export const api = {
  uploadPdf(file) {
    const form = new FormData();
    form.append("file", file);
    return http.post("/upload", form).then((r) => r.data);
  },

  getJobStatus(jobId) {
    return http.get(`/jobs/${jobId}`).then((r) => r.data);
  },

  getDownloadUrl(jobId, docType) {
    return `/jobs/${jobId}/download/${docType}`;
  },

  getDownloadAllUrl(jobId) {
    return `/jobs/${jobId}/download-all`;
  },
};
