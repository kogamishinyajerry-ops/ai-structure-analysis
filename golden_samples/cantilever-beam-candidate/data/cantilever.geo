// FM-04a Phase 21 A — canonical cantilever beam geometry.
//
// 1000 mm × 100 mm × 100 mm prismatic cantilever. Coordinate frame:
//   x = length axis (0..L), root face at x=0 (clamped), tip face at
//       x=L (loaded).
//   y = bending-plane axis (-h/2..+h/2 → here 0..h with origin at corner).
//   z = transverse axis (0..b).
// Origin at the root-bottom-back corner so coordinate-plane node
// selection (`x < tol_m` etc.) works for clamp + tip-load planes.
//
// Phase 20 B documented this geometry analytically; the cross-check
// runner that promotes the case to tier_2_validated lands in Phase
// 21 A via the Phase 20 C `run_tier2_meshed_pipeline` (gmsh → C3D4
// → ccx → read tip displacement).
//
// Expected δ_tip = P · L³ / (3 · E · I) with the parameters below:
//   E = 210e9 Pa (steel-s355)
//   I = b·h³ / 12 = 0.1 · 0.001 / 12 = 8.3333…e-6 m⁴
//   P = -1000 N (downward, applied at tip face)
//   → δ_tip = -1000 · 1.0 / (3 · 210e9 · 8.3333e-6) = -1.9048e-4 m

L = 1.000;  // beam length (m) — root x=0 to tip x=L
h = 0.100;  // cross-section depth in bending plane (m)
b = 0.100;  // cross-section width transverse to bending (m)
cl = 0.050; // characteristic mesh length (m) — overridden by gmsh -clmax

// Root-face outline (x = 0 plane).
Point(1) = {0, 0, 0, cl};
Point(2) = {0, h, 0, cl};
Point(3) = {0, h, b, cl};
Point(4) = {0, 0, b, cl};
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};
Line Loop(10) = {1, 2, 3, 4};
Plane Surface(11) = {10};

// Extrude along x to make the beam.
out[] = Extrude {L, 0, 0} { Surface{11}; };
Physical Volume("cantilever") = {out[1]};
