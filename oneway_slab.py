"""
One-Way Reinforced Concrete Slab Design Module
Per ACI 318-19 (Building Code Requirements for Structural Concrete)

Design checks:
1. Flexural strength (§22.2)
2. Shear strength (§22.5)
3. Minimum thickness / Deflection control (§7.3.1, §24.2)
4. Minimum reinforcement (§7.6)
5. Maximum reinforcement (§9.3.3)
6. Shrinkage and temperature reinforcement (§24.4)
7. Spacing limits (§7.7.2)

Author: CompositeBeamPro
Version: 1.0
"""

import math
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class SlabGeometry:
    """Slab geometry parameters"""
    L: float  # Span length (mm)
    tc: float  # Total thickness (mm)
    cover: float  # Clear cover (mm)
    bar_dia: float  # Main reinforcement diameter (mm)
    d: float  # Effective depth (mm)
    b: float  # Design width (mm), typically 1000mm for per-meter design


@dataclass
class SlabMaterials:
    """Material properties"""
    fc: float  # Concrete compressive strength (MPa)
    fy: float  # Reinforcement yield strength (MPa)
    Es: float  # Steel modulus (MPa)
    Ec: float  # Concrete modulus (MPa)
    n: float  # Modular ratio
    fr: float  # Modulus of rupture (MPa)
    beta1: float  # Stress block factor
    lambda_factor: float  # Lightweight factor (1.0 for normal weight)


def calc_materials(fc: float, fy: float, wc: float = 2400) -> SlabMaterials:
    """
    Calculate material properties per ACI 318-19
    
    Parameters:
    -----------
    fc : float
        Concrete compressive strength (MPa)
    fy : float
        Reinforcement yield strength (MPa)
    wc : float
        Concrete unit weight (kg/m³)
    
    Returns:
    --------
    SlabMaterials object
    """
    Es = 200000  # MPa
    
    # Ec per ACI 318-19 §19.2.2.1
    if wc >= 1440 and wc <= 2560:
        Ec = 0.043 * wc**1.5 * math.sqrt(fc)  # MPa
    else:
        Ec = 4700 * math.sqrt(fc)  # Normal weight approximation
    
    n = Es / Ec
    
    # Modulus of rupture (§19.2.3.1)
    lambda_factor = 1.0  # Normal weight concrete
    fr = 0.62 * lambda_factor * math.sqrt(fc)
    
    # β1 per ACI 318-19 Table 22.2.2.4.3
    if fc <= 28:
        beta1 = 0.85
    elif fc >= 55:
        beta1 = 0.65
    else:
        beta1 = 0.85 - 0.05 * (fc - 28) / 7
    
    return SlabMaterials(
        fc=fc,
        fy=fy,
        Es=Es,
        Ec=Ec,
        n=n,
        fr=fr,
        beta1=beta1,
        lambda_factor=lambda_factor
    )


@dataclass
class MomentCoefficients:
    """Moment coefficients per ACI 318-19 §6.5"""
    positive: float
    negative_int: float  # Negative at first interior support
    negative_ext: float  # Negative at exterior support
    span_type: str


def get_moment_coefficients(span_type: str) -> MomentCoefficients:
    """
    Get moment coefficients per ACI 318-19 §6.5 (approximate method)
    
    Parameters:
    -----------
    span_type : str
        "Simple", "One End Continuous", "Both Ends Continuous", "Cantilever"
    
    Returns:
    --------
    MomentCoefficients object
    """
    if span_type == "Simple":
        return MomentCoefficients(
            positive=1/8,
            negative_int=0,
            negative_ext=0,
            span_type=span_type
        )
    elif span_type == "One End Continuous":
        return MomentCoefficients(
            positive=1/14,  # End span
            negative_int=1/10,  # First interior
            negative_ext=1/24,  # Exterior support with restraint
            span_type=span_type
        )
    elif span_type == "Both Ends Continuous":
        return MomentCoefficients(
            positive=1/16,  # Interior span
            negative_int=1/11,  # Interior supports
            negative_ext=0,
            span_type=span_type
        )
    elif span_type == "Cantilever":
        return MomentCoefficients(
            positive=0,
            negative_int=0,
            negative_ext=1/2,  # M = wL²/2 at fixed end
            span_type=span_type
        )
    else:
        # Default to simple span
        return MomentCoefficients(
            positive=1/8,
            negative_int=0,
            negative_ext=0,
            span_type="Simple"
        )


@dataclass
class FlexuralDesign:
    """Flexural design results"""
    Mu: float  # Factored moment (kN-m/m)
    Mn_req: float  # Required nominal moment (kN-m/m)
    
    rho_req: float  # Required reinforcement ratio
    rho_min: float  # Minimum reinforcement ratio
    rho_max: float  # Maximum reinforcement ratio
    rho_provided: float  # Provided reinforcement ratio
    
    As_req: float  # Required steel area (mm²/m)
    As_min: float  # Minimum steel area (mm²/m)
    As_provided: float  # Provided steel area (mm²/m)
    
    a: float  # Stress block depth (mm)
    c: float  # Neutral axis depth (mm)
    phi: float  # Strength reduction factor
    
    epsilon_t: float  # Tensile strain in steel
    section_type: str  # "Tension-controlled", "Transition", "Compression-controlled"
    
    phi_Mn: float  # Design moment capacity (kN-m/m)
    DCR: float  # Demand/Capacity ratio
    
    bar_dia: float  # Bar diameter (mm)
    spacing: float  # Bar spacing (mm)
    spacing_ok: bool  # Spacing within limits


def design_flexure(geom: SlabGeometry, mat: SlabMaterials, 
                   Mu: float, As_provided: float = None,
                   bar_dia: float = 12) -> FlexuralDesign:
    """
    Design slab for flexure per ACI 318-19
    
    Parameters:
    -----------
    geom : SlabGeometry
        Slab geometry
    mat : SlabMaterials
        Material properties
    Mu : float
        Factored moment (kN-m/m)
    As_provided : float
        Provided reinforcement (mm²/m), if None will calculate required
    bar_dia : float
        Reinforcement bar diameter (mm)
    
    Returns:
    --------
    FlexuralDesign object
    """
    b = geom.b  # 1000 mm for per-meter design
    d = geom.d
    tc = geom.tc
    fc = mat.fc
    fy = mat.fy
    beta1 = mat.beta1
    
    # Required nominal moment
    phi_assumed = 0.90  # Assume tension-controlled initially
    Mn_req = Mu / phi_assumed  # kN-m/m
    
    # Calculate required reinforcement ratio
    # From Mn = As*fy*(d - a/2) and a = As*fy/(0.85*fc*b)
    # Quadratic solution for rho
    
    Mn_req_Nmm = Mn_req * 1e6  # Convert to N-mm/m
    
    # Coefficient for quadratic
    Rn = Mn_req_Nmm / (b * d**2)  # N/mm²
    
    # rho = (0.85*fc/fy) * (1 - sqrt(1 - 2*Rn/(0.85*fc)))
    term = 2 * Rn / (0.85 * fc)
    if term >= 1.0:
        # Section is inadequate, need more depth
        rho_req = 0.999
    else:
        rho_req = (0.85 * fc / fy) * (1 - math.sqrt(1 - term))
    
    # Minimum reinforcement per ACI 318-19 Table 7.6.1.1
    if fy <= 420:
        rho_min = 0.0020
    elif fy >= 500:
        rho_min = max(0.0018 * 420 / fy, 0.0014)
    else:
        rho_min = 0.0018
    
    As_min = rho_min * b * tc  # Based on total thickness
    
    # Maximum reinforcement per ACI 318-19 §9.3.3.1
    # Strain limit: εt ≥ 0.004 for tension-controlled
    epsilon_cu = 0.003
    epsilon_t_min = 0.004
    
    c_max = d * epsilon_cu / (epsilon_cu + epsilon_t_min)
    a_max = beta1 * c_max
    rho_max = 0.85 * fc * beta1 * (epsilon_cu / (epsilon_cu + epsilon_t_min)) / fy
    
    As_max = rho_max * b * d
    
    # Required steel area
    As_req = max(rho_req * b * d, As_min)
    
    # Provided reinforcement
    if As_provided is None:
        As_provided = As_req
    
    rho_provided = As_provided / (b * d)
    
    # Calculate actual capacity
    a = As_provided * fy / (0.85 * fc * b)
    c = a / beta1
    
    # Check strain
    epsilon_t = epsilon_cu * (d - c) / c if c > 0 else 999
    
    # Determine phi based on strain (Table 21.2.2)
    if epsilon_t >= 0.005:
        phi = 0.90
        section_type = "Tension-controlled"
    elif epsilon_t <= 0.002:
        phi = 0.65
        section_type = "Compression-controlled"
    else:
        phi = 0.65 + (epsilon_t - 0.002) * (0.90 - 0.65) / (0.005 - 0.002)
        section_type = "Transition"
    
    # Nominal and design moment capacity
    Mn = As_provided * fy * (d - a/2) / 1e6  # kN-m/m
    phi_Mn = phi * Mn
    
    DCR = Mu / phi_Mn if phi_Mn > 0 else 999
    
    # Bar spacing
    Ab = math.pi * bar_dia**2 / 4
    n_bars = As_provided / Ab
    spacing = b / n_bars if n_bars > 0 else 999
    
    # Spacing limits per ACI 318-19 §7.7.2.3
    s_max = min(3 * tc, 450)  # mm
    spacing_ok = spacing <= s_max
    
    return FlexuralDesign(
        Mu=Mu,
        Mn_req=Mn_req,
        rho_req=rho_req,
        rho_min=rho_min,
        rho_max=rho_max,
        rho_provided=rho_provided,
        As_req=As_req,
        As_min=As_min,
        As_provided=As_provided,
        a=a,
        c=c,
        phi=phi,
        epsilon_t=epsilon_t,
        section_type=section_type,
        phi_Mn=phi_Mn,
        DCR=DCR,
        bar_dia=bar_dia,
        spacing=spacing,
        spacing_ok=spacing_ok
    )


@dataclass
class ShearCheck:
    """Shear design results"""
    Vu: float  # Factored shear at critical section (kN/m)
    Vc: float  # Nominal concrete shear strength (kN/m)
    phi_Vc: float  # Design shear capacity (kN/m)
    DCR: float
    ok: bool
    critical_location: float  # Distance from face of support (mm)


def check_shear(geom: SlabGeometry, mat: SlabMaterials, 
                wu: float, Ln: float) -> ShearCheck:
    """
    Check shear strength per ACI 318-19 §22.5
    
    Parameters:
    -----------
    geom : SlabGeometry
        Slab geometry
    mat : SlabMaterials
        Material properties
    wu : float
        Factored uniform load (kN/m²)
    Ln : float
        Clear span (mm)
    
    Returns:
    --------
    ShearCheck object
    """
    b = geom.b
    d = geom.d
    fc = mat.fc
    lambda_factor = mat.lambda_factor
    
    # Critical section at d from face of support
    critical_location = d
    
    # Shear at critical section
    Vu_face = wu * Ln / 2 / 1000  # kN/m at face
    Vu = Vu_face - wu * d / 1000  # kN/m at d from face
    
    # Concrete shear strength per ACI 318-19 §22.5.5.1
    # Vc = 0.17 * lambda * sqrt(fc) * bw * d (SI units)
    Vc = 0.17 * lambda_factor * math.sqrt(fc) * b * d / 1000  # kN/m
    
    phi_v = 0.75
    phi_Vc = phi_v * Vc
    
    DCR = Vu / phi_Vc if phi_Vc > 0 else 999
    
    return ShearCheck(
        Vu=Vu,
        Vc=Vc,
        phi_Vc=phi_Vc,
        DCR=DCR,
        ok=DCR <= 1.0,
        critical_location=critical_location
    )


@dataclass
class DeflectionCheck:
    """Deflection check results"""
    h_min: float  # Minimum thickness per Table 7.3.1.1 (mm)
    h_provided: float  # Provided thickness (mm)
    thickness_ok: bool  # Meets minimum thickness?
    
    # Calculated deflection (if thickness doesn't meet minimum)
    Ig: float  # Gross moment of inertia (mm⁴/m)
    Icr: float  # Cracked moment of inertia (mm⁴/m)
    Ie: float  # Effective moment of inertia (mm⁴/m)
    
    Mcr: float  # Cracking moment (kN-m/m)
    Ma: float  # Service moment (kN-m/m)
    
    delta_i: float  # Immediate deflection (mm)
    delta_lt: float  # Long-term deflection (mm)
    delta_total: float  # Total deflection (mm)
    
    delta_limit: float  # Deflection limit (mm)
    DCR: float


def check_deflection(geom: SlabGeometry, mat: SlabMaterials, 
                     span_type: str, Ln: float, 
                     w_service: float, As: float,
                     duration_months: int = 60) -> DeflectionCheck:
    """
    Check deflection per ACI 318-19 §24.2
    
    Parameters:
    -----------
    geom : SlabGeometry
        Slab geometry
    mat : SlabMaterials
        Material properties
    span_type : str
        Support condition
    Ln : float
        Clear span (mm)
    w_service : float
        Service load (kN/m²)
    As : float
        Tension reinforcement area (mm²/m)
    duration_months : int
        Load duration in months (for long-term factor)
    
    Returns:
    --------
    DeflectionCheck object
    """
    tc = geom.tc
    d = geom.d
    b = geom.b
    Ec = mat.Ec
    fr = mat.fr
    n = mat.n
    
    # Minimum thickness per ACI Table 7.3.1.1
    if span_type == "Simple":
        h_min = Ln / 20
    elif span_type == "One End Continuous":
        h_min = Ln / 24
    elif span_type == "Both Ends Continuous":
        h_min = Ln / 28
    elif span_type == "Cantilever":
        h_min = Ln / 10
    else:
        h_min = Ln / 20
    
    thickness_ok = tc >= h_min
    
    # Gross moment of inertia
    Ig = b * tc**3 / 12  # mm⁴/m
    
    # Distance to centroid from tension face
    yt = tc / 2
    
    # Cracking moment (§24.2.3.5)
    Mcr = fr * Ig / yt / 1e6  # kN-m/m
    
    # Service moment (approximate)
    coef = get_moment_coefficients(span_type)
    Ma = w_service * (Ln/1000)**2 * coef.positive  # kN-m/m
    
    # Cracked moment of inertia
    # Find neutral axis: b*c²/2 = n*As*(d-c)
    # Solve quadratic: b*c² + 2*n*As*c - 2*n*As*d = 0
    a_coef = b / 2
    b_coef = n * As
    c_coef = -n * As * d
    
    discriminant = b_coef**2 - 4 * a_coef * c_coef
    if discriminant >= 0:
        c_cr = (-b_coef + math.sqrt(discriminant)) / (2 * a_coef)
    else:
        c_cr = d / 3  # Approximation
    
    Icr = b * c_cr**3 / 3 + n * As * (d - c_cr)**2  # mm⁴/m
    
    # Effective moment of inertia (§24.2.3.5)
    if Ma <= 0:
        Ie = Ig
    else:
        Mcr_Ma_ratio = Mcr / Ma
        if Mcr_Ma_ratio > 1.0:
            Ie = Ig
        else:
            Ie = (Mcr_Ma_ratio)**3 * Ig + (1 - (Mcr_Ma_ratio)**3) * Icr
            Ie = min(Ie, Ig)
    
    # Immediate deflection
    # δ = 5*w*L⁴ / (384*E*I) for uniform load, simple span
    w_N_mm = w_service / 1e6  # kN/m² to N/mm²
    
    if span_type == "Simple":
        delta_i = 5 * w_N_mm * b * Ln**4 / (384 * Ec * Ie) if Ie > 0 else 999
    elif span_type == "Cantilever":
        delta_i = w_N_mm * b * Ln**4 / (8 * Ec * Ie) if Ie > 0 else 999
    else:
        # Continuous spans - use 0.4 factor approximately
        delta_i = 0.4 * 5 * w_N_mm * b * Ln**4 / (384 * Ec * Ie) if Ie > 0 else 999
    
    # Long-term deflection factor λΔ (§24.2.4.1)
    # λΔ = ξ / (1 + 50*ρ')
    # ρ' = compression reinforcement ratio (assume 0 for slabs)
    rho_prime = 0
    
    if duration_months <= 3:
        xi = 1.0
    elif duration_months <= 6:
        xi = 1.2
    elif duration_months <= 12:
        xi = 1.4
    else:
        xi = 2.0
    
    lambda_delta = xi / (1 + 50 * rho_prime)
    
    delta_lt = delta_i * lambda_delta
    delta_total = delta_i + delta_lt
    
    # Deflection limit (Table 24.2.2)
    # For floors not supporting partitions: L/240
    delta_limit = Ln / 240
    
    DCR = delta_total / delta_limit if delta_limit > 0 else 999
    
    return DeflectionCheck(
        h_min=h_min,
        h_provided=tc,
        thickness_ok=thickness_ok,
        Ig=Ig,
        Icr=Icr,
        Ie=Ie,
        Mcr=Mcr,
        Ma=Ma,
        delta_i=delta_i,
        delta_lt=delta_lt,
        delta_total=delta_total,
        delta_limit=delta_limit,
        DCR=DCR
    )


@dataclass 
class ShrinkageTempReinf:
    """Shrinkage and temperature reinforcement per ACI 318-19 §24.4"""
    As_req: float  # Required area (mm²/m)
    rho_min: float  # Minimum ratio
    s_max: float  # Maximum spacing (mm)


def calc_shrinkage_temp(tc: float, fy: float) -> ShrinkageTempReinf:
    """
    Calculate shrinkage and temperature reinforcement per ACI 318-19 §24.4
    
    Parameters:
    -----------
    tc : float
        Total slab thickness (mm)
    fy : float
        Reinforcement yield strength (MPa)
    
    Returns:
    --------
    ShrinkageTempReinf object
    """
    b = 1000  # Per meter width
    
    # Per Table 24.4.3.2
    if fy < 420:
        rho_min = 0.0020
    elif fy >= 420:
        rho_min = max(0.0018 * 420 / fy, 0.0014)
    else:
        rho_min = 0.0018
    
    As_req = rho_min * b * tc
    
    # Maximum spacing per §24.4.3.3
    s_max = min(5 * tc, 450)
    
    return ShrinkageTempReinf(
        As_req=As_req,
        rho_min=rho_min,
        s_max=s_max
    )


@dataclass
class OneWaySlabResults:
    """Complete one-way slab design results"""
    # Geometry
    geometry: SlabGeometry
    materials: SlabMaterials
    span_type: str
    Ln: float  # Clear span (mm)
    
    # Loading
    w_DL: float  # Dead load (kN/m²)
    w_SDL: float  # Superimposed dead (kN/m²)
    w_LL: float  # Live load (kN/m²)
    wu: float  # Factored load (kN/m²)
    w_service: float  # Service load (kN/m²)
    
    # Moments
    Mu_pos: float  # Factored positive moment (kN-m/m)
    Mu_neg: float  # Factored negative moment (kN-m/m)
    
    # Design results
    flexure_pos: FlexuralDesign  # Positive moment design
    flexure_neg: FlexuralDesign  # Negative moment design (if applicable)
    shear: ShearCheck
    deflection: DeflectionCheck
    shrinkage_temp: ShrinkageTempReinf
    
    # Summary
    all_pass: bool
    governing_check: str


def design_oneway_slab(
    Ln: float,  # Clear span (mm)
    tc: float,  # Total thickness (mm)
    cover: float,  # Clear cover (mm)
    bar_dia: float,  # Main bar diameter (mm)
    fc: float,  # Concrete strength (MPa)
    fy: float,  # Steel yield strength (MPa)
    w_DL: float,  # Dead load (kN/m²)
    w_SDL: float,  # Superimposed dead load (kN/m²)
    w_LL: float,  # Live load (kN/m²)
    span_type: str = "Simple",  # Support condition
    As_provided_pos: float = None,  # Provided positive reinforcement (mm²/m)
    As_provided_neg: float = None,  # Provided negative reinforcement (mm²/m)
    method: str = "LRFD",
    wc: float = 2400  # Concrete unit weight (kg/m³)
) -> OneWaySlabResults:
    """
    Complete one-way slab design per ACI 318-19
    
    Parameters:
    -----------
    Ln : float
        Clear span (mm)
    tc : float
        Total slab thickness (mm)
    cover : float
        Clear cover (mm)
    bar_dia : float
        Main reinforcement bar diameter (mm)
    fc : float
        Concrete compressive strength (MPa)
    fy : float
        Reinforcement yield strength (MPa)
    w_DL : float
        Dead load including self-weight (kN/m²)
    w_SDL : float
        Superimposed dead load (kN/m²)
    w_LL : float
        Live load (kN/m²)
    span_type : str
        "Simple", "One End Continuous", "Both Ends Continuous", "Cantilever"
    As_provided_pos : float
        Provided positive moment reinforcement (mm²/m)
    As_provided_neg : float
        Provided negative moment reinforcement (mm²/m)
    method : str
        "LRFD" or "ASD"
    wc : float
        Concrete unit weight (kg/m³)
    
    Returns:
    --------
    OneWaySlabResults object
    """
    # Geometry
    d = tc - cover - bar_dia / 2
    b = 1000  # Per meter width
    
    geometry = SlabGeometry(
        L=Ln,
        tc=tc,
        cover=cover,
        bar_dia=bar_dia,
        d=d,
        b=b
    )
    
    # Materials
    materials = calc_materials(fc, fy, wc)
    
    # Loading
    w_total = w_DL + w_SDL + w_LL
    
    if method == "LRFD":
        wu = 1.2 * (w_DL + w_SDL) + 1.6 * w_LL
    else:
        wu = w_total
    
    w_service = w_total
    
    # Get moment coefficients
    coefs = get_moment_coefficients(span_type)
    
    # Calculate moments (using clear span Ln in meters)
    Ln_m = Ln / 1000
    Mu_pos = wu * Ln_m**2 * coefs.positive  # kN-m/m
    Mu_neg_int = wu * Ln_m**2 * coefs.negative_int  # kN-m/m (interior support)
    Mu_neg_ext = wu * Ln_m**2 * coefs.negative_ext  # kN-m/m (exterior support)
    Mu_neg = max(Mu_neg_int, Mu_neg_ext)
    
    # Flexural design - positive moment
    flexure_pos = design_flexure(geometry, materials, Mu_pos, As_provided_pos, bar_dia)
    
    # Flexural design - negative moment (if applicable)
    if Mu_neg > 0:
        flexure_neg = design_flexure(geometry, materials, Mu_neg, As_provided_neg, bar_dia)
    else:
        # Use minimum reinforcement
        flexure_neg = design_flexure(geometry, materials, 0, As_provided_neg, bar_dia)
    
    # Shear check
    shear = check_shear(geometry, materials, wu, Ln)
    
    # Deflection check
    As_for_defl = flexure_pos.As_provided
    deflection = check_deflection(geometry, materials, span_type, Ln, w_service, As_for_defl)
    
    # Shrinkage and temperature reinforcement
    shrinkage_temp = calc_shrinkage_temp(tc, fy)
    
    # Determine overall pass/fail
    checks = {
        "Flexure (Positive)": flexure_pos.DCR,
        "Shear": shear.DCR,
        "Deflection": deflection.DCR
    }
    
    if Mu_neg > 0:
        checks["Flexure (Negative)"] = flexure_neg.DCR
    
    all_pass = all(dcr <= 1.0 for dcr in checks.values())
    governing_check = max(checks, key=checks.get)
    
    return OneWaySlabResults(
        geometry=geometry,
        materials=materials,
        span_type=span_type,
        Ln=Ln,
        w_DL=w_DL,
        w_SDL=w_SDL,
        w_LL=w_LL,
        wu=wu,
        w_service=w_service,
        Mu_pos=Mu_pos,
        Mu_neg=Mu_neg,
        flexure_pos=flexure_pos,
        flexure_neg=flexure_neg,
        shear=shear,
        deflection=deflection,
        shrinkage_temp=shrinkage_temp,
        all_pass=all_pass,
        governing_check=governing_check
    )
