// FM-04a Phase 12 C — modal cantilever candidate (1 m × 50 mm × 50 mm steel).
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Structured 40 × 2 × 2 C3D20 quadratic hex mesh — same topology that was
// smoke-tested against the Euler-Bernoulli analytical solution during
// Phase 12 A de-risking (mode 1: 0.14%, mode 3: 0.98%, mode 8 axial: 0.07%).
//
// Length axis = x; cross-section is y × z. Clamped at x=0.

lc_length = 1.0;
lc_width  = 0.05;
lc_height = 0.05;

n_length = 40;
n_width  = 2;
n_height = 2;

// 8 corners.
Point(1) = {0,        0,        0,        0.05};
Point(2) = {lc_length, 0,        0,        0.05};
Point(3) = {lc_length, lc_width, 0,        0.05};
Point(4) = {0,        lc_width, 0,        0.05};
Point(5) = {0,        0,        lc_height, 0.05};
Point(6) = {lc_length, 0,        lc_height, 0.05};
Point(7) = {lc_length, lc_width, lc_height, 0.05};
Point(8) = {0,        lc_width, lc_height, 0.05};

// 12 edges.
Line(1)  = {1, 2}; Line(2)  = {2, 3}; Line(3)  = {3, 4}; Line(4)  = {4, 1};
Line(5)  = {5, 6}; Line(6)  = {6, 7}; Line(7)  = {7, 8}; Line(8)  = {8, 5};
Line(9)  = {1, 5}; Line(10) = {2, 6}; Line(11) = {3, 7}; Line(12) = {4, 8};

// 6 surfaces.
Line Loop(1) = {1, 2, 3, 4};    Plane Surface(1) = {1};   // z=0 bottom
Line Loop(2) = {5, 6, 7, 8};    Plane Surface(2) = {2};   // z=h top
Line Loop(3) = {1, 10, -5, -9}; Plane Surface(3) = {3};   // y=0
Line Loop(4) = {3, 12, -7, -11};Plane Surface(4) = {4};   // y=w
Line Loop(5) = {4, 9, -8, -12}; Plane Surface(5) = {5};   // x=0 (clamped face)
Line Loop(6) = {2, 11, -6, -10};Plane Surface(6) = {6};   // x=L (free)

// Hex volume.
Surface Loop(1) = {1, 2, 3, 4, 5, 6};
Volume(1) = {1};

// Transfinite + recombine for structured C3D20 hex.
Transfinite Line {1, 3, 5, 7} = n_length + 1;
Transfinite Line {9, 10, 11, 12} = n_height + 1;
Transfinite Line {2, 4, 6, 8} = n_width + 1;
Transfinite Surface "*";
Transfinite Volume "*";
Recombine Surface "*";

// Quadratic elements (C3D20 in CalculiX nomenclature).
Mesh.ElementOrder = 2;
Mesh.SecondOrderIncomplete = 1;

// Physical groups consumed by assemble_modal_deck.py.
Physical Volume("beam_volume", 100) = {1};
Physical Surface("clamped_face", 200) = {5};   // x = 0 — fully fixed
Physical Surface("free_face", 201)    = {6};   // x = L — visualization only
