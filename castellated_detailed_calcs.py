"""
Castellated/Cellular Beam Design - DETAILED PROFESSIONAL CALCULATIONS
=====================================================================

Per AISC Design Guide 31: Castellated and Cellular Beam Design
With references to AISC 360-16 Specification for Structural Steel Buildings

This module provides comprehensive step-by-step calculations suitable for
design review and checking by licensed professional engineers.

Author: CompositeBeam Pro
Version: 2.8
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# =============================================================================
# DATA CLASSES FOR DETAILED CALCULATIONS
# =============================================================================

@dataclass
class DetailedCalcStep:
    """
    A single calculation step with full professional documentation.
    
    Attributes:
        step_number: Sequential step number within section
        title: Brief title of the calculation
        description: Detailed explanation of what is being calculated and why
        equation: The general equation in symbolic form
        substitution: The equation with actual values substituted
        result: Numerical result
        unit: Units of the result
        code_ref: Specific code section reference
        status: PASS/FAIL/INFO for checks
        notes: Additional notes or warnings
    """
    step_number: int
    title: str
    description: str
    equation: str
    substitution: str
    result: float
    unit: str
    code_ref: str
    status: str = "INFO"  # INFO, PASS, FAIL, WARNING
    notes: str = ""


@dataclass
class DetailedCalcSection:
    """
    A section of calculations (e.g., "Section Properties", "Flexural Strength")
    
    Attributes:
        section_number: Sequential section number
        title: Section title
        description: Overview of what this section covers
        code_ref: Primary code reference for this section
        steps: List of calculation steps
        conclusion: Summary conclusion for this section
        status: Overall PASS/FAIL for this section
    """
    section_number: int
    title: str
    description: str
    code_ref: str
    steps: List[DetailedCalcStep] = field(default_factory=list)
    conclusion: str = ""
    status: str = "PASS"


@dataclass
class DetailedDesignReport:
    """
    Complete detailed design report for a castellated/cellular beam.
    """
    project_info: Dict
    beam_designation: str
    beam_type: str  # "Castellated" or "Cellular"
    sections: List[DetailedCalcSection] = field(default_factory=list)
    overall_status: str = "PASS"
    summary: str = ""
    
    def add_section(self, section: DetailedCalcSection):
        self.sections.append(section)
        if section.status == "FAIL":
            self.overall_status = "FAIL"


# =============================================================================
# DETAILED CALCULATION FUNCTIONS
# =============================================================================

def calc_section_properties_detailed(
    parent_name: str,
    d: float, bf: float, tf: float, tw: float,
    A: float, Ix: float,
    beam_type: str,
    ho: float, e: float, b: float, S: float, theta: float = 60,
    Do: float = 0
) -> DetailedCalcSection:
    """
    Calculate expanded section properties with full detailed steps.
    
    Per AISC Design Guide 31 Section 3 and Section 4.
    
    Args:
        parent_name: Parent section designation
        d, bf, tf, tw: Parent section dimensions (mm)
        A, Ix: Parent section properties
        beam_type: "Castellated" or "Cellular"
        ho: Opening height (mm)
        e: Half-length of opening (mm) - castellated only
        b: Web post width (mm)
        S: Opening spacing (mm)
        theta: Cutting angle (degrees) - castellated only
        Do: Opening diameter (mm) - cellular only
        
    Returns:
        DetailedCalcSection with all calculation steps
    """
    section = DetailedCalcSection(
        section_number=1,
        title="SECTION PROPERTIES",
        description="Calculate expanded section geometric and structural properties per AISC DG31 Section 3-4",
        code_ref="AISC DG31 §3, §4"
    )
    
    steps = []
    step_num = 0
    
    # =========================================================================
    # 1. PARENT SECTION DATA
    # =========================================================================
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Parent Section Properties",
        description=f"Record the properties of the parent section {parent_name} before cutting",
        equation="Given data from section tables",
        substitution=f"d = {d} mm, bf = {bf} mm, tf = {tf} mm, tw = {tw} mm, A = {A} mm², Ix = {Ix/1e6:.2f}×10⁶ mm⁴",
        result=d,
        unit="mm (depth)",
        code_ref="Section Tables",
        status="INFO"
    ))
    
    # =========================================================================
    # 2. EXPANDED DEPTH CALCULATION
    # =========================================================================
    if beam_type == "Castellated":
        # For castellated: dg = d + ho/2 (cutting and re-welding adds half opening height)
        dg = d + ho / 2
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Expanded Beam Depth (Castellated)",
            description="The expanded depth is the original depth plus half the opening height. "
                       "When the beam is cut along the zigzag pattern and the halves are offset and rewelded, "
                       "the total depth increases by ho/2.",
            equation="dg = d + ho/2",
            substitution=f"dg = {d} + {ho}/2 = {d} + {ho/2:.1f}",
            result=dg,
            unit="mm",
            code_ref="AISC DG31 §3.2, Eq. 3-1"
        ))
    else:  # Cellular
        # For cellular: dg = d + Do/2
        dg = d + Do / 2
        ho = Do  # For cellular, ho = Do
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Expanded Beam Depth (Cellular)",
            description="For cellular beams, the expanded depth equals the original depth plus half the opening diameter. "
                       "The cutting and re-welding process increases depth by Do/2.",
            equation="dg = d + Do/2",
            substitution=f"dg = {d} + {Do}/2 = {d} + {Do/2:.1f}",
            result=dg,
            unit="mm",
            code_ref="AISC DG31 §3.3, Eq. 3-2"
        ))
    
    # =========================================================================
    # 3. EXPANSION RATIO CHECK
    # =========================================================================
    expansion_ratio = dg / d
    step_num += 1
    exp_status = "PASS" if 1.25 <= expansion_ratio <= 1.75 else "WARNING"
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Expansion Ratio",
        description="The expansion ratio is the ratio of expanded depth to original depth. "
                   "Typical values range from 1.3 to 1.6 for efficient designs. "
                   "Values outside 1.25-1.75 may indicate non-optimal geometry.",
        equation="Expansion Ratio = dg / d",
        substitution=f"Expansion Ratio = {dg:.1f} / {d:.1f}",
        result=expansion_ratio,
        unit="-",
        code_ref="AISC DG31 §3.2",
        status=exp_status,
        notes="Recommended range: 1.3 to 1.6 for optimal efficiency"
    ))
    
    # =========================================================================
    # 4. TEE DEPTH CALCULATION
    # =========================================================================
    dt = (dg - ho) / 2
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Section Depth",
        description="The tee depth is the depth of the top or bottom tee section at the opening location. "
                   "This is critical for Vierendeel bending capacity. "
                   "Both top and bottom tees are assumed symmetric.",
        equation="dt = (dg - ho) / 2",
        substitution=f"dt = ({dg:.1f} - {ho:.1f}) / 2",
        result=dt,
        unit="mm",
        code_ref="AISC DG31 §4.1"
    ))
    
    # =========================================================================
    # 5. TEE DEPTH ADEQUACY CHECK
    # =========================================================================
    dt_min = tf + 3 * tw
    step_num += 1
    dt_status = "PASS" if dt >= dt_min else "FAIL"
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Depth Adequacy Check",
        description="The tee depth must be sufficient to provide adequate flexural and shear capacity. "
                   "A minimum tee depth of tf + 3×tw is recommended to ensure stability "
                   "and prevent local failures.",
        equation="dt ≥ dt,min = tf + 3×tw",
        substitution=f"dt = {dt:.1f} mm ≥ dt,min = {tf} + 3×{tw} = {dt_min:.1f} mm",
        result=dt,
        unit="mm",
        code_ref="AISC DG31 §3.3",
        status=dt_status,
        notes=f"dt,min = {dt_min:.1f} mm; dt,provided = {dt:.1f} mm; Ratio = {dt/dt_min:.2f}"
    ))
    
    # =========================================================================
    # 6. OPENING HEIGHT TO DEPTH RATIO
    # =========================================================================
    ho_dg_ratio = ho / dg
    step_num += 1
    ratio_status = "PASS" if 0.4 <= ho_dg_ratio <= 0.7 else "WARNING"
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Opening Height to Depth Ratio",
        description="The ratio of opening height to expanded depth affects both structural efficiency "
                   "and aesthetics. Too small reduces the benefit of openings; too large weakens the section.",
        equation="ho/dg",
        substitution=f"ho/dg = {ho:.1f} / {dg:.1f}",
        result=ho_dg_ratio,
        unit="-",
        code_ref="AISC DG31 §3.2",
        status=ratio_status,
        notes="Recommended range: 0.50 to 0.70 for optimal performance"
    ))
    
    # =========================================================================
    # 7. TEE SECTION PROPERTIES
    # =========================================================================
    # Area of one tee
    A_tee = bf * tf + (dt - tf) * tw
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Section Area",
        description="Calculate the cross-sectional area of one tee section (top or bottom). "
                   "The tee consists of the flange plus the stem portion of the web.",
        equation="A_tee = bf × tf + (dt - tf) × tw",
        substitution=f"A_tee = {bf} × {tf} + ({dt:.1f} - {tf}) × {tw}",
        result=A_tee,
        unit="mm²",
        code_ref="AISC DG31 §4.2"
    ))
    
    # Centroid of tee from outer flange face
    y_bar_tee = (bf * tf * tf/2 + (dt - tf) * tw * (tf + (dt-tf)/2)) / A_tee
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Section Centroid",
        description="Locate the centroid of the tee section measured from the outer face of the flange. "
                   "This is needed for calculating tee moment of inertia and section modulus.",
        equation="ȳ_tee = Σ(A_i × y_i) / A_tee",
        substitution=f"ȳ_tee = ({bf}×{tf}×{tf/2:.1f} + {(dt-tf):.1f}×{tw}×{(tf+(dt-tf)/2):.1f}) / {A_tee:.0f}",
        result=y_bar_tee,
        unit="mm (from flange face)",
        code_ref="Mechanics of Materials"
    ))
    
    # Moment of inertia of tee about its own centroid
    I_flange = bf * tf**3 / 12 + bf * tf * (y_bar_tee - tf/2)**2
    I_stem = tw * (dt - tf)**3 / 12 + tw * (dt - tf) * (tf + (dt-tf)/2 - y_bar_tee)**2
    I_tee = I_flange + I_stem
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Section Moment of Inertia",
        description="Calculate the moment of inertia of the tee about its centroidal axis "
                   "using the parallel axis theorem. This is critical for Vierendeel bending analysis.",
        equation="I_tee = I_flange + I_stem (using parallel axis theorem)",
        substitution=f"I_tee = {I_flange/1e6:.4f}×10⁶ + {I_stem/1e6:.4f}×10⁶",
        result=I_tee,
        unit="mm⁴",
        code_ref="AISC DG31 §4.2"
    ))
    
    # Section modulus of tee (at stem tip - critical location)
    c_stem = dt - y_bar_tee
    S_tee = I_tee / c_stem
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Section Modulus (at stem)",
        description="Calculate the elastic section modulus of the tee at the stem tip, "
                   "which is typically the critical location for Vierendeel bending stress.",
        equation="S_tee = I_tee / c_stem where c_stem = dt - ȳ_tee",
        substitution=f"S_tee = {I_tee:.0f} / {c_stem:.1f}",
        result=S_tee,
        unit="mm³",
        code_ref="AISC DG31 §4.2"
    ))
    
    # =========================================================================
    # 8. GROSS SECTION PROPERTIES (AT SOLID SECTION)
    # =========================================================================
    # Moment of inertia using parallel axis theorem for expanded section
    # Distance from neutral axis to tee centroid
    d_NA = dg/2 - y_bar_tee
    Ix_gross = 2 * (I_tee + A_tee * d_NA**2)
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Gross Section Moment of Inertia",
        description="Calculate the moment of inertia of the full expanded section at a solid web location "
                   "(between openings) using the parallel axis theorem applied to both tees.",
        equation="Ix,gross = 2 × (I_tee + A_tee × d²) where d = dg/2 - ȳ_tee",
        substitution=f"Ix,gross = 2 × ({I_tee:.0f} + {A_tee:.0f} × {d_NA:.1f}²)",
        result=Ix_gross,
        unit="mm⁴",
        code_ref="AISC DG31 §4.3"
    ))
    
    Sx_gross = Ix_gross / (dg / 2)
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Gross Section Modulus",
        description="Calculate the elastic section modulus of the gross expanded section.",
        equation="Sx,gross = Ix,gross / (dg/2)",
        substitution=f"Sx,gross = {Ix_gross:.0f} / {dg/2:.1f}",
        result=Sx_gross,
        unit="mm³",
        code_ref="AISC DG31 §4.3"
    ))
    
    # Plastic section modulus (approximate as 1.12 × Sx for I-shapes)
    Zx_gross = Sx_gross * 1.12
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Gross Plastic Section Modulus",
        description="Estimate the plastic section modulus. For I-shaped sections, the shape factor "
                   "is typically about 1.12.",
        equation="Zx,gross ≈ 1.12 × Sx,gross (shape factor for I-sections)",
        substitution=f"Zx,gross = 1.12 × {Sx_gross:.0f}",
        result=Zx_gross,
        unit="mm³",
        code_ref="AISC DG31 §4.3"
    ))
    
    # =========================================================================
    # 9. NET SECTION PROPERTIES (AT OPENING)
    # =========================================================================
    # At opening, the section consists of two separated tees
    # Net Ix is based on tees acting compositely through Vierendeel action
    d_net = dg/2 - dt/2  # Distance from NA to centroid of each tee
    Ix_net = 2 * A_tee * d_net**2  # Conservative: ignores tee's own I
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Net Section Moment of Inertia (at opening)",
        description="Calculate the moment of inertia at the opening centerline where the web is absent. "
                   "The section consists of two separated tees. This is a conservative lower bound "
                   "that considers only the parallel axis contribution.",
        equation="Ix,net = 2 × A_tee × d²net where dnet = dg/2 - dt/2",
        substitution=f"Ix,net = 2 × {A_tee:.0f} × {d_net:.1f}²",
        result=Ix_net,
        unit="mm⁴",
        code_ref="AISC DG31 §4.4"
    ))
    
    Sx_net = Ix_net / (dg / 2)
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Net Section Modulus (at opening)",
        description="Calculate the elastic section modulus at the opening centerline.",
        equation="Sx,net = Ix,net / (dg/2)",
        substitution=f"Sx,net = {Ix_net:.0f} / {dg/2:.1f}",
        result=Sx_net,
        unit="mm³",
        code_ref="AISC DG31 §4.4"
    ))
    
    # =========================================================================
    # 10. WEB POST PROPERTIES (FOR BUCKLING CHECK)
    # =========================================================================
    if beam_type == "Castellated":
        # Web post width for castellated
        b_wp = b
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Web Post Width (Castellated)",
            description="The web post is the solid web region between adjacent openings. "
                       "For castellated beams, this equals the parameter 'b' from the cutting pattern.",
            equation="b_wp = b (given)",
            substitution=f"b_wp = {b}",
            result=b_wp,
            unit="mm",
            code_ref="AISC DG31 §3.4"
        ))
    else:
        # Web post width for cellular
        b_wp = S - Do
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Web Post Width (Cellular)",
            description="For cellular beams, the web post width is the spacing minus the diameter.",
            equation="b_wp = S - Do",
            substitution=f"b_wp = {S} - {Do}",
            result=b_wp,
            unit="mm",
            code_ref="AISC DG31 §3.5"
        ))
    
    # Web post slenderness
    h_wp = ho  # Height of web post
    wp_slenderness = h_wp / tw
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Post Slenderness",
        description="The web post slenderness ratio affects the buckling capacity. "
                   "Higher slenderness indicates more susceptibility to buckling.",
        equation="λ_wp = ho / tw",
        substitution=f"λ_wp = {ho:.1f} / {tw}",
        result=wp_slenderness,
        unit="-",
        code_ref="AISC DG31 §5.4"
    ))
    
    # =========================================================================
    # SECTION SUMMARY
    # =========================================================================
    section.steps = steps
    section.conclusion = f"""
SECTION PROPERTIES SUMMARY:
══════════════════════════════════════════════════════════════════════════════
Parent Section: {parent_name}
Beam Type: {beam_type}
──────────────────────────────────────────────────────────────────────────────
GEOMETRY:
  Original depth (d):           {d:.1f} mm
  Expanded depth (dg):          {dg:.1f} mm
  Expansion ratio (dg/d):       {expansion_ratio:.3f}
  Opening height (ho):          {ho:.1f} mm
  Opening ratio (ho/dg):        {ho_dg_ratio:.3f}
  Tee depth (dt):               {dt:.1f} mm
  Web post width (b_wp):        {b_wp:.1f} mm
  Opening spacing (S):          {S:.1f} mm
──────────────────────────────────────────────────────────────────────────────
SECTION PROPERTIES:
  Tee area (A_tee):             {A_tee:.0f} mm²
  Tee centroid (ȳ_tee):         {y_bar_tee:.1f} mm (from flange)
  Tee moment of inertia:        {I_tee/1e6:.4f} × 10⁶ mm⁴
  Tee section modulus:          {S_tee:.0f} mm³
  
  Gross Ix (solid section):     {Ix_gross/1e6:.2f} × 10⁶ mm⁴
  Gross Sx:                     {Sx_gross:.0f} mm³
  Gross Zx:                     {Zx_gross:.0f} mm³
  
  Net Ix (at opening):          {Ix_net/1e6:.2f} × 10⁶ mm⁴
  Net Sx:                       {Sx_net:.0f} mm³
══════════════════════════════════════════════════════════════════════════════
"""
    
    # Check overall status
    if dt < dt_min:
        section.status = "FAIL"
    elif expansion_ratio < 1.25 or expansion_ratio > 1.75:
        section.status = "WARNING"
    
    return section, {
        'dg': dg, 'ho': ho, 'dt': dt,
        'A_tee': A_tee, 'y_bar_tee': y_bar_tee, 'I_tee': I_tee, 'S_tee': S_tee,
        'Ix_gross': Ix_gross, 'Sx_gross': Sx_gross, 'Zx_gross': Zx_gross,
        'Ix_net': Ix_net, 'Sx_net': Sx_net,
        'b_wp': b_wp, 'h_wp': h_wp,
        'expansion_ratio': expansion_ratio, 'ho_dg_ratio': ho_dg_ratio
    }


def calc_global_flexure_detailed(
    parent_name: str,
    dg: float, bf: float, tf: float, tw: float,
    ho: float, dt: float,
    Ix_gross: float, Sx_gross: float, Zx_gross: float,
    Fy: float, E: float,
    Mu: float, Lb: float,
    method: str = "LRFD"
) -> DetailedCalcSection:
    """
    Detailed global flexural strength calculation per AISC DG31 §5.2.
    
    Args:
        All section properties and material properties
        Mu: Required flexural strength (kN·m)
        Lb: Unbraced length (mm)
        method: "LRFD" or "ASD"
        
    Returns:
        DetailedCalcSection with all calculation steps
    """
    section = DetailedCalcSection(
        section_number=2,
        title="GLOBAL FLEXURAL STRENGTH",
        description="Check global flexural capacity of the expanded section per AISC DG31 Section 5.2. "
                   "The presence of web openings is accounted for through modified section properties "
                   "and reduced lateral-torsional buckling resistance.",
        code_ref="AISC DG31 §5.2"
    )
    
    steps = []
    step_num = 0
    
    # =========================================================================
    # 1. MATERIAL AND SECTION DATA
    # =========================================================================
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Material Properties",
        description="Record the material yield strength and modulus of elasticity.",
        equation="Given material properties",
        substitution=f"Fy = {Fy} MPa, E = {E} MPa",
        result=Fy,
        unit="MPa",
        code_ref="AISC 360-16 A3.1"
    ))
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Required Flexural Strength",
        description="The required flexural strength from structural analysis under factored loads.",
        equation="Mu = (factored loads × L²) / 8 for simple span uniform load",
        substitution=f"Mu = {Mu:.2f} kN·m (from analysis)",
        result=Mu,
        unit="kN·m",
        code_ref="ASCE 7 Load Combinations"
    ))
    
    # =========================================================================
    # 2. YIELD MOMENT CALCULATION
    # =========================================================================
    My = Fy * Sx_gross / 1e6  # kN·m
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Yield Moment",
        description="The yield moment is the moment at which the extreme fiber first reaches yield stress. "
                   "This is calculated using the gross section modulus.",
        equation="My = Fy × Sx,gross",
        substitution=f"My = {Fy} × {Sx_gross/1e3:.1f}×10³ / 10⁶ = {Fy} × {Sx_gross:.0f} / 10⁶",
        result=My,
        unit="kN·m",
        code_ref="AISC DG31 §5.2.1"
    ))
    
    # =========================================================================
    # 3. PLASTIC MOMENT CALCULATION
    # =========================================================================
    Mp = Fy * Zx_gross / 1e6  # kN·m
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Plastic Moment",
        description="The plastic moment is the moment required to fully plastify the cross-section. "
                   "This represents the upper bound of flexural strength for compact sections.",
        equation="Mp = Fy × Zx,gross",
        substitution=f"Mp = {Fy} × {Zx_gross/1e3:.1f}×10³ / 10⁶ = {Fy} × {Zx_gross:.0f} / 10⁶",
        result=Mp,
        unit="kN·m",
        code_ref="AISC 360-16 F2.1"
    ))
    
    # =========================================================================
    # 4. LATERAL-TORSIONAL BUCKLING PARAMETERS
    # =========================================================================
    # Radius of gyration about weak axis for compression flange
    ry = bf / math.sqrt(12)
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Radius of Gyration (compression flange)",
        description="Approximate radius of gyration of the compression flange about the y-axis, "
                   "used for lateral-torsional buckling calculations.",
        equation="ry ≈ bf / √12",
        substitution=f"ry = {bf} / √12 = {bf} / {math.sqrt(12):.3f}",
        result=ry,
        unit="mm",
        code_ref="AISC 360-16 F2"
    ))
    
    # Limiting unbraced length Lp (plastic)
    Lp = 1.76 * ry * math.sqrt(E / Fy)
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Limiting Unbraced Length Lp",
        description="Lp is the limiting laterally unbraced length for the limit state of yielding. "
                   "When Lb ≤ Lp, lateral-torsional buckling does not govern and the full plastic "
                   "moment can be achieved.",
        equation="Lp = 1.76 × ry × √(E/Fy)",
        substitution=f"Lp = 1.76 × {ry:.1f} × √({E}/{Fy}) = 1.76 × {ry:.1f} × {math.sqrt(E/Fy):.2f}",
        result=Lp,
        unit="mm",
        code_ref="AISC 360-16 Eq. F2-5"
    ))
    
    # Effective radius of gyration rts
    Iy_flange = tf * bf**3 / 12
    Sxc = Sx_gross  # For doubly symmetric section
    rts_sq = math.sqrt(Iy_flange * (dg/2) / Sxc)
    rts = max(rts_sq, bf/6)  # Ensure reasonable value
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Effective Radius of Gyration rts",
        description="The effective radius of gyration rts is used in the elastic buckling equation. "
                   "For castellated beams, this is computed considering the compression flange properties.",
        equation="rts = √(√(Iy,flange × ho,c / Sxc))",
        substitution=f"rts = √(√({Iy_flange:.0f} × {dg/2:.1f} / {Sxc:.0f})) = √({rts_sq:.1f})",
        result=rts,
        unit="mm",
        code_ref="AISC 360-16 Eq. F2-7"
    ))
    
    # Modification factor for openings
    ho_factor = max(0.7, 1 - 0.3 * ho / dg)
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Opening Modification Factor",
        description="The presence of web openings reduces the torsional stiffness and warping constant, "
                   "effectively reducing the elastic buckling resistance. A reduction factor is applied.",
        equation="Cₒ = max(0.7, 1 - 0.3 × ho/dg)",
        substitution=f"Cₒ = max(0.7, 1 - 0.3 × {ho:.1f}/{dg:.1f}) = max(0.7, {1 - 0.3*ho/dg:.3f})",
        result=ho_factor,
        unit="-",
        code_ref="AISC DG31 §5.2.2"
    ))
    
    # Limiting unbraced length Lr (inelastic)
    Lr = 1.95 * rts * (E / (0.7 * Fy)) * ho_factor
    Lr = max(Lr, 1.5 * Lp)  # Ensure Lr > Lp
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Limiting Unbraced Length Lr",
        description="Lr is the limiting unbraced length for the limit state of inelastic lateral-torsional "
                   "buckling. For castellated beams, this is reduced by the opening modification factor.",
        equation="Lr = 1.95 × rts × (E / 0.7Fy) × Cₒ",
        substitution=f"Lr = 1.95 × {rts:.1f} × ({E} / (0.7×{Fy})) × {ho_factor:.3f}",
        result=Lr,
        unit="mm",
        code_ref="AISC DG31 §5.2.2, AISC 360-16 Eq. F2-6"
    ))
    
    # =========================================================================
    # 5. MOMENT GRADIENT FACTOR
    # =========================================================================
    Cb = 1.0  # Conservative for uniform moment
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Moment Gradient Factor Cb",
        description="The moment gradient factor accounts for non-uniform moment distribution. "
                   "For uniform moment (worst case), Cb = 1.0. Higher values are permitted for "
                   "moment gradients per AISC 360-16 Eq. F1-1.",
        equation="Cb = 1.0 (conservative for uniform moment)",
        substitution="Cb = 1.0",
        result=Cb,
        unit="-",
        code_ref="AISC 360-16 Eq. F1-1"
    ))
    
    # =========================================================================
    # 6. NOMINAL FLEXURAL STRENGTH DETERMINATION
    # =========================================================================
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Unbraced Length Classification",
        description="Compare the actual unbraced length Lb to the limiting lengths Lp and Lr "
                   "to determine which limit state governs.",
        equation="Compare: Lb vs Lp vs Lr",
        substitution=f"Lb = {Lb:.0f} mm, Lp = {Lp:.0f} mm, Lr = {Lr:.0f} mm",
        result=Lb,
        unit="mm",
        code_ref="AISC 360-16 F2.2"
    ))
    
    if Lb <= Lp:
        # Yielding governs - full plastic moment
        Mn = Mp
        gov_state = "Yielding (Lb ≤ Lp)"
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Nominal Flexural Strength - Yielding",
            description="Since Lb ≤ Lp, lateral-torsional buckling does not occur before yielding. "
                       "The full plastic moment capacity can be achieved.",
            equation="Mn = Mp (for Lb ≤ Lp)",
            substitution=f"Lb = {Lb:.0f} mm ≤ Lp = {Lp:.0f} mm ∴ Mn = Mp = {Mp:.2f}",
            result=Mn,
            unit="kN·m",
            code_ref="AISC 360-16 Eq. F2-1"
        ))
        
    elif Lb <= Lr:
        # Inelastic LTB
        Mn_calc = Cb * (Mp - (Mp - 0.7 * My) * (Lb - Lp) / (Lr - Lp))
        Mn = min(Mn_calc, Mp)
        gov_state = "Inelastic LTB (Lp < Lb ≤ Lr)"
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Nominal Flexural Strength - Inelastic LTB",
            description="Since Lp < Lb ≤ Lr, inelastic lateral-torsional buckling governs. "
                       "The nominal strength is linearly interpolated between Mp and 0.7My.",
            equation="Mn = Cb × [Mp - (Mp - 0.7My) × (Lb - Lp)/(Lr - Lp)] ≤ Mp",
            substitution=f"Mn = {Cb} × [{Mp:.2f} - ({Mp:.2f} - 0.7×{My:.2f}) × ({Lb:.0f} - {Lp:.0f})/({Lr:.0f} - {Lp:.0f})]",
            result=Mn,
            unit="kN·m",
            code_ref="AISC 360-16 Eq. F2-2"
        ))
        
    else:
        # Elastic LTB
        Fcr = Cb * math.pi**2 * E / (Lb / rts)**2
        Mn_calc = Fcr * Sx_gross / 1e6
        Mn = min(Mn_calc, Mp)
        gov_state = "Elastic LTB (Lb > Lr)"
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Critical Buckling Stress",
            description="Since Lb > Lr, elastic lateral-torsional buckling governs. "
                       "First calculate the critical buckling stress.",
            equation="Fcr = Cb × π² × E / (Lb/rts)²",
            substitution=f"Fcr = {Cb} × π² × {E} / ({Lb:.0f}/{rts:.1f})² = {Cb} × {math.pi**2:.4f} × {E} / {(Lb/rts)**2:.1f}",
            result=Fcr,
            unit="MPa",
            code_ref="AISC 360-16 Eq. F2-4"
        ))
        
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Nominal Flexural Strength - Elastic LTB",
            description="The nominal flexural strength for elastic LTB is limited by the critical stress.",
            equation="Mn = Fcr × Sx ≤ Mp",
            substitution=f"Mn = {Fcr:.1f} × {Sx_gross:.0f} / 10⁶ = {Mn_calc:.2f} kN·m ≤ Mp = {Mp:.2f} kN·m",
            result=Mn,
            unit="kN·m",
            code_ref="AISC 360-16 Eq. F2-3"
        ))
    
    # =========================================================================
    # 7. DESIGN/ALLOWABLE STRENGTH
    # =========================================================================
    if method == "LRFD":
        phi_b = 0.90
        Mn_design = phi_b * Mn
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Design Flexural Strength (LRFD)",
            description="Apply the resistance factor φb = 0.90 for flexure to obtain the design strength.",
            equation="φbMn = φb × Mn",
            substitution=f"φbMn = 0.90 × {Mn:.2f}",
            result=Mn_design,
            unit="kN·m",
            code_ref="AISC 360-16 F1(1)"
        ))
    else:
        Omega_b = 1.67
        Mn_design = Mn / Omega_b
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Allowable Flexural Strength (ASD)",
            description="Divide by the safety factor Ωb = 1.67 for flexure to obtain the allowable strength.",
            equation="Mn/Ωb = Mn / 1.67",
            substitution=f"Mn/Ωb = {Mn:.2f} / 1.67",
            result=Mn_design,
            unit="kN·m",
            code_ref="AISC 360-16 F1(2)"
        ))
    
    # =========================================================================
    # 8. DEMAND/CAPACITY RATIO
    # =========================================================================
    ratio = Mu / Mn_design if Mn_design > 0 else float('inf')
    status = "PASS" if ratio <= 1.0 else "FAIL"
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Flexural Demand/Capacity Check",
        description="Compare the required flexural strength to the available flexural strength.",
        equation="Mu / φbMn ≤ 1.0" if method == "LRFD" else "Ma / (Mn/Ωb) ≤ 1.0",
        substitution=f"{Mu:.2f} / {Mn_design:.2f}",
        result=ratio,
        unit="-",
        code_ref="AISC 360-16 H1",
        status=status,
        notes=f"{'✓ OK - Flexural strength is adequate' if status == 'PASS' else '✗ NG - Flexural strength is inadequate'}"
    ))
    
    section.steps = steps
    section.status = status
    section.conclusion = f"""
GLOBAL FLEXURAL STRENGTH SUMMARY:
══════════════════════════════════════════════════════════════════════════════
Design Method: {method}
Governing Limit State: {gov_state}
──────────────────────────────────────────────────────────────────────────────
CAPACITY:
  Yield Moment (My):            {My:.2f} kN·m
  Plastic Moment (Mp):          {Mp:.2f} kN·m
  Nominal Strength (Mn):        {Mn:.2f} kN·m
  Design Strength (φMn or Mn/Ω):{Mn_design:.2f} kN·m
──────────────────────────────────────────────────────────────────────────────
DEMAND:
  Required Strength (Mu):       {Mu:.2f} kN·m
──────────────────────────────────────────────────────────────────────────────
CHECK:
  D/C Ratio:                    {ratio:.3f}
  Status:                       {status}
══════════════════════════════════════════════════════════════════════════════
"""
    
    return section, {
        'My': My, 'Mp': Mp, 'Lp': Lp, 'Lr': Lr, 'Cb': Cb,
        'Mn': Mn, 'Mn_design': Mn_design, 'ratio': ratio,
        'gov_state': gov_state
    }


def calc_vierendeel_bending_detailed(
    parent_name: str,
    dg: float, ho: float, dt: float, bf: float, tf: float, tw: float,
    A_tee: float, I_tee: float, S_tee: float, y_bar_tee: float,
    beam_type: str, e: float, Do: float,
    Fy: float, E: float,
    Vu: float,
    method: str = "LRFD"
) -> DetailedCalcSection:
    """
    Detailed Vierendeel bending calculation per AISC DG31 §5.3.
    
    Vierendeel bending occurs in the tee sections as they transfer shear
    across the web opening through local bending action.
    
    Args:
        Section properties, geometry, material properties
        Vu: Required shear strength at opening (kN)
        method: "LRFD" or "ASD"
        
    Returns:
        DetailedCalcSection with all calculation steps
    """
    section = DetailedCalcSection(
        section_number=3,
        title="VIERENDEEL BENDING",
        description="Check local bending in tee sections at web openings per AISC DG31 Section 5.3. "
                   "As shear force is transferred across the opening, each tee section acts as a "
                   "short beam subjected to local bending moments (Vierendeel action).",
        code_ref="AISC DG31 §5.3"
    )
    
    steps = []
    step_num = 0
    
    # =========================================================================
    # 1. INTRODUCTION TO VIERENDEEL BENDING
    # =========================================================================
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Vierendeel Bending Mechanism",
        description="When a shear force V is transferred across a web opening, each tee (top and bottom) "
                   "must resist local bending moments. The shear is shared between the tees approximately "
                   "in proportion to their flexural stiffness. For symmetric sections, each tee carries V/2.",
        equation="V_tee = Vu / 2 (for symmetric tees)",
        substitution=f"V_tee = {Vu:.2f} / 2 = {Vu/2:.2f} kN",
        result=Vu/2,
        unit="kN",
        code_ref="AISC DG31 §5.3.1"
    ))
    
    # =========================================================================
    # 2. VIERENDEEL MOMENT CALCULATION
    # =========================================================================
    # For castellated beams, the critical section is at e from center
    # For cellular beams, use Do/2 as the half-length
    if beam_type == "Castellated":
        a_v = e  # Half-length of opening
    else:
        a_v = Do / 2
    
    # Vierendeel moment in each tee
    # Mvr = V_tee × a_v (moment arm from center of opening to web post)
    V_tee = Vu / 2
    Mvr = V_tee * a_v / 1000  # kN·m (converting mm to m)
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Vierendeel Moment in Tee",
        description="The local bending moment in each tee is calculated as the tee shear times "
                   "the moment arm (half-length of opening). This moment causes bending stress "
                   "in the tee section.",
        equation="Mvr = V_tee × e" if beam_type == "Castellated" else "Mvr = V_tee × (Do/2)",
        substitution=f"Mvr = {V_tee:.2f} × {a_v:.1f} / 1000",
        result=Mvr,
        unit="kN·m",
        code_ref="AISC DG31 §5.3.1, Eq. 5-3"
    ))
    
    # =========================================================================
    # 3. TEE SECTION CLASSIFICATION
    # =========================================================================
    # Check flange slenderness
    lambda_f = bf / (2 * tf)
    lambda_pf = 0.38 * math.sqrt(E / Fy)
    step_num += 1
    flange_status = "Compact" if lambda_f <= lambda_pf else "Noncompact"
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Flange Slenderness",
        description="Classify the tee flange as compact or noncompact for flexure. "
                   "Compact flanges can develop the full plastic moment.",
        equation="λf = bf/(2tf), λpf = 0.38√(E/Fy)",
        substitution=f"λf = {bf}/(2×{tf}) = {lambda_f:.2f}, λpf = 0.38×√({E}/{Fy}) = {lambda_pf:.2f}",
        result=lambda_f,
        unit="-",
        code_ref="AISC 360-16 Table B4.1b",
        status="PASS" if lambda_f <= lambda_pf else "WARNING",
        notes=f"Flange is {flange_status} (λf {'≤' if lambda_f <= lambda_pf else '>'} λpf)"
    ))
    
    # Check stem slenderness (web of tee)
    d_stem = dt - tf
    lambda_w = d_stem / tw
    lambda_pw = 0.84 * math.sqrt(E / Fy)  # For tee stems in flexure
    step_num += 1
    stem_status = "Compact" if lambda_w <= lambda_pw else "Noncompact"
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Stem Slenderness",
        description="Classify the tee stem (web) as compact or noncompact for flexure. "
                   "This affects the available flexural strength of the tee.",
        equation="λw = (dt-tf)/tw, λpw = 0.84√(E/Fy)",
        substitution=f"λw = ({dt:.1f}-{tf})/{tw} = {lambda_w:.2f}, λpw = 0.84×√({E}/{Fy}) = {lambda_pw:.2f}",
        result=lambda_w,
        unit="-",
        code_ref="AISC 360-16 Table B4.1b",
        status="PASS" if lambda_w <= lambda_pw else "WARNING",
        notes=f"Stem is {stem_status} (λw {'≤' if lambda_w <= lambda_pw else '>'} λpw)"
    ))
    
    # =========================================================================
    # 4. TEE FLEXURAL STRENGTH
    # =========================================================================
    # Plastic section modulus of tee (approximate)
    # For tee with stem in compression, use 1.5×S_tee as approximate Zx
    Z_tee = 1.5 * S_tee  # Approximate for compact tee
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Plastic Section Modulus",
        description="Estimate the plastic section modulus of the tee for calculating plastic moment. "
                   "For tee sections, Zx is typically about 1.5 times the elastic section modulus.",
        equation="Zx,tee ≈ 1.5 × Sx,tee (approximate for tee sections)",
        substitution=f"Zx,tee = 1.5 × {S_tee:.0f}",
        result=Z_tee,
        unit="mm³",
        code_ref="AISC DG31 §5.3.2"
    ))
    
    # Plastic moment of tee
    Mp_tee = Fy * Z_tee / 1e6  # kN·m
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Plastic Moment",
        description="Calculate the plastic moment capacity of one tee section.",
        equation="Mp,tee = Fy × Zx,tee",
        substitution=f"Mp,tee = {Fy} × {Z_tee:.0f} / 10⁶",
        result=Mp_tee,
        unit="kN·m",
        code_ref="AISC 360-16 F9"
    ))
    
    # For noncompact stems, reduce capacity
    if lambda_w > lambda_pw:
        lambda_rw = 1.52 * math.sqrt(E / Fy)
        if lambda_w <= lambda_rw:
            # Inelastic reduction
            Mn_tee = Mp_tee * (1 - (lambda_w - lambda_pw) / (lambda_rw - lambda_pw) * 0.3)
        else:
            # Use elastic section modulus
            Mn_tee = Fy * S_tee / 1e6
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Tee Nominal Moment (Noncompact Stem)",
            description="Since the tee stem is noncompact, the nominal moment capacity is reduced.",
            equation="Mn,tee = Mp,tee × [1 - 0.3×(λw-λpw)/(λrw-λpw)] for λw ≤ λrw",
            substitution=f"Mn,tee = {Mp_tee:.3f} × [1 - 0.3×({lambda_w:.2f}-{lambda_pw:.2f})/({lambda_rw:.2f}-{lambda_pw:.2f})]",
            result=Mn_tee,
            unit="kN·m",
            code_ref="AISC 360-16 F9.2"
        ))
    else:
        Mn_tee = Mp_tee
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Tee Nominal Moment (Compact)",
            description="Since the tee section is compact, the full plastic moment can be developed.",
            equation="Mn,tee = Mp,tee",
            substitution=f"Mn,tee = {Mp_tee:.3f}",
            result=Mn_tee,
            unit="kN·m",
            code_ref="AISC 360-16 F9.1"
        ))
    
    # =========================================================================
    # 5. COMBINED TEE CAPACITY
    # =========================================================================
    # Total Vierendeel capacity from both tees
    Mn_vr = 2 * Mn_tee  # Both top and bottom tees contribute
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Total Vierendeel Moment Capacity",
        description="The total Vierendeel moment resistance is provided by both top and bottom tees "
                   "acting together. For symmetric sections, this is twice the single tee capacity.",
        equation="Mn,vr = 2 × Mn,tee",
        substitution=f"Mn,vr = 2 × {Mn_tee:.3f}",
        result=Mn_vr,
        unit="kN·m",
        code_ref="AISC DG31 §5.3.3"
    ))
    
    # =========================================================================
    # 6. DESIGN/ALLOWABLE STRENGTH
    # =========================================================================
    if method == "LRFD":
        phi_b = 0.90
        Mn_vr_design = phi_b * Mn_vr
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Design Vierendeel Strength (LRFD)",
            description="Apply the resistance factor φb = 0.90 for flexure.",
            equation="φMn,vr = 0.90 × Mn,vr",
            substitution=f"φMn,vr = 0.90 × {Mn_vr:.3f}",
            result=Mn_vr_design,
            unit="kN·m",
            code_ref="AISC 360-16 F1(1)"
        ))
    else:
        Omega_b = 1.67
        Mn_vr_design = Mn_vr / Omega_b
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Allowable Vierendeel Strength (ASD)",
            description="Apply the safety factor Ωb = 1.67 for flexure.",
            equation="Mn,vr/Ωb = Mn,vr / 1.67",
            substitution=f"Mn,vr/Ωb = {Mn_vr:.3f} / 1.67",
            result=Mn_vr_design,
            unit="kN·m",
            code_ref="AISC 360-16 F1(2)"
        ))
    
    # =========================================================================
    # 7. DEMAND/CAPACITY CHECK
    # =========================================================================
    # Required Vierendeel moment (both tees together)
    Mvr_total = 2 * Mvr  # Total demand on both tees
    ratio = Mvr_total / Mn_vr_design if Mn_vr_design > 0 else float('inf')
    status = "PASS" if ratio <= 1.0 else "FAIL"
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Vierendeel Bending Check",
        description="Compare the required Vierendeel moment to the available capacity.",
        equation="Mvr / φMn,vr ≤ 1.0" if method == "LRFD" else "Mvr / (Mn,vr/Ωb) ≤ 1.0",
        substitution=f"{Mvr_total:.3f} / {Mn_vr_design:.3f}",
        result=ratio,
        unit="-",
        code_ref="AISC DG31 §5.3",
        status=status,
        notes=f"{'✓ OK - Vierendeel bending is adequate' if status == 'PASS' else '✗ NG - Vierendeel bending capacity exceeded'}"
    ))
    
    section.steps = steps
    section.status = status
    section.conclusion = f"""
VIERENDEEL BENDING SUMMARY:
══════════════════════════════════════════════════════════════════════════════
Design Method: {method}
──────────────────────────────────────────────────────────────────────────────
TEE CLASSIFICATION:
  Flange slenderness (λf):      {lambda_f:.2f} ({flange_status})
  Stem slenderness (λw):        {lambda_w:.2f} ({stem_status})
──────────────────────────────────────────────────────────────────────────────
CAPACITY:
  Single tee moment (Mn,tee):   {Mn_tee:.3f} kN·m
  Total Vierendeel (Mn,vr):     {Mn_vr:.3f} kN·m
  Design strength:              {Mn_vr_design:.3f} kN·m
──────────────────────────────────────────────────────────────────────────────
DEMAND:
  Shear at opening (Vu):        {Vu:.2f} kN
  Vierendeel moment (Mvr):      {Mvr_total:.3f} kN·m
──────────────────────────────────────────────────────────────────────────────
CHECK:
  D/C Ratio:                    {ratio:.3f}
  Status:                       {status}
══════════════════════════════════════════════════════════════════════════════
"""
    
    return section, {
        'V_tee': V_tee, 'Mvr': Mvr, 'Mvr_total': Mvr_total,
        'Mn_tee': Mn_tee, 'Mn_vr': Mn_vr, 'Mn_vr_design': Mn_vr_design,
        'ratio': ratio
    }


def calc_web_post_buckling_detailed(
    parent_name: str,
    ho: float, b_wp: float, tw: float,
    beam_type: str, S: float, Do: float, theta: float,
    Fy: float, E: float,
    Vh: float,
    method: str = "LRFD"
) -> DetailedCalcSection:
    """
    Detailed web post buckling calculation per AISC DG31 §5.4.
    
    The web post between openings is subjected to horizontal shear and
    compression forces that can cause buckling.
    
    Args:
        Section properties and geometry
        Vh: Horizontal shear force in web post (kN)
        method: "LRFD" or "ASD"
        
    Returns:
        DetailedCalcSection with all calculation steps
    """
    section = DetailedCalcSection(
        section_number=4,
        title="WEB POST BUCKLING",
        description="Check web post stability under combined horizontal shear and compression "
                   "per AISC DG31 Section 5.4. The web post is the solid web region between "
                   "adjacent openings and must resist forces transferred between tees.",
        code_ref="AISC DG31 §5.4"
    )
    
    steps = []
    step_num = 0
    
    # =========================================================================
    # 1. WEB POST GEOMETRY
    # =========================================================================
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Post Dimensions",
        description="The web post is the solid web region between adjacent openings. "
                   "Its geometry affects its buckling resistance.",
        equation="b_wp = b (castellated) or S - Do (cellular)",
        substitution=f"b_wp = {b_wp:.1f} mm, ho = {ho:.1f} mm, tw = {tw} mm",
        result=b_wp,
        unit="mm",
        code_ref="AISC DG31 §5.4.1"
    ))
    
    # =========================================================================
    # 2. WEB POST SLENDERNESS
    # =========================================================================
    # Effective length of web post for buckling
    if beam_type == "Castellated":
        # For castellated, the buckle half-wavelength depends on geometry
        # Per DG31, use ho as the effective height
        h_eff = ho
    else:
        # For cellular, similar approach
        h_eff = Do
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Post Effective Height",
        description="The effective height of the web post for buckling analysis. "
                   "This is the height over which buckling can occur.",
        equation="h_eff = ho (castellated) or Do (cellular)",
        substitution=f"h_eff = {h_eff:.1f} mm",
        result=h_eff,
        unit="mm",
        code_ref="AISC DG31 §5.4.1"
    ))
    
    # Slenderness ratio
    lambda_wp = h_eff / tw
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Post Slenderness Ratio",
        description="The slenderness ratio of the web post, which affects its buckling capacity.",
        equation="λ_wp = h_eff / tw",
        substitution=f"λ_wp = {h_eff:.1f} / {tw}",
        result=lambda_wp,
        unit="-",
        code_ref="AISC DG31 §5.4.1"
    ))
    
    # =========================================================================
    # 3. WEB POST BUCKLING EQUATIONS
    # =========================================================================
    # Per DG31, the web post buckling capacity is based on empirical equations
    # that account for the complex stress field
    
    # For castellated beams (hexagonal openings)
    if beam_type == "Castellated":
        # Buckling coefficient depends on b/ho ratio
        b_ho_ratio = b_wp / ho
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Web Post Width Ratio",
            description="The ratio of web post width to opening height affects the buckling mode.",
            equation="b/ho ratio",
            substitution=f"b/ho = {b_wp:.1f} / {ho:.1f}",
            result=b_ho_ratio,
            unit="-",
            code_ref="AISC DG31 §5.4.2"
        ))
        
        # Critical buckling stress - empirical equation from DG31
        # Simplified approach: treat as compression member with modified K
        K_wp = 0.9  # Effective length factor for web post
        Fe_wp = math.pi**2 * E / (K_wp * lambda_wp)**2
        
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Elastic Buckling Stress",
            description="Calculate the elastic buckling stress of the web post as a compression element.",
            equation="Fe = π²E / (K × λ_wp)²",
            substitution=f"Fe = π² × {E} / ({K_wp} × {lambda_wp:.1f})²",
            result=Fe_wp,
            unit="MPa",
            code_ref="AISC DG31 §5.4.2, AISC 360-16 E3"
        ))
        
    else:  # Cellular
        # For cellular beams, buckling is around the circular opening
        # Use similar approach with adjusted parameters
        b_Do_ratio = b_wp / Do
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Web Post Width Ratio (Cellular)",
            description="The ratio of web post width to opening diameter.",
            equation="(S-Do)/Do ratio",
            substitution=f"b/Do = {b_wp:.1f} / {Do:.1f}",
            result=b_Do_ratio,
            unit="-",
            code_ref="AISC DG31 §5.4.3"
        ))
        
        K_wp = 0.85  # Slightly lower K for cellular
        Fe_wp = math.pi**2 * E / (K_wp * lambda_wp)**2
        
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Elastic Buckling Stress (Cellular)",
            description="Elastic buckling stress for the web post between circular openings.",
            equation="Fe = π²E / (K × λ_wp)²",
            substitution=f"Fe = π² × {E} / ({K_wp} × {lambda_wp:.1f})²",
            result=Fe_wp,
            unit="MPa",
            code_ref="AISC DG31 §5.4.3"
        ))
    
    # =========================================================================
    # 4. CRITICAL BUCKLING STRESS
    # =========================================================================
    # Apply AISC column equations
    Fe_Fy = Fe_wp / Fy
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Elastic-to-Yield Ratio",
        description="Compare elastic buckling stress to yield stress to determine which "
                   "column curve equation applies.",
        equation="Fe/Fy",
        substitution=f"Fe/Fy = {Fe_wp:.1f} / {Fy}",
        result=Fe_Fy,
        unit="-",
        code_ref="AISC 360-16 E3"
    ))
    
    if Fe_Fy >= 2.25:
        # Inelastic buckling
        Fcr = Fy * 0.658**(Fy/Fe_wp)
        buckle_type = "Inelastic"
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Critical Stress (Inelastic Buckling)",
            description="Since Fe ≥ 2.25Fy, inelastic buckling governs. Use AISC Eq. E3-2.",
            equation="Fcr = Fy × 0.658^(Fy/Fe)",
            substitution=f"Fcr = {Fy} × 0.658^({Fy}/{Fe_wp:.1f})",
            result=Fcr,
            unit="MPa",
            code_ref="AISC 360-16 Eq. E3-2"
        ))
    else:
        # Elastic buckling
        Fcr = 0.877 * Fe_wp
        buckle_type = "Elastic"
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Critical Stress (Elastic Buckling)",
            description="Since Fe < 2.25Fy, elastic buckling governs. Use AISC Eq. E3-3.",
            equation="Fcr = 0.877 × Fe",
            substitution=f"Fcr = 0.877 × {Fe_wp:.1f}",
            result=Fcr,
            unit="MPa",
            code_ref="AISC 360-16 Eq. E3-3"
        ))
    
    # =========================================================================
    # 5. WEB POST BUCKLING CAPACITY
    # =========================================================================
    # Area of web post in shear/compression
    A_wp = b_wp * tw
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Post Area",
        description="The effective area of the web post resisting buckling forces.",
        equation="A_wp = b_wp × tw",
        substitution=f"A_wp = {b_wp:.1f} × {tw}",
        result=A_wp,
        unit="mm²",
        code_ref="AISC DG31 §5.4"
    ))
    
    # Nominal buckling capacity
    Pn_wp = Fcr * A_wp / 1000  # kN
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Nominal Buckling Capacity",
        description="The nominal web post buckling resistance.",
        equation="Pn = Fcr × A_wp",
        substitution=f"Pn = {Fcr:.1f} × {A_wp:.0f} / 1000",
        result=Pn_wp,
        unit="kN",
        code_ref="AISC DG31 §5.4"
    ))
    
    # =========================================================================
    # 6. DESIGN/ALLOWABLE CAPACITY
    # =========================================================================
    if method == "LRFD":
        phi_c = 0.90
        Pn_design = phi_c * Pn_wp
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Design Buckling Capacity (LRFD)",
            description="Apply the resistance factor φc = 0.90 for compression.",
            equation="φPn = 0.90 × Pn",
            substitution=f"φPn = 0.90 × {Pn_wp:.2f}",
            result=Pn_design,
            unit="kN",
            code_ref="AISC 360-16 E1"
        ))
    else:
        Omega_c = 1.67
        Pn_design = Pn_wp / Omega_c
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Allowable Buckling Capacity (ASD)",
            description="Apply the safety factor Ωc = 1.67 for compression.",
            equation="Pn/Ωc = Pn / 1.67",
            substitution=f"Pn/Ωc = {Pn_wp:.2f} / 1.67",
            result=Pn_design,
            unit="kN",
            code_ref="AISC 360-16 E1"
        ))
    
    # =========================================================================
    # 7. DEMAND/CAPACITY CHECK
    # =========================================================================
    ratio = Vh / Pn_design if Pn_design > 0 else float('inf')
    status = "PASS" if ratio <= 1.0 else "FAIL"
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Post Buckling Check",
        description="Compare the horizontal shear force in the web post to its buckling capacity.",
        equation="Vh / φPn ≤ 1.0" if method == "LRFD" else "Vh / (Pn/Ωc) ≤ 1.0",
        substitution=f"{Vh:.2f} / {Pn_design:.2f}",
        result=ratio,
        unit="-",
        code_ref="AISC DG31 §5.4",
        status=status,
        notes=f"{'✓ OK - Web post buckling is adequate' if status == 'PASS' else '✗ NG - Web post buckling capacity exceeded'}"
    ))
    
    section.steps = steps
    section.status = status
    section.conclusion = f"""
WEB POST BUCKLING SUMMARY:
══════════════════════════════════════════════════════════════════════════════
Design Method: {method}
Buckling Type: {buckle_type}
──────────────────────────────────────────────────────────────────────────────
WEB POST GEOMETRY:
  Width (b_wp):                 {b_wp:.1f} mm
  Height (h_eff):               {h_eff:.1f} mm
  Thickness (tw):               {tw} mm
  Slenderness (λ_wp):           {lambda_wp:.1f}
──────────────────────────────────────────────────────────────────────────────
BUCKLING ANALYSIS:
  Elastic buckling (Fe):        {Fe_wp:.1f} MPa
  Critical stress (Fcr):        {Fcr:.1f} MPa
  Nominal capacity (Pn):        {Pn_wp:.2f} kN
  Design capacity:              {Pn_design:.2f} kN
──────────────────────────────────────────────────────────────────────────────
DEMAND:
  Horizontal shear (Vh):        {Vh:.2f} kN
──────────────────────────────────────────────────────────────────────────────
CHECK:
  D/C Ratio:                    {ratio:.3f}
  Status:                       {status}
══════════════════════════════════════════════════════════════════════════════
"""
    
    return section, {
        'lambda_wp': lambda_wp, 'Fe_wp': Fe_wp, 'Fcr': Fcr,
        'Pn_wp': Pn_wp, 'Pn_design': Pn_design, 'ratio': ratio,
        'buckle_type': buckle_type
    }


def calc_horizontal_shear_detailed(
    dg: float, ho: float, dt: float, tw: float,
    Ix_gross: float, Ix_net: float,
    Mu: float, S: float,
    Fy: float, E: float,
    method: str = "LRFD"
) -> DetailedCalcSection:
    """
    Detailed horizontal shear calculation per AISC DG31 §5.5.
    
    Horizontal shear force develops in the web post due to the change in
    moment across the opening, transferred through the web post.
    """
    section = DetailedCalcSection(
        section_number=5,
        title="HORIZONTAL SHEAR",
        description="Calculate the horizontal shear force in the web post due to moment gradient "
                   "across the opening per AISC DG31 Section 5.5.",
        code_ref="AISC DG31 §5.5"
    )
    
    steps = []
    step_num = 0
    
    # =========================================================================
    # 1. MOMENT GRADIENT AND HORIZONTAL SHEAR
    # =========================================================================
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Horizontal Shear Mechanism",
        description="As moment varies along the beam, the compression and tension forces in the "
                   "tees change. This change must be transferred through the web post as horizontal shear.",
        equation="Vh = ΔT = ΔC (force equilibrium)",
        substitution="The horizontal shear equals the change in axial force across the opening",
        result=0,
        unit="kN",
        code_ref="AISC DG31 §5.5.1"
    ))
    
    # Calculate horizontal shear from moment
    # Vh = (M/dg) × (S/dg) approximately
    # Or more accurately: Vh = V × S × ho / (2 × Ix_gross) × A_tee
    
    # Simplified approach: Vh based on global moment
    arm = dg - dt  # Moment arm between tee centroids
    T_flange = Mu * 1000 / arm  # Force in one flange (N converted from kN·m)
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Flange Force from Moment",
        description="Calculate the approximate axial force in each tee from the global moment.",
        equation="T = M / (dg - dt)",
        substitution=f"T = {Mu:.2f} × 1000 / ({dg:.1f} - {dt:.1f})",
        result=T_flange/1000,
        unit="kN",
        code_ref="AISC DG31 §5.5.1"
    ))
    
    # Horizontal shear is related to how this force changes across one opening
    # Simplified: Vh ≈ T × (S/L) for uniform moment gradient
    # Use conservative estimate
    Vh = T_flange / 1000 * S / (dg * 10)  # Approximate horizontal shear
    Vh = max(Vh, 0.05 * T_flange / 1000)  # Minimum 5% of flange force
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Horizontal Shear Force",
        description="Estimate the horizontal shear force in the web post. This is conservatively "
                   "taken as a fraction of the flange force based on the moment gradient.",
        equation="Vh ≈ T × (S / 10dg) (approximate for uniform load)",
        substitution=f"Vh = {T_flange/1000:.1f} × {S:.0f} / (10 × {dg:.1f})",
        result=Vh,
        unit="kN",
        code_ref="AISC DG31 §5.5.2"
    ))
    
    # =========================================================================
    # 2. HORIZONTAL SHEAR CAPACITY
    # =========================================================================
    # Web post resists horizontal shear through its cross-section
    # Capacity based on shear yield
    A_wp_shear = ho * tw  # Effective area for horizontal shear
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Post Shear Area",
        description="The effective area of the web post resisting horizontal shear.",
        equation="Aw = ho × tw",
        substitution=f"Aw = {ho:.1f} × {tw}",
        result=A_wp_shear,
        unit="mm²",
        code_ref="AISC DG31 §5.5.3"
    ))
    
    # Nominal shear capacity
    Fv = 0.6 * Fy  # Shear yield stress
    Vn_h = Fv * A_wp_shear / 1000  # kN
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Nominal Horizontal Shear Capacity",
        description="The nominal horizontal shear capacity based on shear yielding of the web post.",
        equation="Vn = 0.6Fy × Aw",
        substitution=f"Vn = 0.6 × {Fy} × {A_wp_shear:.0f} / 1000",
        result=Vn_h,
        unit="kN",
        code_ref="AISC 360-16 J4.2"
    ))
    
    # =========================================================================
    # 3. DESIGN/ALLOWABLE CAPACITY
    # =========================================================================
    if method == "LRFD":
        phi_v = 1.00
        Vn_design = phi_v * Vn_h
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Design Horizontal Shear Capacity (LRFD)",
            description="Apply the resistance factor φv = 1.00 for shear yielding.",
            equation="φVn = 1.00 × Vn",
            substitution=f"φVn = 1.00 × {Vn_h:.2f}",
            result=Vn_design,
            unit="kN",
            code_ref="AISC 360-16 J4.2"
        ))
    else:
        Omega_v = 1.50
        Vn_design = Vn_h / Omega_v
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Allowable Horizontal Shear Capacity (ASD)",
            description="Apply the safety factor Ωv = 1.50 for shear.",
            equation="Vn/Ωv = Vn / 1.50",
            substitution=f"Vn/Ωv = {Vn_h:.2f} / 1.50",
            result=Vn_design,
            unit="kN",
            code_ref="AISC 360-16 J4.2"
        ))
    
    # =========================================================================
    # 4. DEMAND/CAPACITY CHECK
    # =========================================================================
    ratio = Vh / Vn_design if Vn_design > 0 else float('inf')
    status = "PASS" if ratio <= 1.0 else "FAIL"
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Horizontal Shear Check",
        description="Compare the horizontal shear force to the available capacity.",
        equation="Vh / φVn ≤ 1.0" if method == "LRFD" else "Vh / (Vn/Ωv) ≤ 1.0",
        substitution=f"{Vh:.2f} / {Vn_design:.2f}",
        result=ratio,
        unit="-",
        code_ref="AISC DG31 §5.5",
        status=status,
        notes=f"{'✓ OK - Horizontal shear is adequate' if status == 'PASS' else '✗ NG - Horizontal shear capacity exceeded'}"
    ))
    
    section.steps = steps
    section.status = status
    section.conclusion = f"""
HORIZONTAL SHEAR SUMMARY:
══════════════════════════════════════════════════════════════════════════════
Design Method: {method}
──────────────────────────────────────────────────────────────────────────────
CAPACITY:
  Shear area (Aw):              {A_wp_shear:.0f} mm²
  Shear yield stress (0.6Fy):   {Fv:.1f} MPa
  Nominal capacity (Vn):        {Vn_h:.2f} kN
  Design capacity:              {Vn_design:.2f} kN
──────────────────────────────────────────────────────────────────────────────
DEMAND:
  Horizontal shear (Vh):        {Vh:.2f} kN
──────────────────────────────────────────────────────────────────────────────
CHECK:
  D/C Ratio:                    {ratio:.3f}
  Status:                       {status}
══════════════════════════════════════════════════════════════════════════════
"""
    
    return section, {
        'Vh': Vh, 'Vn_h': Vn_h, 'Vn_design': Vn_design, 'ratio': ratio
    }


def calc_vertical_shear_detailed(
    dg: float, ho: float, dt: float, bf: float, tf: float, tw: float,
    A_tee: float,
    Fy: float, E: float,
    Vu: float,
    method: str = "LRFD"
) -> DetailedCalcSection:
    """
    Detailed vertical shear calculation at openings per AISC DG31 §5.6.
    """
    section = DetailedCalcSection(
        section_number=6,
        title="VERTICAL SHEAR AT OPENINGS",
        description="Check vertical shear capacity at web openings per AISC DG31 Section 5.6. "
                   "At openings, shear must be transferred through the tee sections.",
        code_ref="AISC DG31 §5.6"
    )
    
    steps = []
    step_num = 0
    
    # =========================================================================
    # 1. SHEAR AT OPENING
    # =========================================================================
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Required Vertical Shear",
        description="The required vertical shear strength at the critical opening location.",
        equation="Vu from structural analysis",
        substitution=f"Vu = {Vu:.2f} kN",
        result=Vu,
        unit="kN",
        code_ref="ASCE 7 Load Combinations"
    ))
    
    # =========================================================================
    # 2. TEE SHEAR AREA
    # =========================================================================
    # At opening, shear is carried by the two tee stems
    d_stem = dt - tf
    Aw_tee = d_stem * tw  # Shear area of one tee stem
    Aw_total = 2 * Aw_tee  # Both tees
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Stem Depth",
        description="The depth of the tee stem (web portion of tee).",
        equation="d_stem = dt - tf",
        substitution=f"d_stem = {dt:.1f} - {tf}",
        result=d_stem,
        unit="mm",
        code_ref="AISC DG31 §5.6.1"
    ))
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Total Shear Area at Opening",
        description="The total area resisting vertical shear consists of both tee stems.",
        equation="Aw = 2 × d_stem × tw",
        substitution=f"Aw = 2 × {d_stem:.1f} × {tw}",
        result=Aw_total,
        unit="mm²",
        code_ref="AISC DG31 §5.6.1"
    ))
    
    # =========================================================================
    # 3. WEB SHEAR COEFFICIENT
    # =========================================================================
    # Check if web is compact for shear
    h_tw = d_stem / tw
    kv = 5.34  # For unstiffened webs
    Cv1_limit = 1.10 * math.sqrt(kv * E / Fy)
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Tee Stem Slenderness for Shear",
        description="Check the web slenderness to determine the shear coefficient Cv.",
        equation="h/tw vs 1.10√(kvE/Fy)",
        substitution=f"h/tw = {h_tw:.1f}, limit = 1.10×√({kv}×{E}/{Fy}) = {Cv1_limit:.1f}",
        result=h_tw,
        unit="-",
        code_ref="AISC 360-16 G2.1"
    ))
    
    if h_tw <= Cv1_limit:
        Cv = 1.0
        shear_type = "Yielding"
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Web Shear Coefficient",
            description="Since h/tw ≤ 1.10√(kvE/Fy), the web is compact for shear and Cv = 1.0.",
            equation="Cv = 1.0 (compact web)",
            substitution=f"h/tw = {h_tw:.1f} ≤ {Cv1_limit:.1f} ∴ Cv = 1.0",
            result=Cv,
            unit="-",
            code_ref="AISC 360-16 G2.1(a)"
        ))
    else:
        Cv2_limit = 1.37 * math.sqrt(kv * E / Fy)
        if h_tw <= Cv2_limit:
            Cv = Cv1_limit / h_tw
            shear_type = "Inelastic Buckling"
        else:
            Cv = 1.51 * kv * E / (h_tw**2 * Fy)
            shear_type = "Elastic Buckling"
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Web Shear Coefficient (Noncompact)",
            description=f"Since h/tw > 1.10√(kvE/Fy), {shear_type.lower()} governs.",
            equation="Cv from AISC 360-16 G2.1",
            substitution=f"Cv = {Cv:.3f}",
            result=Cv,
            unit="-",
            code_ref="AISC 360-16 G2.1"
        ))
    
    # =========================================================================
    # 4. NOMINAL SHEAR STRENGTH
    # =========================================================================
    Vn = 0.6 * Fy * Aw_total * Cv / 1000  # kN
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Nominal Vertical Shear Strength",
        description="Calculate the nominal shear strength at the opening.",
        equation="Vn = 0.6 × Fy × Aw × Cv",
        substitution=f"Vn = 0.6 × {Fy} × {Aw_total:.0f} × {Cv:.3f} / 1000",
        result=Vn,
        unit="kN",
        code_ref="AISC 360-16 G2.1"
    ))
    
    # =========================================================================
    # 5. DESIGN/ALLOWABLE CAPACITY
    # =========================================================================
    if method == "LRFD":
        if Cv == 1.0:
            phi_v = 1.00
        else:
            phi_v = 0.90
        Vn_design = phi_v * Vn
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Design Shear Strength (LRFD)",
            description=f"Apply φv = {phi_v:.2f} for shear.",
            equation=f"φVn = {phi_v:.2f} × Vn",
            substitution=f"φVn = {phi_v:.2f} × {Vn:.2f}",
            result=Vn_design,
            unit="kN",
            code_ref="AISC 360-16 G1"
        ))
    else:
        if Cv == 1.0:
            Omega_v = 1.50
        else:
            Omega_v = 1.67
        Vn_design = Vn / Omega_v
        step_num += 1
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Allowable Shear Strength (ASD)",
            description=f"Apply Ωv = {Omega_v:.2f} for shear.",
            equation=f"Vn/Ωv = Vn / {Omega_v:.2f}",
            substitution=f"Vn/Ωv = {Vn:.2f} / {Omega_v:.2f}",
            result=Vn_design,
            unit="kN",
            code_ref="AISC 360-16 G1"
        ))
    
    # =========================================================================
    # 6. DEMAND/CAPACITY CHECK
    # =========================================================================
    ratio = Vu / Vn_design if Vn_design > 0 else float('inf')
    status = "PASS" if ratio <= 1.0 else "FAIL"
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Vertical Shear Check",
        description="Compare the required shear to the available shear strength at the opening.",
        equation="Vu / φVn ≤ 1.0" if method == "LRFD" else "Va / (Vn/Ωv) ≤ 1.0",
        substitution=f"{Vu:.2f} / {Vn_design:.2f}",
        result=ratio,
        unit="-",
        code_ref="AISC DG31 §5.6",
        status=status,
        notes=f"{'✓ OK - Vertical shear at opening is adequate' if status == 'PASS' else '✗ NG - Vertical shear capacity exceeded'}"
    ))
    
    section.steps = steps
    section.status = status
    section.conclusion = f"""
VERTICAL SHEAR AT OPENINGS SUMMARY:
══════════════════════════════════════════════════════════════════════════════
Design Method: {method}
Shear Behavior: {shear_type}
──────────────────────────────────────────────────────────────────────────────
SHEAR AREA:
  Tee stem depth (d_stem):      {d_stem:.1f} mm
  Total shear area (Aw):        {Aw_total:.0f} mm²
  Web slenderness (h/tw):       {h_tw:.1f}
  Shear coefficient (Cv):       {Cv:.3f}
──────────────────────────────────────────────────────────────────────────────
CAPACITY:
  Nominal capacity (Vn):        {Vn:.2f} kN
  Design capacity:              {Vn_design:.2f} kN
──────────────────────────────────────────────────────────────────────────────
DEMAND:
  Required shear (Vu):          {Vu:.2f} kN
──────────────────────────────────────────────────────────────────────────────
CHECK:
  D/C Ratio:                    {ratio:.3f}
  Status:                       {status}
══════════════════════════════════════════════════════════════════════════════
"""
    
    return section, {
        'Aw_total': Aw_total, 'Cv': Cv, 'Vn': Vn, 
        'Vn_design': Vn_design, 'ratio': ratio
    }


def calc_deflection_detailed(
    L: float, dg: float,
    Ix_gross: float, Ix_net: float,
    E: float,
    w_dead: float, w_live: float,
    n_openings: int = 10
) -> DetailedCalcSection:
    """
    Detailed deflection calculation per AISC DG31 §5.7.
    """
    section = DetailedCalcSection(
        section_number=7,
        title="DEFLECTION",
        description="Calculate beam deflection considering the effect of web openings "
                   "per AISC DG31 Section 5.7. Web openings reduce stiffness and increase deflection.",
        code_ref="AISC DG31 §5.7"
    )
    
    steps = []
    step_num = 0
    
    # =========================================================================
    # 1. LOADING
    # =========================================================================
    w_total = w_dead + w_live
    w_service = w_total  # kN/m
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Service Load",
        description="The total service load for deflection calculation (unfactored).",
        equation="w = wD + wL",
        substitution=f"w = {w_dead} + {w_live}",
        result=w_service,
        unit="kN/m",
        code_ref="Service Load Combination"
    ))
    
    # =========================================================================
    # 2. EFFECTIVE MOMENT OF INERTIA
    # =========================================================================
    # For castellated/cellular beams, use weighted average Ix
    # Approximate: 85-90% of gross Ix to account for openings
    
    # More accurate: Ix_eff = Ix_gross × (1 - k × Aₒ/Ag)
    # where k is a factor depending on opening geometry
    # Simplified approach: use ratio of opening length to spacing
    
    Ix_avg = (Ix_gross + Ix_net) / 2
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Average Moment of Inertia",
        description="Calculate an average moment of inertia considering both solid and open sections.",
        equation="Ix,avg = (Ix,gross + Ix,net) / 2",
        substitution=f"Ix,avg = ({Ix_gross/1e6:.2f}×10⁶ + {Ix_net/1e6:.2f}×10⁶) / 2",
        result=Ix_avg,
        unit="mm⁴",
        code_ref="AISC DG31 §5.7.1"
    ))
    
    # Effective Ix considering additional shear deformation at openings
    # Use reduction factor based on number of openings
    alpha = 1.0 + 0.015 * n_openings  # Deflection increase factor
    Ix_eff = Ix_avg / alpha
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Effective Moment of Inertia",
        description="Apply a reduction to account for additional shear deformation at openings. "
                   "The factor increases with the number of openings.",
        equation="Ix,eff = Ix,avg / α where α = 1 + 0.015 × n_openings",
        substitution=f"Ix,eff = {Ix_avg/1e6:.2f}×10⁶ / {alpha:.3f}",
        result=Ix_eff,
        unit="mm⁴",
        code_ref="AISC DG31 §5.7.2"
    ))
    
    # =========================================================================
    # 3. CALCULATED DEFLECTION
    # =========================================================================
    # Simple span uniform load deflection
    # δ = 5wL⁴ / (384EI)
    # Units: w in kN/m = N/mm (numerically), L in mm, E in MPa = N/mm², I in mm⁴
    # Result in mm
    delta = 5 * w_service * (L**4) / (384 * E * Ix_eff)  # mm
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Calculated Deflection",
        description="Calculate the maximum deflection at midspan for a uniformly loaded simple span. "
                   "Note: 1 kN/m = 1 N/mm numerically, so units work directly.",
        equation="δ = 5wL⁴ / (384EI)",
        substitution=f"δ = 5 × {w_service:.2f} × ({L:.0f})⁴ / (384 × {E} × {Ix_eff/1e6:.2f}×10⁶)",
        result=delta,
        unit="mm",
        code_ref="AISC DG31 §5.7.3"
    ))
    
    # =========================================================================
    # 4. DEFLECTION LIMITS
    # =========================================================================
    # L/240 for total load, L/360 for live load
    delta_limit_total = L / 240
    delta_limit_live = L / 360
    delta_live = delta * w_live / w_total if w_total > 0 else 0
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Deflection Limit (Total Load)",
        description="The allowable deflection limit for total load is typically L/240.",
        equation="δ_allow = L / 240",
        substitution=f"δ_allow = {L:.0f} / 240",
        result=delta_limit_total,
        unit="mm",
        code_ref="IBC Table 1604.3"
    ))
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Deflection Limit (Live Load)",
        description="The allowable deflection limit for live load is typically L/360.",
        equation="δ_allow = L / 360",
        substitution=f"δ_allow = {L:.0f} / 360",
        result=delta_limit_live,
        unit="mm",
        code_ref="IBC Table 1604.3"
    ))
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Live Load Deflection",
        description="Calculate the deflection due to live load only.",
        equation="δL = δ_total × wL / (wD + wL)",
        substitution=f"δL = {delta:.2f} × {w_live} / {w_total}",
        result=delta_live,
        unit="mm",
        code_ref="Proportional to loads"
    ))
    
    # =========================================================================
    # 5. DEFLECTION CHECKS
    # =========================================================================
    ratio_total = delta / delta_limit_total
    ratio_live = delta_live / delta_limit_live
    status = "PASS" if ratio_total <= 1.0 and ratio_live <= 1.0 else "FAIL"
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Total Load Deflection Check",
        description="Compare calculated total load deflection to the L/240 limit.",
        equation="δ / (L/240) ≤ 1.0",
        substitution=f"{delta:.2f} / {delta_limit_total:.2f}",
        result=ratio_total,
        unit="-",
        code_ref="IBC 1604.3",
        status="PASS" if ratio_total <= 1.0 else "FAIL",
        notes=f"{'✓ OK' if ratio_total <= 1.0 else '✗ NG'} - δ = L/{L/delta:.0f}"
    ))
    
    step_num += 1
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Live Load Deflection Check",
        description="Compare calculated live load deflection to the L/360 limit.",
        equation="δL / (L/360) ≤ 1.0",
        substitution=f"{delta_live:.2f} / {delta_limit_live:.2f}",
        result=ratio_live,
        unit="-",
        code_ref="IBC 1604.3",
        status="PASS" if ratio_live <= 1.0 else "FAIL",
        notes=f"{'✓ OK' if ratio_live <= 1.0 else '✗ NG'} - δL = L/{int(L/delta_live) if delta_live > 0 else 'inf'}"
    ))
    
    section.steps = steps
    section.status = status
    section.conclusion = f"""
DEFLECTION SUMMARY:
══════════════════════════════════════════════════════════════════════════════
STIFFNESS:
  Gross Ix:                     {Ix_gross/1e6:.2f} × 10⁶ mm⁴
  Net Ix (at opening):          {Ix_net/1e6:.2f} × 10⁶ mm⁴
  Effective Ix:                 {Ix_eff/1e6:.2f} × 10⁶ mm⁴
  Reduction factor (α):         {alpha:.3f}
──────────────────────────────────────────────────────────────────────────────
CALCULATED DEFLECTIONS:
  Total load deflection:        {delta:.2f} mm = L/{L/delta:.0f}
  Live load deflection:         {delta_live:.2f} mm = L/{int(L/delta_live) if delta_live > 0 else 'inf'}
──────────────────────────────────────────────────────────────────────────────
LIMITS:
  Total (L/240):                {delta_limit_total:.2f} mm
  Live (L/360):                 {delta_limit_live:.2f} mm
──────────────────────────────────────────────────────────────────────────────
CHECKS:
  Total D/C:                    {ratio_total:.3f} {'✓ OK' if ratio_total <= 1.0 else '✗ NG'}
  Live D/C:                     {ratio_live:.3f} {'✓ OK' if ratio_live <= 1.0 else '✗ NG'}
  Overall Status:               {status}
══════════════════════════════════════════════════════════════════════════════
"""
    
    return section, {
        'Ix_eff': Ix_eff, 'alpha': alpha,
        'delta': delta, 'delta_live': delta_live,
        'delta_limit_total': delta_limit_total, 'delta_limit_live': delta_limit_live,
        'ratio_total': ratio_total, 'ratio_live': ratio_live
    }


# =============================================================================
# MAIN DETAILED DESIGN FUNCTION
# =============================================================================

def design_castellated_detailed(
    parent_name: str,
    d: float, bf: float, tf: float, tw: float, A: float, Ix: float,
    beam_type: str,
    ho: float, e: float, b: float, S: float, theta: float,
    Do: float,
    Fy: float, Fu: float, E: float,
    w_dead: float, w_live: float, L: float,
    Lb: float,
    method: str = "LRFD"
) -> DetailedDesignReport:
    """
    Complete detailed design of castellated/cellular beam.
    
    Returns:
        DetailedDesignReport with all calculation sections
    """
    report = DetailedDesignReport(
        project_info={
            'title': 'Castellated/Cellular Beam Design',
            'code': 'AISC Design Guide 31',
            'designer': 'CompositeBeam Pro v2.8'
        },
        beam_designation=f"{beam_type} from {parent_name}",
        beam_type=beam_type
    )
    
    # =========================================================================
    # 1. SECTION PROPERTIES
    # =========================================================================
    sec_props_section, props = calc_section_properties_detailed(
        parent_name, d, bf, tf, tw, A, Ix,
        beam_type, ho, e, b, S, theta, Do
    )
    report.add_section(sec_props_section)
    
    # =========================================================================
    # 2. LOAD CALCULATIONS
    # =========================================================================
    # Input units: w_dead, w_live in kN/m, L in mm
    # Convert L to meters for calculation
    L_m = L / 1000  # m
    
    # Factored loads for strength design
    if method == "LRFD":
        w_u = 1.2 * w_dead + 1.6 * w_live  # kN/m
    else:
        w_u = w_dead + w_live  # kN/m
    
    # Calculate demands
    # Mu = w × L² / 8 (for simply supported beam with uniform load)
    Mu = w_u * L_m**2 / 8  # kN·m
    Vu = w_u * L_m / 2  # kN
    
    # =========================================================================
    # 3. GLOBAL FLEXURE
    # =========================================================================
    flexure_section, flex_results = calc_global_flexure_detailed(
        parent_name,
        props['dg'], bf, tf, tw, props['ho'], props['dt'],
        props['Ix_gross'], props['Sx_gross'], props['Zx_gross'],
        Fy, E,
        Mu, Lb,
        method
    )
    report.add_section(flexure_section)
    
    # =========================================================================
    # 4. VIERENDEEL BENDING
    # =========================================================================
    vierendeel_section, vier_results = calc_vierendeel_bending_detailed(
        parent_name,
        props['dg'], props['ho'], props['dt'], bf, tf, tw,
        props['A_tee'], props['I_tee'], props['S_tee'], props['y_bar_tee'],
        beam_type, e, Do,
        Fy, E,
        Vu,  # kN
        method
    )
    report.add_section(vierendeel_section)
    
    # =========================================================================
    # 5. WEB POST BUCKLING
    # =========================================================================
    # Horizontal shear in web post (approximate)
    Vh = Vu * 0.15  # Approximate as 15% of vertical shear (kN)
    
    wp_section, wp_results = calc_web_post_buckling_detailed(
        parent_name,
        props['ho'], props['b_wp'], tw,
        beam_type, S, Do, theta,
        Fy, E,
        Vh,
        method
    )
    report.add_section(wp_section)
    
    # =========================================================================
    # 6. HORIZONTAL SHEAR
    # =========================================================================
    horiz_section, horiz_results = calc_horizontal_shear_detailed(
        props['dg'], props['ho'], props['dt'], tw,
        props['Ix_gross'], props['Ix_net'],
        Mu, S,
        Fy, E,
        method
    )
    report.add_section(horiz_section)
    
    # =========================================================================
    # 7. VERTICAL SHEAR
    # =========================================================================
    vert_section, vert_results = calc_vertical_shear_detailed(
        props['dg'], props['ho'], props['dt'], bf, tf, tw,
        props['A_tee'],
        Fy, E,
        Vu,  # kN
        method
    )
    report.add_section(vert_section)
    
    # =========================================================================
    # 8. DEFLECTION
    # =========================================================================
    n_openings = int(L / S) if S > 0 else 10
    defl_section, defl_results = calc_deflection_detailed(
        L, props['dg'],
        props['Ix_gross'], props['Ix_net'],
        E,
        w_dead, w_live,  # kN/m
        n_openings
    )
    report.add_section(defl_section)
    
    # =========================================================================
    # OVERALL SUMMARY
    # =========================================================================
    report.summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CASTELLATED/CELLULAR BEAM DESIGN SUMMARY                           ║
║                    Per AISC Design Guide 31                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Beam: {report.beam_designation[:60]:<60} ║
║ Method: {method:<68} ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ CHECK                          │ DEMAND    │ CAPACITY  │ D/C   │ STATUS     ║
╠────────────────────────────────┼───────────┼───────────┼───────┼────────────╣
║ Global Flexure (§5.2)          │ {Mu:>7.1f}   │ {flex_results['Mn_design']:>7.1f}   │ {flex_results['ratio']:>5.3f} │ {flexure_section.status:<10} ║
║ Vierendeel Bending (§5.3)      │ {vier_results['Mvr_total']:>7.3f}   │ {vier_results['Mn_vr_design']:>7.3f}   │ {vier_results['ratio']:>5.3f} │ {vierendeel_section.status:<10} ║
║ Web Post Buckling (§5.4)       │ {Vh:>7.1f}   │ {wp_results['Pn_design']:>7.1f}   │ {wp_results['ratio']:>5.3f} │ {wp_section.status:<10} ║
║ Horizontal Shear (§5.5)        │ {horiz_results['Vh']:>7.1f}   │ {horiz_results['Vn_design']:>7.1f}   │ {horiz_results['ratio']:>5.3f} │ {horiz_section.status:<10} ║
║ Vertical Shear (§5.6)          │ {Vu:>7.1f}   │ {vert_results['Vn_design']:>7.1f}   │ {vert_results['ratio']:>5.3f} │ {vert_section.status:<10} ║
║ Deflection (§5.7)              │ {defl_results['delta']:>7.1f}   │ {defl_results['delta_limit_total']:>7.1f}   │ {defl_results['ratio_total']:>5.3f} │ {defl_section.status:<10} ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ OVERALL RESULT: {report.overall_status:<62} ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    
    return report


def format_detailed_report(report: DetailedDesignReport) -> str:
    """
    Format the detailed design report as a complete text document.
    """
    output = []
    
    # Title
    output.append("=" * 80)
    output.append(f"  {report.project_info.get('title', 'DESIGN REPORT')}")
    output.append(f"  Code: {report.project_info.get('code', 'AISC DG31')}")
    output.append(f"  Generated by: {report.project_info.get('designer', 'CompositeBeam Pro')}")
    output.append("=" * 80)
    output.append("")
    output.append(f"BEAM: {report.beam_designation}")
    output.append(f"TYPE: {report.beam_type}")
    output.append("")
    
    # Each section
    for section in report.sections:
        output.append("")
        output.append("=" * 80)
        output.append(f"SECTION {section.section_number}: {section.title}")
        output.append(f"Reference: {section.code_ref}")
        output.append("-" * 80)
        output.append(section.description)
        output.append("-" * 80)
        output.append("")
        
        for step in section.steps:
            status_marker = ""
            if step.status == "PASS":
                status_marker = " ✓"
            elif step.status == "FAIL":
                status_marker = " ✗"
            elif step.status == "WARNING":
                status_marker = " ⚠"
            
            output.append(f"Step {step.step_number}: {step.title}{status_marker}")
            output.append(f"  {step.description}")
            output.append(f"  Equation: {step.equation}")
            output.append(f"  Calculation: {step.substitution}")
            output.append(f"  Result: {step.result:.4g} {step.unit}")
            output.append(f"  Reference: {step.code_ref}")
            if step.notes:
                output.append(f"  Note: {step.notes}")
            output.append("")
        
        output.append(section.conclusion)
    
    # Summary
    output.append(report.summary)
    
    return "\n".join(output)
