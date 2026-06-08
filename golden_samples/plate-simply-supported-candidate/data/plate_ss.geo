// FM-04a Phase 25 A — canonical simply-supported plate geometry.
//
// 1.0 m × 1.0 m × 0.02 m square plate (a/t = 50, well inside the
// Kirchhoff thin-plate envelope). Coordinate frame: origin at one
// corner, x along one side, y along the other, z = thickness (0..T).
// The simply-supported boundary condition is the "pin bottom edge"
// 3D approximation: w (u_z) = 0 along the 4 edge lines of the
// bottom face (z=0 + on one of the 4 perimeter sides).
//
// Phase 25 A's plate_ss_runner consumes this geometry with the
// closed-form Timoshenko α coefficient (0.00406 for square ν=0.3
// plate) to flip the case to tier_2_validated.

a = 1.0;     // plate side length (m)
t = 0.020;   // plate thickness (m)
cl = 0.060;  // characteristic mesh length (m) — overridden by gmsh -clmax

// Bottom face corners.
Point(1) = {0, 0, 0, cl};
Point(2) = {a, 0, 0, cl};
Point(3) = {a, a, 0, cl};
Point(4) = {0, a, 0, cl};
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};
Line Loop(10) = {1, 2, 3, 4};
Plane Surface(11) = {10};

// Extrude through thickness.
out[] = Extrude {0, 0, t} { Surface{11}; };
Physical Volume("plate") = {out[1]};
