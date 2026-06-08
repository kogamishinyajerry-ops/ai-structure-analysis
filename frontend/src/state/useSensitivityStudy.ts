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

  // Plain closures (not useCallback): they are mutually recursive (a study
  // failure's Retry either resumes polling or relaunches the study) and are
  // recreated per render exactly as the original inline App.tsx handlers were,
  // so there is no referential-stability regression.

  const pollExperiment = (id: string, relaunch?: () => void): void => {
    // ErrorCard label: the active case when known, else the experiment id
    // (the Copilot path may have no selected case).
    const caseId = activeCaseId ?? id;
    // Surface a study failure. `retryAction` is the MEANINGFUL recovery for
    // this failure mode; when omitted the Retry only dismisses, so we never
    // make a false "Retry will recover" promise nor strand loading=true. It
    // re-enters setLoading(true) itself because withRecovery's own Retry
    // reruns only its inner closure, not the outer loading set (Codex R1 P2-a).
    const surface = (line: string, retryAction?: () => void): void => {
      setLoading(false);
      appendLog(`[ERROR] ${line} (see workbench banner)`);
      setUploadError({
        ...studyRunRecoveryOptions(caseId),
        onRetry: retryAction
          ? () => {
              clearUploadError();
              setLoading(true);
              retryAction();
            }
          : () => clearUploadError(),
      });
    };
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase}/sensitivity/status/${id}`);
        if (res.status === 404) {
          // The backend lost the experiment record (e.g. a restart drops
          // SensitivityService.experiments, which is in-memory) — re-polling
          // would 404 forever, so relaunch is the only recovery (Codex R2 P2).
          // Copilot path with no relaunch thunk → dismiss-only.
          clearInterval(interval);
          surface(
            'Sensitivity study is no longer tracked by the backend',
            relaunch,
          );
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as ExperimentStatus;
        // The backend only ever rolls up to COMPLETED (sensitivity.py
        // get_experiment_status), so detect a failed sweep run directly off
        // the per-run status — otherwise a failed run polls forever.
        const failed =
          data.status === 'FAILED' ||
          (data.runs ?? []).some((r) => r.status === 'FAILED');
        // Normalise the stored status to FAILED on a failed run so the rest of
        // the UI stops advertising RUNNING once polling has terminally stopped
        // (Codex R0 P2-b; the run-state tone consumer is fixed in App.tsx per
        // Codex R1 P3).
        setActiveExperiment(failed ? { ...data, status: 'FAILED' } : data);
        if (failed) {
          clearInterval(interval);
          // Terminal: re-polling returns the same FAILED, so the only real
          // recovery is to RELAUNCH the study (Codex R1 P2-b). The Copilot
          // path has no relaunch thunk → Retry dismisses rather than loop.
          surface('Sensitivity study run failed', relaunch);
        } else if (data.status === 'COMPLETED') {
          clearInterval(interval);
          setLoading(false);
          onComplete();
        }
      } catch (err) {
        clearInterval(interval);
        console.error('Study status poll failed', err);
        // Transient /status error: resume polling the SAME experiment.
        surface('Sensitivity study status poll failed', () =>
          pollExperiment(id, relaunch),
        );
      }
    }, pollIntervalMs);
  };

  const handleRunStudy = async (
    param: string,
    values: number[],
  ): Promise<void> => {
    if (!activeCaseId) return;
    // Relaunch thunk for a terminal failed sweep's Retry (Codex R1 P2-b).
    const relaunch = (): void => {
      void handleRunStudy(param, values);
    };
    // The full start → poll handoff AND its failure cleanup run INSIDE
    // withRecovery. withRecovery's Retry reruns only this closure (not any
    // outer block), so keeping setLoading(true)/setLoading(false) here means
    // loading is restored on EVERY attempt — including a retried failed start
    // (Codex R0 P2-a + R1 P2-a + R2 P1). On success the closure starts polling
    // and leaves loading true; on failure it resets loading and rethrows so
    // withRecovery still surfaces the ErrorCard + wires Retry.
    await withRecovery(async () => {
      setLoading(true);
      try {
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
            typeof body.detail === 'string'
              ? body.detail
              : `HTTP ${res.status}`,
          );
        }
        if (!body.experiment_id) {
          throw new Error('backend returned no experiment_id');
        }
        pollExperiment(body.experiment_id, relaunch);
        return body as { experiment_id: string };
      } catch (err) {
        appendLog(
          '[ERROR] Sensitivity study failed to start (see workbench banner)',
        );
        setLoading(false);
        throw err;
      }
    }, studyRunRecoveryOptions(activeCaseId));
  };

  return { handleRunStudy, pollExperiment };
}
