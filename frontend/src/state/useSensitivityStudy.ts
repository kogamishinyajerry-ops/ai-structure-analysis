// FM-04a Phase 38 I — sensitivity-study run + poll flow, extracted from
// App.tsx.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Closes eval-fleet finding #6 (Phase 38 E): the study run + poll path in
// App.tsx previously swallowed errors in a bare `console.error` catch and,
// because the backend never rolls a failed sweep run up to a FAILED
// experiment status, a failed/unreachable backend left the UI stuck in
// `loading` with no surface. This hook routes BOTH the start failure and a
// mid-study poll/run failure through the shared ErrorCard recovery surface.
//
// Extracted (rather than inlined) to respect the App.tsx <1500 LOC pin
// (anti-gaming guard M:-1) — the same Phase 35 C precedent that moved the
// upload/case-load recovery wiring into `useUploadErrorRecovery`. App.tsx
// gains only an import + a single hook call + the `{ handleRunStudy }`
// destructure.

import type { ExperimentStatus } from '../types/AppTypes';
import {
  studyRunRecoveryOptions,
  type UseUploadErrorRecoveryActions,
} from './useUploadErrorRecovery';

export interface UseSensitivityStudyOptions {
  /** API base URL (e.g. http://localhost:8000/api/v1). */
  readonly apiBase: string;
  /** Currently selected case id, or null when none is loaded. */
  readonly activeCaseId: string | null;
  readonly setLoading: (loading: boolean) => void;
  readonly setActiveExperiment: (exp: ExperimentStatus) => void;
  /** Called once when the study reaches COMPLETED (App switches tab). */
  readonly onComplete: () => void;
  /** Append a single line to the workbench console log trail. */
  readonly appendLog: (line: string) => void;
  /** Shared ErrorCard recovery wrapper (from useUploadErrorRecovery). */
  readonly withRecovery: UseUploadErrorRecoveryActions['withRecovery'];
  readonly setUploadError: UseUploadErrorRecoveryActions['setUploadError'];
  readonly clearUploadError: UseUploadErrorRecoveryActions['clearUploadError'];
  /** Poll cadence in ms; injectable so tests need not wait 2 s. */
  readonly pollIntervalMs?: number;
}

export interface UseSensitivityStudyResult {
  readonly handleRunStudy: (param: string, values: number[]) => Promise<void>;
  /** Begin polling an already-started experiment (e.g. one launched by a
   * Copilot action that returns an experiment_id). Shares the same failure
   * surfacing + terminal-FAILED detection as a study started via
   * handleRunStudy. */
  readonly pollExperiment: (experimentId: string) => void;
}

export function useSensitivityStudy(
  opts: UseSensitivityStudyOptions,
): UseSensitivityStudyResult {
  const {
    apiBase,
    activeCaseId,
    setLoading,
    setActiveExperiment,
    onComplete,
    appendLog,
    withRecovery,
    setUploadError,
    clearUploadError,
    pollIntervalMs = 2000,
  } = opts;

  // Plain closures (not useCallback): they are mutually recursive — a
  // poll-failure Retry resumes pollExperiment (Codex R0 P2-c) — and are
  // recreated per render exactly as the original inline App.tsx handlers
  // were, so there is no referential-stability regression.

  /** Surface a study failure via the shared ErrorCard. The Retry resumes
   * polling the (possibly still-running) study rather than abandoning it
   * (Codex R0 P2-c) — `pollExperiment` is referenced before its declaration
   * but only inside the click-time onRetry closure, so it is assigned by
   * the time Retry fires. */
  const failStudy = (line: string, id: string): void => {
    setLoading(false);
    appendLog(`[ERROR] ${line} (see workbench banner)`);
    setUploadError({
      ...studyRunRecoveryOptions(activeCaseId ?? id),
      onRetry: () => {
        clearUploadError();
        setLoading(true);
        pollExperiment(id);
      },
    });
  };

  const pollExperiment = (id: string): void => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase}/sensitivity/status/${id}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as ExperimentStatus;
        // The backend only ever rolls up to COMPLETED (sensitivity.py
        // get_experiment_status), so detect a failed sweep run directly off
        // the per-run status — otherwise a failed run polls forever.
        const failed =
          data.status === 'FAILED' ||
          (data.runs ?? []).some((r) => r.status === 'FAILED');
        // Normalise the stored status to FAILED on a failed run so the rest
        // of the UI (App / Sidebar status pill) stops advertising RUNNING
        // once polling has terminally stopped (Codex R0 P2-b).
        setActiveExperiment(failed ? { ...data, status: 'FAILED' } : data);
        if (failed) {
          clearInterval(interval);
          failStudy('Sensitivity study run failed', id);
        } else if (data.status === 'COMPLETED') {
          clearInterval(interval);
          setLoading(false);
          onComplete();
        }
      } catch (err) {
        clearInterval(interval);
        console.error('Study status poll failed', err);
        failStudy('Sensitivity study status poll failed', id);
      }
    }, pollIntervalMs);
  };

  const handleRunStudy = async (
    param: string,
    values: number[],
  ): Promise<void> => {
    if (!activeCaseId) return;
    setLoading(true);
    // The whole start → poll handoff runs INSIDE withRecovery, so its Retry
    // re-runs the full flow: a successful retry actually starts polling the
    // experiment instead of discarding the id (Codex R0 P2-a).
    const started = await withRecovery(async () => {
      const res = await fetch(`${apiBase}/sensitivity/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_id: activeCaseId,
          parameter: param,
          values,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof body.detail === 'string' ? body.detail : `HTTP ${res.status}`,
        );
      }
      if (!body.experiment_id) {
        throw new Error('backend returned no experiment_id');
      }
      pollExperiment(body.experiment_id);
      return body as { experiment_id: string };
    }, studyRunRecoveryOptions(activeCaseId));
    if (!started) {
      appendLog(
        '[ERROR] Sensitivity study failed to start (see workbench banner)',
      );
      setLoading(false);
    }
  };

  return { handleRunStudy, pollExperiment };
}
