// FM-04a Phase 24 C — viewport animation/runtime detection helpers
// extracted from ResultMeshWebGLViewport.tsx for LOC discipline. Pure
// functions only.
//
// Constraint: ZERO behavior change.

export function detectWebGLSupport(): boolean {
  if (typeof window === 'undefined' || typeof document === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    return Boolean(
      canvas.getContext('webgl2') ||
        canvas.getContext('webgl') ||
        canvas.getContext('experimental-webgl'),
    );
  } catch {
    return false;
  }
}
