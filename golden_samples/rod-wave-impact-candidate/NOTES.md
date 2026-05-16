# rod-wave-impact-candidate — fixture notes

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

## Geometry

* Rod length L = 1.0 m
* Cross-section area A = 0.0001 m^2 (10 mm x 10 mm).
* Material: SA-516 Gr.70 carbon steel (E = 2.000e+11 Pa, rho = 7850.0 kg/m^3).

## Loading

* Axial impact velocity v = 10.0 m/s applied at x = 0; far end at x = L is FREE (reflection sign-flips the compression wave).

## Analytical cross-check

* Wave speed c = sqrt(E/rho) = 5047.5 m/s.
* First reflection (one-way travel) t_refl = L/c = 198.1 us.
* Frame dt = 10.0 us; first-reflection frame index = 20 (observed = 200.0 us; residual = 0.95%; within the 5% WAVE_CROSS_CHECK_TOLERANCE_PCT band).

## What this fixture is NOT

* Not a real OpenRadioss or CalculiX *DYNAMIC run; the animation manifest is synthetic.
* Not Tier 2 benchmark agreement.
* Not a signed validation packet.

Regenerate with `python scripts/gen_rod_wave_impact_deck.py`.
