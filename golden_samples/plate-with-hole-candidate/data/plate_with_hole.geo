// FM-04a Phase 20 C — canonical plate-with-circular-hole geometry.
//
// 100 mm × 50 mm × 5 mm plate with a 10 mm-radius hole in the centre.
// Coordinate frame: x = long axis (0..L), y = short axis (-W/2..+W/2),
// z = thickness (0..T). Origin at one corner so coordinate-plane
// node selection (`x < tol_m` etc.) works for clamped/loaded faces.
//
// Phase 20 C uses this geometry to demonstrate the meshed Tier 2
// pipeline (gmsh STEP/GEO → C3D4 → ccx). A Phase 21+ Kirsch
// analytical cross-check (σ_max = 3·σ_∞ at the hole edge under
// uniaxial tension) could promote the case to tier_2_validated;
// the runner is NOT shipped in Phase 20 C.

L = 0.100;  // plate length (m)
W = 0.050;  // plate width (m)
T = 0.005;  // plate thickness (m)
R = 0.010;  // hole radius (m)
cl = 0.005;  // characteristic mesh length (m) — overridden by gmsh -clmax

// Plate outline (Z=0 face), centred on (L/2, W/2).
Point(1) = {0, 0, 0, cl};
Point(2) = {L, 0, 0, cl};
Point(3) = {L, W, 0, cl};
Point(4) = {0, W, 0, cl};
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};

// Hole centred at (L/2, W/2, 0). Four arcs for the circle (gmsh
// requires <180° arcs; quartering is the simplest robust form).
cx = L / 2;
cy = W / 2;
Point(5) = {cx, cy, 0, cl};       // centre
Point(6) = {cx + R, cy, 0, cl};
Point(7) = {cx, cy + R, 0, cl};
Point(8) = {cx - R, cy, 0, cl};
Point(9) = {cx, cy - R, 0, cl};
Circle(5) = {6, 5, 7};
Circle(6) = {7, 5, 8};
Circle(7) = {8, 5, 9};
Circle(8) = {9, 5, 6};

Line Loop(10) = {1, 2, 3, 4};
Line Loop(11) = {5, 6, 7, 8};
Plane Surface(12) = {10, 11};  // plate face with hole subtracted

// Extrude through thickness to make a 3D volume.
out[] = Extrude {0, 0, T} { Surface{12}; };
//+
Physical Volume("plate") = {out[1]};
