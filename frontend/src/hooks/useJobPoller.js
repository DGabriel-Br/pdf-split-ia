import { useEffect } from "react";
import { api } from "../api/client";

const TERMINAL_STATES = ["DONE", "ERROR"];

export function useJobPoller(jobId, onUpdate, intervalMs = 2000) {
  useEffect(() => {
    if (!jobId) return;

    const id = setInterval(async () => {
      try {
        const state = await api.getJobStatus(jobId);
        onUpdate(state);
        if (TERMINAL_STATES.includes(state.status)) {
          clearInterval(id);
        }
      } catch {
        // network hiccup — keep polling
      }
    }, intervalMs);

    return () => clearInterval(id);
  }, [jobId]);
}
