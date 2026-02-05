"""
Pre-Composite Steel Beam Design - DETAILED PROFESSIONAL CALCULATIONS
=====================================================================

Per AISC 360-16 Specification for Structural Steel Buildings
Chapter F - Flexural Members
Chapter G - Shear

This module provides step-by-step calculations for steel beam design
during the construction (pre-composite) stage before deck concrete cures.

Author: CompositeBeam Pro
Version: 2.9
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class DetailedCalcStep:
    """A single calculation step with full professional documentation."""
    step_number: int
    title: str
    description: str
    equation: str
    substitution: str
    result: float
    unit: str
    code_ref: str
    status: str = "INFO"
    notes: str = ""


@dataclass
class DetailedCalcSection:
    """A section of calculations."""
    section_number: int
    title: str
    description: str
    code_ref: str
    steps: List[DetailedCalcStep] = field(default_factory=list)
    conclusion: str = ""
    status: str = "PASS"


@dataclass 
class PreCompositeDesignReport:
    """Complete design report for pre-composite steel beam."""
    project_info: Dict
    beam_designation: str
    sections: List[DetailedCalcSection] = field(default_factory=list)
    overall_status: str = "PASS"
    summary: str = ""
    
    def add_section(self, section: DetailedCalcSection):
        self.sections.append(section)
        if section.status == "FAIL":
            self.overall_status = "FAIL"


# =============================================================================
# SECTION 1: STEEL SECTION PROPERTIES
# =============================================================================

def calc_section_properties_precomp(
    section_name: str,
    d: float, bf: float, tf: float, tw: float,
    A: float, Ix: float, Sx: float, Zx: float,
    Fy: float, E: float
) -> DetailedCalcSection:
    """Calculate and document steel section properties and classification."""
    
    section = DetailedCalcSection(
        section_number=1,
        title="STEEL SECTION PROPERTIES & CLASSIFICATION",
        description="Document steel section properties and check local buckling classification per AISC 360-16.",
        code_ref="AISC 360-16 Table B4.1b"
    )
    steps = []
    step_num = 1
    
    # Step 1: Section identification
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Steel Section",
        description=f"Selected steel section: {section_name}",
        equation="Section from AISC Manual Table 1-1",
        substitution=f"Section = {section_name}",
        result=d,
        unit="mm (depth)",
        code_ref="AISC 360-16 Table 1-1"
    ))
    step_num += 1
    
    # Step 2: Section dimensions
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Section Dimensions",
        description="Key geometric properties of the steel section.",
        equation="d, bf, tf, tw from section tables",
        substitution=f"d = {d:.1f} mm, bf = {bf:.1f} mm, tf = {tf:.1f} mm, tw = {tw:.1f} mm",
        result=d,
        unit="mm",
        code_ref="AISC Manual Table 1-1"
    ))
    step_num += 1
    
    # Step 3: Section properties
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Section Properties",
        description="Area, moment of inertia, and section moduli.",
        equation="A, Ix, Sx, Zx from section tables",
        substitution=f"A = {A:.0f} mm², Ix = {Ix/1e6:.2f}×10⁶ mm⁴, Sx = {Sx/1e3:.2f}×10³ mm³, Zx = {Zx/1e3:.2f}×10³ mm³",
        result=Ix,
        unit="mm⁴",
        code_ref="AISC Manual Table 1-1"
    ))
    step_num += 1
    
    # Step 4: Material properties
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Material Properties",
        description="Steel yield strength and modulus of elasticity.",
        equation="Fy, E from material specification",
        substitution=f"Fy = {Fy:.0f} MPa, E = {E:.0f} MPa",
        result=Fy,
        unit="MPa",
        code_ref="AISC 360-16 Table A3.1"
    ))
    step_num += 1
    
    # Step 5: Flange compactness
    lambda_f = bf / (2 * tf)
    lambda_pf = 0.38 * math.sqrt(E / Fy)
    lambda_rf = 1.0 * math.sqrt(E / Fy)
    
    if lambda_f <= lambda_pf:
        flange_class = "Compact"
        flange_status = "PASS"
    elif lambda_f <= lambda_rf:
        flange_class = "Noncompact"
        flange_status = "WARNING"
    else:
        flange_class = "Slender"
        flange_status = "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Flange Compactness Check",
        description="Check flange width-to-thickness ratio for local buckling.",
        equation="λf = bf/(2×tf) ≤ λpf = 0.38√(E/Fy)",
        substitution=f"λf = {bf:.1f}/(2×{tf:.1f}) = {lambda_f:.2f} vs λpf = 0.38×√({E}/{Fy}) = {lambda_pf:.2f}",
        result=lambda_f,
        unit="",
        code_ref="AISC 360-16 Table B4.1b Case 10",
        status=flange_status,
        notes=f"Flange is {flange_class}"
    ))
    step_num += 1
    
    # Step 6: Web compactness
    h = d - 2 * tf
    lambda_w = h / tw
    lambda_pw = 3.76 * math.sqrt(E / Fy)
    lambda_rw = 5.70 * math.sqrt(E / Fy)
    
    if lambda_w <= lambda_pw:
        web_class = "Compact"
        web_status = "PASS"
    elif lambda_w <= lambda_rw:
        web_class = "Noncompact"
        web_status = "WARNING"
    else:
        web_class = "Slender"
        web_status = "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Compactness Check",
        description="Check web height-to-thickness ratio for local buckling.",
        equation="λw = h/tw ≤ λpw = 3.76√(E/Fy)",
        substitution=f"λw = ({d:.1f}-2×{tf:.1f})/{tw:.1f} = {lambda_w:.2f} vs λpw = 3.76×√({E}/{Fy}) = {lambda_pw:.2f}",
        result=lambda_w,
        unit="",
        code_ref="AISC 360-16 Table B4.1b Case 15",
        status=web_status,
        notes=f"Web is {web_class}"
    ))
    step_num += 1
    
    # Step 7: Overall classification
    if flange_class == "Compact" and web_class == "Compact":
        overall_class = "Compact"
        overall_status = "PASS"
    elif flange_class == "Slender" or web_class == "Slender":
        overall_class = "Slender"
        overall_status = "FAIL"
    else:
        overall_class = "Noncompact"
        overall_status = "WARNING"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Overall Section Classification",
        description="Section classified based on most restrictive element.",
        equation="Classification = most restrictive of (flange, web)",
        substitution=f"Flange: {flange_class}, Web: {web_class} → Overall: {overall_class}",
        result=1.0 if overall_class == "Compact" else 0.5,
        unit="",
        code_ref="AISC 360-16 §B4",
        status=overall_status,
        notes=f"Section is {overall_class}"
    ))
    
    section.steps = steps
    section.conclusion = f"Steel section {section_name} is {overall_class}. λf = {lambda_f:.2f}, λw = {lambda_w:.2f}"
    section.status = overall_status
    
    return section


# =============================================================================
# SECTION 2: FLEXURAL STRENGTH
# =============================================================================

def calc_flexural_strength_precomp(
    d: float, bf: float, tf: float, tw: float,
    A: float, Ix: float, Sx: float, Zx: float,
    Fy: float, E: float,
    Lb: float,
    Cb: float = 1.0,
    method: str = "LRFD"
) -> Tuple[DetailedCalcSection, Dict]:
    """
    Calculate flexural strength for pre-composite stage per AISC 360-16 Chapter F.
    
    Parameters:
        Lb: Unbraced length (mm)
        Cb: Lateral-torsional buckling modification factor
        method: "LRFD" or "ASD"
    """
    section = DetailedCalcSection(
        section_number=2,
        title="FLEXURAL STRENGTH (PRE-COMPOSITE)",
        description="Calculate available flexural strength for construction stage when beam is unshored and unbraced by deck.",
        code_ref="AISC 360-16 Chapter F"
    )
    steps = []
    step_num = 1
    
    phi_b = 0.90 if method == "LRFD" else 1.0
    omega_b = 1.67 if method == "ASD" else 1.0
    
    # Step 1: Plastic moment
    Mp = Fy * Zx / 1e6  # kN⋅m
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Plastic Moment Mp",
        description="The plastic moment is the moment to fully plastify the cross-section. This is the upper bound of flexural strength.",
        equation="Mp = Fy × Zx",
        substitution=f"Mp = {Fy:.0f} × {Zx/1e3:.2f}×10³ / 10⁶ = {Mp:.2f} kN⋅m",
        result=Mp,
        unit="kN⋅m",
        code_ref="AISC 360-16 Eq. F2-1"
    ))
    step_num += 1
    
    # Step 2: Yield moment
    My = Fy * Sx / 1e6  # kN⋅m
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Yield Moment My",
        description="The moment at which the extreme fiber first reaches yield stress.",
        equation="My = Fy × Sx",
        substitution=f"My = {Fy:.0f} × {Sx/1e3:.2f}×10³ / 10⁶ = {My:.2f} kN⋅m",
        result=My,
        unit="kN⋅m",
        code_ref="AISC 360-16 §F2"
    ))
    step_num += 1
    
    # Step 3: Torsional constant (approximate for doubly symmetric I-shapes)
    # J ≈ 2 × bf × tf³/3 + (d - 2tf) × tw³/3
    h = d - 2 * tf
    J = 2 * bf * tf**3 / 3 + h * tw**3 / 3
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Torsional Constant J",
        description="Approximate torsional constant for I-shaped section.",
        equation="J ≈ 2×bf×tf³/3 + h×tw³/3",
        substitution=f"J ≈ 2×{bf:.1f}×{tf:.1f}³/3 + {h:.1f}×{tw:.1f}³/3 = {J:.0f} mm⁴",
        result=J,
        unit="mm⁴",
        code_ref="AISC Manual"
    ))
    step_num += 1
    
    # Step 4: Warping constant (approximate)
    # Cw ≈ Iy × h²/4
    Iy = 2 * tf * bf**3 / 12 + h * tw**3 / 12
    Cw = Iy * (d - tf)**2 / 4
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Warping Constant Cw",
        description="Warping constant for lateral-torsional buckling calculations.",
        equation="Cw ≈ Iy × (d-tf)²/4",
        substitution=f"Cw ≈ {Iy:.0f} × ({d:.1f}-{tf:.1f})²/4 = {Cw/1e6:.2f}×10⁶ mm⁶",
        result=Cw,
        unit="mm⁶",
        code_ref="AISC Manual"
    ))
    step_num += 1
    
    # Step 5: Radius of gyration
    rts = math.sqrt(math.sqrt(Iy * Cw) / Sx) if Sx > 0 else bf / 4
    ry = math.sqrt(Iy / A) if A > 0 else bf / math.sqrt(12)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Radius of Gyration",
        description="Effective radius of gyration for LTB and weak-axis radius of gyration.",
        equation="rts = √(√(Iy×Cw)/Sx), ry = √(Iy/A)",
        substitution=f"rts = {rts:.2f} mm, ry = {ry:.2f} mm",
        result=rts,
        unit="mm",
        code_ref="AISC 360-16 §F2"
    ))
    step_num += 1
    
    # Step 6: c parameter
    c = 1.0  # For doubly symmetric I-shapes
    ho = d - tf  # Distance between flange centroids
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="LTB Parameters",
        description="Parameters for lateral-torsional buckling equations.",
        equation="c = 1.0 for doubly symmetric I-shapes, ho = d - tf",
        substitution=f"c = {c}, ho = {d:.1f} - {tf:.1f} = {ho:.2f} mm",
        result=c,
        unit="",
        code_ref="AISC 360-16 §F2"
    ))
    step_num += 1
    
    # Step 7: Limiting unbraced lengths
    Lp = 1.76 * ry * math.sqrt(E / Fy)
    
    # Lr calculation
    G = 77200  # Shear modulus MPa
    Lr_term1 = (J * c) / (Sx * ho)
    Lr_term2 = 6.76 * (0.7 * Fy / E)**2
    Lr = 1.95 * rts * (E / (0.7 * Fy)) * math.sqrt(Lr_term1 + math.sqrt(Lr_term1**2 + Lr_term2))
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Limiting Unbraced Length Lp",
        description="The limiting laterally unbraced length for yielding (below which LTB does not occur).",
        equation="Lp = 1.76 × ry × √(E/Fy)",
        substitution=f"Lp = 1.76 × {ry:.2f} × √({E}/{Fy}) = {Lp:.0f} mm = {Lp/1000:.2f} m",
        result=Lp,
        unit="mm",
        code_ref="AISC 360-16 Eq. F2-5"
    ))
    step_num += 1
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Limiting Unbraced Length Lr",
        description="The limiting unbraced length for inelastic LTB (above which elastic LTB controls).",
        equation="Lr = 1.95×rts×(E/0.7Fy)×√[(J×c)/(Sx×ho)+√[((J×c)/(Sx×ho))²+6.76(0.7Fy/E)²]]",
        substitution=f"Lr = {Lr:.0f} mm = {Lr/1000:.2f} m",
        result=Lr,
        unit="mm",
        code_ref="AISC 360-16 Eq. F2-6"
    ))
    step_num += 1
    
    # Step 8: Unbraced length classification
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Unbraced Length",
        description=f"Actual unbraced length Lb = {Lb:.0f} mm = {Lb/1000:.2f} m. Compare to Lp and Lr.",
        equation="Check: Lb vs Lp vs Lr",
        substitution=f"Lb = {Lb:.0f} mm, Lp = {Lp:.0f} mm, Lr = {Lr:.0f} mm",
        result=Lb,
        unit="mm",
        code_ref="AISC 360-16 §F2.2"
    ))
    step_num += 1
    
    # Step 9: Cb factor
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Cb Factor",
        description="Lateral-torsional buckling modification factor. Cb = 1.0 is conservative for uniform moment.",
        equation="Cb = 12.5Mmax / (2.5Mmax + 3MA + 4MB + 3MC)",
        substitution=f"Cb = {Cb:.2f} (given or assumed)",
        result=Cb,
        unit="",
        code_ref="AISC 360-16 Eq. F1-1"
    ))
    step_num += 1
    
    # Step 10: Nominal flexural strength
    if Lb <= Lp:
        # Yielding controls
        Mn = Mp
        limit_state = "Yielding (Lb ≤ Lp)"
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Nominal Flexural Strength (Yielding)",
            description="Since Lb ≤ Lp, lateral-torsional buckling does not occur and yielding controls.",
            equation="Mn = Mp (for Lb ≤ Lp)",
            substitution=f"Lb = {Lb:.0f} mm ≤ Lp = {Lp:.0f} mm → Mn = Mp = {Mp:.2f} kN⋅m",
            result=Mn,
            unit="kN⋅m",
            code_ref="AISC 360-16 Eq. F2-1",
            notes="Yielding controls - full plastic moment achieved"
        ))
        
    elif Lb <= Lr:
        # Inelastic LTB
        Mn_ltb = Cb * (Mp - (Mp - 0.7 * My) * (Lb - Lp) / (Lr - Lp))
        Mn = min(Mn_ltb, Mp)
        limit_state = "Inelastic LTB (Lp < Lb ≤ Lr)"
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Nominal Flexural Strength (Inelastic LTB)",
            description="Since Lp < Lb ≤ Lr, inelastic lateral-torsional buckling controls with linear interpolation.",
            equation="Mn = Cb × [Mp - (Mp - 0.7×Fy×Sx) × (Lb-Lp)/(Lr-Lp)] ≤ Mp",
            substitution=f"Mn = {Cb:.2f} × [{Mp:.2f} - ({Mp:.2f} - 0.7×{My:.2f}) × ({Lb:.0f}-{Lp:.0f})/({Lr:.0f}-{Lp:.0f})] = {Mn_ltb:.2f} kN⋅m",
            result=Mn,
            unit="kN⋅m",
            code_ref="AISC 360-16 Eq. F2-2",
            notes=f"Inelastic LTB controls. Cb amplification applied."
        ))
        
    else:
        # Elastic LTB
        Fe = (Cb * math.pi**2 * E) / (Lb / rts)**2
        Fcr = Fe * math.sqrt(1 + 0.078 * (J * c) / (Sx * ho) * (Lb / rts)**2)
        Mn_ltb = Fcr * Sx / 1e6
        Mn = min(Mn_ltb, Mp)
        limit_state = "Elastic LTB (Lb > Lr)"
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Nominal Flexural Strength (Elastic LTB)",
            description="Since Lb > Lr, elastic lateral-torsional buckling controls.",
            equation="Fcr = Cb×π²×E/(Lb/rts)² × √[1 + 0.078×(J×c)/(Sx×ho)×(Lb/rts)²], Mn = Fcr×Sx",
            substitution=f"Fcr = {Fcr:.1f} MPa, Mn = {Fcr:.1f} × {Sx/1e3:.2f}×10³ / 10⁶ = {Mn_ltb:.2f} kN⋅m",
            result=Mn,
            unit="kN⋅m",
            code_ref="AISC 360-16 Eq. F2-3, F2-4",
            notes=f"Elastic LTB controls. Fcr = {Fcr:.1f} MPa"
        ))
    
    step_num += 1
    
    # Step 11: Design strength
    if method == "LRFD":
        phi_Mn = phi_b * Mn
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Design Flexural Strength (LRFD)",
            description="The design flexural strength is the nominal strength multiplied by the resistance factor.",
            equation="φbMn = φb × Mn",
            substitution=f"φbMn = {phi_b} × {Mn:.2f} = {phi_Mn:.2f} kN⋅m",
            result=phi_Mn,
            unit="kN⋅m",
            code_ref="AISC 360-16 §F1"
        ))
        design_strength = phi_Mn
    else:
        Mn_omega = Mn / omega_b
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Allowable Flexural Strength (ASD)",
            description="The allowable flexural strength is the nominal strength divided by the safety factor.",
            equation="Mn/Ωb = Mn / Ωb",
            substitution=f"Mn/Ωb = {Mn:.2f} / {omega_b} = {Mn_omega:.2f} kN⋅m",
            result=Mn_omega,
            unit="kN⋅m",
            code_ref="AISC 360-16 §F1"
        ))
        design_strength = Mn_omega
    
    section.steps = steps
    section.conclusion = f"Limit state: {limit_state}. Mn = {Mn:.2f} kN⋅m, Design strength = {design_strength:.2f} kN⋅m"
    section.status = "PASS"
    
    results = {
        'Mp': Mp,
        'My': My,
        'Lp': Lp,
        'Lr': Lr,
        'Lb': Lb,
        'Cb': Cb,
        'Mn': Mn,
        'phi_Mn': design_strength,
        'limit_state': limit_state
    }
    
    return section, results


# =============================================================================
# SECTION 3: SHEAR STRENGTH
# =============================================================================

def calc_shear_strength_precomp(
    d: float, tw: float,
    Fy: float, E: float,
    method: str = "LRFD"
) -> Tuple[DetailedCalcSection, Dict]:
    """Calculate shear strength per AISC 360-16 Chapter G."""
    
    section = DetailedCalcSection(
        section_number=3,
        title="SHEAR STRENGTH (PRE-COMPOSITE)",
        description="Calculate available shear strength of steel beam per AISC 360-16 Chapter G.",
        code_ref="AISC 360-16 §G2.1"
    )
    steps = []
    step_num = 1
    
    phi_v = 0.90 if method == "LRFD" else 1.0
    omega_v = 1.67 if method == "ASD" else 1.0
    
    # Step 1: Web area
    Aw = d * tw
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Area",
        description="The shear area is the overall depth times web thickness.",
        equation="Aw = d × tw",
        substitution=f"Aw = {d:.1f} × {tw:.1f} = {Aw:.0f} mm²",
        result=Aw,
        unit="mm²",
        code_ref="AISC 360-16 §G2.1"
    ))
    step_num += 1
    
    # Step 2: Web slenderness
    lambda_w = d / tw
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Slenderness Ratio",
        description="Web height-to-thickness ratio for shear buckling check.",
        equation="h/tw ≈ d/tw (conservative)",
        substitution=f"h/tw ≈ {d:.1f}/{tw:.1f} = {lambda_w:.1f}",
        result=lambda_w,
        unit="",
        code_ref="AISC 360-16 §G2.1"
    ))
    step_num += 1
    
    # Step 3: Shear buckling limits
    kv = 5.34  # No transverse stiffeners
    limit_1 = 1.10 * math.sqrt(kv * E / Fy)
    limit_2 = 1.37 * math.sqrt(kv * E / Fy)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Shear Buckling Limits",
        description="Limiting slenderness ratios for web shear coefficient.",
        equation="1.10√(kv×E/Fy) and 1.37√(kv×E/Fy)",
        substitution=f"1.10×√({kv}×{E}/{Fy}) = {limit_1:.1f}, 1.37×√({kv}×{E}/{Fy}) = {limit_2:.1f}",
        result=limit_1,
        unit="",
        code_ref="AISC 360-16 §G2.1"
    ))
    step_num += 1
    
    # Step 4: Web shear coefficient
    if lambda_w <= limit_1:
        Cv1 = 1.0
        shear_type = "Web yields in shear"
    elif lambda_w <= limit_2:
        Cv1 = limit_1 / lambda_w
        shear_type = "Inelastic web shear buckling"
    else:
        Cv1 = 1.51 * kv * E / (Fy * lambda_w**2)
        shear_type = "Elastic web shear buckling"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Shear Coefficient Cv1",
        description="Accounts for shear buckling strength of web.",
        equation="Cv1 = 1.0 if h/tw ≤ 1.10√(kv×E/Fy); else interpolate or elastic buckling",
        substitution=f"h/tw = {lambda_w:.1f}, Cv1 = {Cv1:.3f}",
        result=Cv1,
        unit="",
        code_ref="AISC 360-16 §G2.1(a)",
        notes=shear_type
    ))
    step_num += 1
    
    # Step 5: Nominal shear strength
    Vn = 0.6 * Fy * Aw * Cv1 / 1000  # kN
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Nominal Shear Strength",
        description="Nominal shear strength based on web yielding or buckling.",
        equation="Vn = 0.6 × Fy × Aw × Cv1",
        substitution=f"Vn = 0.6 × {Fy} × {Aw:.0f} × {Cv1:.3f} / 1000 = {Vn:.1f} kN",
        result=Vn,
        unit="kN",
        code_ref="AISC 360-16 Eq. G2-1"
    ))
    step_num += 1
    
    # Step 6: Design strength
    if method == "LRFD":
        phi_Vn = phi_v * Vn
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Design Shear Strength (LRFD)",
            description="Design shear strength is nominal strength times resistance factor.",
            equation="φvVn = φv × Vn",
            substitution=f"φvVn = {phi_v} × {Vn:.1f} = {phi_Vn:.1f} kN",
            result=phi_Vn,
            unit="kN",
            code_ref="AISC 360-16 §G1"
        ))
        design_strength = phi_Vn
    else:
        Vn_omega = Vn / omega_v
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Allowable Shear Strength (ASD)",
            description="Allowable shear strength is nominal strength divided by safety factor.",
            equation="Vn/Ωv = Vn / Ωv",
            substitution=f"Vn/Ωv = {Vn:.1f} / {omega_v} = {Vn_omega:.1f} kN",
            result=Vn_omega,
            unit="kN",
            code_ref="AISC 360-16 §G1"
        ))
        design_strength = Vn_omega
    
    section.steps = steps
    section.conclusion = f"Vn = {Vn:.1f} kN ({shear_type}), Design strength = {design_strength:.1f} kN"
    section.status = "PASS"
    
    results = {
        'Aw': Aw,
        'Cv1': Cv1,
        'Vn': Vn,
        'phi_Vn': design_strength,
        'shear_type': shear_type
    }
    
    return section, results


# =============================================================================
# SECTION 4: DEFLECTION
# =============================================================================

def calc_deflection_precomp(
    L: float,
    Ix: float,
    E: float,
    w_precomp: float,
    defl_limit: float = 240
) -> Tuple[DetailedCalcSection, Dict]:
    """
    Calculate pre-composite deflection.
    
    Parameters:
        L: Span (mm)
        Ix: Steel moment of inertia (mm⁴)
        E: Elastic modulus (MPa)
        w_precomp: Pre-composite uniform load (kN/m)
        defl_limit: Span/limit (default L/240)
    """
    section = DetailedCalcSection(
        section_number=4,
        title="DEFLECTION (PRE-COMPOSITE)",
        description="Calculate beam deflection during construction stage under wet concrete and construction loads.",
        code_ref="IBC Table 1604.3"
    )
    steps = []
    step_num = 1
    
    # Step 1: Load
    w_Nmm = w_precomp  # kN/m = N/mm
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Pre-Composite Load",
        description="Total construction load including wet concrete, beam self-weight, and construction live load.",
        equation="w_precomp = w_DL + w_const",
        substitution=f"w_precomp = {w_precomp:.3f} kN/m",
        result=w_precomp,
        unit="kN/m",
        code_ref=""
    ))
    step_num += 1
    
    # Step 2: Deflection calculation
    delta = 5 * w_Nmm * L**4 / (384 * E * Ix)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Pre-Composite Deflection",
        description="Maximum deflection under uniformly distributed load using steel section Ix only.",
        equation="δ = 5 × w × L⁴ / (384 × E × Ix)",
        substitution=f"δ = 5 × {w_Nmm:.3f} × {L:.0f}⁴ / (384 × {E:.0f} × {Ix/1e6:.2f}×10⁶) = {delta:.2f} mm",
        result=delta,
        unit="mm",
        code_ref="Beam theory"
    ))
    step_num += 1
    
    # Step 3: Allowable deflection
    delta_limit = L / defl_limit
    DCR = delta / delta_limit
    status = "PASS" if DCR <= 1.0 else "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Deflection Check",
        description=f"Compare actual deflection to allowable limit of L/{defl_limit}.",
        equation=f"δ ≤ L/{defl_limit}",
        substitution=f"δ = {delta:.2f} mm vs L/{defl_limit} = {L:.0f}/{defl_limit} = {delta_limit:.2f} mm",
        result=DCR,
        unit="D/C",
        code_ref="IBC Table 1604.3",
        status=status,
        notes=f"D/C = {DCR:.3f} {'≤ 1.0 OK' if DCR <= 1.0 else '> 1.0 NG'}"
    ))
    
    section.steps = steps
    section.conclusion = f"δ = {delta:.2f} mm vs {delta_limit:.2f} mm allowable. D/C = {DCR:.3f}"
    section.status = status
    
    results = {
        'delta': delta,
        'delta_limit': delta_limit,
        'DCR': DCR,
        'status': status
    }
    
    return section, results


# =============================================================================
# SECTION 5: DEMAND VS CAPACITY
# =============================================================================

def calc_demand_capacity_precomp(
    Mu: float, Vu: float,
    phi_Mn: float, phi_Vn: float,
    method: str = "LRFD"
) -> Tuple[DetailedCalcSection, Dict]:
    """Calculate D/C ratios for pre-composite checks."""
    
    section = DetailedCalcSection(
        section_number=5,
        title="STRENGTH VERIFICATION (PRE-COMPOSITE)",
        description="Verify steel beam has adequate strength for construction loads.",
        code_ref="AISC 360-16 Chapter B"
    )
    steps = []
    step_num = 1
    
    # Step 1: Required flexural strength
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Required Flexural Strength",
        description=f"Required flexural strength from analysis using {method} load combinations.",
        equation=f"{'Mu' if method == 'LRFD' else 'Ma'} = w × L² / 8",
        substitution=f"{'Mu' if method == 'LRFD' else 'Ma'} = {Mu:.2f} kN⋅m",
        result=Mu,
        unit="kN⋅m",
        code_ref="ASCE 7-22"
    ))
    step_num += 1
    
    # Step 2: Required shear strength
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Required Shear Strength",
        description=f"Required shear strength from analysis.",
        equation=f"{'Vu' if method == 'LRFD' else 'Va'} = w × L / 2",
        substitution=f"{'Vu' if method == 'LRFD' else 'Va'} = {Vu:.2f} kN",
        result=Vu,
        unit="kN",
        code_ref="ASCE 7-22"
    ))
    step_num += 1
    
    # Step 3: Flexure check
    DCR_flex = Mu / phi_Mn if phi_Mn > 0 else 999
    status_flex = "PASS" if DCR_flex <= 1.0 else "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Flexural Strength Check",
        description="Verify design strength exceeds required strength.",
        equation=f"{'Mu ≤ φMn' if method == 'LRFD' else 'Ma ≤ Mn/Ω'}",
        substitution=f"D/C = {Mu:.2f} / {phi_Mn:.2f} = {DCR_flex:.3f}",
        result=DCR_flex,
        unit="",
        code_ref="AISC 360-16 §B3.1",
        status=status_flex,
        notes=f"{'✓ OK' if DCR_flex <= 1.0 else '✗ NG'}"
    ))
    step_num += 1
    
    # Step 4: Shear check
    DCR_shear = Vu / phi_Vn if phi_Vn > 0 else 999
    status_shear = "PASS" if DCR_shear <= 1.0 else "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Shear Strength Check",
        description="Verify design shear strength exceeds required strength.",
        equation=f"{'Vu ≤ φVn' if method == 'LRFD' else 'Va ≤ Vn/Ω'}",
        substitution=f"D/C = {Vu:.2f} / {phi_Vn:.2f} = {DCR_shear:.3f}",
        result=DCR_shear,
        unit="",
        code_ref="AISC 360-16 §B3.1",
        status=status_shear,
        notes=f"{'✓ OK' if DCR_shear <= 1.0 else '✗ NG'}"
    ))
    
    section.steps = steps
    overall_status = "PASS" if status_flex == "PASS" and status_shear == "PASS" else "FAIL"
    section.conclusion = f"Flexure D/C = {DCR_flex:.3f} ({status_flex}), Shear D/C = {DCR_shear:.3f} ({status_shear})"
    section.status = overall_status
    
    results = {
        'Mu': Mu,
        'Vu': Vu,
        'phi_Mn': phi_Mn,
        'phi_Vn': phi_Vn,
        'DCR_flex': DCR_flex,
        'DCR_shear': DCR_shear,
        'status_flex': status_flex,
        'status_shear': status_shear
    }
    
    return section, results


# =============================================================================
# MASTER FUNCTION
# =============================================================================

def design_precomposite_detailed(
    section_name: str,
    d: float, bf: float, tf: float, tw: float,
    A: float, Ix: float, Sx: float, Zx: float,
    Fy: float, E: float = 200000,
    w_precomp: float = 0,
    L: float = 0,
    Lb: float = 0,
    Cb: float = 1.0,
    method: str = "LRFD"
) -> PreCompositeDesignReport:
    """
    Complete pre-composite design with detailed calculations.
    
    Parameters:
        All section properties in mm
        w_precomp: Pre-composite load (kN/m)
        L: Span (mm)
        Lb: Unbraced length (mm)
        Cb: Moment modification factor
        method: "LRFD" or "ASD"
    """
    report = PreCompositeDesignReport(
        project_info={'method': method},
        beam_designation=section_name
    )
    
    # Section 1: Properties
    sec1 = calc_section_properties_precomp(
        section_name, d, bf, tf, tw, A, Ix, Sx, Zx, Fy, E
    )
    report.add_section(sec1)
    
    # Section 2: Flexure
    sec2, flex_results = calc_flexural_strength_precomp(
        d, bf, tf, tw, A, Ix, Sx, Zx, Fy, E, Lb, Cb, method
    )
    report.add_section(sec2)
    
    # Section 3: Shear
    sec3, shear_results = calc_shear_strength_precomp(d, tw, Fy, E, method)
    report.add_section(sec3)
    
    # Section 4: Deflection
    if L > 0 and w_precomp > 0:
        sec4, defl_results = calc_deflection_precomp(L, Ix, E, w_precomp)
        report.add_section(sec4)
    
    # Section 5: D/C check
    if L > 0 and w_precomp > 0:
        w_u = 1.2 * w_precomp if method == "LRFD" else w_precomp
        Mu = w_u * L**2 / 8 / 1e6  # kN⋅m
        Vu = w_u * L / 2 / 1000    # kN
        
        sec5, dc_results = calc_demand_capacity_precomp(
            Mu, Vu, flex_results['phi_Mn'], shear_results['phi_Vn'], method
        )
        report.add_section(sec5)
    
    # Generate summary
    report.summary = _generate_precomp_summary(report, section_name, method)
    
    return report


def _generate_precomp_summary(report, beam, method) -> str:
    """Generate summary table."""
    lines = []
    lines.append("")
    lines.append("╔══════════════════════════════════════════════════════════════════════════════╗")
    lines.append("║         PRE-COMPOSITE STEEL BEAM DESIGN SUMMARY                              ║")
    lines.append("║                    Per AISC 360-16                                           ║")
    lines.append("╠══════════════════════════════════════════════════════════════════════════════╣")
    lines.append(f"║ Beam: {beam:<72}║")
    lines.append(f"║ Method: {method:<70}║")
    lines.append("╠══════════════════════════════════════════════════════════════════════════════╣")
    lines.append("║ SECTION                        │ STATUS                                      ║")
    lines.append("╠────────────────────────────────┼─────────────────────────────────────────────╣")
    
    for sec in report.sections:
        status_icon = "✓ PASS" if sec.status == "PASS" else "✗ FAIL" if sec.status == "FAIL" else "⚠ WARN"
        title = sec.title[:30] if len(sec.title) > 30 else sec.title
        lines.append(f"║ {title:<30} │ {status_icon:<43}║")
    
    lines.append("╠══════════════════════════════════════════════════════════════════════════════╣")
    overall = "✓ PASS" if report.overall_status == "PASS" else "✗ FAIL"
    lines.append(f"║ OVERALL RESULT: {overall:<61}║")
    lines.append("╚══════════════════════════════════════════════════════════════════════════════╝")
    lines.append("")
    
    return "\n".join(lines)


def format_precomp_report(report: PreCompositeDesignReport) -> str:
    """Format complete report as text."""
    lines = []
    
    lines.append("=" * 80)
    lines.append("PRE-COMPOSITE STEEL BEAM DESIGN - DETAILED CALCULATIONS")
    lines.append("Per AISC 360-16 Specification for Structural Steel Buildings")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Beam: {report.beam_designation}")
    lines.append(f"Method: {report.project_info.get('method', 'LRFD')}")
    lines.append("")
    
    for section in report.sections:
        lines.append("=" * 80)
        lines.append(f"SECTION {section.section_number}: {section.title}")
        lines.append(f"Reference: {section.code_ref}")
        lines.append("-" * 80)
        lines.append(section.description)
        lines.append("")
        
        for step in section.steps:
            lines.append(f"Step {step.step_number}: {step.title}")
            lines.append(f"    {step.description}")
            lines.append(f"    Equation: {step.equation}")
            lines.append(f"    Substitution: {step.substitution}")
            lines.append(f"    Result: {step.result:.4f} {step.unit}")
            if step.code_ref:
                lines.append(f"    Reference: {step.code_ref}")
            if step.status != "INFO":
                lines.append(f"    Status: {step.status}")
            if step.notes:
                lines.append(f"    Notes: {step.notes}")
            lines.append("")
        
        lines.append(f"Conclusion: {section.conclusion}")
        lines.append(f"Section Status: {section.status}")
        lines.append("")
    
    lines.append(report.summary)
    
    return "\n".join(lines)
