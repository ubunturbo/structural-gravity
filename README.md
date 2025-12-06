# Structural Gravity: Code and Data Repository

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17649694.svg)](https://doi.org/10.5281/zenodo.17649694)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Supporting code and data for the paper:

> **"Emergent Structural Gravity from Entanglement Time: Flat Rotation Curves without Dark Matter"**  
> Takayuki Takagi  
> Submitted to Nature Communications (2025)

## Overview

This repository contains:

1. **Qiskit circuits** for measuring structural coherence via GHZ states on IBM Quantum hardware
2. **SPARC fitting code** for galactic rotation curve analysis with structural gravity
3. **Analysis scripts** for reproducing paper results

## Key Results

| Measurement | Value | Source |
|-------------|-------|--------|
| λ₃* (geometric) | 0.15198 | 3/(2π²) |
| λ_exp (quantum) | 0.152 ± 0.003 | IBM Quantum GHZ |
| λ_fit (galactic) | ~0.15 | SPARC fits |
| Mermin violation | 69σ (shot noise) | ibm_torino |

## Installation

```bash
# Clone repository
git clone https://github.com/ubunturbo/structural-gravity.git
cd structural-gravity

# Install dependencies
pip install -r requirements.txt
```

## Requirements

```
qiskit>=0.45
qiskit-aer>=0.12
qiskit-ibm-runtime>=0.15
numpy>=1.20
scipy>=1.7
matplotlib>=3.5
```

## Usage

### 1. GHZ Structural Coherence Measurement

```python
from ghz_structural_coherence import (
    create_mermin_circuits_n3,
    get_mermin_bases_n3,
    simulate_circuits,
    analyze_mermin_results,
    print_analysis_report
)

# Create circuits
circuits = create_mermin_circuits_n3()
bases = get_mermin_bases_n3()

# Simulate (or run on IBM Quantum)
counts_list = simulate_circuits(circuits, shots=8192)

# Analyze
results = analyze_mermin_results(counts_list, bases)
print_analysis_report(results)
```

### 2. SPARC Rotation Curve Fitting

```python
from sparc_structural_gravity import (
    fit_structural_gravity,
    compare_models,
    plot_rotation_curve
)

# Your galaxy data
r = [...]        # kpc
v_obs = [...]    # km/s
v_err = [...]    # km/s
v_baryon = [...] # km/s

# Fit structural gravity model
result = fit_structural_gravity(r, v_obs, v_err, v_baryon)
print(f"v_struct = {result['v_struct']:.1f} km/s")
print(f"χ²_ν = {result['chi2_reduced']:.3f}")
```

### 3. Run on IBM Quantum Hardware

```python
from ghz_structural_coherence import (
    create_mermin_circuits_n3,
    run_on_ibm_quantum
)

# Create circuits
circuits = create_mermin_circuits_n3()

# Execute on ibm_torino
result = run_on_ibm_quantum(
    circuits,
    backend_name="ibm_torino",
    shots=8192
)

print(f"Job ID: {result['job_id']}")
```

## File Structure

```
structural-gravity/
├── README.md
├── LICENSE
├── requirements.txt
├── ghz_structural_coherence.py    # GHZ experiment code
├── sparc_structural_gravity.py    # SPARC fitting code
├── data/
│   ├── mermin_results.json        # IBM Quantum raw data
│   └── sparc_fits.csv             # SPARC fitting results
└── notebooks/
    └── analysis_example.ipynb     # Jupyter notebook example
```

## Theoretical Background

The structural gravity framework proposes:

1. **Structural constant**: λ₃* = 3/(2π²) ≈ 0.152, defined as information density on S³
2. **Emergent time**: Time as entanglement phase rotation (Page-Wootters construction)
3. **Flat rotation curves**: From logarithmic scalar field profile, v² = v_baryon² + v_struct²

The same constant λ₃* appears in:
- Geometric definition (S³ topology)
- Quantum GHZ coherence maximum
- Galactic rotation curve fits

## Citation

If you use this code, please cite:

```bibtex
@article{takagi2025structural,
  title={Emergent Structural Gravity from Entanglement Time: 
         Flat Rotation Curves without Dark Matter},
  author={Takagi, Takayuki},
  journal={Nature Communications},
  year={2025},
  note={Submitted}
}

@dataset{takagi2025ghz,
  title={Even-Odd Vacuum Structure in N-Qubit GHZ Structural Coherence},
  author={Takagi, Takayuki},
  year={2025},
  publisher={Zenodo},
  doi={10.5281/zenodo.17649694}
}
```

## Related Publications

- [Universal Structural Constant from 2⊕3 Symmetry](https://doi.org/10.5281/zenodo.17767833)
- [CMB Even-Odd Parity as Quantum Structural Coherence](https://doi.org/10.5281/zenodo.17660391)
- [Field Equations of Formal Causation](https://doi.org/10.5281/zenodo.17666320)
- [TSTT V3.3: Soul of Formal Causation](https://doi.org/10.5281/zenodo.17620967)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contact

Takayuki Takagi  
Email: lemissio@gmail.com  
Independent Researcher, Higashimatsuyama, Saitama, Japan

## Acknowledgments

- IBM Quantum Network for hardware access
- SPARC database team for rotation curve data
