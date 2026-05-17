// FM-04a Phase 26 A — slender steel cantilever beam for modal cross-check.
//
// 0.5 m × 0.020 m × 0.020 m steel beam. L/h = L/w = 25 (well inside
// Euler-Bernoulli slender-beam envelope ≥ 10). Vibration direction
// is +y (height). Clamped at x = 0; free at x = L. *FREQUENCY step
// extracts the first 5 eigenfrequencies; the runner compares mode 1
// against Rao §8.5 / Inman §6.4 closed-form analytical.

L = 0.500;    // beam length (m)
H = 0.020;    // beam height (m, vibration direction)
W = 0.020;    // beam width (m, transverse to vibration)
cl = 0.012;   // characteristic mesh length (m) — overridden by gmsh -clmax

// Cantilever cross-section corners at x=0.
Point(1) = {0, 0, 0, cl};
Point(2) = {0, H, 0, cl};
Point(3) = {0, H, W, cl};
Point(4) = {0, 0, W, cl};
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};
Line Loop(10) = {1, 2, 3, 4};
Plane Surface(11) = {10};

// Extrude along +x to L.
out[] = Extrude {L, 0, 0} { Surface{11}; };
Physical Volume("beam") = {out[1]};
