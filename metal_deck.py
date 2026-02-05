"""
Metal Deck Design Module - AISI S100-16 / SDI C-2017
=====================================================
Phase 2, Week 7 - CompositeBeam Pro

Comprehensive metal deck design checks including:
- Flexural strength (positive and negative moment)
- Shear strength
- Web crippling under concentrated loads
- Combined bending and web crippling
- Deflection limits

Design Standards:
- AISI S100-16 (North American Specification for Cold-Formed Steel)
- SDI C-2017 (Steel Deck Institute Composite Deck Design)
- SDI DDM04 (Diaphragm Design Manual)

Author: CompositeBeam Pro
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class DesignMethod(Enum):
    """Design method for capacity calculation"""
    LRFD = "LRFD"
    ASD = "ASD"


class LoadingCondition(Enum):
    """Web crippling loading condition per AISI S100-16"""
    EOF = "End One-Flange"          # End reaction, one flange
    IOF = "Interior One-Flange"     # Interior load, one flange
    ETF = "End Two-Flange"          # End reaction, two flanges
    ITF = "Interior Two-Flange"     # Interior load, two flanges


@dataclass
class DesignStep:
    """Single step in design calculation for report generation"""
    description: str
    equation_latex: str
    substitution_latex: str
    result: float
    unit: str
    code_ref: str


@dataclass
class DesignCheckResult:
    """Result of a design check"""
    check_name: str
    demand: float
    capacity: float
    ratio: float
    status: str                     # "PASS", "FAIL", or "WARNING"
    steps: List[DesignStep] = field(default_factory=list)
    code_ref: str = ""
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.capacity > 0:
            self.ratio = self.demand / self.capacity
        else:
            self.ratio = float('inf')
        
        if self.ratio <= 1.0:
            self.status = "PASS"
        elif self.ratio <= 1.05:
            self.status = "WARNING"
        else:
            self.status = "FAIL"


@dataclass
class DeckMaterial:
    """Metal deck material properties"""
    Fy: float = 230.0               # Yield strength (MPa), typical for deck
    Fu: float = 310.0               # Ultimate strength (MPa)
    E: float = 200000.0             # Modulus of elasticity (MPa)
    nu: float = 0.30                # Poisson's ratio
    name: str = "ASTM A653 SS Grade 33"


@dataclass 
class DeckGeometry:
    """Metal deck geometry from DXF parser"""
    hr: float                       # Rib height (mm)
    wr_top: float                   # Top rib opening (mm)
    wr_bot: float                   # Bottom width (mm)
    pitch: float                    # Rib pitch (mm)
    t: float                        # Base metal thickness (mm)
    theta: float = 80.0             # Web angle from horizontal (degrees)
    n_ribs: int = 1                 # Number of ribs in strip
    
    @property
    def web_depth(self) -> float:
        """Inclined web length"""
        return self.hr / np.sin(np.radians(self.theta))
    
    @property
    def web_flat_width(self) -> float:
        """Flat width of web element"""
        r = 2 * self.t  # Assumed corner radius
        return self.web_depth - 2 * r


@dataclass
class DeckSectionProperties:
    """Section properties for deck (from DXF parser and effective width)"""
    # Gross properties
    Ag: float = 0.0                 # Gross area (mm²/m)
    Ig: float = 0.0                 # Gross moment of inertia (mm⁴/m)
    Sg_top: float = 0.0             # Gross section modulus at top (mm³/m)
    Sg_bot: float = 0.0             # Gross section modulus at bottom (mm³/m)
    ycg: float = 0.0                # Centroid from bottom (mm)
    
    # Effective properties
    Ae: float = 0.0                 # Effective area (mm²/m)
    Ie: float = 0.0                 # Effective moment of inertia (mm⁴/m)
    Se_pos: float = 0.0             # Effective section modulus, +M (mm³/m)
    Se_neg: float = 0.0             # Effective section modulus, -M (mm³/m)
    yce: float = 0.0                # Effective centroid (mm)
    
    # Deflection
    Id: float = 0.0                 # Deflection moment of inertia (mm⁴/m)


@dataclass
class DeckDesignInput:
    """Input data for deck design checks"""
    # Geometry
    geometry: DeckGeometry
    properties: DeckSectionProperties
    material: DeckMaterial
    
    # Span configuration
    span: float                     # Clear span (mm)
    span_type: str = "simple"       # "simple", "two_span", "three_span"
    
    # Loads
    w_dead: float = 0.0             # Dead load (kN/m²) - deck + concrete
    w_live: float = 0.0             # Live load (kN/m²) - construction
    P_conc: float = 0.0             # Concentrated load (kN) - worker + equipment
    
    # Design method
    method: DesignMethod = DesignMethod.LRFD


# =====================================================================
# FLEXURAL STRENGTH - AISI S100-16 Section F
# =====================================================================

def check_flexural_strength(
    Se: float,
    Fy: float,
    Mu: float,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check flexural strength of metal deck per AISI S100-16 Section F.
    
    For deck sections with effective section properties:
    M_n = S_e × F_y  (Eq. F3.1-1)
    
    Args:
        Se: Effective section modulus (mm³/m)
        Fy: Yield strength (MPa)
        Mu: Required moment (kN-m/m for LRFD, kN-m/m for ASD)
        method: Design method (LRFD or ASD)
        
    Returns:
        DesignCheckResult with flexural check results
        
    Reference:
        AISI S100-16 Section F3.1 - Flexural Strength Based on
        Effective Section Modulus
        
    Equations:
        M_n = S_e × F_y  ... Eq. F3.1-1 (Nominal flexural strength)
        
        LRFD: φ_b = 0.90
        ASD: Ω_b = 1.67
        
        LRFD: φ_b × M_n ≥ M_u
        ASD: M_n / Ω_b ≥ M_a
    """
    steps = []
    
    # Nominal flexural strength (Eq. F3.1-1)
    # Mn in N-mm/m, convert to kN-m/m
    Mn = Se * Fy / 1e6  # kN-m/m
    
    steps.append(DesignStep(
        description="Nominal flexural strength",
        equation_latex=r"M_n = S_e \times F_y",
        substitution_latex=f"M_n = {Se:.0f} \\times {Fy}",
        result=Mn,
        unit="kN-m/m",
        code_ref="AISI S100-16 Eq. F3.1-1"
    ))
    
    # Design/Allowable strength
    if method == DesignMethod.LRFD:
        phi_b = 0.90
        Mn_design = phi_b * Mn
        steps.append(DesignStep(
            description="Design flexural strength",
            equation_latex=r"\phi_b M_n = \phi_b \times M_n",
            substitution_latex=f"\\phi_b M_n = {phi_b} \\times {Mn:.3f}",
            result=Mn_design,
            unit="kN-m/m",
            code_ref="AISI S100-16 Section F1 (φ_b = 0.90)"
        ))
        capacity = Mn_design
    else:
        omega_b = 1.67
        Mn_allow = Mn / omega_b
        steps.append(DesignStep(
            description="Allowable flexural strength",
            equation_latex=r"\frac{M_n}{\Omega_b}",
            substitution_latex=f"M_n/\\Omega_b = {Mn:.3f} / {omega_b}",
            result=Mn_allow,
            unit="kN-m/m",
            code_ref="AISI S100-16 Section F1 (Ω_b = 1.67)"
        ))
        capacity = Mn_allow
    
    # D/C ratio
    ratio = Mu / capacity if capacity > 0 else float('inf')
    steps.append(DesignStep(
        description="Demand/Capacity ratio",
        equation_latex=r"\frac{M_u}{\phi M_n} \leq 1.0",
        substitution_latex=f"{Mu:.3f} / {capacity:.3f}",
        result=ratio,
        unit="",
        code_ref="AISI S100-16 Section B3.2"
    ))
    
    return DesignCheckResult(
        check_name="Flexural Strength",
        demand=Mu,
        capacity=capacity,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        steps=steps,
        code_ref="AISI S100-16 Section F3.1"
    )


# =====================================================================
# SHEAR STRENGTH - AISI S100-16 Section G
# =====================================================================

def check_shear_strength(
    h: float,
    t: float,
    Fy: float,
    Vu: float,
    E: float = 200000.0,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check shear strength of deck web per AISI S100-16 Section G2.
    
    Args:
        h: Flat web depth (mm)
        t: Thickness (mm)
        Fy: Yield strength (MPa)
        Vu: Required shear (kN/m)
        E: Modulus of elasticity (MPa)
        method: Design method
        
    Returns:
        DesignCheckResult with shear check results
        
    Reference:
        AISI S100-16 Section G2 - Shear Strength of Webs Without Holes
        
    Equations:
        V_n = A_w × F_v  ... Eq. G2.1-1
        
        where A_w = h × t (web area)
        
        For h/t ≤ √(k_v × E / F_y):
            F_v = 0.60 × F_y  ... Eq. G2.1-2
            
        For √(k_v × E / F_y) < h/t ≤ 1.51√(k_v × E / F_y):
            F_v = 0.60 × √(k_v × E × F_y) / (h/t)  ... Eq. G2.1-3
            
        For h/t > 1.51√(k_v × E / F_y):
            F_v = π²k_v × E / (12(1-μ²)(h/t)²)  ... Eq. G2.1-4
            
        k_v = 5.34 (for unreinforced webs)
        
        LRFD: φ_v = 0.95
        ASD: Ω_v = 1.60
    """
    steps = []
    
    kv = 5.34  # Unreinforced web
    mu = 0.30  # Poisson's ratio
    
    # Web slenderness
    ht_ratio = h / t if t > 0 else 0
    
    steps.append(DesignStep(
        description="Web slenderness ratio",
        equation_latex=r"\frac{h}{t}",
        substitution_latex=f"{h:.1f} / {t:.2f}",
        result=ht_ratio,
        unit="",
        code_ref="AISI S100-16 Section G2"
    ))
    
    # Slenderness limits
    limit1 = np.sqrt(kv * E / Fy)
    limit2 = 1.51 * np.sqrt(kv * E / Fy)
    
    # Shear stress capacity Fv
    if ht_ratio <= limit1:
        # Yield limit (Eq. G2.1-2)
        Fv = 0.60 * Fy
        eq_ref = "Eq. G2.1-2"
    elif ht_ratio <= limit2:
        # Inelastic buckling (Eq. G2.1-3)
        Fv = 0.60 * np.sqrt(kv * E * Fy) / ht_ratio
        eq_ref = "Eq. G2.1-3"
    else:
        # Elastic buckling (Eq. G2.1-4)
        Fv = np.pi**2 * kv * E / (12 * (1 - mu**2) * ht_ratio**2)
        eq_ref = "Eq. G2.1-4"
    
    steps.append(DesignStep(
        description="Nominal shear stress",
        equation_latex=r"F_v",
        substitution_latex=f"F_v (from {eq_ref})",
        result=Fv,
        unit="MPa",
        code_ref=f"AISI S100-16 {eq_ref}"
    ))
    
    # Web area (per meter width)
    # For deck: use total web area based on pitch
    Aw = h * t  # mm² per web
    # Scale to per meter if needed
    
    # Nominal shear strength (Eq. G2.1-1)
    # Vn in N per web, need to scale for multiple webs per meter
    Vn_per_web = Aw * Fv / 1000  # kN per web
    
    steps.append(DesignStep(
        description="Nominal shear strength per web",
        equation_latex=r"V_n = A_w \times F_v",
        substitution_latex=f"V_n = {Aw:.0f} \\times {Fv:.1f}",
        result=Vn_per_web,
        unit="kN/web",
        code_ref="AISI S100-16 Eq. G2.1-1"
    ))
    
    # Design/Allowable strength
    if method == DesignMethod.LRFD:
        phi_v = 0.95
        Vn_design = phi_v * Vn_per_web
        capacity_label = "φ_v V_n"
        factor_ref = "φ_v = 0.95"
    else:
        omega_v = 1.60
        Vn_design = Vn_per_web / omega_v
        capacity_label = "V_n/Ω_v"
        factor_ref = "Ω_v = 1.60"
    
    steps.append(DesignStep(
        description="Design shear strength per web",
        equation_latex=capacity_label,
        substitution_latex=f"{capacity_label} = {Vn_design:.2f}",
        result=Vn_design,
        unit="kN/web",
        code_ref=f"AISI S100-16 Section G1 ({factor_ref})"
    ))
    
    # D/C ratio
    ratio = Vu / Vn_design if Vn_design > 0 else float('inf')
    
    return DesignCheckResult(
        check_name="Shear Strength",
        demand=Vu,
        capacity=Vn_design,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        steps=steps,
        code_ref="AISI S100-16 Section G2"
    )


# =====================================================================
# WEB CRIPPLING - AISI S100-16 Section G5
# =====================================================================

def check_web_crippling(
    t: float,
    h: float,
    N: float,
    R: float,
    theta: float,
    Fy: float,
    Pu: float,
    loading: LoadingCondition = LoadingCondition.IOF,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check web crippling strength per AISI S100-16 Section G5.
    
    Args:
        t: Web thickness (mm)
        h: Flat web depth (mm)
        N: Bearing length (mm)
        R: Inside bend radius (mm)
        theta: Angle between web and bearing surface (degrees)
        Fy: Yield strength (MPa)
        Pu: Required bearing load (kN per web)
        loading: Loading condition (EOF, IOF, ETF, ITF)
        method: Design method
        
    Returns:
        DesignCheckResult with web crippling check results
        
    Reference:
        AISI S100-16 Section G5 - Web Crippling Strength of Webs
        Without Holes
        
    Equations:
        P_n = C × t² × F_y × sin(θ) × [1 - C_R√(R/t)] × 
              [1 + C_N√(N/t)] × [1 - C_h√(h/t)]  ... Eq. G5-1
              
        Coefficients C, C_R, C_N, C_h from Table G5-1 based on loading
        
        LRFD: φ_w = 0.75-0.90 (varies by condition)
        ASD: Ω_w = 1.65-2.00
    """
    steps = []
    
    # Coefficients from AISI S100-16 Table G5-1
    # Format: (C, C_R, C_N, C_h, phi, omega)
    coefficients = {
        LoadingCondition.EOF: (4.0, 0.14, 0.35, 0.02, 0.75, 2.00),
        LoadingCondition.IOF: (13.0, 0.23, 0.14, 0.01, 0.80, 1.85),
        LoadingCondition.ETF: (2.0, 0.11, 0.37, 0.01, 0.75, 2.00),
        LoadingCondition.ITF: (7.5, 0.08, 0.12, 0.048, 0.90, 1.65),
    }
    
    C, C_R, C_N, C_h, phi_w, omega_w = coefficients[loading]
    
    # Angle in radians
    theta_rad = np.radians(theta)
    
    # Web crippling factors
    factor_R = 1 - C_R * np.sqrt(R / t) if t > 0 else 0
    factor_N = 1 + C_N * np.sqrt(N / t) if t > 0 else 1
    factor_h = 1 - C_h * np.sqrt(h / t) if t > 0 else 0
    
    # Ensure factors are non-negative
    factor_R = max(0, factor_R)
    factor_h = max(0, factor_h)
    
    steps.append(DesignStep(
        description="Web crippling reduction factors",
        equation_latex=r"[1 - C_R\sqrt{R/t}][1 + C_N\sqrt{N/t}][1 - C_h\sqrt{h/t}]",
        substitution_latex=f"[{factor_R:.3f}][{factor_N:.3f}][{factor_h:.3f}]",
        result=factor_R * factor_N * factor_h,
        unit="",
        code_ref="AISI S100-16 Eq. G5-1"
    ))
    
    # Nominal web crippling strength (Eq. G5-1)
    # Pn in N, convert to kN
    Pn = C * t**2 * Fy * np.sin(theta_rad) * factor_R * factor_N * factor_h / 1000
    
    steps.append(DesignStep(
        description="Nominal web crippling strength",
        equation_latex=r"P_n = C t^2 F_y \sin\theta \times factors",
        substitution_latex=f"P_n = {C} \\times {t:.2f}^2 \\times {Fy} \\times \\sin({theta}°)",
        result=Pn,
        unit="kN/web",
        code_ref=f"AISI S100-16 Eq. G5-1 ({loading.value})"
    ))
    
    # Design/Allowable strength
    if method == DesignMethod.LRFD:
        Pn_design = phi_w * Pn
        steps.append(DesignStep(
            description="Design web crippling strength",
            equation_latex=r"\phi_w P_n",
            substitution_latex=f"{phi_w} \\times {Pn:.2f}",
            result=Pn_design,
            unit="kN/web",
            code_ref=f"AISI S100-16 Section G5 (φ_w = {phi_w})"
        ))
        capacity = Pn_design
    else:
        Pn_allow = Pn / omega_w
        steps.append(DesignStep(
            description="Allowable web crippling strength",
            equation_latex=r"\frac{P_n}{\Omega_w}",
            substitution_latex=f"{Pn:.2f} / {omega_w}",
            result=Pn_allow,
            unit="kN/web",
            code_ref=f"AISI S100-16 Section G5 (Ω_w = {omega_w})"
        ))
        capacity = Pn_allow
    
    # D/C ratio
    ratio = Pu / capacity if capacity > 0 else float('inf')
    
    return DesignCheckResult(
        check_name=f"Web Crippling ({loading.value})",
        demand=Pu,
        capacity=capacity,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        steps=steps,
        code_ref="AISI S100-16 Section G5"
    )


# =====================================================================
# COMBINED BENDING AND WEB CRIPPLING - AISI S100-16 Section G6
# =====================================================================

def check_combined_bending_web_crippling(
    Mu: float,
    phi_Mn: float,
    Pu: float,
    phi_Pn: float,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check combined bending and web crippling per AISI S100-16 Section G6.
    
    Args:
        Mu: Required moment (kN-m/m)
        phi_Mn: Design flexural strength (kN-m/m)
        Pu: Required concentrated load (kN/web)
        phi_Pn: Design web crippling strength (kN/web)
        method: Design method
        
    Returns:
        DesignCheckResult with combined check results
        
    Reference:
        AISI S100-16 Section G6 - Combined Bending and Web Crippling
        
    Equations:
        For interior loading (IOF):
            (M_u / φ_b M_n) + (P_u / φ_w P_n) ≤ 1.32  ... Eq. G6-1
            
        For end reaction (EOF):
            (M_u / φ_b M_n) + (P_u / φ_w P_n) ≤ 1.52  ... Eq. G6-2
    """
    steps = []
    
    # Calculate interaction ratios
    M_ratio = Mu / phi_Mn if phi_Mn > 0 else 0
    P_ratio = Pu / phi_Pn if phi_Pn > 0 else 0
    
    # Combined ratio
    combined_ratio = M_ratio + P_ratio
    
    steps.append(DesignStep(
        description="Moment ratio",
        equation_latex=r"\frac{M_u}{\phi_b M_n}",
        substitution_latex=f"{Mu:.3f} / {phi_Mn:.3f}",
        result=M_ratio,
        unit="",
        code_ref="AISI S100-16 Eq. G6-1"
    ))
    
    steps.append(DesignStep(
        description="Web crippling ratio",
        equation_latex=r"\frac{P_u}{\phi_w P_n}",
        substitution_latex=f"{Pu:.3f} / {phi_Pn:.3f}",
        result=P_ratio,
        unit="",
        code_ref="AISI S100-16 Eq. G6-1"
    ))
    
    # Interaction limit (use 1.32 for IOF, conservative)
    limit = 1.32
    
    steps.append(DesignStep(
        description="Combined interaction",
        equation_latex=r"\frac{M_u}{\phi_b M_n} + \frac{P_u}{\phi_w P_n} \leq 1.32",
        substitution_latex=f"{M_ratio:.3f} + {P_ratio:.3f} = {combined_ratio:.3f}",
        result=combined_ratio,
        unit="",
        code_ref="AISI S100-16 Eq. G6-1"
    ))
    
    # D/C ratio (normalized to limit)
    ratio = combined_ratio / limit
    
    return DesignCheckResult(
        check_name="Combined Bending & Web Crippling",
        demand=combined_ratio,
        capacity=limit,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        steps=steps,
        code_ref="AISI S100-16 Section G6"
    )


# =====================================================================
# DEFLECTION CHECK - SDI C-2017
# =====================================================================

def check_deflection(
    Id: float,
    E: float,
    span: float,
    w: float,
    limit_ratio: float = 180.0,
    span_type: str = "simple"
) -> DesignCheckResult:
    """
    Check deck deflection per SDI C-2017 recommendations.
    
    Args:
        Id: Deflection moment of inertia (mm⁴/m)
        E: Modulus of elasticity (MPa)
        span: Clear span (mm)
        w: Uniform load (kN/m²)
        limit_ratio: Deflection limit as L/ratio (default L/180)
        span_type: "simple", "two_span", "three_span"
        
    Returns:
        DesignCheckResult with deflection check results
        
    Reference:
        SDI C-2017 Section 2.4 - Deflection
        
    Equations:
        Simple span:
            Δ = (5 × w × L⁴) / (384 × E × I)
            
        Two-span continuous:
            Δ = (w × L⁴) / (185 × E × I)
            
        Three-span continuous:
            Δ = (w × L⁴) / (145 × E × I)
            
        Limit: Δ ≤ L / 180 (typical for construction)
    """
    steps = []
    
    # Convert units
    # w in kN/m², span in mm, I in mm⁴/m
    # Need: w in N/mm (per unit width), span in mm
    w_per_mm = w * 1000 / 1000  # N/mm per mm width
    
    # Deflection coefficient based on span type
    coef = {
        "simple": 5/384,
        "two_span": 1/185,
        "three_span": 1/145
    }
    
    k_defl = coef.get(span_type, 5/384)
    
    # Calculate deflection
    # Δ = k × w × L⁴ / (E × I)
    delta = k_defl * w_per_mm * span**4 / (E * Id) if Id > 0 else float('inf')
    
    steps.append(DesignStep(
        description="Calculated deflection",
        equation_latex=r"\Delta = k \times \frac{w L^4}{E I_d}",
        substitution_latex=f"\\Delta = {k_defl:.4f} \\times ({w_per_mm:.2f} \\times {span}^4) / ({E} \\times {Id:.0f})",
        result=delta,
        unit="mm",
        code_ref=f"SDI C-2017 ({span_type} span)"
    ))
    
    # Allowable deflection
    delta_allow = span / limit_ratio
    
    steps.append(DesignStep(
        description="Allowable deflection",
        equation_latex=r"\Delta_{allow} = \frac{L}{180}",
        substitution_latex=f"\\Delta_{{allow}} = {span} / {limit_ratio}",
        result=delta_allow,
        unit="mm",
        code_ref="SDI C-2017 Section 2.4"
    ))
    
    # D/C ratio
    ratio = delta / delta_allow if delta_allow > 0 else float('inf')
    
    return DesignCheckResult(
        check_name="Deflection",
        demand=delta,
        capacity=delta_allow,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        steps=steps,
        code_ref="SDI C-2017 Section 2.4"
    )


# =====================================================================
# COMPREHENSIVE DECK DESIGN
# =====================================================================

def design_metal_deck(
    geometry: DeckGeometry,
    properties: DeckSectionProperties,
    material: DeckMaterial,
    span: float,
    w_construction: float,
    P_concentrated: float = 1.1,
    bearing_length: float = 50.0,
    method: DesignMethod = DesignMethod.LRFD,
    span_type: str = "simple"
) -> Dict[str, DesignCheckResult]:
    """
    Perform comprehensive metal deck design checks.
    
    Checks include:
    1. Positive moment flexure
    2. Negative moment flexure (for continuous spans)
    3. Shear
    4. Web crippling (end and interior)
    5. Combined bending and web crippling
    6. Deflection
    
    Args:
        geometry: Deck geometry
        properties: Section properties (gross and effective)
        material: Material properties
        span: Clear span (mm)
        w_construction: Construction load (kN/m²)
        P_concentrated: Concentrated load (kN), default 1.1 kN (worker)
        bearing_length: Bearing length at supports (mm)
        method: Design method
        span_type: "simple", "two_span", or "three_span"
        
    Returns:
        Dictionary of DesignCheckResult for each check
        
    Reference:
        AISI S100-16, SDI C-2017
    """
    results = {}
    
    t = geometry.t
    h = geometry.web_flat_width
    hr = geometry.hr
    R = 2 * t  # Typical inside bend radius
    theta = geometry.theta
    
    Fy = material.Fy
    E = material.E
    
    # Load factors
    if method == DesignMethod.LRFD:
        load_factor = 1.6  # Construction live load factor
    else:
        load_factor = 1.0  # ASD
    
    # Calculate demands
    # Moment coefficients
    if span_type == "simple":
        M_coef = 1/8
        V_coef = 0.5
    elif span_type == "two_span":
        M_coef = 0.07  # Approximate for two-span
        V_coef = 0.625
    else:  # three_span
        M_coef = 0.08
        V_coef = 0.60
    
    # Required moment (kN-m per meter width)
    w_factored = load_factor * w_construction  # kN/m² per m width = kN/m
    Mu = M_coef * w_factored * (span/1000)**2  # kN-m/m
    
    # Required shear (kN per meter width)
    Vu = V_coef * w_factored * (span/1000)  # kN/m
    
    # 1. Flexural Strength (Positive Moment)
    results["Flexure_Pos"] = check_flexural_strength(
        Se=properties.Se_pos,
        Fy=Fy,
        Mu=Mu,
        method=method
    )
    
    # 2. Flexural Strength (Negative Moment) - for continuous spans
    if span_type != "simple":
        Mu_neg = 0.125 * w_factored * (span/1000)**2  # Approximate negative moment
        results["Flexure_Neg"] = check_flexural_strength(
            Se=properties.Se_neg,
            Fy=Fy,
            Mu=Mu_neg,
            method=method
        )
    
    # 3. Shear Strength
    # Shear per web
    n_webs_per_m = 1000 / geometry.pitch * 2  # Two webs per rib
    Vu_per_web = Vu / n_webs_per_m if n_webs_per_m > 0 else Vu
    
    results["Shear"] = check_shear_strength(
        h=h,
        t=t,
        Fy=Fy,
        Vu=Vu_per_web,
        E=E,
        method=method
    )
    
    # 4. Web Crippling - End (EOF)
    # End reaction
    Pu_end = V_coef * w_factored * (span/1000)  # Total reaction per meter
    Pu_per_web = Pu_end / n_webs_per_m if n_webs_per_m > 0 else Pu_end
    
    results["WebCrip_End"] = check_web_crippling(
        t=t,
        h=h,
        N=bearing_length,
        R=R,
        theta=theta,
        Fy=Fy,
        Pu=Pu_per_web,
        loading=LoadingCondition.EOF,
        method=method
    )
    
    # 5. Web Crippling - Interior (IOF) for concentrated load
    Pu_conc = load_factor * P_concentrated / n_webs_per_m if n_webs_per_m > 0 else load_factor * P_concentrated
    
    results["WebCrip_Int"] = check_web_crippling(
        t=t,
        h=h,
        N=50,  # Typical foot size
        R=R,
        theta=theta,
        Fy=Fy,
        Pu=Pu_conc,
        loading=LoadingCondition.IOF,
        method=method
    )
    
    # 6. Combined Bending and Web Crippling
    # At midspan under concentrated load
    M_at_load = Mu + load_factor * P_concentrated * span / (4 * 1000)  # kN-m/m
    
    results["Combined"] = check_combined_bending_web_crippling(
        Mu=M_at_load,
        phi_Mn=results["Flexure_Pos"].capacity,
        Pu=Pu_conc,
        phi_Pn=results["WebCrip_Int"].capacity,
        method=method
    )
    
    # 7. Deflection
    results["Deflection"] = check_deflection(
        Id=properties.Id,
        E=E,
        span=span,
        w=w_construction,
        limit_ratio=180,
        span_type=span_type
    )
    
    return results


def generate_design_summary(results: Dict[str, DesignCheckResult]) -> str:
    """
    Generate formatted design summary.
    
    Args:
        results: Dictionary of design check results
        
    Returns:
        Formatted summary string
    """
    lines = []
    lines.append("=" * 70)
    lines.append("METAL DECK DESIGN SUMMARY")
    lines.append("Per AISI S100-16 and SDI C-2017")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"{'Check':<30} {'Demand':>10} {'Capacity':>10} {'D/C':>8} {'Status':>8}")
    lines.append("-" * 70)
    
    all_pass = True
    for name, result in results.items():
        status_symbol = "✓" if result.status == "PASS" else "✗"
        lines.append(
            f"{result.check_name:<30} "
            f"{result.demand:>10.3f} "
            f"{result.capacity:>10.3f} "
            f"{result.ratio:>8.3f} "
            f"{status_symbol:>8}"
        )
        if result.status != "PASS":
            all_pass = False
    
    lines.append("-" * 70)
    overall = "ALL CHECKS PASS" if all_pass else "DESIGN NOT ADEQUATE"
    lines.append(f"Overall: {overall}")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# =====================================================================
# Module Testing
# =====================================================================
if __name__ == "__main__":
    print("Testing Metal Deck Design Module")
    print("=" * 70)
    
    # Create test geometry (typical 2" x 6" deck)
    geometry = DeckGeometry(
        hr=50.8,          # 2 inch
        wr_top=114,       # mm
        wr_bot=38,        # mm
        pitch=152.4,      # 6 inch
        t=0.9,            # mm (20 gage)
        theta=80,         # degrees
        n_ribs=6          # ~1m strip
    )
    
    # Approximate section properties (would come from DXF parser)
    properties = DeckSectionProperties(
        Ag=850,           # mm²/m (approximate)
        Ig=180000,        # mm⁴/m
        Sg_top=5300,      # mm³/m
        Sg_bot=4800,      # mm³/m
        ycg=22,           # mm
        # Effective properties (assuming ~85% reduction)
        Ae=720,
        Ie=153000,
        Se_pos=4500,
        Se_neg=4100,
        yce=23,
        Id=170000         # SDI average method
    )
    
    # Material
    material = DeckMaterial(
        Fy=230,           # MPa (Grade 33)
        Fu=310,
        E=200000
    )
    
    # Design parameters
    span = 2400          # mm (8 ft unshored)
    w_construction = 2.5  # kN/m² (wet concrete + construction)
    
    print(f"\nDesign Parameters:")
    print(f"  Deck: hr={geometry.hr}mm, t={geometry.t}mm, pitch={geometry.pitch}mm")
    print(f"  Span: {span}mm (simple)")
    print(f"  Load: {w_construction} kN/m² (construction)")
    print(f"  Material: Fy={material.Fy} MPa")
    
    # Run design checks
    results = design_metal_deck(
        geometry=geometry,
        properties=properties,
        material=material,
        span=span,
        w_construction=w_construction,
        method=DesignMethod.LRFD,
        span_type="simple"
    )
    
    # Print summary
    print("\n" + generate_design_summary(results))
    
    # Print detailed steps for one check
    print("\nDetailed Calculation - Flexural Strength:")
    print("-" * 50)
    for step in results["Flexure_Pos"].steps:
        print(f"  {step.description}: {step.result:.3f} {step.unit}")
        print(f"    Ref: {step.code_ref}")
