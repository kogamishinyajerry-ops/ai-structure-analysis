// Thick-walled pressure cylinder, 5-degree wedge (1/72 circumferential symmetry).
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Units: mm, MPa, N (CalculiX-default consistent unit set)
//   Inner radius Ri = 100 mm
//   Outer radius Ro = 150 mm
//   Slice length L  = 100 mm
//   Wedge angle    = 5 degrees about the Z-axis.
//
// Mesh: 8 elements through wall x 1 circumferentially x 4 axially.
//       Quadratic 20-node hex (C3D20) once extruded with Recombine.

Ri  = 100;
Ro  = 150;
L   = 100;
thetaDeg = 5;
nr  = 8;
na  = 4;
nt  = 1;

theta = thetaDeg * Pi / 180.0;
lc    = 10;  // baseline mesh-size hint; transfinite controls dominate.

// Center point on the axis, plus 4 corners of the bottom face.
Point(0) = {0,                  0,                  0,  lc};
Point(1) = {Ri,                 0,                  0,  lc};
Point(2) = {Ro,                 0,                  0,  lc};
Point(3) = {Ro*Cos(theta),      Ro*Sin(theta),      0,  lc};
Point(4) = {Ri*Cos(theta),      Ri*Sin(theta),      0,  lc};

// Bottom face boundary: radial line (1->2), outer arc (2->3),
// radial line (3->4), inner arc (4->1).
Line(1) = {1, 2};
Circle(2) = {2, 0, 3};
Line(3) = {3, 4};
Circle(4) = {4, 0, 1};
Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

// Structured mesh on the bottom face.
Transfinite Curve {1, 3} = nr + 1 Using Progression 1;
Transfinite Curve {2, 4} = nt + 1 Using Progression 1;
Transfinite Surface {1} = {1, 2, 3, 4};
Recombine Surface {1};

// Extrude axially with na layers; Recombine to get hexes.
Extrude {0, 0, L} {
  Surface{1};
  Layers{na};
  Recombine;
}

// Quadratic order, 20-node hex (incomplete = no center node).
Mesh.ElementOrder         = 2;
Mesh.SecondOrderIncomplete = 1;
Mesh.HighOrderOptimize    = 0;
Mesh.RecombineAll         = 1;

// Generate + save as CalculiX-compatible .inp (Abaqus format).
Mesh.Format = 39;
Mesh.SaveAll = 1;
Mesh 3;
Save "cylinder.inp";
