import { useEffect } from "react";
import { api } from "../api/client";

const TERMINAL_STATES = ["DONE", "ERROR"];
const MAX_CONSECUTIVE_ERRORS = 5;

export function useJobPoller(jobId, onUpdate, onNetworkError, intervalMs = 2000) {
  useEffect(() => {
    if (!jobId) return;

    let consecutiveErrors = 0;

    const id = setInterval(async () => {
      try {
        const state = await api.getJobStatus(jobId);
        consecutiveErrors = 0;
        onUpdate(state);
        if (TERMINAL_STATES.includes(state.status)) {
          clearInterval(id);
        }
      } catch {
        consecutiveErrors++;
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          clearInterval(id);
          onNetworkError?.("Servidor inacessível após várias tentativas. Verifique sua conexão.");
        }
      }
    }, intervalMs);

    return () => clearInterval(id);
  }, [jobId, onUpdate, onNetworkError, intervalMs]);
}
