// FM-04a Phase 23 B — pure-function stress-tensor derivatives.
//
// Phase 22 D shipped a read-only field-component label on the WebGL
// legend; the per-component σ_xx / σ_yy / σ_zz / max-principal /
// Mises switcher was deferred because `ResultMeshElement` carried
// only a single scalar `value`. Phase 23 B extends the schema with
// an optional `stressTensor` and implements the closed-form
// derivatives here.
//
// All functions are pure (no I/O, no mutation, no globals).
//
// Tier 1 / Tier 2 engineering candidate; not signed validation; not
// benchmark agreement.

export interface StressTensor {
  /** σ_xx — normal stress on the x-face along x. */
  sxx: number;
  /** σ_yy — normal stress on the y-face along y. */
  syy: number;
  /** σ_zz — normal stress on the z-face along z. */
  szz: number;
  /** σ_xy — shear on the x-face along y. */
  sxy: number;
  /** σ_yz — shear on the y-face along z. */
  syz: number;
  /** σ_xz — shear on the x-face along z. */
  sxz: number;
}

export type StressComponent =
  | 'mises'
  | 'sxx'
  | 'syy'
  | 'szz'
  | 'sxy'
  | 'syz'
  | 'sxz'
  | 'max_principal'
  | 'min_principal';

/**
 * Compute Von Mises equivalent stress from a stress tensor.
 *
 * σ_vm = √( ((σ_xx-σ_yy)² + (σ_yy-σ_zz)² + (σ_zz-σ_xx)²)/2
 *           + 3·(σ_xy² + σ_yz² + σ_xz²) )
 *
 * The factor 3 comes from the deviatoric stress contribution; in
 * principal-stress form σ_vm = √(((σ_1-σ_2)² + (σ_2-σ_3)² + (σ_3-σ_1)²)/2).
 *
 * Canonical pins:
 *   - Uniaxial σ_xx=100, rest=0 → σ_vm = 100
 *   - Hydrostatic σ_xx=σ_yy=σ_zz=100, rest=0 → σ_vm = 0
 *   - Pure shear σ_xy=τ, rest=0 → σ_vm = √3·τ
 */
export function computeVonMises(t: StressTensor): number {
  const d1 = t.sxx - t.syy;
  const d2 = t.syy - t.szz;
  const d3 = t.szz - t.sxx;
  const normalTerm = (d1 * d1 + d2 * d2 + d3 * d3) / 2;
  const shearTerm = 3 * (t.sxy * t.sxy + t.syz * t.syz + t.sxz * t.sxz);
  return Math.sqrt(normalTerm + shearTerm);
}

/**
 * Compute the three principal stresses (eigenvalues of the symmetric
 * stress tensor) using the closed-form characteristic polynomial
 * solution. Returns [σ_1, σ_2, σ_3] sorted in DESCENDING order
 * (σ_1 ≥ σ_2 ≥ σ_3).
 *
 * For a symmetric 3×3 matrix the eigenvalues solve
 *   λ³ - I₁·λ² + I₂·λ - I₃ = 0
 * where I₁ = tr(σ), I₂ = principal minors sum, I₃ = det(σ).
 *
 * We use the trigonometric form (Smith 1961) for real-roots symmetric
 * matrices which is stable for our use cases.
 */
export function computePrincipalStresses(t: StressTensor): [number, number, number] {
  const I1 = t.sxx + t.syy + t.szz;
  // I2 and I3 are not needed in the trigonometric form below; the
  // deviator + det path is more numerically stable for the symmetric
  // real-eigenvalue case.

  // Trigonometric form via deviator.
  const p1 =
    t.sxy * t.sxy + t.sxz * t.sxz + t.syz * t.syz;
  if (p1 === 0) {
    // Tensor is already diagonal.
    const eigs: number[] = [t.sxx, t.syy, t.szz];
    eigs.sort((a, b) => b - a);
    return [eigs[0], eigs[1], eigs[2]];
  }
  const q = I1 / 3;
  const p2 =
    (t.sxx - q) ** 2
    + (t.syy - q) ** 2
    + (t.szz - q) ** 2
    + 2 * p1;
  const p = Math.sqrt(p2 / 6);
  // Deviatoric matrix B = (σ - q·I) / p
  const Bxx = (t.sxx - q) / p;
  const Byy = (t.syy - q) / p;
  const Bzz = (t.szz - q) / p;
  const Bxy = t.sxy / p;
  const Byz = t.syz / p;
  const Bxz = t.sxz / p;
  const detB =
    Bxx * (Byy * Bzz - Byz * Byz)
    - Bxy * (Bxy * Bzz - Byz * Bxz)
    + Bxz * (Bxy * Byz - Byy * Bxz);
  // r = det(B)/2, clamp to [-1, 1] for numeric safety.
  const r = Math.max(-1, Math.min(1, detB / 2));
  const phi = Math.acos(r) / 3;
  const sigma1 = q + 2 * p * Math.cos(phi);
  const sigma3 = q + 2 * p * Math.cos(phi + (2 * Math.PI) / 3);
  const sigma2 = I1 - sigma1 - sigma3;
  return [sigma1, sigma2, sigma3];
}

/**
 * Switch the value displayed in the WebGL viewport based on the
 * selected component. For pure-component selectors returns the
 * corresponding tensor entry directly; for Mises / principal returns
 * the derived scalar; falls back to `fallback` when the tensor is
 * absent.
 */
export function componentValue(
  tensor: StressTensor | null | undefined,
  component: StressComponent,
  fallback: number,
): number {
  if (!tensor) return fallback;
  switch (component) {
    case 'mises':
      return computeVonMises(tensor);
    case 'sxx':
      return tensor.sxx;
    case 'syy':
      return tensor.syy;
    case 'szz':
      return tensor.szz;
    case 'sxy':
      return tensor.sxy;
    case 'syz':
      return tensor.syz;
    case 'sxz':
      return tensor.sxz;
    case 'max_principal': {
      const [s1] = computePrincipalStresses(tensor);
      return s1;
    }
    case 'min_principal': {
      const [, , s3] = computePrincipalStresses(tensor);
      return s3;
    }
  }
}
