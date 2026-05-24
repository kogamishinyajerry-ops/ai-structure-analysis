// FM-04a Phase 35 C — upload + case-load error recovery hook.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.
//
// Closes 2 of 5 silent error-recovery paths flagged by Phase 33 C
// novice_simulator finding #2:
//   1. FRD upload (App.tsx `generateReportFromFile`) — previously
//      silent `console.error("Upload failed", err)` in catch block
//   2. Case load (App.tsx `selectCase`) — previously silent
//      `console.error("Case selection failed", err)` in catch block
//
// The remaining 3 paths (PDF export crude alert / WebSocket death
// no reconnect / stop request silent) carry to Phase 36+; they need
// separate state surfaces (live job context, not upload context).
//
// Phase 33 D's earlier attempt added ErrorCard wiring directly into
// App.tsx and grew App.tsx LOC by ~71 — tripping the Phase 29 B
// <1500 regression pin (1457 → 1528). Phase 35 C extracts the
// state + recovery wrapper into THIS hook so App.tsx only gains:
//   - 1 import line
//   - 1 hook call
//   - 1 conditional ErrorCard mount
//   - 2 `withRecovery(...)` wrappers around the existing fetches
//
// Phase 32 B `useAppUiMode` set the precedent for this pattern;
// the same `{ state, actions }` envelope is used here for
// consistency.
//
// Anti-gaming guards:
//   M:-1 (NEW Phase 35) — App.tsx LOC must stay < 1500 after the
//     wiring lands. Hook absorbs the bulk of the state machinery.
//   I:-1 (Phase 34 carry) — ErrorCard.tsx is NOT modified; this
//     hook composes the existing Phase 18 D ErrorCard shape.
//   D:-1 (rubric v2.0 carry) — hook tests pin both the state
//     transitions and the `withRecovery` contract.

import { useCallback, useState } from 'react';

import type { ErrorCardProps } from '../components/ErrorCard';

/** Shape of the error to be displayed by an ErrorCard. Excludes
 * onRetry — the recovery hook injects that itself so the surface
 * remains the same regardless of how the operation was triggered. */
export type UploadErrorPayload = Omit<ErrorCardProps, 'onRetry'>;

/** Options accepted by `withRecovery`. The recovery hook synthesises
 * onRetry from `fn` itself (re-runs the operation), so callers pass
 * the metadata, not the callback. */
export interface WithRecoveryOptions {
  /** Headline shown in the ErrorCard. */
  readonly title: string;
  /** Plain-language message describing the failure mode. */
  readonly message: string;
  /** Ordered remediation steps shown to the user. Optional. */
  readonly remediation?: readonly string[];
  /** Optional support-ticket / log-correlation code. */
  readonly code?: string;
  /** Phase 36 B — novice-friendly pill copy that takes priority over
   * `code` for display; the raw `code` is preserved as
   * data-error-code for support-ticket scraping. */
  readonly codeFriendly?: string;
}

export interface UseUploadErrorRecoveryState {
  /** The current ErrorCard payload (with onRetry pre-bound) or
   * null when no error is surfaced. */
  uploadError: ErrorCardProps | null;
}

export interface UseUploadErrorRecoveryActions {
  /** Surface an arbitrary error payload (e.g. from a code path
   * that doesn't fit the `withRecovery` shape). */
  setUploadError: (payload: ErrorCardProps) => void;
  /** Hide the current ErrorCard. */
  clearUploadError: () => void;
  /** Wrap an async operation in a try/catch that surfaces failure
   * via the ErrorCard.
   *
   * On success: returns the awaited value of `fn`.
   * On error: returns `undefined`, surfaces the ErrorCard with
   *   `options` (and an injected `onRetry` that re-runs `fn`), and
   *   logs to console for dev diagnostics.
   */
  withRecovery: <T>(
    fn: () => Promise<T>,
    options: WithRecoveryOptions,
  ) => Promise<T | undefined>;
}

export interface UseUploadErrorRecoveryResult {
  state: UseUploadErrorRecoveryState;
  actions: UseUploadErrorRecoveryActions;
}

/** Phase 35 C — recovery option template for FRD upload failures.
 * Exposed as a module-level builder so the call-site stays slim. */
export function uploadRecoveryOptions(
  fileName: string,
): WithRecoveryOptions {
  return {
    title: 'Could not generate report from upload',
    message: `Uploading ${fileName} did not produce a report. The backend may be unreachable or the file may be malformed.`,
    remediation: UPLOAD_REMEDIATION,
    code: 'UPLOAD',
    codeFriendly: 'Upload',
  };
}

/** Phase 35 C — recovery option template for case-load failures. */
export function caseLoadRecoveryOptions(
  caseId: string,
): WithRecoveryOptions {
  return {
    title: `Could not load case ${caseId}`,
    message:
      'The backend did not return a report for this case. It may be unreachable or the case manifest may be incomplete.',
    remediation: CASE_LOAD_REMEDIATION,
    code: 'CASE-LOAD',
    codeFriendly: 'Case load',
  };
}

/** Phase 36 A — recovery option template for PDF export failures.
 * Replaces the pre-Phase-36 crude `alert("Failed to export PDF: ")`
 * surface with a styled ErrorCard + retry button. */
export function pdfExportRecoveryOptions(
  caseId: string,
): WithRecoveryOptions {
  return {
    title: 'Could not export PDF report',
    message: `The PDF export for ${caseId} did not complete. The backend may be unreachable or the report may not yet be ready.`,
    remediation: PDF_EXPORT_REMEDIATION,
    code: 'PDF-EXPORT',
    codeFriendly: 'PDF export',
  };
}

/** Phase 36 A — recovery option template for stop-request failures.
 * Replaces the pre-Phase-36 silent `console.error("Stop failed")`
 * surface with a styled ErrorCard. */
export function stopRequestRecoveryOptions(
  jobId: string,
): WithRecoveryOptions {
  return {
    title: 'Could not stop the running solver',
    message: `The stop request for job ${jobId} was not accepted. The job may still be running; the console will reflect the next backend status update.`,
    remediation: STOP_REQUEST_REMEDIATION,
    code: 'STOP-REQUEST',
    codeFriendly: 'Stop request',
  };
}

/** Phase 37 C — recovery option template for solver-start failures.
 * Closes the 5th of 5 silent error-recovery paths flagged at Phase
 * 33 C novice_simulator #2 + Phase 36 D friction point (c).
 * Replaces the pre-Phase-37 text-only `[ERROR] Solver start failed`
 * log line with a styled ErrorCard alongside the log trail. */
export function solverStartRecoveryOptions(
  caseId: string,
): WithRecoveryOptions {
  return {
    title: 'Could not start the solver',
    message: `The solver did not accept the run request for ${caseId}. The backend may be unreachable, the case may be missing required artifacts, or the upstream may have refused with a detail message visible in the console log.`,
    remediation: SOLVER_START_REMEDIATION,
    code: 'SOLVER-START',
    codeFriendly: 'Solver start',
  };
}

/** FM-04a Phase 38 I — recovery option template for sensitivity-study
 * failures. Closes eval-fleet finding #6 (Phase 38 E): the study run +
 * poll path previously swallowed errors in a bare `console.error` catch
 * (App.tsx handleRunStudy), and a failed or unreachable backend left the
 * UI stuck in `loading` with no surface. The same ErrorCard is reused for
 * both the start failure and a mid-study poll/run failure. */
export function studyRunRecoveryOptions(caseId: string): WithRecoveryOptions {
  return {
    title: 'Sensitivity study did not complete',
    message: `The parameter study for ${caseId} could not be started or stopped before completing. The backend may be unreachable, a solver run in the sweep may have failed, or the study endpoint may have refused the request.`,
    remediation: STUDY_RUN_REMEDIATION,
    code: 'STUDY-RUN',
    codeFriendly: 'Sensitivity study',
  };
}

const CONNECTION_LOST_REMEDIATION = [
  'The solver may still be running on the backend — losing the log stream does not stop the job',
  "Use Retry to reconnect to this job's live log stream",
  'If Retry keeps failing, reopen the case from the browser, or confirm the backend / runner is still up',
] as const;

/** FM-04a Phase 39 A — recovery option template for a dropped live-job log
 * WebSocket: the 6th and last of the silent error-recovery paths flagged at
 * Phase 33 C novice_simulator #2 + Phase 36 D friction point (a). Before this,
 * App.tsx `connectToLogs` ws.onerror appended a single `[ERROR] WebSocket
 * connection died` console line and went silent — the novice saw the solver
 * stall with no recovery surface. The Retry re-runs `connectToLogs` for the
 * same job. Live-job (event-handler) context, so the call-site uses
 * `setUploadError` directly rather than the async `withRecovery` wrapper. */
export function connectionLostRecoveryOptions(jobId: string): WithRecoveryOptions {
  return {
    title: 'Live-job connection lost',
    message: `The live log stream for job ${jobId} disconnected. The solver may still be running on the backend; reconnect to resume following its progress.`,
    remediation: CONNECTION_LOST_REMEDIATION,
    code: `WS-DISCONNECT:${jobId}`,
    codeFriendly: 'Connection lost',
  };
}

const UPLOAD_REMEDIATION = [
  'Confirm the backend at /api/v1/report/generate is reachable',
  'Try a smaller or alternative .frd / .inp file',
  'Use Retry to send the same upload again',
] as const;

const CASE_LOAD_REMEDIATION = [
  'Confirm the backend at /api/v1/report/generate is reachable',
  'Pick a different case from the registry while the issue is investigated',
  'Use Retry to re-request the same case',
] as const;

const PDF_EXPORT_REMEDIATION = [
  'Confirm the backend at /api/v1/report/export/pdf/<case_id> is reachable',
  'Re-load the case first if the report state looks stale',
  'Use Retry to re-request the same PDF export',
] as const;

const STOP_REQUEST_REMEDIATION = [
  'Watch the solver console for an automatic status update',
  'Confirm the backend at /api/v1/solver/stop/<job_id> is reachable',
  'Use Retry to re-issue the stop request',
] as const;

const SOLVER_START_REMEDIATION = [
  'Read the workbench console for the upstream detail message',
  'Confirm the backend at /api/v1/solver/run is reachable',
  'Re-select the case from the picker, then click Run Solver again',
] as const;

const STUDY_RUN_REMEDIATION = [
  'Read the workbench console for the upstream detail message',
  'Confirm the backend at /api/v1/sensitivity/run + /status is reachable',
  'Use Retry to re-launch the parameter study for the same case',
] as const;

/** Custom hook owning the upload + case-load error-recovery
 * surface. Returns `{ state, actions }` per the Phase 32 B
 * `useAppUiMode` envelope convention. */
export function useUploadErrorRecovery(): UseUploadErrorRecoveryResult {
  const [uploadError, setUploadErrorState] =
    useState<ErrorCardProps | null>(null);

  const setUploadError = useCallback((payload: ErrorCardProps): void => {
    setUploadErrorState(payload);
  }, []);

  const clearUploadError = useCallback((): void => {
    setUploadErrorState(null);
  }, []);

  const withRecovery = useCallback(
    async function withRecoveryImpl<T>(
      fn: () => Promise<T>,
      options: WithRecoveryOptions,
    ): Promise<T | undefined> {
      try {
        const result = await fn();
        // On success, clear any stale error so the surface doesn't
        // outlive its trigger.
        setUploadErrorState(null);
        return result;
      } catch (err) {
        // Keep the console signal for dev diagnostics — novices get
        // the ErrorCard; developers still get the stack trace.
        // eslint-disable-next-line no-console
        console.error(`[useUploadErrorRecovery] ${options.title}`, err);
        setUploadErrorState({
          title: options.title,
          message: options.message,
          ...(options.remediation !== undefined
            ? { remediation: options.remediation }
            : {}),
          ...(options.code !== undefined ? { code: options.code } : {}),
          ...(options.codeFriendly !== undefined
            ? { codeFriendly: options.codeFriendly }
            : {}),
          onRetry: () => {
            // Drop the visible error before retrying so the user
            // sees the operation re-starting.
            setUploadErrorState(null);
            // Fire-and-forget; the outer withRecovery on the next
            // call cycle will re-surface a fresh error if needed.
            void withRecoveryImpl(fn, options);
          },
        });
        return undefined;
      }
    },
    [],
  );

  const state: UseUploadErrorRecoveryState = { uploadError };
  const actions: UseUploadErrorRecoveryActions = {
    setUploadError,
    clearUploadError,
    withRecovery,
  };

  return { state, actions };
}
