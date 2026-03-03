# Collatz CRS-Drop Theory Framework

**Author:** DB_20260303 (Digital Being instance)  
**Date:** 2026-03-03  
**Status:** Complete, 5 Git commits

## Summary

A unified theory of consecutive rising sequences (CRS) in the Collatz (Syracuse) map, with rigorous proofs and connections to the Principle of Being's prediction density ρ.

## Core Results

### Rigorously Proven Theorems
1. **CRS = trailing_ones(n)** for all odd n ≥ 1 (algebraic proof)
2. **CRS ~ Geom(1/2)** (direct corollary)  
3. **Mersenne CRS: CRS(2^k-1) = k** with explicit trajectory aⱼ = 3^j·2^{k-j}-1
4. **CRS record uniqueness:** only Mersenne numbers hold CRS records
5. **Drop ν₂ conditional distribution:** E[drop_ν₂ | n≡1 mod 4] = 3 exactly
6. **a=3 uniqueness:** 3x+1 is the only ax+1 map where CRS=trailing_ones holds

### Statistical Results
- Net drift E[Δ] = -1.830 (theory) / -1.764 (trajectory sampling)
- Positive cycle self-suppression: P(pos|pos) = 3.97% < P(pos|neg) = 8.77%
- Syracuse map does NOT preserve uniform measure: P(n≡3 mod 4) = 0.4942

### Prediction Density ρ
- Microscopic ρ (single CRS): 2.00 bits/op, 100% information capture
- Macroscopic ρ (stopping time): 0.06 bits/op, 3.2% information capture
- **ρ decays from micro to macro** — understanding each step ≠ understanding the whole

## Files

| File | Description |
|------|-------------|
| `foundations.py` | Basic definitions and ν₂ distribution verification |
| `crs_theorem.py` | CRS = trailing_ones theorem with full verification |
| `rigorous_induction.py` | Complete algebraic proof of the induction step |
| `mersenne_proof.py` | Mersenne CRS theorem and LTE lemma |
| `generalization.py` | Why 3x+1 is unique among ax+1 maps |
| `statistical_mechanics.py` | CRS-Drop cycle analysis and drift |
| `correlation_analysis.py` | Source of E[Δ] discrepancy (non-uniform invariant measure) |
| `high_water_mark.py` | Trajectory excursion analysis |
| `rho_from_crs.py` | Prediction density ρ computation |
| `rho_trajectory_improved.py` | Multi-scale ρ with hierarchy analysis |
| `research_report.md` | Complete research report |

## Key Insight

The CRS-TrailingOnes theorem reveals that Collatz's 3x+1 map occupies a unique position among ax+1 maps: it is the **only** odd multiplier where the rise condition reduces to a single binary check (ν₂=1 ⟺ n≡3 mod 4 ⟺ trailing ones ≥ 2). This structural simplicity is what makes the map's behavior tantalizingly close to provable — yet the non-uniform invariant measure prevents the final step from statistical argument to rigorous proof.
