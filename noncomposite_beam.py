"""
Non-Composite Steel Beam Design Module
Per AISC 360-16 (Specification for Structural Steel Buildings)

Complete design checks:
1. Section Classification (Table B4.1b)
2. Flexural Strength (Chapter F)
3. Shear Strength (Chapter G)
4. Deflection (Chapter L)
5. Web Local Yielding (J10.2)
6. Web Crippling (J10.3)
7. Axial Tension Strength (Chapter D)
8. Axial Compression Strength (Chapter E)
9. Combined Axial + Bending (Chapter H)

Supports:
- Pure bending (beam design)
- Combined axial + bending (beam-column design)
- Temperature-induced axial forces

Author: CompositeBeamPro
Version: 2.0
"""

import math
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

# Material constants
E_STEEL = 200000  # MPa


@dataclass
class SectionClassification:
    """Section classification results per AISC Table B4.1b"""
    lambda_f: float  # Flange slenderness
    lambda_pf: float  # Compact limit for flange
    lambda_rf: float  # Noncompact limit for flange
    flange_class: str  # "Compact", "Noncompact", "Slender"
    
    lambda_w: float  # Web slenderness
    lambda_pw: float  # Compact limit for web
    lambda_rw: float  # Noncompact limit for web
    web_class: str  # "Compact", "Noncompact", "Slender"
    
    overall_class: str  # Governing classification


def classify_section(sec: Dict, Fy: float) -> SectionClassification:
    """
    Classify section per AISC 360-16 Table B4.1b
    
    Parameters:
    -----------
    sec : dict
        Section properties with keys: d, bf, tf, tw
    Fy : float
        Yield strength (MPa)
    
    Returns:
    --------
    SectionClassification object
    """
    d = sec['d']
    bf = sec['bf']
    tf = sec['tf']
    tw = sec['tw']
    
    # Flange slenderness (Table B4.1b Case 10 - Rolled I-shapes)
    lambda_f = bf / (2 * tf)
    lambda_pf = 0.38 * math.sqrt(E_STEEL / Fy)
    lambda_rf = 1.0 * math.sqrt(E_STEEL / Fy)
    
    if lambda_f <= lambda_pf:
        flange_class = "Compact"
    elif lambda_f <= lambda_rf:
        flange_class = "Noncompact"
    else:
        flange_class = "Slender"
    
    # Web slenderness (Table B4.1b Case 15)
    h = d - 2 * tf  # Clear web height
    lambda_w = h / tw
    lambda_pw = 3.76 * math.sqrt(E_STEEL / Fy)
    lambda_rw = 5.70 * math.sqrt(E_STEEL / Fy)
    
    if lambda_w <= lambda_pw:
        web_class = "Compact"
    elif lambda_w <= lambda_rw:
        web_class = "Noncompact"
    else:
        web_class = "Slender"
    
    # Overall classification (most restrictive)
    class_order = {"Compact": 0, "Noncompact": 1, "Slender": 2}
    if class_order[flange_class] >= class_order[web_class]:
        overall_class = flange_class
    else:
        overall_class = web_class
    
    return SectionClassification(
        lambda_f=lambda_f,
        lambda_pf=lambda_pf,
        lambda_rf=lambda_rf,
        flange_class=flange_class,
        lambda_w=lambda_w,
        lambda_pw=lambda_pw,
        lambda_rw=lambda_rw,
        web_class=web_class,
        overall_class=overall_class
    )


@dataclass
class FlexuralStrength:
    """Flexural strength results per AISC Chapter F"""
    Mp: float  # Plastic moment (kN-m)
    Mn: float  # Nominal moment capacity (kN-m)
    phi_Mn: float  # Design capacity LRFD (kN-m)
    Mn_omega: float  # Allowable capacity ASD (kN-m)
    
    Lp: float  # Limiting unbraced length for plastic (mm)
    Lr: float  # Limiting unbraced length for inelastic LTB (mm)
    Lb: float  # Actual unbraced length (mm)
    
    Cb: float  # Moment gradient factor
    
    limit_state: str  # Governing limit state
    Fcr: float  # Critical stress for LTB (MPa), if applicable


def calc_Cb(loading: str = "uniform") -> float:
    """
    Calculate moment gradient factor Cb per AISC F1
    
    Parameters:
    -----------
    loading : str
        Load type: "uniform", "midpoint", "third_points", "cantilever"
    
    Returns:
    --------
    float : Cb value
    """
    cb_values = {
        "uniform": 1.14,
        "midpoint": 1.32,
        "third_points": 1.01,
        "cantilever": 1.0,
        "equal_end_moments": 2.27,
    }
    return cb_values.get(loading, 1.0)


def calc_flexural_strength(sec: Dict, Fy: float, Lb: float, 
                           Cb: float = 1.0, method: str = "LRFD") -> FlexuralStrength:
    """
    Calculate flexural strength per AISC 360-16 Chapter F
    
    Parameters:
    -----------
    sec : dict
        Section properties with keys: d, bf, tf, tw, Ix, Sx, Zx, ry, J, Cw
    Fy : float
        Yield strength (MPa)
    Lb : float
        Unbraced length (mm)
    Cb : float
        Moment gradient factor (default 1.0)
    method : str
        "LRFD" or "ASD"
    
    Returns:
    --------
    FlexuralStrength object
    """
    d = sec['d']
    bf = sec['bf']
    tf = sec['tf']
    tw = sec['tw']
    Ix = sec['Ix']
    Sx = sec.get('Sx', Ix / (d/2))
    Zx = sec.get('Zx', Sx * 1.12)  # Approximate if not provided
    ry = sec.get('ry', bf / 4)  # Approximate if not provided
    
    # Torsional properties - approximate if not provided
    J = sec.get('J', (2 * bf * tf**3 + (d - 2*tf) * tw**3) / 3)
    h0 = d - tf  # Distance between flange centroids
    
    # Warping constant - approximate for doubly symmetric I-shapes
    Iy = sec.get('Iy', 2 * (tf * bf**3 / 12))
    Cw = sec.get('Cw', Iy * h0**2 / 4)
    
    # Plastic moment (F2.1)
    Mp = Fy * Zx / 1e6  # kN-m
    
    # Calculate rts (F2.2)
    rts_sq = math.sqrt(Iy * Cw) / Sx if Sx > 0 else ry
    rts = math.sqrt(rts_sq) if rts_sq > 0 else ry
    
    # Limiting lengths
    # Lp (F2-5)
    Lp = 1.76 * ry * math.sqrt(E_STEEL / Fy)
    
    # Lr (F2-6)
    c = 1.0  # For doubly symmetric I-shapes
    term1 = (J * c) / (Sx * h0) if (Sx * h0) > 0 else 0
    term2 = 6.76 * (0.7 * Fy / E_STEEL)**2
    
    Lr = 1.95 * rts * (E_STEEL / (0.7 * Fy)) * math.sqrt(term1 + math.sqrt(term1**2 + term2))
    
    # Determine Mn based on Lb
    if Lb <= Lp:
        # Zone 1: Full plastic capacity (F2.1)
        Mn = Mp
        limit_state = "Yielding (Compact)"
        Fcr = Fy
    elif Lb <= Lr:
        # Zone 2: Inelastic LTB (F2.2)
        Mn_ltb = Cb * (Mp - (Mp - 0.7 * Fy * Sx / 1e6) * (Lb - Lp) / (Lr - Lp))
        Mn = min(Mn_ltb, Mp)
        limit_state = "Inelastic LTB"
        Fcr = Mn * 1e6 / Sx if Sx > 0 else Fy
    else:
        # Zone 3: Elastic LTB (F2.3)
        Fcr = (Cb * math.pi**2 * E_STEEL / (Lb / rts)**2) * \
              math.sqrt(1 + 0.078 * (J * c) / (Sx * h0) * (Lb / rts)**2) if (Sx * h0) > 0 else 0
        Mn_ltb = Fcr * Sx / 1e6
        Mn = min(Mn_ltb, Mp)
        limit_state = "Elastic LTB"
    
    # Design/Allowable capacity
    phi_b = 0.90
    omega_b = 1.67
    
    phi_Mn = phi_b * Mn
    Mn_omega = Mn / omega_b
    
    return FlexuralStrength(
        Mp=Mp,
        Mn=Mn,
        phi_Mn=phi_Mn,
        Mn_omega=Mn_omega,
        Lp=Lp,
        Lr=Lr,
        Lb=Lb,
        Cb=Cb,
        limit_state=limit_state,
        Fcr=Fcr
    )


@dataclass
class ShearStrength:
    """Shear strength results per AISC Chapter G"""
    Aw: float  # Web area (mm²)
    Cv1: float  # Web shear coefficient
    Vn: float  # Nominal shear strength (kN)
    phi_Vn: float  # Design capacity LRFD (kN)
    Vn_omega: float  # Allowable capacity ASD (kN)
    phi_v: float  # Resistance factor used
    h_tw_ratio: float  # Web slenderness
    limit: float  # Slenderness limit for Cv1=1.0


def calc_shear_strength(sec: Dict, Fy: float, method: str = "LRFD") -> ShearStrength:
    """
    Calculate shear strength per AISC 360-16 Chapter G
    
    Parameters:
    -----------
    sec : dict
        Section properties with keys: d, tf, tw
    Fy : float
        Yield strength (MPa)
    method : str
        "LRFD" or "ASD"
    
    Returns:
    --------
    ShearStrength object
    """
    d = sec['d']
    tf = sec['tf']
    tw = sec['tw']
    
    # Web area
    Aw = d * tw  # Using full depth per AISC G2.1
    
    # Web slenderness
    h = d - 2 * tf
    h_tw = h / tw
    
    # Cv1 and phi_v per G2.1
    kv = 5.34  # Unstiffened web
    limit_1 = 2.24 * math.sqrt(E_STEEL / Fy)
    limit_2 = 1.10 * math.sqrt(kv * E_STEEL / Fy)
    
    if h_tw <= limit_1:
        Cv1 = 1.0
        phi_v = 1.0
        omega_v = 1.50
    elif h_tw <= limit_2:
        Cv1 = 1.0
        phi_v = 0.90
        omega_v = 1.67
    else:
        Cv1 = limit_2 / h_tw
        phi_v = 0.90
        omega_v = 1.67
    
    # Nominal shear strength (G2-1)
    Vn = 0.6 * Fy * Aw * Cv1 / 1000  # kN
    
    # Design/Allowable capacity
    phi_Vn = phi_v * Vn
    Vn_omega = Vn / omega_v
    
    return ShearStrength(
        Aw=Aw,
        Cv1=Cv1,
        Vn=Vn,
        phi_Vn=phi_Vn,
        Vn_omega=Vn_omega,
        phi_v=phi_v,
        h_tw_ratio=h_tw,
        limit=limit_1
    )


@dataclass
class DeflectionResults:
    """Deflection calculation results"""
    delta_DL: float  # Dead load deflection (mm)
    delta_LL: float  # Live load deflection (mm)
    delta_total: float  # Total deflection (mm)
    
    limit_LL: float  # Live load limit (mm)
    limit_total: float  # Total load limit (mm)
    
    DCR_LL: float  # Demand/Capacity for LL
    DCR_total: float  # Demand/Capacity for total
    
    ok_LL: bool
    ok_total: bool


def calc_deflection(Ix: float, L: float, w_DL: float, w_LL: float, 
                    limit_LL: float = 360, limit_total: float = 240) -> DeflectionResults:
    """
    Calculate deflection using bare steel moment of inertia
    
    Parameters:
    -----------
    Ix : float
        Moment of inertia (mm⁴)
    L : float
        Span length (m)
    w_DL : float
        Dead load (kN/m)
    w_LL : float
        Live load (kN/m)
    limit_LL : float
        L/? limit for live load (default L/360)
    limit_total : float
        L/? limit for total load (default L/240)
    
    Returns:
    --------
    DeflectionResults object
    """
    L_mm = L * 1000
    
    # δ = 5wL⁴ / (384EI)
    delta_DL = 5 * w_DL * L_mm**4 / (384 * E_STEEL * Ix) if Ix > 0 else 999
    delta_LL = 5 * w_LL * L_mm**4 / (384 * E_STEEL * Ix) if Ix > 0 else 999
    delta_total = delta_DL + delta_LL
    
    # Limits
    delta_limit_LL = L_mm / limit_LL
    delta_limit_total = L_mm / limit_total
    
    # DCR
    DCR_LL = delta_LL / delta_limit_LL if delta_limit_LL > 0 else 999
    DCR_total = delta_total / delta_limit_total if delta_limit_total > 0 else 999
    
    return DeflectionResults(
        delta_DL=delta_DL,
        delta_LL=delta_LL,
        delta_total=delta_total,
        limit_LL=delta_limit_LL,
        limit_total=delta_limit_total,
        DCR_LL=DCR_LL,
        DCR_total=DCR_total,
        ok_LL=DCR_LL <= 1.0,
        ok_total=DCR_total <= 1.0
    )


@dataclass
class WebLocalYielding:
    """Web local yielding results per AISC J10.2"""
    Rn_end: float  # Nominal strength at end (kN)
    Rn_int: float  # Nominal strength at interior (kN)
    phi_Rn_end: float  # Design strength at end (kN)
    phi_Rn_int: float  # Design strength at interior (kN)
    k: float  # Distance to web toe of fillet


def calc_web_local_yielding(sec: Dict, Fy: float, lb: float = 100) -> WebLocalYielding:
    """
    Calculate web local yielding strength per AISC J10.2
    
    Parameters:
    -----------
    sec : dict
        Section properties with keys: d, tf, tw, k (or calculate k)
    Fy : float
        Yield strength (MPa)
    lb : float
        Bearing length (mm)
    
    Returns:
    --------
    WebLocalYielding object
    """
    tf = sec['tf']
    tw = sec['tw']
    
    # k = distance from outer face of flange to web toe of fillet
    # Approximate as tf + fillet radius (typically tf for approximation)
    k = sec.get('k', tf * 1.25)
    
    # At end reaction (J10-2)
    Rn_end = Fy * tw * (2.5 * k + lb) / 1000  # kN
    
    # At interior concentrated load (J10-3)
    Rn_int = Fy * tw * (5 * k + lb) / 1000  # kN
    
    phi = 1.0
    omega = 1.50
    
    return WebLocalYielding(
        Rn_end=Rn_end,
        Rn_int=Rn_int,
        phi_Rn_end=phi * Rn_end,
        phi_Rn_int=phi * Rn_int,
        k=k
    )


@dataclass
class WebCrippling:
    """Web crippling results per AISC J10.3"""
    Rn_end: float  # Nominal strength at end (kN)
    Rn_int: float  # Nominal strength at interior (kN)
    phi_Rn_end: float  # Design strength at end (kN)
    phi_Rn_int: float  # Design strength at interior (kN)
    lb_d_ratio: float  # Bearing length to depth ratio


def calc_web_crippling(sec: Dict, Fy: float, lb: float = 100) -> WebCrippling:
    """
    Calculate web crippling strength per AISC J10.3
    
    Parameters:
    -----------
    sec : dict
        Section properties with keys: d, tf, tw
    Fy : float
        Yield strength (MPa)
    lb : float
        Bearing length (mm)
    
    Returns:
    --------
    WebCrippling object
    """
    d = sec['d']
    tf = sec['tf']
    tw = sec['tw']
    
    lb_d = lb / d
    
    # At end, when lb/d ≤ 0.2 (J10-5a)
    if lb_d <= 0.2:
        Rn_end = 0.40 * tw**2 * (1 + 3 * lb_d * (tw/tf)**1.5) * \
                 math.sqrt(E_STEEL * Fy * tf / tw) / 1000
    else:
        # (J10-5b)
        Rn_end = 0.40 * tw**2 * (1 + (4 * lb_d - 0.2) * (tw/tf)**1.5) * \
                 math.sqrt(E_STEEL * Fy * tf / tw) / 1000
    
    # At interior (J10-4)
    Rn_int = 0.80 * tw**2 * (1 + 3 * lb_d * (tw/tf)**1.5) * \
             math.sqrt(E_STEEL * Fy * tf / tw) / 1000
    
    phi = 0.75
    omega = 2.00
    
    return WebCrippling(
        Rn_end=Rn_end,
        Rn_int=Rn_int,
        phi_Rn_end=phi * Rn_end,
        phi_Rn_int=phi * Rn_int,
        lb_d_ratio=lb_d
    )


@dataclass
class NonCompositeBeamResults:
    """Complete non-composite beam analysis results"""
    # Input summary
    sec_name: str
    L: float
    w_DL: float
    w_SDL: float
    w_LL: float
    w_total: float
    method: str
    
    # Demands
    Mu: float  # Factored moment (kN-m)
    Vu: float  # Factored shear (kN)
    Ru: float  # Factored reaction (kN)
    
    # Classification
    classification: SectionClassification
    
    # Capacities
    flexure: FlexuralStrength
    shear: ShearStrength
    deflection: DeflectionResults
    web_yielding: WebLocalYielding
    web_crippling: WebCrippling
    
    # DCR values
    DCR_flex: float
    DCR_shear: float
    DCR_web_yielding: float
    DCR_web_crippling: float
    
    # Overall
    all_pass: bool
    governing_check: str


def design_noncomposite_beam(sec: Dict, sec_name: str, Fy: float, 
                             L: float, w_DL: float, w_SDL: float, w_LL: float,
                             Lb: float = None, Cb: float = 1.14,
                             lb: float = 100, method: str = "LRFD") -> NonCompositeBeamResults:
    """
    Complete non-composite steel beam design per AISC 360-16
    
    Parameters:
    -----------
    sec : dict
        Section properties
    sec_name : str
        Section designation
    Fy : float
        Yield strength (MPa)
    L : float
        Span length (m)
    w_DL : float
        Dead load including beam self-weight (kN/m)
    w_SDL : float
        Superimposed dead load (kN/m)
    w_LL : float
        Live load (kN/m)
    Lb : float
        Unbraced length (mm), default = L/4
    Cb : float
        Moment gradient factor (default 1.14 for uniform load)
    lb : float
        Bearing length (mm)
    method : str
        "LRFD" or "ASD"
    
    Returns:
    --------
    NonCompositeBeamResults object
    """
    # Default Lb if not provided
    if Lb is None:
        Lb = L * 1000 / 4  # Quarter-span bracing typical
    
    # Total load
    w_total = w_DL + w_SDL + w_LL
    
    # Load factors
    if method == "LRFD":
        w_u = 1.2 * (w_DL + w_SDL) + 1.6 * w_LL
    else:
        w_u = w_DL + w_SDL + w_LL
    
    # Demands
    Mu = w_u * L**2 / 8  # kN-m
    Vu = w_u * L / 2  # kN
    Ru = Vu  # Reaction = shear for simply supported
    
    # Section classification
    classification = classify_section(sec, Fy)
    
    # Flexural strength
    flexure = calc_flexural_strength(sec, Fy, Lb, Cb, method)
    
    # Shear strength
    shear = calc_shear_strength(sec, Fy, method)
    
    # Deflection (unfactored loads)
    w_service_DL = w_DL + w_SDL
    deflection = calc_deflection(sec['Ix'], L, w_service_DL, w_LL)
    
    # Web local yielding
    web_yielding = calc_web_local_yielding(sec, Fy, lb)
    
    # Web crippling
    web_crippling = calc_web_crippling(sec, Fy, lb)
    
    # DCR calculations
    if method == "LRFD":
        DCR_flex = Mu / flexure.phi_Mn if flexure.phi_Mn > 0 else 999
        DCR_shear = Vu / shear.phi_Vn if shear.phi_Vn > 0 else 999
        DCR_web_yielding = Ru / web_yielding.phi_Rn_end if web_yielding.phi_Rn_end > 0 else 999
        DCR_web_crippling = Ru / web_crippling.phi_Rn_end if web_crippling.phi_Rn_end > 0 else 999
    else:
        DCR_flex = Mu / flexure.Mn_omega if flexure.Mn_omega > 0 else 999
        DCR_shear = Vu / shear.Vn_omega if shear.Vn_omega > 0 else 999
        DCR_web_yielding = Ru / (web_yielding.Rn_end / 1.50) if web_yielding.Rn_end > 0 else 999
        DCR_web_crippling = Ru / (web_crippling.Rn_end / 2.00) if web_crippling.Rn_end > 0 else 999
    
    # Determine all pass and governing check
    checks = {
        "Flexure": DCR_flex,
        "Shear": DCR_shear,
        "Deflection (LL)": deflection.DCR_LL,
        "Deflection (Total)": deflection.DCR_total,
        "Web Local Yielding": DCR_web_yielding,
        "Web Crippling": DCR_web_crippling
    }
    
    all_pass = all(dcr <= 1.0 for dcr in checks.values())
    governing_check = max(checks, key=checks.get)
    
    return NonCompositeBeamResults(
        sec_name=sec_name,
        L=L,
        w_DL=w_DL,
        w_SDL=w_SDL,
        w_LL=w_LL,
        w_total=w_total,
        method=method,
        Mu=Mu,
        Vu=Vu,
        Ru=Ru,
        classification=classification,
        flexure=flexure,
        shear=shear,
        deflection=deflection,
        web_yielding=web_yielding,
        web_crippling=web_crippling,
        DCR_flex=DCR_flex,
        DCR_shear=DCR_shear,
        DCR_web_yielding=DCR_web_yielding,
        DCR_web_crippling=DCR_web_crippling,
        all_pass=all_pass,
        governing_check=governing_check
    )


# =============================================================================
# AXIAL STRENGTH AND COMBINED LOADING (AISC Chapters D, E, H)
# =============================================================================

@dataclass
class AxialTensionStrength:
    """Axial tension strength results per AISC Chapter D"""
    Ag: float  # Gross area (mm²)
    Pn_yield: float  # Nominal yielding strength (kN)
    Pn_rupture: float  # Nominal rupture strength (kN) - if applicable
    Pn: float  # Governing nominal strength (kN)
    phi_Pn: float  # Design strength LRFD (kN)
    Pn_omega: float  # Allowable strength ASD (kN)
    limit_state: str  # "Yielding" or "Rupture"


def calc_tension_strength(sec: Dict, Fy: float, Fu: float = None, 
                          method: str = "LRFD") -> AxialTensionStrength:
    """
    Calculate axial tension strength per AISC 360-16 Chapter D
    
    Parameters:
    -----------
    sec : dict
        Section properties with key: A (gross area)
    Fy : float
        Yield strength (MPa)
    Fu : float
        Tensile strength (MPa), default = 1.25*Fy
    method : str
        "LRFD" or "ASD"
    
    Returns:
    --------
    AxialTensionStrength object
    """
    Ag = sec['A']
    
    if Fu is None:
        Fu = 1.25 * Fy  # Approximate
    
    # Yielding on gross section (D2-1)
    Pn_yield = Fy * Ag / 1000  # kN
    
    # Rupture on net section (D2-2) - assume no holes for beam
    Ae = Ag  # Effective net area = gross area (no holes)
    Pn_rupture = Fu * Ae / 1000  # kN
    
    # Governing
    phi_yield = 0.90
    phi_rupture = 0.75
    omega_yield = 1.67
    omega_rupture = 2.00
    
    phi_Pn_yield = phi_yield * Pn_yield
    phi_Pn_rupture = phi_rupture * Pn_rupture
    
    if phi_Pn_yield <= phi_Pn_rupture:
        Pn = Pn_yield
        phi_Pn = phi_Pn_yield
        Pn_omega = Pn_yield / omega_yield
        limit_state = "Yielding"
    else:
        Pn = Pn_rupture
        phi_Pn = phi_Pn_rupture
        Pn_omega = Pn_rupture / omega_rupture
        limit_state = "Rupture"
    
    return AxialTensionStrength(
        Ag=Ag,
        Pn_yield=Pn_yield,
        Pn_rupture=Pn_rupture,
        Pn=Pn,
        phi_Pn=phi_Pn,
        Pn_omega=Pn_omega,
        limit_state=limit_state
    )


@dataclass
class AxialCompressionStrength:
    """Axial compression strength results per AISC Chapter E"""
    Ag: float  # Gross area (mm²)
    Lc: float  # Effective length (mm)
    r: float  # Governing radius of gyration (mm)
    KL_r: float  # Slenderness ratio
    Fe: float  # Elastic buckling stress (MPa)
    Fcr: float  # Critical stress (MPa)
    Pn: float  # Nominal compression strength (kN)
    phi_Pn: float  # Design strength LRFD (kN)
    Pn_omega: float  # Allowable strength ASD (kN)
    limit_state: str  # "Yielding", "Inelastic Buckling", "Elastic Buckling"


def calc_compression_strength(sec: Dict, Fy: float, Lc: float, K: float = 1.0,
                              method: str = "LRFD") -> AxialCompressionStrength:
    """
    Calculate axial compression strength per AISC 360-16 Chapter E
    
    Parameters:
    -----------
    sec : dict
        Section properties with keys: A, ry, rx (or Ix, Iy)
    Fy : float
        Yield strength (MPa)
    Lc : float
        Unbraced length for compression (mm)
    K : float
        Effective length factor (default 1.0)
    method : str
        "LRFD" or "ASD"
    
    Returns:
    --------
    AxialCompressionStrength object
    """
    Ag = sec['A']
    
    # Get radius of gyration
    ry = sec.get('ry', math.sqrt(sec.get('Iy', sec['Ix']/10) / Ag))
    rx = sec.get('rx', math.sqrt(sec['Ix'] / Ag))
    
    # Use minimum r for weak-axis buckling (typically ry)
    r = min(rx, ry)
    
    # Slenderness ratio
    KL_r = K * Lc / r
    
    # Elastic buckling stress (E3-4)
    Fe = math.pi**2 * E_STEEL / KL_r**2 if KL_r > 0 else Fy
    
    # Critical stress determination
    limit_ratio = 4.71 * math.sqrt(E_STEEL / Fy)
    
    if KL_r <= limit_ratio:
        # Inelastic buckling (E3-2)
        Fcr = (0.658**(Fy/Fe)) * Fy
        limit_state = "Inelastic Buckling" if KL_r > 25 else "Yielding"
    else:
        # Elastic buckling (E3-3)
        Fcr = 0.877 * Fe
        limit_state = "Elastic Buckling"
    
    # Nominal strength (E3-1)
    Pn = Fcr * Ag / 1000  # kN
    
    phi_c = 0.90
    omega_c = 1.67
    
    phi_Pn = phi_c * Pn
    Pn_omega = Pn / omega_c
    
    return AxialCompressionStrength(
        Ag=Ag,
        Lc=Lc,
        r=r,
        KL_r=KL_r,
        Fe=Fe,
        Fcr=Fcr,
        Pn=Pn,
        phi_Pn=phi_Pn,
        Pn_omega=Pn_omega,
        limit_state=limit_state
    )


@dataclass
class CombinedLoadingResults:
    """Combined axial + bending interaction results per AISC Chapter H"""
    Pr: float  # Required axial strength (kN)
    Pc: float  # Available axial strength (kN)
    Mrx: float  # Required flexural strength, x-axis (kN-m)
    Mcx: float  # Available flexural strength, x-axis (kN-m)
    
    Pr_Pc: float  # Axial ratio
    Mrx_Mcx: float  # Moment ratio
    
    equation_used: str  # "H1-1a" or "H1-1b"
    interaction_value: float  # Left side of interaction equation
    DCR: float  # Demand/Capacity ratio
    ok: bool
    
    axial_type: str  # "Compression" or "Tension"
    axial_strength: object  # AxialCompressionStrength or AxialTensionStrength


def check_combined_loading(sec: Dict, Fy: float, Fu: float,
                           Pu: float, Mu: float, 
                           flexure: FlexuralStrength,
                           Lc: float, K: float = 1.0,
                           method: str = "LRFD") -> CombinedLoadingResults:
    """
    Check combined axial + bending per AISC 360-16 Chapter H
    
    Parameters:
    -----------
    sec : dict
        Section properties
    Fy : float
        Yield strength (MPa)
    Fu : float
        Tensile strength (MPa)
    Pu : float
        Required axial strength (kN), positive = compression
    Mu : float
        Required flexural strength (kN-m)
    flexure : FlexuralStrength
        Flexural strength results
    Lc : float
        Unbraced length for compression (mm)
    K : float
        Effective length factor
    method : str
        "LRFD" or "ASD"
    
    Returns:
    --------
    CombinedLoadingResults object
    """
    # Determine axial type and calculate capacity
    if Pu >= 0:
        # Compression
        axial_type = "Compression"
        axial_strength = calc_compression_strength(sec, Fy, Lc, K, method)
        if method == "LRFD":
            Pc = axial_strength.phi_Pn
        else:
            Pc = axial_strength.Pn_omega
    else:
        # Tension
        axial_type = "Tension"
        axial_strength = calc_tension_strength(sec, Fy, Fu, method)
        if method == "LRFD":
            Pc = axial_strength.phi_Pn
        else:
            Pc = axial_strength.Pn_omega
        Pu = abs(Pu)  # Use absolute value for interaction
    
    # Required and available strengths
    Pr = Pu
    if method == "LRFD":
        Mcx = flexure.phi_Mn
    else:
        Mcx = flexure.Mn_omega
    Mrx = Mu
    
    # Calculate ratios
    Pr_Pc = Pr / Pc if Pc > 0 else 999
    Mrx_Mcx = Mrx / Mcx if Mcx > 0 else 999
    
    # Interaction equations (H1-1)
    if Pr_Pc >= 0.2:
        # Equation H1-1a
        equation_used = "H1-1a"
        interaction_value = Pr_Pc + (8/9) * Mrx_Mcx
    else:
        # Equation H1-1b
        equation_used = "H1-1b"
        interaction_value = Pr_Pc / 2 + Mrx_Mcx
    
    DCR = interaction_value  # Limit is 1.0
    ok = interaction_value <= 1.0
    
    return CombinedLoadingResults(
        Pr=Pr,
        Pc=Pc,
        Mrx=Mrx,
        Mcx=Mcx,
        Pr_Pc=Pr_Pc,
        Mrx_Mcx=Mrx_Mcx,
        equation_used=equation_used,
        interaction_value=interaction_value,
        DCR=DCR,
        ok=ok,
        axial_type=axial_type,
        axial_strength=axial_strength
    )


@dataclass
class NonCompositeBeamColumnResults:
    """Complete beam-column (axial + bending) analysis results"""
    # Base beam results
    beam_results: NonCompositeBeamResults
    
    # Axial load
    Pu: float  # Factored axial force (kN)
    axial_type: str  # "Compression", "Tension", or "None"
    
    # Axial strength
    axial_strength: object  # AxialCompressionStrength or AxialTensionStrength or None
    
    # Combined loading
    combined: CombinedLoadingResults  # Interaction check results
    
    # Overall
    all_pass: bool
    governing_check: str


def design_noncomposite_beam_column(
    sec: Dict, sec_name: str, Fy: float, Fu: float,
    L: float, w_DL: float, w_SDL: float, w_LL: float,
    Pu: float = 0.0,  # Factored axial force (kN), positive = compression
    Lb: float = None, Cb: float = 1.14,
    Lc: float = None, K: float = 1.0,
    lb: float = 100, method: str = "LRFD"
) -> NonCompositeBeamColumnResults:
    """
    Complete non-composite steel beam-column design per AISC 360-16
    Handles combined axial + bending (Chapter H)
    
    Parameters:
    -----------
    sec : dict
        Section properties
    sec_name : str
        Section designation
    Fy : float
        Yield strength (MPa)
    Fu : float
        Tensile strength (MPa)
    L : float
        Span length (m)
    w_DL : float
        Dead load including beam self-weight (kN/m)
    w_SDL : float
        Superimposed dead load (kN/m)
    w_LL : float
        Live load (kN/m)
    Pu : float
        Factored axial force (kN), positive = compression, negative = tension
    Lb : float
        Unbraced length for flexure (mm), default = L/4
    Cb : float
        Moment gradient factor (default 1.14 for uniform load)
    Lc : float
        Unbraced length for compression (mm), default = L
    K : float
        Effective length factor for compression (default 1.0)
    lb : float
        Bearing length (mm)
    method : str
        "LRFD" or "ASD"
    
    Returns:
    --------
    NonCompositeBeamColumnResults object
    """
    # First, run standard beam design
    if Lb is None:
        Lb = L * 1000 / 4
    
    if Lc is None:
        Lc = L * 1000  # Full span for compression buckling
    
    beam_results = design_noncomposite_beam(
        sec=sec, sec_name=sec_name, Fy=Fy,
        L=L, w_DL=w_DL, w_SDL=w_SDL, w_LL=w_LL,
        Lb=Lb, Cb=Cb, lb=lb, method=method
    )
    
    # Check if axial load is significant
    if abs(Pu) < 0.1:  # Negligible axial
        axial_type = "None"
        axial_strength = None
        combined = None
        
        all_pass = beam_results.all_pass
        governing_check = beam_results.governing_check
    else:
        # Determine axial type
        if Pu > 0:
            axial_type = "Compression"
            axial_strength = calc_compression_strength(sec, Fy, Lc, K, method)
        else:
            axial_type = "Tension"
            axial_strength = calc_tension_strength(sec, Fy, Fu, method)
        
        # Combined loading check
        combined = check_combined_loading(
            sec=sec, Fy=Fy, Fu=Fu,
            Pu=Pu, Mu=beam_results.Mu,
            flexure=beam_results.flexure,
            Lc=Lc, K=K, method=method
        )
        
        # Update overall pass/fail
        checks = {
            "Flexure": beam_results.DCR_flex,
            "Shear": beam_results.DCR_shear,
            "Deflection (LL)": beam_results.deflection.DCR_LL,
            "Deflection (Total)": beam_results.deflection.DCR_total,
            "Web Local Yielding": beam_results.DCR_web_yielding,
            "Web Crippling": beam_results.DCR_web_crippling,
            "Combined Axial+Bending": combined.DCR
        }
        
        all_pass = all(dcr <= 1.0 for dcr in checks.values())
        governing_check = max(checks, key=checks.get)
    
    return NonCompositeBeamColumnResults(
        beam_results=beam_results,
        Pu=Pu,
        axial_type=axial_type,
        axial_strength=axial_strength,
        combined=combined,
        all_pass=all_pass,
        governing_check=governing_check
    )
