# rod-wave-impact-stiff-candidate — fixture notes

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Sibling of `rod-wave-impact-candidate` (Phase 14 D). The STIFF variant changes ONLY Young's modulus (200 GPa -> 210 GPa) so the analytical 1D-bar wave-propagation cross-check shifts to a faster wave and earlier reflection.

## Geometry (unchanged from canonical)

* Rod length L = 1.0 m
* Cross-section area A = 0.0001 m^2 (10 mm x 10 mm)
* Impact velocity v = 10.0 m/s at x = 0; far end at x = L is FREE

## Material (STIFF variant)

* E = 2.100e+11 Pa (tool steel; vs 2.0e+11 carbon steel in the canonical case)
* rho = 7850.0 kg/m^3 (unchanged)

## Analytical cross-check

* Wave speed c = sqrt(E/rho) = 5172.2 m/s.
* First reflection t_refl = L/c = 193.34 us.
* Frame dt = 10.0 us; first-reflection frame index = 19 (observed = 190.0 us; residual = 1.73%; within the 5% WAVE_CROSS_CHECK_TOLERANCE_PCT band).

## What this fixture is NOT

* Not a real OpenRadioss or CalculiX *DYNAMIC run; the animation manifest is synthetic.
* Not Tier 2 benchmark agreement.
* Not a signed validation packet.

Regenerate with `python scripts/gen_rod_wave_impact_stiff_deck.py`.
