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
