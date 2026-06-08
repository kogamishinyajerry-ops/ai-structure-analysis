// FM-04a Phase 12 C — stiff modal cantilever candidate (1 m × 75 mm × 75 mm).
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Variant of demo_modal_cantilever_pv with stiffer 75 × 75 mm cross-section.
// Mode 1 for a square-cross-section cantilever scales as h / L^2 (since
// √(EI/ρA) = √(E/12ρ) × h × const), so the 75/50 = 1.5× ratio puts the
// expected mode 1 at 41.78 × 1.5 = 62.67 Hz analytical. Provides a
// second modal candidate so the cohort dashboard sees within-type
// variation.

lc_length = 1.0;
lc_width  = 0.075;
lc_height = 0.075;

n_length = 40;
n_width  = 3;
n_height = 3;

Point(1) = {0,         0,         0,         0.06};
Point(2) = {lc_length, 0,         0,         0.06};
Point(3) = {lc_length, lc_width,  0,         0.06};
Point(4) = {0,         lc_width,  0,         0.06};
Point(5) = {0,         0,         lc_height, 0.06};
Point(6) = {lc_length, 0,         lc_height, 0.06};
Point(7) = {lc_length, lc_width,  lc_height, 0.06};
Point(8) = {0,         lc_width,  lc_height, 0.06};

Line(1)  = {1, 2}; Line(2)  = {2, 3}; Line(3)  = {3, 4}; Line(4)  = {4, 1};
Line(5)  = {5, 6}; Line(6)  = {6, 7}; Line(7)  = {7, 8}; Line(8)  = {8, 5};
Line(9)  = {1, 5}; Line(10) = {2, 6}; Line(11) = {3, 7}; Line(12) = {4, 8};

Line Loop(1) = {1, 2, 3, 4};      Plane Surface(1) = {1};
Line Loop(2) = {5, 6, 7, 8};      Plane Surface(2) = {2};
Line Loop(3) = {1, 10, -5, -9};   Plane Surface(3) = {3};
Line Loop(4) = {3, 12, -7, -11};  Plane Surface(4) = {4};
Line Loop(5) = {4, 9, -8, -12};   Plane Surface(5) = {5};
Line Loop(6) = {2, 11, -6, -10};  Plane Surface(6) = {6};

Surface Loop(1) = {1, 2, 3, 4, 5, 6};
Volume(1) = {1};

Transfinite Line {1, 3, 5, 7} = n_length + 1;
Transfinite Line {9, 10, 11, 12} = n_height + 1;
Transfinite Line {2, 4, 6, 8} = n_width + 1;
Transfinite Surface "*";
Transfinite Volume "*";
Recombine Surface "*";

Mesh.ElementOrder = 2;
Mesh.SecondOrderIncomplete = 1;

Physical Volume("beam_volume", 100) = {1};
Physical Surface("clamped_face", 200) = {5};
Physical Surface("free_face", 201) = {6};
