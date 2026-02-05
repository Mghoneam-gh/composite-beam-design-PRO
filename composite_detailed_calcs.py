"""
Composite Beam Design - DETAILED PROFESSIONAL CALCULATIONS
==========================================================

Per AISC 360-16 Specification for Structural Steel Buildings
Chapter I - Design of Composite Members

This module provides comprehensive step-by-step calculations suitable for
design review and checking by licensed professional engineers.

All calculations follow the methodology in:
- AISC 360-16 Chapter I: Design of Composite Members
- AISC Design Guide 3: Partially Restrained Composite Connections
- ASCE 7-22: Load Combinations

Author: CompositeBeam Pro
Version: 2.9
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# =============================================================================
# DATA CLASSES FOR DETAILED CALCULATIONS
# =============================================================================

@dataclass
class DetailedCalcStep:
    """
    A single calculation step with full professional documentation.
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
    """
    section_number: int
    title: str
    description: str
    code_ref: str
    steps: List[DetailedCalcStep] = field(default_factory=list)
    conclusion: str = ""
    status: str = "PASS"


@dataclass
class CompositeDesignReport:
    """
    Complete detailed design report for a composite beam.
    """
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

def calc_steel_section_properties_detailed(
    section_name: str,
    d: float, bf: float, tf: float, tw: float,
    A: float, Ix: float, Sx: float, Zx: float,
    Fy: float, E: float
) -> DetailedCalcSection:
    """
    Calculate and document steel section properties.
    
    Parameters (all in mm and MPa):
        d: Total depth
        bf: Flange width
        tf: Flange thickness
        tw: Web thickness
        A: Cross-sectional area
        Ix: Moment of inertia (mm^4)
        Sx: Section modulus (mm^3)
        Zx: Plastic section modulus (mm^3)
        Fy: Yield stress (MPa)
        E: Modulus of elasticity (MPa)
    """
    section = DetailedCalcSection(
        section_number=1,
        title="STEEL SECTION PROPERTIES",
        description="Document the properties of the steel section per AISC 360-16.",
        code_ref="AISC 360-16 Table 1-1"
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
        description="Record the key geometric properties of the selected section.",
        equation="d, bf, tf, tw from section tables",
        substitution=f"d = {d:.1f} mm, bf = {bf:.1f} mm, tf = {tf:.1f} mm, tw = {tw:.1f} mm",
        result=d,
        unit="mm",
        code_ref="AISC Manual Table 1-1"
    ))
    step_num += 1
    
    # Step 3: Cross-sectional area
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Cross-Sectional Area",
        description="Total cross-sectional area of the steel section.",
        equation="A = As (from section tables)",
        substitution=f"As = {A:.0f} mm²",
        result=A,
        unit="mm²",
        code_ref="AISC Manual Table 1-1"
    ))
    step_num += 1
    
    # Step 4: Moment of inertia
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Moment of Inertia (Strong Axis)",
        description="Second moment of area about the strong (x-x) axis.",
        equation="Ix from section tables",
        substitution=f"Ix = {Ix/1e6:.2f}×10⁶ mm⁴",
        result=Ix,
        unit="mm⁴",
        code_ref="AISC Manual Table 1-1"
    ))
    step_num += 1
    
    # Step 5: Elastic section modulus
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Elastic Section Modulus",
        description="Section modulus for elastic bending stress calculations.",
        equation="Sx = Ix / (d/2)",
        substitution=f"Sx = {Sx/1e3:.2f}×10³ mm³",
        result=Sx,
        unit="mm³",
        code_ref="AISC Manual Table 1-1"
    ))
    step_num += 1
    
    # Step 6: Plastic section modulus
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Plastic Section Modulus",
        description="Plastic section modulus for full plastification of the cross-section.",
        equation="Zx from section tables",
        substitution=f"Zx = {Zx/1e3:.2f}×10³ mm³",
        result=Zx,
        unit="mm³",
        code_ref="AISC Manual Table 1-1"
    ))
    step_num += 1
    
    # Step 7: Material properties
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
    
    # Step 8: Flange classification
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
        title="Flange Compactness (Flexure)",
        description="Check flange width-to-thickness ratio for local buckling per Table B4.1b Case 10.",
        equation="λf = bf/(2×tf) ≤ λpf = 0.38√(E/Fy)",
        substitution=f"λf = {bf:.1f}/(2×{tf:.1f}) = {lambda_f:.2f} vs λpf = 0.38×√({E}/{Fy}) = {lambda_pf:.2f}",
        result=lambda_f,
        unit="",
        code_ref="AISC 360-16 Table B4.1b",
        status=flange_status,
        notes=f"Flange is {flange_class}"
    ))
    step_num += 1
    
    # Step 9: Web classification
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
        title="Web Compactness (Flexure)",
        description="Check web height-to-thickness ratio for local buckling per Table B4.1b Case 15.",
        equation="λw = h/tw ≤ λpw = 3.76√(E/Fy)",
        substitution=f"λw = {h:.1f}/{tw:.1f} = {lambda_w:.2f} vs λpw = 3.76×√({E}/{Fy}) = {lambda_pw:.2f}",
        result=lambda_w,
        unit="",
        code_ref="AISC 360-16 Table B4.1b",
        status=web_status,
        notes=f"Web is {web_class}"
    ))
    step_num += 1
    
    # Step 10: Overall classification
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
        description="The section is classified based on the most restrictive element (flange or web).",
        equation="Classification = most restrictive of (flange, web)",
        substitution=f"Flange: {flange_class}, Web: {web_class}",
        result=1.0 if overall_class == "Compact" else 0.5,
        unit="",
        code_ref="AISC 360-16 §B4",
        status=overall_status,
        notes=f"Section is {overall_class}"
    ))
    
    section.steps = steps
    section.conclusion = f"Steel section {section_name} is {overall_class}. All properties documented for composite design."
    section.status = overall_status
    
    return section


# =============================================================================
# SECTION 2: EFFECTIVE CONCRETE SLAB WIDTH
# =============================================================================

def calc_effective_width_detailed(
    L: float,
    spacing: float,
    edge_distance: float,
    beam_position: str,
    overhang: float = 0
) -> Tuple[DetailedCalcSection, float]:
    """
    Calculate effective concrete slab width per AISC 360-16 §I3.1a.
    
    Parameters:
        L: Beam span (mm)
        spacing: Beam spacing (mm)
        edge_distance: Distance to slab edge for edge beams (mm)
        beam_position: "Interior" or "Edge"
        overhang: Slab overhang beyond edge beam (mm)
    
    Returns:
        Tuple of (DetailedCalcSection, effective_width in mm)
    """
    section = DetailedCalcSection(
        section_number=2,
        title="EFFECTIVE CONCRETE SLAB WIDTH",
        description="Determine the effective width of concrete slab acting compositely with the steel beam.",
        code_ref="AISC 360-16 §I3.1a"
    )
    steps = []
    step_num = 1
    
    # Step 1: Code requirement overview
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Code Requirement",
        description="The effective width of the concrete slab on each side of the beam centerline shall not exceed the least of the following limits per AISC 360-16 §I3.1a.",
        equation="beff = Σ(min of limiting values on each side)",
        substitution="See calculation below for each side",
        result=0,
        unit="mm",
        code_ref="AISC 360-16 §I3.1a"
    ))
    step_num += 1
    
    # Step 2: Limit 1 - One-eighth of beam span
    b_limit_1 = L / 8
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Limit 1: Span/8 (Each Side)",
        description="One-eighth of the beam span, measured from center of beam.",
        equation="b₁ = L/8",
        substitution=f"b₁ = {L:.0f}/8 = {b_limit_1:.1f} mm",
        result=b_limit_1,
        unit="mm",
        code_ref="AISC 360-16 §I3.1a(a)"
    ))
    step_num += 1
    
    # Step 3: Limit 2 - Half distance to adjacent beam
    b_limit_2 = spacing / 2
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Limit 2: Half Spacing to Adjacent Beam",
        description="One-half the distance to the centerline of the adjacent beam.",
        equation="b₂ = s/2",
        substitution=f"b₂ = {spacing:.0f}/2 = {b_limit_2:.1f} mm",
        result=b_limit_2,
        unit="mm",
        code_ref="AISC 360-16 §I3.1a(b)"
    ))
    step_num += 1
    
    if beam_position == "Interior":
        # Interior beam - symmetric effective width
        b_each_side = min(b_limit_1, b_limit_2)
        beff = 2 * b_each_side
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Interior Beam: Each Side",
            description="For interior beams, the effective width on each side is the minimum of the two limits.",
            equation="b_side = min(b₁, b₂)",
            substitution=f"b_side = min({b_limit_1:.1f}, {b_limit_2:.1f}) = {b_each_side:.1f} mm",
            result=b_each_side,
            unit="mm",
            code_ref="AISC 360-16 §I3.1a"
        ))
        step_num += 1
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Total Effective Width",
            description="Total effective width is twice the effective width per side.",
            equation="beff = 2 × b_side",
            substitution=f"beff = 2 × {b_each_side:.1f} = {beff:.1f} mm",
            result=beff,
            unit="mm",
            code_ref="AISC 360-16 §I3.1a"
        ))
        
    else:  # Edge beam
        # Limit 3 - Distance to slab edge (for edge beams only)
        b_limit_3 = edge_distance if edge_distance > 0 else overhang
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Limit 3: Distance to Slab Edge",
            description="The distance to the edge of the slab (for edge beams only).",
            equation="b₃ = distance to slab edge",
            substitution=f"b₃ = {b_limit_3:.1f} mm",
            result=b_limit_3,
            unit="mm",
            code_ref="AISC 360-16 §I3.1a(c)"
        ))
        step_num += 1
        
        # Interior side
        b_interior = min(b_limit_1, b_limit_2)
        # Edge side
        b_edge = min(b_limit_1, b_limit_3)
        beff = b_interior + b_edge
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Edge Beam: Interior Side",
            description="Effective width on the interior side (towards adjacent beam).",
            equation="b_int = min(b₁, b₂)",
            substitution=f"b_int = min({b_limit_1:.1f}, {b_limit_2:.1f}) = {b_interior:.1f} mm",
            result=b_interior,
            unit="mm",
            code_ref="AISC 360-16 §I3.1a"
        ))
        step_num += 1
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Edge Beam: Edge Side",
            description="Effective width on the edge side (towards slab edge).",
            equation="b_edge = min(b₁, b₃)",
            substitution=f"b_edge = min({b_limit_1:.1f}, {b_limit_3:.1f}) = {b_edge:.1f} mm",
            result=b_edge,
            unit="mm",
            code_ref="AISC 360-16 §I3.1a"
        ))
        step_num += 1
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Total Effective Width",
            description="Total effective width is the sum of interior and edge sides.",
            equation="beff = b_int + b_edge",
            substitution=f"beff = {b_interior:.1f} + {b_edge:.1f} = {beff:.1f} mm",
            result=beff,
            unit="mm",
            code_ref="AISC 360-16 §I3.1a"
        ))
    
    section.steps = steps
    section.conclusion = f"Effective concrete slab width beff = {beff:.0f} mm"
    section.status = "PASS"
    
    return section, beff


# =============================================================================
# SECTION 3: CONCRETE PROPERTIES
# =============================================================================

def calc_concrete_properties_detailed(
    fc: float,
    tc: float,
    hr: float,
    wr: float,
    unit_wt: float = 23.5
) -> Tuple[DetailedCalcSection, Dict]:
    """
    Calculate concrete slab properties for composite design.
    
    Parameters:
        fc: Concrete compressive strength (MPa)
        tc: Total slab thickness (mm)
        hr: Deck rib height (mm)
        wr: Average deck rib width (mm)
        unit_wt: Concrete unit weight (kN/m³), default 23.5 for normal weight
    
    Returns:
        Tuple of (DetailedCalcSection, dict of properties)
    """
    section = DetailedCalcSection(
        section_number=3,
        title="CONCRETE SLAB PROPERTIES",
        description="Determine the properties of the concrete slab for composite action calculations.",
        code_ref="AISC 360-16 §I1.2, ACI 318-19"
    )
    steps = []
    step_num = 1
    
    # Step 1: Concrete strength
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Specified Concrete Strength",
        description="The specified compressive strength of concrete at 28 days.",
        equation="f'c = specified strength",
        substitution=f"f'c = {fc:.1f} MPa",
        result=fc,
        unit="MPa",
        code_ref="ACI 318-19 §19.2.1"
    ))
    step_num += 1
    
    # Step 2: Modulus of elasticity
    # ACI 318-19 Eq. 19.2.2.1b for normal weight concrete
    Ec = 4700 * math.sqrt(fc)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Modulus of Elasticity",
        description="Concrete modulus of elasticity per ACI 318-19 for normal weight concrete (wc = 2300 kg/m³).",
        equation="Ec = 4700√f'c (MPa)",
        substitution=f"Ec = 4700 × √{fc:.1f} = 4700 × {math.sqrt(fc):.3f} = {Ec:.0f} MPa",
        result=Ec,
        unit="MPa",
        code_ref="ACI 318-19 Eq. 19.2.2.1b"
    ))
    step_num += 1
    
    # Step 3: Slab geometry
    t_above = tc - hr
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Slab Geometry",
        description="Total slab thickness and thickness above metal deck ribs.",
        equation="t_above = tc - hr",
        substitution=f"t_above = {tc:.0f} - {hr:.0f} = {t_above:.0f} mm",
        result=t_above,
        unit="mm",
        code_ref="AISC 360-16 §I3.2c"
    ))
    step_num += 1
    
    # Step 4: Modular ratio
    Es = 200000  # Steel modulus
    n = Es / Ec
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Modular Ratio",
        description="The ratio of steel to concrete elastic moduli, used to transform concrete area to equivalent steel area.",
        equation="n = Es / Ec",
        substitution=f"n = {Es:.0f} / {Ec:.0f} = {n:.2f}",
        result=n,
        unit="",
        code_ref="AISC 360-16 §I3.2"
    ))
    step_num += 1
    
    # Step 5: Equivalent concrete stress block depth factor
    if fc <= 28:
        beta1 = 0.85
    elif fc >= 55:
        beta1 = 0.65
    else:
        beta1 = 0.85 - 0.05 * (fc - 28) / 7
        beta1 = max(0.65, beta1)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Stress Block Factor β₁",
        description="Factor relating depth of equivalent rectangular concrete stress block to neutral axis depth.",
        equation="β₁ = 0.85 for f'c ≤ 28 MPa; 0.85 - 0.05(f'c-28)/7 for 28 < f'c < 55 MPa; 0.65 for f'c ≥ 55 MPa",
        substitution=f"For f'c = {fc:.1f} MPa: β₁ = {beta1:.3f}",
        result=beta1,
        unit="",
        code_ref="ACI 318-19 §22.2.2.4.3"
    ))
    step_num += 1
    
    # Step 6: Concrete crushing strain
    ecu = 0.003
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Ultimate Concrete Strain",
        description="Maximum usable compressive strain in concrete at crushing.",
        equation="εcu = 0.003",
        substitution=f"εcu = {ecu}",
        result=ecu,
        unit="mm/mm",
        code_ref="ACI 318-19 §22.2.2.1"
    ))
    
    section.steps = steps
    section.conclusion = f"Concrete f'c = {fc:.0f} MPa, Ec = {Ec:.0f} MPa, n = {n:.2f}, β₁ = {beta1:.3f}"
    section.status = "PASS"
    
    props = {
        'fc': fc,
        'Ec': Ec,
        'n': n,
        'beta1': beta1,
        'tc': tc,
        'hr': hr,
        't_above': t_above,
        'wr': wr,
        'ecu': ecu
    }
    
    return section, props


# =============================================================================
# SECTION 4: PLASTIC NEUTRAL AXIS AND COMPOSITE STRENGTH
# =============================================================================

def calc_composite_flexure_detailed(
    d: float, bf: float, tf: float, tw: float,
    A: float, Zx: float,
    beff: float,
    tc: float, hr: float,
    fc: float, Fy: float, E: float,
    Qn_total: float,
    method: str = "LRFD"
) -> Tuple[DetailedCalcSection, Dict]:
    """
    Calculate composite flexural strength with detailed PNA location.
    
    This is the KEY calculation showing the plastic neutral axis location
    that the user specifically requested.
    
    Parameters:
        d, bf, tf, tw: Steel section dimensions (mm)
        A: Steel area (mm²)
        Zx: Plastic section modulus (mm³)
        beff: Effective slab width (mm)
        tc, hr: Slab thickness and rib height (mm)
        fc: Concrete strength (MPa)
        Fy: Steel yield stress (MPa)
        E: Steel modulus (MPa)
        Qn_total: Total shear connector strength (N)
        method: "LRFD" or "ASD"
    
    Returns:
        Tuple of (DetailedCalcSection, dict of results)
    """
    section = DetailedCalcSection(
        section_number=4,
        title="COMPOSITE FLEXURAL STRENGTH",
        description="Determine the plastic neutral axis location and nominal flexural strength of the composite section per AISC 360-16 Chapter I.",
        code_ref="AISC 360-16 §I3.2"
    )
    steps = []
    step_num = 1
    
    # Resistance/safety factors
    phi_b = 0.90 if method == "LRFD" else 1.0
    omega_b = 1.67 if method == "ASD" else 1.0
    
    # Derived values
    t_above = tc - hr  # Concrete above deck
    Ec = 4700 * math.sqrt(fc)
    
    # Step 1: Steel tensile force capacity
    Ts = A * Fy / 1000  # Convert to kN
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Steel Tensile Capacity",
        description="Maximum tensile force that can be developed in the steel section when fully yielded.",
        equation="Ts = As × Fy",
        substitution=f"Ts = {A:.0f} × {Fy:.0f} / 1000 = {Ts:.1f} kN",
        result=Ts,
        unit="kN",
        code_ref="AISC 360-16 §I3.2a"
    ))
    step_num += 1
    
    # Step 2: Maximum concrete compression capacity
    # Using 0.85f'c over effective area (Whitney stress block)
    Ac_max = beff * t_above  # Maximum concrete area above deck
    Cc_max = 0.85 * fc * Ac_max / 1000  # kN
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Maximum Concrete Compression Capacity",
        description="Maximum compression force in concrete using Whitney stress block (0.85f'c). Only concrete above deck ribs is considered effective.",
        equation="Cc,max = 0.85 × f'c × beff × (tc - hr)",
        substitution=f"Cc,max = 0.85 × {fc:.1f} × {beff:.0f} × {t_above:.0f} / 1000 = {Cc_max:.1f} kN",
        result=Cc_max,
        unit="kN",
        code_ref="AISC 360-16 §I3.2a"
    ))
    step_num += 1
    
    # Step 3: Shear connector capacity
    Qn = Qn_total / 1000  # Convert to kN
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Total Shear Connector Capacity",
        description="Sum of nominal strength of all shear connectors between point of maximum moment and point of zero moment.",
        equation="ΣQn = n × Qn (for n studs)",
        substitution=f"ΣQn = {Qn:.1f} kN (from shear stud design)",
        result=Qn,
        unit="kN",
        code_ref="AISC 360-16 §I3.2d"
    ))
    step_num += 1
    
    # Step 4: Determine compression force and composite type
    C = min(Ts, Cc_max, Qn)
    
    if Qn >= min(Ts, Cc_max):
        comp_type = "Full"
        comp_ratio = 1.0
    else:
        comp_type = "Partial"
        comp_ratio = Qn / min(Ts, Cc_max)
    
    # Determine which governs
    if C == Ts:
        governing = "Steel yielding (Ts)"
    elif C == Cc_max:
        governing = "Concrete crushing (Cc,max)"
    else:
        governing = "Shear connector capacity (ΣQn)"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Compression Force (Governs Design)",
        description=f"The compression force is the minimum of steel tension capacity, concrete compression capacity, and shear connector strength. This determines {comp_type} composite action.",
        equation="C = min(Ts, Cc,max, ΣQn)",
        substitution=f"C = min({Ts:.1f}, {Cc_max:.1f}, {Qn:.1f}) = {C:.1f} kN (governed by {governing})",
        result=C,
        unit="kN",
        code_ref="AISC 360-16 §I3.2a, I3.2d",
        notes=f"{comp_type} Composite: {comp_ratio*100:.0f}%"
    ))
    step_num += 1
    
    # Step 5: Depth of concrete compression block
    a = C * 1000 / (0.85 * fc * beff)  # mm
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Concrete Compression Block Depth",
        description="Depth of the equivalent rectangular stress block in the concrete slab.",
        equation="a = C / (0.85 × f'c × beff)",
        substitution=f"a = {C:.1f} × 1000 / (0.85 × {fc:.1f} × {beff:.0f}) = {a:.2f} mm",
        result=a,
        unit="mm",
        code_ref="AISC 360-16 §I3.2a"
    ))
    step_num += 1
    
    # Step 6: Check if PNA is in concrete or steel
    # If a <= t_above, PNA is in concrete slab
    # If a > t_above, PNA is in steel section
    
    if a <= t_above:
        PNA_location = "in concrete slab"
        y_PNA = tc - a/2  # Distance from top of slab to PNA
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="PNA Location Check",
            description=f"Since the compression block depth a = {a:.2f} mm is less than the concrete thickness above deck (tc - hr) = {t_above:.0f} mm, the plastic neutral axis is located within the concrete slab.",
            equation="a ≤ (tc - hr) → PNA in concrete",
            substitution=f"a = {a:.2f} mm ≤ {t_above:.0f} mm → PNA {PNA_location}",
            result=a,
            unit="mm",
            code_ref="AISC 360-16 §I3.2a",
            notes="Steel section fully in tension, concrete takes all compression"
        ))
        step_num += 1
        
        # Step 7a: Calculate moment arm for PNA in slab
        # Distance from centroid of steel to centroid of concrete block
        d1 = d/2 + hr + t_above - a/2
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Moment Arm (PNA in Slab)",
            description="The moment arm is the distance from the centroid of the steel section to the centroid of the concrete compression block.",
            equation="d₁ = d/2 + hr + (tc - hr) - a/2 = d/2 + tc - a/2",
            substitution=f"d₁ = {d:.1f}/2 + {tc:.0f} - {a:.2f}/2 = {d/2:.1f} + {tc:.0f} - {a/2:.2f} = {d1:.2f} mm",
            result=d1,
            unit="mm",
            code_ref="AISC 360-16 §I3.2a"
        ))
        step_num += 1
        
        # Step 8a: Nominal moment strength
        Mn = C * d1 / 1000  # kN⋅m (C is in kN, d1 in mm)
        
    else:
        # PNA is in steel section - more complex calculation
        PNA_location = "in steel section"
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="PNA Location Check",
            description=f"Since the compression block depth a = {a:.2f} mm exceeds the concrete thickness above deck (tc - hr) = {t_above:.0f} mm, the plastic neutral axis is located within the steel section.",
            equation="a > (tc - hr) → PNA in steel",
            substitution=f"a = {a:.2f} mm > {t_above:.0f} mm → PNA {PNA_location}",
            result=a,
            unit="mm",
            code_ref="AISC 360-16 §I3.2a",
            notes="Steel section partially in compression"
        ))
        step_num += 1
        
        # Recalculate with full concrete depth
        Cc = 0.85 * fc * beff * t_above / 1000  # kN - actual concrete force
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Actual Concrete Compression Force",
            description="When PNA is in steel, the full concrete above deck is in compression.",
            equation="Cc = 0.85 × f'c × beff × (tc - hr)",
            substitution=f"Cc = 0.85 × {fc:.1f} × {beff:.0f} × {t_above:.0f} / 1000 = {Cc:.1f} kN",
            result=Cc,
            unit="kN",
            code_ref="AISC 360-16 §I3.2a"
        ))
        step_num += 1
        
        # Force that must be carried by steel in compression
        Cs = C - Cc  # kN - steel compression force
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Steel Compression Force",
            description="The portion of the compression force carried by the steel section.",
            equation="Cs = C - Cc",
            substitution=f"Cs = {C:.1f} - {Cc:.1f} = {Cs:.1f} kN",
            result=Cs,
            unit="kN",
            code_ref="AISC 360-16 §I3.2a"
        ))
        step_num += 1
        
        # Find PNA location in steel
        # Area of steel in compression = Cs / Fy
        As_comp = Cs * 1000 / Fy  # mm²
        
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Steel Area in Compression",
            description="The area of steel above the plastic neutral axis that is in compression.",
            equation="As,comp = Cs / Fy",
            substitution=f"As,comp = {Cs:.1f} × 1000 / {Fy:.0f} = {As_comp:.0f} mm²",
            result=As_comp,
            unit="mm²",
            code_ref="AISC 360-16 §I3.2a"
        ))
        step_num += 1
        
        # Determine if PNA is in flange or web
        Af = bf * tf  # Top flange area
        
        if As_comp <= Af:
            # PNA in top flange
            y_steel = As_comp / bf  # Distance from top of steel to PNA
            PNA_location = "in top flange of steel section"
            
            steps.append(DetailedCalcStep(
                step_number=step_num,
                title="PNA Location in Steel",
                description=f"Since As,comp = {As_comp:.0f} mm² < Af = {Af:.0f} mm², the PNA is in the top flange.",
                equation="y_steel = As,comp / bf (for PNA in flange)",
                substitution=f"y_steel = {As_comp:.0f} / {bf:.0f} = {y_steel:.2f} mm from top of steel",
                result=y_steel,
                unit="mm",
                code_ref="AISC 360-16 §I3.2a",
                notes=f"PNA is {PNA_location}"
            ))
            step_num += 1
            
            # Calculate moment components
            # Concrete force arm
            d_cc = t_above/2 + hr + y_steel/2
            # Steel compression arm (from PNA)
            d_sc = y_steel/2
            # Steel tension arm (centroid of tension region from PNA)
            # This requires more detailed calculation
            
        else:
            # PNA in web
            y_flange = tf  # Full flange in compression
            As_web_comp = As_comp - Af
            y_web = As_web_comp / tw
            y_steel = tf + y_web
            PNA_location = "in web of steel section"
            
            steps.append(DetailedCalcStep(
                step_number=step_num,
                title="PNA Location in Steel",
                description=f"Since As,comp = {As_comp:.0f} mm² > Af = {Af:.0f} mm², the PNA is in the web.",
                equation="y_steel = tf + (As,comp - Af)/tw",
                substitution=f"y_steel = {tf:.1f} + ({As_comp:.0f} - {Af:.0f})/{tw:.1f} = {y_steel:.2f} mm from top of steel",
                result=y_steel,
                unit="mm",
                code_ref="AISC 360-16 §I3.2a",
                notes=f"PNA is {PNA_location}"
            ))
            step_num += 1
        
        # For simplicity, use the approximate method for Mn
        # d1 = d/2 + tc - t_above/2 (center of concrete to center of steel)
        d1 = d/2 + hr + t_above/2
        d2 = y_steel  # compression region in steel
        
        # Moment from concrete
        Mc = Cc * (d1) / 1000
        # Moment contribution from steel (simplified - use plastic moment reduction)
        # More accurate would be to integrate over the section
        
        # Use the general formula: Mn = C × d1 for PNA in steel (approximate)
        Mn = Ts * (d/2 + hr + t_above/2) / 1000
        
        # Apply reduction for PNA in steel
        # Simplified approach using AISC method
        if comp_ratio < 1.0:
            # Interpolation formula per AISC §I3.2a
            Mp = Fy * Zx / 1e6  # Steel plastic moment (kN⋅m)
            Mn = Mp + (Mn - Mp) * comp_ratio
    
    # Final Mn for PNA in concrete case
    if a <= t_above:
        steps.append(DetailedCalcStep(
            step_number=step_num,
            title="Nominal Flexural Strength",
            description="The nominal flexural strength is the product of the compression force and the moment arm.",
            equation="Mn = C × d₁",
            substitution=f"Mn = {C:.1f} × {d1:.2f} / 1000 = {Mn:.2f} kN⋅m",
            result=Mn,
            unit="kN⋅m",
            code_ref="AISC 360-16 §I3.2a(a)"
        ))
        step_num += 1
    
    # Step: Design strength
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
            code_ref="AISC 360-16 §I3.2"
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
            code_ref="AISC 360-16 §I3.2"
        ))
        design_strength = Mn_omega
    
    section.steps = steps
    section.conclusion = f"PNA is {PNA_location}. Nominal strength Mn = {Mn:.2f} kN⋅m, Design strength = {design_strength:.2f} kN⋅m"
    section.status = "PASS"
    
    results = {
        'Ts': Ts,
        'Cc_max': Cc_max,
        'Qn': Qn,
        'C': C,
        'a': a,
        'PNA_location': PNA_location,
        'Mn': Mn,
        'phi_Mn': phi_Mn if method == "LRFD" else Mn_omega,
        'comp_type': comp_type,
        'comp_ratio': comp_ratio
    }
    
    return section, results


# =============================================================================
# SECTION 5: SHEAR STRENGTH
# =============================================================================

def calc_composite_shear_detailed(
    d: float, tw: float,
    Fy: float, E: float,
    method: str = "LRFD"
) -> Tuple[DetailedCalcSection, Dict]:
    """
    Calculate shear strength of composite beam per AISC 360-16 Chapter G.
    
    Note: Concrete slab does not contribute to shear strength.
    
    Parameters:
        d: Steel beam depth (mm)
        tw: Web thickness (mm)
        Fy: Yield stress (MPa)
        E: Elastic modulus (MPa)
        method: "LRFD" or "ASD"
    """
    section = DetailedCalcSection(
        section_number=5,
        title="SHEAR STRENGTH",
        description="Determine the shear strength of the composite beam. Per AISC 360-16 §I4.2, the concrete slab does not contribute to shear resistance.",
        code_ref="AISC 360-16 §G2.1"
    )
    steps = []
    step_num = 1
    
    # Resistance factors
    phi_v = 0.90 if method == "LRFD" else 1.0
    omega_v = 1.67 if method == "ASD" else 1.0
    
    # Step 1: Web area
    Aw = d * tw
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Area",
        description="The shear area is taken as the overall depth times the web thickness.",
        equation="Aw = d × tw",
        substitution=f"Aw = {d:.1f} × {tw:.1f} = {Aw:.0f} mm²",
        result=Aw,
        unit="mm²",
        code_ref="AISC 360-16 §G2.1"
    ))
    step_num += 1
    
    # Step 2: Web slenderness
    h = d - 2 * 0  # Assuming rolled section, h ≈ d for simplicity
    # For rolled I-shapes, use clear distance between flanges
    # This is approximated as d - 2*tf, but we'll use d for conservative estimate
    lambda_w = h / tw
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Slenderness Ratio",
        description="The web height-to-thickness ratio for shear buckling check.",
        equation="h/tw = d/tw (conservative)",
        substitution=f"h/tw = {d:.1f}/{tw:.1f} = {lambda_w:.1f}",
        result=lambda_w,
        unit="",
        code_ref="AISC 360-16 §G2.1"
    ))
    step_num += 1
    
    # Step 3: Web shear coefficient
    kv = 5.34  # No transverse stiffeners
    limit_1 = 1.10 * math.sqrt(kv * E / Fy)
    limit_2 = 1.37 * math.sqrt(kv * E / Fy)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Shear Buckling Limits",
        description="Calculate the limits for determining the web shear coefficient Cv1.",
        equation="Limit₁ = 1.10√(kv×E/Fy), Limit₂ = 1.37√(kv×E/Fy)",
        substitution=f"Limit₁ = 1.10×√({kv}×{E}/{Fy}) = {limit_1:.1f}, Limit₂ = 1.37×√({kv}×{E}/{Fy}) = {limit_2:.1f}",
        result=limit_1,
        unit="",
        code_ref="AISC 360-16 §G2.1"
    ))
    step_num += 1
    
    # Step 4: Web shear coefficient Cv1
    if lambda_w <= limit_1:
        Cv1 = 1.0
        shear_yielding = True
    elif lambda_w <= limit_2:
        Cv1 = limit_1 / lambda_w
        shear_yielding = False
    else:
        Cv1 = 1.51 * kv * E / (Fy * lambda_w**2)
        shear_yielding = False
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Web Shear Coefficient Cv1",
        description="The web shear coefficient accounts for the shear buckling strength of the web.",
        equation="Cv1 = 1.0 if h/tw ≤ 1.10√(kv×E/Fy); = 1.10√(kv×E/Fy)/(h/tw) if intermediate; = 1.51kv×E/(Fy×(h/tw)²) otherwise",
        substitution=f"h/tw = {lambda_w:.1f} vs limits [{limit_1:.1f}, {limit_2:.1f}] → Cv1 = {Cv1:.3f}",
        result=Cv1,
        unit="",
        code_ref="AISC 360-16 §G2.1(a)",
        notes="Web yields in shear" if shear_yielding else "Web shear buckling controls"
    ))
    step_num += 1
    
    # Step 5: Nominal shear strength
    Vn = 0.6 * Fy * Aw * Cv1 / 1000  # kN
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Nominal Shear Strength",
        description="The nominal shear strength based on web yielding or buckling.",
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
            description="The design shear strength is the nominal strength multiplied by the resistance factor.",
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
            description="The allowable shear strength is the nominal strength divided by the safety factor.",
            equation="Vn/Ωv = Vn / Ωv",
            substitution=f"Vn/Ωv = {Vn:.1f} / {omega_v} = {Vn_omega:.1f} kN",
            result=Vn_omega,
            unit="kN",
            code_ref="AISC 360-16 §G1"
        ))
        design_strength = Vn_omega
    
    section.steps = steps
    section.conclusion = f"Nominal shear strength Vn = {Vn:.1f} kN, Design strength = {design_strength:.1f} kN"
    section.status = "PASS"
    
    results = {
        'Aw': Aw,
        'Cv1': Cv1,
        'Vn': Vn,
        'phi_Vn': design_strength
    }
    
    return section, results


# =============================================================================
# SECTION 6: EFFECTIVE MOMENT OF INERTIA (LOWER BOUND)
# =============================================================================

def calc_effective_Itr_detailed(
    d: float, A: float, Ix: float,
    beff: float, tc: float, hr: float,
    fc: float, E: float,
    Qn_total: float,
    Ts: float, Cc_max: float
) -> Tuple[DetailedCalcSection, Dict]:
    """
    Calculate the lower-bound moment of inertia per AISC 360-16 §I3.2.
    
    This is used for deflection calculations and accounts for
    partial composite action.
    
    Parameters:
        d, A, Ix: Steel section properties
        beff, tc, hr: Slab geometry
        fc, E: Material properties
        Qn_total: Total stud capacity (N)
        Ts: Steel tensile capacity (kN)
        Cc_max: Max concrete compression (kN)
    """
    section = DetailedCalcSection(
        section_number=6,
        title="LOWER-BOUND MOMENT OF INERTIA",
        description="Calculate the effective moment of inertia for deflection calculations per AISC 360-16 Commentary §I3.2.",
        code_ref="AISC 360-16 §I3.2"
    )
    steps = []
    step_num = 1
    
    # Concrete modulus
    Ec = 4700 * math.sqrt(fc)
    n = E / Ec
    t_above = tc - hr
    
    # Step 1: Modular ratio
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Modular Ratio",
        description="Ratio of steel to concrete elastic moduli.",
        equation="n = Es / Ec",
        substitution=f"n = {E:.0f} / {Ec:.0f} = {n:.2f}",
        result=n,
        unit="",
        code_ref="AISC 360-16 §I2"
    ))
    step_num += 1
    
    # Step 2: Transformed concrete area
    Ac = beff * t_above  # Concrete area above deck
    Atr = Ac / n  # Transformed area
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Transformed Concrete Area",
        description="Concrete area transformed to equivalent steel area.",
        equation="Atr = Ac / n = (beff × t_above) / n",
        substitution=f"Atr = ({beff:.0f} × {t_above:.0f}) / {n:.2f} = {Atr:.0f} mm²",
        result=Atr,
        unit="mm²",
        code_ref="Elastic theory"
    ))
    step_num += 1
    
    # Step 3: Full composite elastic neutral axis from top of steel
    # Taking moments about top of steel
    # y_bar × (A + Atr) = A × (d/2) + Atr × (-hr - t_above/2)
    # Note: negative means above top of steel
    
    y_steel = d / 2  # Distance from top of steel to centroid of steel
    y_conc = -(hr + t_above/2)  # Distance from top of steel to centroid of concrete (negative = above)
    
    y_bar_from_top_steel = (A * y_steel + Atr * y_conc) / (A + Atr)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Full Composite NA Location",
        description="Location of elastic neutral axis for full composite section, measured from top of steel flange.",
        equation="ȳ = (As×ys + Atr×yc) / (As + Atr)",
        substitution=f"ȳ = ({A:.0f}×{y_steel:.1f} + {Atr:.0f}×{y_conc:.1f}) / ({A:.0f} + {Atr:.0f}) = {y_bar_from_top_steel:.2f} mm",
        result=y_bar_from_top_steel,
        unit="mm from top of steel",
        code_ref="Elastic theory",
        notes="Negative = NA above top of steel"
    ))
    step_num += 1
    
    # Step 4: Full composite moment of inertia using parallel axis theorem
    # Itr = Ix + A×(d/2 - y_bar)² + (beff×t_above³/12)/n + Atr×(y_conc - y_bar)²
    
    Ic = beff * t_above**3 / 12 / n  # Moment of inertia of transformed concrete about its own centroid
    
    d_steel = y_steel - y_bar_from_top_steel  # Distance from steel centroid to composite NA
    d_conc = y_conc - y_bar_from_top_steel   # Distance from concrete centroid to composite NA
    
    Itr = Ix + A * d_steel**2 + Ic + Atr * d_conc**2
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Full Composite Moment of Inertia",
        description="Transformed moment of inertia for full composite section using parallel axis theorem.",
        equation="Itr = Ix + As×ds² + Ic + Atr×dc²",
        substitution=f"Itr = {Ix/1e6:.2f}×10⁶ + {A:.0f}×{d_steel:.1f}² + {Ic/1e6:.4f}×10⁶ + {Atr:.0f}×{d_conc:.1f}² = {Itr/1e6:.2f}×10⁶ mm⁴",
        result=Itr,
        unit="mm⁴",
        code_ref="Elastic theory"
    ))
    step_num += 1
    
    # Step 5: Composite ratio
    Qn = Qn_total / 1000  # kN
    C_full = min(Ts, Cc_max)
    comp_ratio = min(Qn / C_full, 1.0) if C_full > 0 else 1.0
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Composite Ratio",
        description="Ratio of actual shear connector capacity to that required for full composite action.",
        equation="η = ΣQn / min(Ts, Cc)",
        substitution=f"η = {Qn:.1f} / min({Ts:.1f}, {Cc_max:.1f}) = {Qn:.1f} / {C_full:.1f} = {comp_ratio:.3f}",
        result=comp_ratio,
        unit="",
        code_ref="AISC 360-16 §I3.2d"
    ))
    step_num += 1
    
    # Step 6: Lower-bound moment of inertia per AISC Commentary
    # Ieff = Ix + √(η) × (Itr - Ix)
    
    Ieff = Ix + math.sqrt(comp_ratio) * (Itr - Ix)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Lower-Bound Effective Moment of Inertia",
        description="The effective moment of inertia accounting for partial composite action. This lower-bound value is used for serviceability (deflection) calculations.",
        equation="Ieff = Ix + √η × (Itr - Ix)",
        substitution=f"Ieff = {Ix/1e6:.2f}×10⁶ + √{comp_ratio:.3f} × ({Itr/1e6:.2f}×10⁶ - {Ix/1e6:.2f}×10⁶) = {Ieff/1e6:.2f}×10⁶ mm⁴",
        result=Ieff,
        unit="mm⁴",
        code_ref="AISC 360-16 Commentary §I3.2",
        notes=f"Effective I is {Ieff/Ix:.2f}× steel Ix"
    ))
    
    section.steps = steps
    section.conclusion = f"Lower-bound Ieff = {Ieff/1e6:.2f}×10⁶ mm⁴ for {comp_ratio*100:.0f}% composite action"
    section.status = "PASS"
    
    results = {
        'n': n,
        'Atr': Atr,
        'y_bar': y_bar_from_top_steel,
        'Itr': Itr,
        'Ieff': Ieff,
        'comp_ratio': comp_ratio
    }
    
    return section, results


# =============================================================================
# SECTION 7: DEFLECTION CALCULATIONS
# =============================================================================

def calc_deflection_detailed(
    L: float,
    Ix: float, Ieff: float,
    E: float,
    w_DL: float, w_SDL: float, w_LL: float,
    defl_limit_LL: float = 360,
    defl_limit_total: float = 240
) -> Tuple[DetailedCalcSection, Dict]:
    """
    Calculate deflections for composite beam.
    
    Parameters:
        L: Span (mm)
        Ix: Steel moment of inertia (mm⁴)
        Ieff: Effective composite moment of inertia (mm⁴)
        E: Elastic modulus (MPa)
        w_DL: Dead load (kN/m) - before composite
        w_SDL: Superimposed dead load (kN/m) - after composite
        w_LL: Live load (kN/m) - after composite
        defl_limit_LL: Span/limit for live load (default L/360)
        defl_limit_total: Span/limit for total (default L/240)
    """
    section = DetailedCalcSection(
        section_number=7,
        title="DEFLECTION SERVICEABILITY CHECK",
        description="Calculate beam deflections and compare to serviceability limits per IBC/AISC requirements.",
        code_ref="IBC Table 1604.3"
    )
    steps = []
    step_num = 1
    
    # Convert w from kN/m to N/mm for deflection formula
    # δ = 5wL⁴/(384EI) where w is in N/mm, L in mm, E in MPa, I in mm⁴
    
    # Step 1: Pre-composite deflection (DL only, using steel Ix)
    w_DL_Nmm = w_DL  # kN/m = N/mm
    delta_DL = 5 * w_DL_Nmm * L**4 / (384 * E * Ix)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Pre-Composite Dead Load Deflection",
        description="Deflection under dead load (wet concrete + beam) before composite action is achieved. Uses steel section Ix only.",
        equation="δDL = 5 × wDL × L⁴ / (384 × E × Ix)",
        substitution=f"δDL = 5 × {w_DL_Nmm:.3f} × {L:.0f}⁴ / (384 × {E:.0f} × {Ix/1e6:.2f}×10⁶) = {delta_DL:.2f} mm",
        result=delta_DL,
        unit="mm",
        code_ref="AISC DG3",
        notes="Pre-composite stage - steel beam alone"
    ))
    step_num += 1
    
    # Step 2: Post-composite SDL deflection
    w_SDL_Nmm = w_SDL
    delta_SDL = 5 * w_SDL_Nmm * L**4 / (384 * E * Ieff)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Post-Composite Superimposed Dead Load Deflection",
        description="Deflection under superimposed dead loads (finishes, partitions, MEP) after composite action. Uses effective Ieff.",
        equation="δSDL = 5 × wSDL × L⁴ / (384 × E × Ieff)",
        substitution=f"δSDL = 5 × {w_SDL_Nmm:.3f} × {L:.0f}⁴ / (384 × {E:.0f} × {Ieff/1e6:.2f}×10⁶) = {delta_SDL:.2f} mm",
        result=delta_SDL,
        unit="mm",
        code_ref="AISC DG3",
        notes="Post-composite stage - uses lower-bound Ieff"
    ))
    step_num += 1
    
    # Step 3: Live load deflection
    w_LL_Nmm = w_LL
    delta_LL = 5 * w_LL_Nmm * L**4 / (384 * E * Ieff)
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Live Load Deflection",
        description="Deflection under service live load using effective moment of inertia.",
        equation="δLL = 5 × wLL × L⁴ / (384 × E × Ieff)",
        substitution=f"δLL = 5 × {w_LL_Nmm:.3f} × {L:.0f}⁴ / (384 × {E:.0f} × {Ieff/1e6:.2f}×10⁶) = {delta_LL:.2f} mm",
        result=delta_LL,
        unit="mm",
        code_ref="AISC DG3"
    ))
    step_num += 1
    
    # Step 4: Total deflection
    delta_total = delta_DL + delta_SDL + delta_LL
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Total Deflection",
        description="Sum of all deflection components.",
        equation="δtotal = δDL + δSDL + δLL",
        substitution=f"δtotal = {delta_DL:.2f} + {delta_SDL:.2f} + {delta_LL:.2f} = {delta_total:.2f} mm",
        result=delta_total,
        unit="mm",
        code_ref=""
    ))
    step_num += 1
    
    # Step 5: Live load deflection limit
    delta_limit_LL_val = L / defl_limit_LL
    DCR_LL = delta_LL / delta_limit_LL_val
    status_LL = "PASS" if DCR_LL <= 1.0 else "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Live Load Deflection Check",
        description=f"Check live load deflection against L/{defl_limit_LL} limit.",
        equation=f"δLL ≤ L/{defl_limit_LL}",
        substitution=f"δLL = {delta_LL:.2f} mm vs L/{defl_limit_LL} = {L:.0f}/{defl_limit_LL} = {delta_limit_LL_val:.2f} mm",
        result=DCR_LL,
        unit="D/C",
        code_ref="IBC Table 1604.3",
        status=status_LL,
        notes=f"D/C = {DCR_LL:.3f} {'≤ 1.0 OK' if DCR_LL <= 1.0 else '> 1.0 NG'}"
    ))
    step_num += 1
    
    # Step 6: Total deflection limit
    delta_limit_total_val = L / defl_limit_total
    DCR_total = delta_total / delta_limit_total_val
    status_total = "PASS" if DCR_total <= 1.0 else "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Total Deflection Check",
        description=f"Check total deflection against L/{defl_limit_total} limit.",
        equation=f"δtotal ≤ L/{defl_limit_total}",
        substitution=f"δtotal = {delta_total:.2f} mm vs L/{defl_limit_total} = {L:.0f}/{defl_limit_total} = {delta_limit_total_val:.2f} mm",
        result=DCR_total,
        unit="D/C",
        code_ref="IBC Table 1604.3",
        status=status_total,
        notes=f"D/C = {DCR_total:.3f} {'≤ 1.0 OK' if DCR_total <= 1.0 else '> 1.0 NG'}"
    ))
    
    section.steps = steps
    overall_status = "PASS" if status_LL == "PASS" and status_total == "PASS" else "FAIL"
    section.conclusion = f"δLL = {delta_LL:.2f} mm (D/C = {DCR_LL:.3f}), δtotal = {delta_total:.2f} mm (D/C = {DCR_total:.3f})"
    section.status = overall_status
    
    results = {
        'delta_DL': delta_DL,
        'delta_SDL': delta_SDL,
        'delta_LL': delta_LL,
        'delta_total': delta_total,
        'delta_limit_LL': delta_limit_LL_val,
        'delta_limit_total': delta_limit_total_val,
        'DCR_LL': DCR_LL,
        'DCR_total': DCR_total,
        'status_LL': status_LL,
        'status_total': status_total
    }
    
    return section, results


# =============================================================================
# SECTION 8: DEMAND VS CAPACITY
# =============================================================================

def calc_demand_capacity_detailed(
    Mu: float, Vu: float,
    phi_Mn: float, phi_Vn: float,
    method: str = "LRFD"
) -> Tuple[DetailedCalcSection, Dict]:
    """
    Calculate demand-to-capacity ratios for strength checks.
    
    Parameters:
        Mu: Required flexural strength (kN⋅m)
        Vu: Required shear strength (kN)
        phi_Mn: Design flexural strength (kN⋅m)
        phi_Vn: Design shear strength (kN)
        method: "LRFD" or "ASD"
    """
    section = DetailedCalcSection(
        section_number=8,
        title="STRENGTH VERIFICATION",
        description="Verify that the composite beam has adequate strength for the applied loads.",
        code_ref="AISC 360-16 Chapter B"
    )
    steps = []
    step_num = 1
    
    # Step 1: Required flexural strength
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Required Flexural Strength",
        description=f"The required flexural strength from structural analysis using {'LRFD' if method == 'LRFD' else 'ASD'} load combinations.",
        equation=f"{'Mu' if method == 'LRFD' else 'Ma'} = factored moment from analysis",
        substitution=f"{'Mu' if method == 'LRFD' else 'Ma'} = {Mu:.2f} kN⋅m",
        result=Mu,
        unit="kN⋅m",
        code_ref="ASCE 7-22 Load Combinations"
    ))
    step_num += 1
    
    # Step 2: Required shear strength
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Required Shear Strength",
        description=f"The required shear strength from structural analysis using {'LRFD' if method == 'LRFD' else 'ASD'} load combinations.",
        equation=f"{'Vu' if method == 'LRFD' else 'Va'} = factored shear from analysis",
        substitution=f"{'Vu' if method == 'LRFD' else 'Va'} = {Vu:.2f} kN",
        result=Vu,
        unit="kN",
        code_ref="ASCE 7-22 Load Combinations"
    ))
    step_num += 1
    
    # Step 3: Flexural strength check
    DCR_flex = Mu / phi_Mn if phi_Mn > 0 else 999
    status_flex = "PASS" if DCR_flex <= 1.0 else "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Flexural Strength Check",
        description="Verify that the design flexural strength exceeds the required flexural strength.",
        equation=f"{'Mu ≤ φMn' if method == 'LRFD' else 'Ma ≤ Mn/Ω'}",
        substitution=f"D/C = {Mu:.2f} / {phi_Mn:.2f} = {DCR_flex:.3f}",
        result=DCR_flex,
        unit="",
        code_ref="AISC 360-16 §B3.1",
        status=status_flex,
        notes=f"{'✓ OK' if DCR_flex <= 1.0 else '✗ NG'} - D/C = {DCR_flex:.3f}"
    ))
    step_num += 1
    
    # Step 4: Shear strength check
    DCR_shear = Vu / phi_Vn if phi_Vn > 0 else 999
    status_shear = "PASS" if DCR_shear <= 1.0 else "FAIL"
    
    steps.append(DetailedCalcStep(
        step_number=step_num,
        title="Shear Strength Check",
        description="Verify that the design shear strength exceeds the required shear strength.",
        equation=f"{'Vu ≤ φVn' if method == 'LRFD' else 'Va ≤ Vn/Ω'}",
        substitution=f"D/C = {Vu:.2f} / {phi_Vn:.2f} = {DCR_shear:.3f}",
        result=DCR_shear,
        unit="",
        code_ref="AISC 360-16 §B3.1",
        status=status_shear,
        notes=f"{'✓ OK' if DCR_shear <= 1.0 else '✗ NG'} - D/C = {DCR_shear:.3f}"
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
# MASTER FUNCTION: COMPLETE COMPOSITE BEAM DESIGN
# =============================================================================

def design_composite_detailed(
    # Steel section
    section_name: str,
    d: float, bf: float, tf: float, tw: float,
    A: float, Ix: float, Sx: float, Zx: float,
    # Slab
    beff: float, tc: float, hr: float,
    # Materials
    fc: float, Fy: float, E: float = 200000,
    # Studs
    Qn_total: float = 0,
    # Loading (kN/m)
    w_DL: float = 0, w_SDL: float = 0, w_LL: float = 0,
    # Geometry
    L: float = 0,
    # Method
    method: str = "LRFD"
) -> CompositeDesignReport:
    """
    Complete composite beam design with detailed professional calculations.
    
    Parameters:
        section_name: Steel section designation (e.g., "W16x31")
        d, bf, tf, tw: Section dimensions (mm)
        A, Ix, Sx, Zx: Section properties (mm², mm⁴, mm³, mm³)
        beff: Effective slab width (mm)
        tc, hr: Slab thickness and rib height (mm)
        fc: Concrete strength (MPa)
        Fy: Steel yield stress (MPa)
        E: Steel elastic modulus (MPa)
        Qn_total: Total shear connector capacity (N)
        w_DL, w_SDL, w_LL: Loads (kN/m)
        L: Span (mm)
        method: "LRFD" or "ASD"
    
    Returns:
        CompositeDesignReport with all detailed calculations
    """
    
    report = CompositeDesignReport(
        project_info={'method': method},
        beam_designation=section_name
    )
    
    # Section 1: Steel properties
    sec1 = calc_steel_section_properties_detailed(
        section_name, d, bf, tf, tw, A, Ix, Sx, Zx, Fy, E
    )
    report.add_section(sec1)
    
    # Section 2: Concrete properties
    sec2, conc_props = calc_concrete_properties_detailed(fc, tc, hr, wr=50)
    report.add_section(sec2)
    
    # Section 3: Composite flexural strength (with PNA!)
    sec3, flex_results = calc_composite_flexure_detailed(
        d, bf, tf, tw, A, Zx, beff, tc, hr, fc, Fy, E, Qn_total, method
    )
    report.add_section(sec3)
    
    # Section 4: Shear strength
    sec4, shear_results = calc_composite_shear_detailed(d, tw, Fy, E, method)
    report.add_section(sec4)
    
    # Section 5: Effective moment of inertia
    sec5, Ieff_results = calc_effective_Itr_detailed(
        d, A, Ix, beff, tc, hr, fc, E,
        Qn_total, flex_results['Ts'], flex_results['Cc_max']
    )
    report.add_section(sec5)
    
    # Section 6: Deflection
    if L > 0:
        sec6, defl_results = calc_deflection_detailed(
            L, Ix, Ieff_results['Ieff'], E, w_DL, w_SDL, w_LL
        )
        report.add_section(sec6)
    
    # Section 7: Demand vs capacity
    if L > 0 and (w_DL + w_SDL + w_LL) > 0:
        # Calculate demands
        w_u = 1.2 * (w_DL + w_SDL) + 1.6 * w_LL if method == "LRFD" else w_DL + w_SDL + w_LL
        Mu = w_u * L**2 / 8 / 1e6  # kN⋅m
        Vu = w_u * L / 2 / 1000    # kN
        
        sec7, dc_results = calc_demand_capacity_detailed(
            Mu, Vu, flex_results['phi_Mn'], shear_results['phi_Vn'], method
        )
        report.add_section(sec7)
    
    # Generate summary
    report.summary = _generate_composite_summary(report, section_name, method)
    
    return report


def _generate_composite_summary(report: CompositeDesignReport, beam: str, method: str) -> str:
    """Generate a formatted summary table for the composite beam design."""
    
    lines = []
    lines.append("")
    lines.append("╔══════════════════════════════════════════════════════════════════════════════╗")
    lines.append("║              COMPOSITE BEAM DESIGN SUMMARY                                    ║")
    lines.append("║                    Per AISC 360-16 Chapter I                                  ║")
    lines.append("╠══════════════════════════════════════════════════════════════════════════════╣")
    lines.append(f"║ Beam: {beam:<72}║")
    lines.append(f"║ Method: {method:<70}║")
    lines.append("╠══════════════════════════════════════════════════════════════════════════════╣")
    lines.append("║ SECTION                        │ STATUS                                      ║")
    lines.append("╠────────────────────────────────┼─────────────────────────────────────────────╣")
    
    for sec in report.sections:
        status_icon = "✓ PASS" if sec.status == "PASS" else "✗ FAIL" if sec.status == "FAIL" else "⚠ WARN"
        # Truncate title if too long
        title = sec.title[:30] if len(sec.title) > 30 else sec.title
        lines.append(f"║ {title:<30} │ {status_icon:<43}║")
    
    lines.append("╠══════════════════════════════════════════════════════════════════════════════╣")
    overall = "✓ PASS" if report.overall_status == "PASS" else "✗ FAIL"
    lines.append(f"║ OVERALL RESULT: {overall:<61}║")
    lines.append("╚══════════════════════════════════════════════════════════════════════════════╝")
    lines.append("")
    
    return "\n".join(lines)


def format_composite_report(report: CompositeDesignReport) -> str:
    """
    Format the complete design report as a text string for display or export.
    """
    lines = []
    
    # Header
    lines.append("=" * 80)
    lines.append("COMPOSITE BEAM DESIGN - DETAILED CALCULATIONS")
    lines.append("Per AISC 360-16 Specification for Structural Steel Buildings")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Beam: {report.beam_designation}")
    lines.append(f"Method: {report.project_info.get('method', 'LRFD')}")
    lines.append("")
    
    # Each section
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
    
    # Summary
    lines.append(report.summary)
    
    return "\n".join(lines)
