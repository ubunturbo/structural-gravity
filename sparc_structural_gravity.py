# =============================================================================
# SPARC Galaxy Rotation Curve Fitting with Structural Gravity
# Supporting code for: "Emergent Structural Gravity from Entanglement Time"
# Author: Takayuki Takagi (lemissio@gmail.com)
# License: MIT
# =============================================================================

"""
This module fits galactic rotation curves from the SPARC database using
the structural gravity framework, which predicts:

    v_c(r) = sqrt(v_baryon²(r) + v_struct²)

where v_struct is a constant structural velocity arising from the
logarithmic Logos field profile.

Key features:
- Single free parameter per galaxy (v_struct)
- No dark matter particles required
- Reproduces baryonic Tully-Fisher relation
"""

import numpy as np
from scipy.optimize import curve_fit, minimize
from scipy.stats import chi2
from typing import Tuple, Dict, List, Optional
import warnings

# =============================================================================
# THEORETICAL CONSTANTS
# =============================================================================

LAMBDA_3_STAR = 3 / (2 * np.pi**2)  # ≈ 0.15198
G_NEWTON = 4.302e-6  # kpc (km/s)² / M_sun


# =============================================================================
# STRUCTURAL GRAVITY MODEL
# =============================================================================

def v_structural_gravity(
    r: np.ndarray,
    v_baryon: np.ndarray,
    v_struct: float
) -> np.ndarray:
    """
    Compute total rotation velocity in structural gravity framework.
    
    v_c(r) = sqrt(v_baryon²(r) + v_struct²)
    
    Parameters
    ----------
    r : np.ndarray
        Radial positions [kpc]
    v_baryon : np.ndarray
        Baryonic contribution to rotation velocity [km/s]
    v_struct : float
        Structural velocity parameter [km/s]
    
    Returns
    -------
    np.ndarray
        Total circular velocity [km/s]
    """
    return np.sqrt(v_baryon**2 + v_struct**2)


def v_logarithmic_halo(
    r: np.ndarray,
    v_baryon: np.ndarray,
    v_inf: float,
    r_c: float
) -> np.ndarray:
    """
    Alternative: Logarithmic halo profile (for comparison).
    
    v_halo²(r) = v_inf² × r² / (r² + r_c²)
    """
    v_halo_sq = v_inf**2 * r**2 / (r**2 + r_c**2)
    return np.sqrt(v_baryon**2 + v_halo_sq)


# =============================================================================
# FITTING FUNCTIONS
# =============================================================================

def fit_structural_gravity(
    r: np.ndarray,
    v_obs: np.ndarray,
    v_err: np.ndarray,
    v_baryon: np.ndarray,
    v_struct_init: float = 100.0
) -> Dict:
    """
    Fit rotation curve with structural gravity model.
    
    Parameters
    ----------
    r : np.ndarray
        Radial positions [kpc]
    v_obs : np.ndarray
        Observed rotation velocities [km/s]
    v_err : np.ndarray
        Velocity uncertainties [km/s]
    v_baryon : np.ndarray
        Baryonic contribution [km/s]
    v_struct_init : float
        Initial guess for v_struct [km/s]
    
    Returns
    -------
    Dict
        Fitting results including v_struct, chi2, etc.
    """
    def model(v_bar, v_s):
        return np.sqrt(v_bar**2 + v_s**2)
    
    def chi2_func(v_struct):
        v_model = model(v_baryon, v_struct)
        residuals = (v_obs - v_model) / v_err
        return np.sum(residuals**2)
    
    # Optimize
    from scipy.optimize import minimize_scalar
    result = minimize_scalar(
        chi2_func, 
        bounds=(0, 500), 
        method='bounded'
    )
    
    v_struct_best = result.x
    chi2_best = result.fun
    
    # Degrees of freedom
    n_points = len(r)
    n_params = 1  # Only v_struct
    dof = n_points - n_params
    
    # Reduced chi-squared
    chi2_reduced = chi2_best / dof if dof > 0 else np.inf
    
    # P-value
    p_value = 1 - chi2.cdf(chi2_best, dof) if dof > 0 else 0
    
    # Model velocities
    v_model = model(v_baryon, v_struct_best)
    
    # Residuals
    residuals = v_obs - v_model
    
    return {
        'v_struct': v_struct_best,
        'chi2': chi2_best,
        'chi2_reduced': chi2_reduced,
        'dof': dof,
        'p_value': p_value,
        'v_model': v_model,
        'residuals': residuals,
        'n_points': n_points
    }


def fit_nfw_halo(
    r: np.ndarray,
    v_obs: np.ndarray,
    v_err: np.ndarray,
    v_baryon: np.ndarray
) -> Dict:
    """
    Fit rotation curve with NFW dark matter halo (for comparison).
    
    v_NFW²(r) = v_200² × [ln(1 + r/r_s) - (r/r_s)/(1 + r/r_s)] / 
                         [r/r_s × (ln(1 + c) - c/(1 + c))]
    
    Two free parameters: v_200, r_s (or equivalently M_200, c)
    """
    def nfw_velocity(r, v_200, r_s):
        x = r / r_s
        c = 10.0  # Typical concentration
        f_c = np.log(1 + c) - c / (1 + c)
        f_x = np.log(1 + x) - x / (1 + x)
        # Avoid division by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            v_nfw_sq = v_200**2 * f_x / (x * f_c)
            v_nfw_sq = np.where(x > 0, v_nfw_sq, 0)
        return np.sqrt(v_baryon**2 + np.maximum(v_nfw_sq, 0))
    
    try:
        popt, pcov = curve_fit(
            nfw_velocity, r, v_obs, 
            p0=[150, 10],
            sigma=v_err,
            bounds=([0, 0.1], [500, 100]),
            maxfev=5000
        )
        
        v_model = nfw_velocity(r, *popt)
        chi2_val = np.sum(((v_obs - v_model) / v_err)**2)
        dof = len(r) - 2
        
        return {
            'v_200': popt[0],
            'r_s': popt[1],
            'chi2': chi2_val,
            'chi2_reduced': chi2_val / dof if dof > 0 else np.inf,
            'dof': dof,
            'v_model': v_model,
            'n_params': 2
        }
    except Exception as e:
        return {
            'error': str(e),
            'chi2_reduced': np.inf
        }


# =============================================================================
# SPARC DATA HANDLING
# =============================================================================

def load_sparc_galaxy(filepath: str) -> Dict:
    """
    Load a single SPARC galaxy data file.
    
    Expected format (space-separated):
    r  v_obs  v_err  v_gas  v_disk  v_bulge
    
    Parameters
    ----------
    filepath : str
        Path to SPARC data file
    
    Returns
    -------
    Dict
        Galaxy data dictionary
    """
    data = np.loadtxt(filepath)
    
    return {
        'r': data[:, 0],           # kpc
        'v_obs': data[:, 1],       # km/s
        'v_err': data[:, 2],       # km/s
        'v_gas': data[:, 3],       # km/s
        'v_disk': data[:, 4],      # km/s
        'v_bulge': data[:, 5] if data.shape[1] > 5 else np.zeros_like(data[:, 0])
    }


def compute_baryonic_velocity(
    v_gas: np.ndarray,
    v_disk: np.ndarray,
    v_bulge: np.ndarray,
    upsilon_disk: float = 0.5,
    upsilon_bulge: float = 0.7
) -> np.ndarray:
    """
    Compute total baryonic contribution to rotation velocity.
    
    v_baryon² = v_gas² + Υ_disk × v_disk² + Υ_bulge × v_bulge²
    
    Parameters
    ----------
    v_gas : np.ndarray
        Gas contribution [km/s]
    v_disk : np.ndarray
        Disk contribution (at Υ=1) [km/s]
    v_bulge : np.ndarray
        Bulge contribution (at Υ=1) [km/s]
    upsilon_disk : float
        Disk mass-to-light ratio [M_sun/L_sun]
    upsilon_bulge : float
        Bulge mass-to-light ratio [M_sun/L_sun]
    
    Returns
    -------
    np.ndarray
        Total baryonic velocity [km/s]
    """
    v_bar_sq = (v_gas**2 + 
                upsilon_disk * np.sign(v_disk) * v_disk**2 + 
                upsilon_bulge * np.sign(v_bulge) * v_bulge**2)
    return np.sqrt(np.maximum(v_bar_sq, 0))


# =============================================================================
# MODEL COMPARISON
# =============================================================================

def compute_aic(chi2: float, n_params: int, n_points: int) -> float:
    """Compute Akaike Information Criterion."""
    return chi2 + 2 * n_params


def compute_bic(chi2: float, n_params: int, n_points: int) -> float:
    """Compute Bayesian Information Criterion."""
    return chi2 + n_params * np.log(n_points)


def compare_models(
    r: np.ndarray,
    v_obs: np.ndarray,
    v_err: np.ndarray,
    v_baryon: np.ndarray
) -> Dict:
    """
    Compare structural gravity with NFW halo fit.
    
    Returns
    -------
    Dict
        Comparison statistics including AIC, BIC, chi2
    """
    # Fit structural gravity
    sg_result = fit_structural_gravity(r, v_obs, v_err, v_baryon)
    
    # Fit NFW
    nfw_result = fit_nfw_halo(r, v_obs, v_err, v_baryon)
    
    n_points = len(r)
    
    # Compute information criteria
    sg_aic = compute_aic(sg_result['chi2'], 1, n_points)
    sg_bic = compute_bic(sg_result['chi2'], 1, n_points)
    
    if 'chi2' in nfw_result:
        nfw_aic = compute_aic(nfw_result['chi2'], 2, n_points)
        nfw_bic = compute_bic(nfw_result['chi2'], 2, n_points)
    else:
        nfw_aic = np.inf
        nfw_bic = np.inf
    
    return {
        'structural_gravity': {
            **sg_result,
            'AIC': sg_aic,
            'BIC': sg_bic,
            'n_params': 1
        },
        'nfw': {
            **nfw_result,
            'AIC': nfw_aic,
            'BIC': nfw_bic
        },
        'delta_AIC': sg_aic - nfw_aic,
        'delta_BIC': sg_bic - nfw_bic,
        'preferred': 'structural_gravity' if sg_aic < nfw_aic else 'nfw'
    }


# =============================================================================
# TULLY-FISHER ANALYSIS
# =============================================================================

def baryonic_tully_fisher(
    v_flat: np.ndarray,
    M_baryon: np.ndarray
) -> Dict:
    """
    Analyze baryonic Tully-Fisher relation.
    
    Structural gravity predicts: v^4 ∝ M_baryon
    
    Parameters
    ----------
    v_flat : np.ndarray
        Flat rotation velocities [km/s]
    M_baryon : np.ndarray
        Baryonic masses [M_sun]
    
    Returns
    -------
    Dict
        TF relation fit parameters
    """
    # Fit log(v) = a + b × log(M)
    log_v = np.log10(v_flat)
    log_M = np.log10(M_baryon)
    
    # Linear regression
    coeffs = np.polyfit(log_M, log_v, 1)
    slope = coeffs[0]
    intercept = coeffs[1]
    
    # Structural gravity predicts slope = 0.25 (since v^4 ∝ M → v ∝ M^{1/4})
    expected_slope = 0.25
    
    # Residuals
    log_v_pred = np.polyval(coeffs, log_M)
    residuals = log_v - log_v_pred
    rms = np.sqrt(np.mean(residuals**2))
    
    return {
        'slope': slope,
        'intercept': intercept,
        'expected_slope': expected_slope,
        'slope_deviation': slope - expected_slope,
        'rms_scatter': rms,
        'log_v_predicted': log_v_pred
    }


# =============================================================================
# VISUALIZATION
# =============================================================================

def plot_rotation_curve(
    r: np.ndarray,
    v_obs: np.ndarray,
    v_err: np.ndarray,
    v_baryon: np.ndarray,
    fit_result: Dict,
    galaxy_name: str = "Galaxy",
    save_path: Optional[str] = None
):
    """
    Plot rotation curve with structural gravity fit.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available for plotting")
        return
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Observed data
    ax.errorbar(r, v_obs, yerr=v_err, fmt='ko', markersize=6, 
                capsize=2, label='Observed', zorder=3)
    
    # Baryonic contribution
    ax.plot(r, v_baryon, 'b--', linewidth=1.5, label='Baryons only')
    
    # Structural gravity fit
    v_struct = fit_result['v_struct']
    v_total = np.sqrt(v_baryon**2 + v_struct**2)
    ax.plot(r, v_total, 'r-', linewidth=2, 
            label=f'Structural gravity ($v_{{struct}}$ = {v_struct:.0f} km/s)')
    
    # Structural contribution (horizontal)
    ax.axhline(v_struct, color='gray', linestyle=':', alpha=0.5)
    
    ax.set_xlabel('Radius (kpc)', fontsize=12)
    ax.set_ylabel('$v_c$ (km/s)', fontsize=12)
    ax.set_title(f'{galaxy_name}\n$\\chi^2_\\nu$ = {fit_result["chi2_reduced"]:.2f}', 
                 fontsize=12)
    ax.legend(loc='lower right')
    ax.set_xlim(0, max(r) * 1.1)
    ax.set_ylim(0, max(v_obs) * 1.3)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    plt.show()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  STRUCTURAL GRAVITY ROTATION CURVE FITTING")
    print("  Supporting: Emergent Structural Gravity from Entanglement Time")
    print("=" * 60)
    
    # Create example data (NGC 2903-like)
    print("\n--- Example: NGC 2903-like galaxy ---")
    
    r = np.array([1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23])
    v_obs = np.array([120, 175, 195, 200, 198, 195, 192, 190, 188, 186, 185, 184])
    v_err = np.array([8, 10, 10, 8, 8, 7, 7, 8, 9, 10, 10, 12])
    v_baryon = np.array([100, 145, 160, 158, 150, 140, 130, 120, 110, 100, 92, 85])
    
    # Fit structural gravity
    result = fit_structural_gravity(r, v_obs, v_err, v_baryon)
    
    print(f"\nResults:")
    print(f"  v_struct = {result['v_struct']:.1f} km/s")
    print(f"  χ² = {result['chi2']:.2f}")
    print(f"  χ²_ν = {result['chi2_reduced']:.3f}")
    print(f"  DOF = {result['dof']}")
    print(f"  p-value = {result['p_value']:.3f}")
    
    # Compare with NFW
    print("\n--- Model Comparison ---")
    comparison = compare_models(r, v_obs, v_err, v_baryon)
    
    print(f"\nStructural Gravity:")
    print(f"  χ²_ν = {comparison['structural_gravity']['chi2_reduced']:.3f}")
    print(f"  AIC = {comparison['structural_gravity']['AIC']:.1f}")
    print(f"  Parameters: 1")
    
    if 'chi2_reduced' in comparison['nfw']:
        print(f"\nNFW Halo:")
        print(f"  χ²_ν = {comparison['nfw']['chi2_reduced']:.3f}")
        print(f"  AIC = {comparison['nfw']['AIC']:.1f}")
        print(f"  Parameters: 2")
    
    print(f"\nPreferred model: {comparison['preferred']}")
    print(f"ΔAIC = {comparison['delta_AIC']:.1f}")
    
    print("\n" + "=" * 60)
    print("Note: For real SPARC data, download from:")
    print("  http://astroweb.cwru.edu/SPARC/")
    print("=" * 60)
