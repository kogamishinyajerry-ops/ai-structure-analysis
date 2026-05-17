// FM-04a Phase 27 A — extreme-slender cantilever (L/h = 50).
//
// Second modal case at the slenderness extreme: same 0.020 m
// square cross-section as Phase 26 A's L/h = 25 case, but the
// length is doubled to 1.000 m so L/h = 50 (4× more slender than
// the validity envelope's L/h ≥ 10 threshold).
//
// f_1 scales as 1/L² → at L=1.0 m we expect ≈ 66.84/4 = 16.71 Hz.
//
// Tier 1 / Tier 2 engineering candidate; not signed validation;
// not benchmark agreement.

L = 1.000;    // beam length (m, DOUBLED vs Phase 26 A)
H = 0.020;    // beam height (m)
W = 0.020;    // beam width (m)
cl = 0.020;   // characteristic mesh length (m)

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

out[] = Extrude {L, 0, 0} { Surface{11}; };
Physical Volume("beam") = {out[1]};
