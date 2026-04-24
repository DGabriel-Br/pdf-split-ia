import { useEffect } from "react";
import { api } from "../api/client";

const TERMINAL_STATES = ["DONE", "ERROR"];
const MAX_CONSECUTIVE_ERRORS = 5;

export function useJobPoller(jobId, onUpdate, onNetworkError, intervalMs = 2000) {
  useEffect(() => {
    if (!jobId) return;

    let consecutiveErrors = 0;
    let stopped = false;

    async function poll() {
      if (stopped) return;
      try {
        const state = await api.getJobStatus(jobId);
        consecutiveErrors = 0;
        onUpdate(state);
        if (TERMINAL_STATES.includes(state.status)) {
          stopped = true;
          return;
        }
      } catch {
        consecutiveErrors++;
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          stopped = true;
          onNetworkError?.("Servidor inacessível após várias tentativas. Verifique sua conexão.");
          return;
        }
      }
      if (!stopped) setTimeout(poll, intervalMs);
    }

    poll();
    return () => { stopped = true; };
  }, [jobId, onUpdate, onNetworkError, intervalMs]);
}
