// FM-04a Phase 12 C — extended thick-walled pressure cylinder candidate.
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Variation of demo_cylinder_pv/cylinder.geo with:
//   - Length L = 400 mm (vs 200 mm baseline) — provides a long-cylinder
//     PV case so the cohort sees geometry variation within the PV type.
//   - Outer-axial mesh density bumped to 8 layers (vs 4) to keep aspect
//     ratio close to 1 on the extended length.
//
// Units: mm, MPa, N (CalculiX-default consistent unit set)

Ri  = 100;
Ro  = 150;
L   = 400;
thetaDeg = 5;
nr  = 8;
na  = 8;
nt  = 1;

theta = thetaDeg * Pi / 180.0;
lc    = 10;

Point(0) = {0,                  0,                  0,  lc};
Point(1) = {Ri,                 0,                  0,  lc};
Point(2) = {Ro,                 0,                  0,  lc};
Point(3) = {Ro*Cos(theta),      Ro*Sin(theta),      0,  lc};
Point(4) = {Ri*Cos(theta),      Ri*Sin(theta),      0,  lc};

Line(1) = {1, 2};
Circle(2) = {2, 0, 3};
Line(3) = {3, 4};
Circle(4) = {4, 0, 1};
Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

Transfinite Curve {1, 3} = nr + 1 Using Progression 1;
Transfinite Curve {2, 4} = nt + 1 Using Progression 1;
Transfinite Surface {1} = {1, 2, 3, 4};
Recombine Surface {1};

Extrude {0, 0, L} {
  Surface{1};
  Layers{na};
  Recombine;
}

Mesh.ElementOrder = 2;
Mesh.SecondOrderIncomplete = 1;

Physical Volume("cylinder_volume", 100) = {1};
Physical Surface("inner_pressure_surface", 200) = {26};
Physical Surface("bottom_axial_constraint", 201) = {1};
Physical Surface("top_axial_constraint", 202) = {15};
