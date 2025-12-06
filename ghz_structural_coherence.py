# =============================================================================
# Structural Coherence Measurement via GHZ States
# Supporting code for: "Emergent Structural Gravity from Entanglement Time"
# Author: Takayuki Takagi (lemissio@gmail.com)
# License: MIT
# =============================================================================

"""
This module provides Qiskit circuits and analysis tools for measuring
the structural coherence constant λ₃* ≈ 0.152 using N-qubit GHZ states
on IBM Quantum hardware.

Key experiments:
1. Mermin inequality violation (local realism test)
2. Structural coherence λ-scan
3. N-dependence scaling analysis
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
import json

# Qiskit imports
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

# For IBM Quantum execution (optional)
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Options
    IBM_AVAILABLE = True
except ImportError:
    IBM_AVAILABLE = False
    print("Note: qiskit_ibm_runtime not available. Simulation mode only.")

# For simulation
try:
    from qiskit_aer import AerSimulator
    AER_AVAILABLE = True
except ImportError:
    AER_AVAILABLE = False


# =============================================================================
# THEORETICAL CONSTANTS
# =============================================================================

LAMBDA_3_STAR = 3 / (2 * np.pi**2)  # ≈ 0.15198 (geometric definition)
MERMIN_LOCAL_BOUND = 2.0            # Local realistic bound
MERMIN_QUANTUM_MAX = 4.0            # Quantum maximum for N=3


# =============================================================================
# CIRCUIT CREATION
# =============================================================================

def create_ghz_circuit(n_qubits: int) -> QuantumCircuit:
    """
    Create an N-qubit GHZ state: |GHZ⟩ = (|00...0⟩ + |11...1⟩) / √2
    
    Parameters
    ----------
    n_qubits : int
        Number of qubits (typically 3, 5, 7, or 9)
    
    Returns
    -------
    QuantumCircuit
        Circuit preparing the GHZ state (without measurement)
    """
    qc = QuantumCircuit(n_qubits, name=f'GHZ_{n_qubits}')
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    return qc


def create_mermin_circuit(n_qubits: int, basis: str) -> QuantumCircuit:
    """
    Create circuit for Mermin operator measurement in specified basis.
    
    Parameters
    ----------
    n_qubits : int
        Number of qubits
    basis : str
        Measurement basis string, e.g., 'XXX', 'XYY', 'YXY', 'YYX'
        'X' = measure in X basis (apply H before Z measurement)
        'Y' = measure in Y basis (apply S†H before Z measurement)
        'Z' = measure in Z basis (standard measurement)
    
    Returns
    -------
    QuantumCircuit
        Complete circuit with GHZ preparation and measurement
    """
    if len(basis) != n_qubits:
        raise ValueError(f"Basis string length {len(basis)} != n_qubits {n_qubits}")
    
    qc = QuantumCircuit(n_qubits, n_qubits, name=f'Mermin_{basis}')
    
    # Prepare GHZ state
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    
    qc.barrier()
    
    # Apply basis rotations
    for i, b in enumerate(basis):
        if b == 'X':
            qc.h(i)
        elif b == 'Y':
            qc.sdg(i)
            qc.h(i)
        elif b == 'Z':
            pass  # No rotation needed
        else:
            raise ValueError(f"Unknown basis '{b}'. Use 'X', 'Y', or 'Z'.")
    
    # Measure all qubits
    qc.measure(range(n_qubits), range(n_qubits))
    
    return qc


def create_lambda_scan_circuit(n_qubits: int, lambda_ctrl: float) -> QuantumCircuit:
    """
    Create circuit for λ-scan experiment.
    
    The control parameter λ_ctrl sets the phase of the entangling gate:
    θ = 2π × λ_ctrl
    
    Parameters
    ----------
    n_qubits : int
        Number of qubits
    lambda_ctrl : float
        Control parameter (0 to 1, structural coherence peaks at ~0.152)
    
    Returns
    -------
    QuantumCircuit
        Circuit with parameterized entanglement phase
    """
    qc = QuantumCircuit(n_qubits, n_qubits, name=f'Lambda_{lambda_ctrl:.3f}')
    
    theta = 2 * np.pi * lambda_ctrl
    
    # Prepare GHZ-like state with controlled phase
    qc.h(0)
    for i in range(n_qubits - 1):
        qc.cx(i, i + 1)
    
    # Apply global phase rotation (affects coherence measurement)
    qc.rz(theta, 0)
    
    # Measure in X basis to detect coherence
    for i in range(n_qubits):
        qc.h(i)
    qc.measure(range(n_qubits), range(n_qubits))
    
    return qc


# =============================================================================
# N=3 MERMIN EXPERIMENT
# =============================================================================

def get_mermin_bases_n3() -> List[str]:
    """Return the four measurement bases for N=3 Mermin inequality."""
    return ['XXX', 'XYY', 'YXY', 'YYX']


def create_mermin_circuits_n3() -> List[QuantumCircuit]:
    """Create all circuits needed for N=3 Mermin inequality test."""
    bases = get_mermin_bases_n3()
    return [create_mermin_circuit(3, basis) for basis in bases]


def compute_expectation(counts: Dict[str, int], n_qubits: int) -> float:
    """
    Compute expectation value from measurement counts.
    
    E = Σ (-1)^(parity) × P(outcome)
    
    where parity = number of 1s in the bitstring
    """
    total_shots = sum(counts.values())
    expectation = 0.0
    
    for bitstring, count in counts.items():
        parity = bitstring.count('1') % 2
        sign = (-1) ** parity
        expectation += sign * count / total_shots
    
    return expectation


def compute_mermin_parameter(expectations: Dict[str, float]) -> float:
    """
    Compute Mermin parameter M from expectation values.
    
    M = ⟨XXX⟩ - ⟨XYY⟩ - ⟨YXY⟩ - ⟨YYX⟩
    
    Local realistic bound: |M| ≤ 2
    Quantum maximum: |M| = 4 (for ideal GHZ)
    """
    return (expectations['XXX'] 
            - expectations['XYY'] 
            - expectations['YXY'] 
            - expectations['YYX'])


def compute_structural_coherence(mermin_value: float) -> float:
    """
    Compute normalized structural coherence from Mermin parameter.
    
    S̄₃ = (M - 2) / 2
    
    Range: 0 (local realistic) to 1 (maximum quantum)
    """
    return (mermin_value - MERMIN_LOCAL_BOUND) / 2


# =============================================================================
# N=5 MERMIN EXPERIMENT
# =============================================================================

def get_mermin_bases_n5() -> List[str]:
    """Return measurement bases for N=5 Mermin inequality."""
    return ['XXXXX', 'XXXYY', 'XXYXY', 'XXYYX', 'XYXXY']


def create_mermin_circuits_n5() -> List[QuantumCircuit]:
    """Create circuits for N=5 Mermin inequality test."""
    bases = get_mermin_bases_n5()
    return [create_mermin_circuit(5, basis) for basis in bases]


# =============================================================================
# IBM QUANTUM EXECUTION
# =============================================================================

def run_on_ibm_quantum(
    circuits: List[QuantumCircuit],
    backend_name: str = "ibm_torino",
    shots: int = 8192,
    optimization_level: int = 1
) -> Dict:
    """
    Execute circuits on IBM Quantum hardware.
    
    Parameters
    ----------
    circuits : List[QuantumCircuit]
        Circuits to execute
    backend_name : str
        IBM Quantum backend name
    shots : int
        Number of shots per circuit
    optimization_level : int
        Transpiler optimization level (0-3)
    
    Returns
    -------
    Dict
        Results including job_id, counts, and metadata
    """
    if not IBM_AVAILABLE:
        raise RuntimeError("qiskit_ibm_runtime not installed")
    
    # Initialize service
    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.backend(backend_name)
    
    print(f"Backend: {backend.name}")
    print(f"Qubits: {backend.num_qubits}")
    
    # Transpile
    transpiled = transpile(
        circuits, 
        backend, 
        optimization_level=optimization_level,
        seed_transpiler=42
    )
    
    # Execute
    options = Options()
    options.execution.shots = shots
    options.resilience_level = 1  # Enable error mitigation
    
    with Sampler(backend, options=options) as sampler:
        job = sampler.run(transpiled)
        print(f"Job ID: {job.job_id()}")
        print(f"Monitor: https://quantum.ibm.com/jobs/{job.job_id()}")
        result = job.result()
    
    return {
        'job_id': job.job_id(),
        'backend': backend_name,
        'shots': shots,
        'results': result
    }


# =============================================================================
# SIMULATION
# =============================================================================

def simulate_circuits(
    circuits: List[QuantumCircuit],
    shots: int = 8192,
    noise_model=None
) -> List[Dict[str, int]]:
    """
    Simulate circuits using Qiskit Aer.
    
    Parameters
    ----------
    circuits : List[QuantumCircuit]
        Circuits to simulate
    shots : int
        Number of shots per circuit
    noise_model : optional
        Qiskit noise model for realistic simulation
    
    Returns
    -------
    List[Dict[str, int]]
        List of count dictionaries
    """
    if not AER_AVAILABLE:
        raise RuntimeError("qiskit_aer not installed")
    
    simulator = AerSimulator(noise_model=noise_model)
    transpiled = transpile(circuits, simulator)
    
    results = []
    for qc in transpiled:
        job = simulator.run(qc, shots=shots)
        counts = job.result().get_counts()
        results.append(counts)
    
    return results


# =============================================================================
# ANALYSIS
# =============================================================================

def analyze_mermin_results(
    counts_list: List[Dict[str, int]],
    bases: List[str]
) -> Dict:
    """
    Analyze Mermin measurement results.
    
    Parameters
    ----------
    counts_list : List[Dict[str, int]]
        Count dictionaries for each basis
    bases : List[str]
        Basis strings corresponding to each circuit
    
    Returns
    -------
    Dict
        Analysis results including M, S̄₃, significance, etc.
    """
    n_qubits = len(bases[0])
    
    # Compute expectation values
    expectations = {}
    errors = {}
    
    for basis, counts in zip(bases, counts_list):
        exp_val = compute_expectation(counts, n_qubits)
        total_shots = sum(counts.values())
        # Standard error for binomial proportion
        err = np.sqrt((1 - exp_val**2) / total_shots)
        expectations[basis] = exp_val
        errors[basis] = err
    
    # Compute Mermin parameter
    M = compute_mermin_parameter(expectations)
    
    # Error propagation
    M_err = np.sqrt(sum(errors[b]**2 for b in bases))
    
    # Structural coherence
    S_bar = compute_structural_coherence(M)
    
    # Statistical significance of violation
    sigma = (M - MERMIN_LOCAL_BOUND) / M_err
    
    return {
        'n_qubits': n_qubits,
        'expectations': expectations,
        'errors': errors,
        'mermin_parameter': M,
        'mermin_error': M_err,
        'structural_coherence': S_bar,
        'violation_sigma': sigma,
        'lambda_3_star': LAMBDA_3_STAR,
        'local_bound': MERMIN_LOCAL_BOUND
    }


def print_analysis_report(results: Dict):
    """Print formatted analysis report."""
    print("\n" + "=" * 60)
    print(f"  N={results['n_qubits']} GHZ MERMIN ANALYSIS REPORT")
    print("=" * 60)
    
    print("\n--- Expectation Values ---")
    for basis, exp in results['expectations'].items():
        err = results['errors'][basis]
        print(f"  ⟨{basis}⟩ = {exp:+.4f} ± {err:.4f}")
    
    print("\n--- Mermin Inequality ---")
    M = results['mermin_parameter']
    M_err = results['mermin_error']
    print(f"  M = {M:.3f} ± {M_err:.3f}")
    print(f"  Local bound: |M| ≤ {results['local_bound']}")
    print(f"  Quantum max: |M| = 4.0")
    
    print("\n--- Violation Analysis ---")
    sigma = results['violation_sigma']
    print(f"  Violation: {M - results['local_bound']:.3f}")
    print(f"  Significance: {sigma:.1f}σ")
    
    if sigma > 3:
        print(f"  ✓ Local realism RULED OUT (>{sigma:.0f}σ)")
    
    print("\n--- Structural Coherence ---")
    S = results['structural_coherence']
    print(f"  S̄₃ = (M - 2)/2 = {S:.4f}")
    print(f"  λ₃* (geometric) = {results['lambda_3_star']:.5f}")
    
    print("=" * 60 + "\n")


# =============================================================================
# MAIN EXAMPLE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  STRUCTURAL COHERENCE GHZ EXPERIMENT")
    print("  Supporting: Emergent Structural Gravity")
    print("=" * 60)
    
    # Create N=3 Mermin circuits
    circuits = create_mermin_circuits_n3()
    bases = get_mermin_bases_n3()
    
    print(f"\nCreated {len(circuits)} circuits for N=3 Mermin test")
    for i, (qc, basis) in enumerate(zip(circuits, bases)):
        print(f"  Circuit {i+1}: {basis}")
    
    # Simulate
    if AER_AVAILABLE:
        print("\nRunning simulation (ideal)...")
        counts_list = simulate_circuits(circuits, shots=8192)
        
        # Analyze
        results = analyze_mermin_results(counts_list, bases)
        print_analysis_report(results)
    else:
        print("\nNote: Install qiskit-aer to run simulations")
        print("  pip install qiskit-aer")
    
    print("\nTo run on IBM Quantum hardware:")
    print("  1. Set up IBM Quantum account")
    print("  2. Save credentials: QiskitRuntimeService.save_account(...)")
    print("  3. Call: run_on_ibm_quantum(circuits)")
