"""
Castellated and Cellular Beam Design Module
=============================================
Per AISC Design Guide 31 and AISC 360-16

Design of steel beams with web openings:
- Castellated beams (hexagonal openings)
- Cellular beams (circular openings)

Design Standards:
- AISC Design Guide 31: Castellated and Cellular Beam Design
- AISC 360-16: Specification for Structural Steel Buildings

Author: CompositeBeam Pro
Version: 1.0
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from enum import Enum


# =============================================================================
# ENUMERATIONS
# =============================================================================

class BeamType(Enum):
    """Type of beam with web openings"""
    CASTELLATED = "castellated"  # Hexagonal openings
    CELLULAR = "cellular"        # Circular openings


# =============================================================================
# DIMENSION LIMITS - AISC DG31 Section 3
# =============================================================================

# Castellated beam limits (hexagonal openings)
CASTELLATED_LIMITS = {
    'ho_dg_max': 0.70,      # ho/dg ≤ 0.70 (opening height to expanded depth)
    'ho_dg_min': 0.50,      # ho/dg ≥ 0.50 (practical minimum)
    'e_ho_max': 0.50,       # e/ho ≤ 0.50 (half-length to height)
    'e_ho_min': 0.25,       # e/ho ≥ 0.25
    'b_ho_min': 0.25,       # b/ho ≥ 0.25 (web post width ratio)
    'S_ho_min': 1.08,       # S/ho ≥ 1.08 (spacing to height)
    'S_ho_max': 1.50,       # S/ho ≤ 1.50
    'theta_min': 45,        # θ ≥ 45° (cutting angle)
    'theta_max': 70,        # θ ≤ 70°
    'dt_tf_min': 1.0,       # dt/tf ≥ 1.0 (tee depth to flange thickness)
    'expansion_min': 1.3,   # dg/d ≥ 1.3 (minimum expansion)
    'expansion_max': 1.6,   # dg/d ≤ 1.6 (maximum expansion)
}

# Cellular beam limits (circular openings)
CELLULAR_LIMITS = {
    'Do_dg_max': 0.80,      # Do/dg ≤ 0.80 (diameter to expanded depth)
    'Do_dg_min': 0.50,      # Do/dg ≥ 0.50 (practical minimum)
    'S_Do_min': 1.10,       # S/Do ≥ 1.10 (spacing to diameter)
    'S_Do_max': 1.80,       # S/Do ≤ 1.80
    'b_Do_min': 0.10,       # (S-Do)/Do ≥ 0.10 (web post width ratio)
    'b_Do_rec': 0.30,       # (S-Do)/Do ≥ 0.30 (recommended)
    'dt_tf_min': 1.0,       # dt/tf ≥ 1.0 (tee depth to flange thickness)
    'expansion_min': 1.3,   # dg/d ≥ 1.3 (minimum expansion)
    'expansion_max': 1.6,   # dg/d ≤ 1.6 (maximum expansion)
}


class DesignMethod(Enum):
    """Design methodology"""
    LRFD = "LRFD"
    ASD = "ASD"


class LoadType(Enum):
    """Type of loading"""
    UNIFORM = "uniform"
    CONCENTRATED = "concentrated"
    COMBINED = "combined"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ParentSection:
    """Parent beam section properties (before cutting)"""
    designation: str      # Section name (e.g., "W410x60")
    d: float             # Depth (mm)
    bf: float            # Flange width (mm)
    tf: float            # Flange thickness (mm)
    tw: float            # Web thickness (mm)
    A: float             # Area (mm²)
    Ix: float            # Moment of inertia (mm⁴)
    Sx: float            # Section modulus (mm³)
    Zx: float            # Plastic section modulus (mm³)
    ry: float            # Radius of gyration about y-axis (mm)
    J: float = 0         # Torsional constant (mm⁴)
    Cw: float = 0        # Warping constant (mm⁶)
    wt: float = 0        # Weight (kg/m)
    
    @classmethod
    def from_dict(cls, name: str, props: dict) -> 'ParentSection':
        """
        Create ParentSection from dictionary of properties.
        Useful for converting from SECTIONS database format.
        
        Args:
            name: Section designation
            props: Dictionary with section properties
            
        Returns:
            ParentSection object
        """
        d = props.get('d', 0)
        Ix = props.get('Ix', 0)
        bf = props.get('bf', 100)
        A = props.get('A', 0)
        
        # Calculate Sx if not provided
        Sx = props.get('Sx', Ix / (d / 2) if d > 0 else 0)
        
        # Estimate Zx if not provided (shape factor ~1.12 for I-shapes)
        Zx = props.get('Zx', Sx * 1.12 if Sx > 0 else 0)
        
        # Estimate ry if not provided
        ry = props.get('ry', bf / 4 if bf > 0 else 25)
        
        # Get weight or calculate from area (steel density 7850 kg/m³)
        wt = props.get('wt', A * 7850 / 1e6 if A > 0 else 0)
        
        return cls(
            designation=name,
            d=d,
            bf=bf,
            tf=props.get('tf', 0),
            tw=props.get('tw', 0),
            A=A,
            Ix=Ix,
            Sx=Sx,
            Zx=Zx,
            ry=ry,
            J=props.get('J', 0),
            Cw=props.get('Cw', 0),
            wt=wt
        )


@dataclass
class CastellatedGeometry:
    """Geometry of castellated beam (hexagonal openings)"""
    ho: float            # Opening height (mm)
    e: float             # Half-length of opening (mm) - horizontal projection
    b: float             # Web post width at narrowest point (mm)
    S: float             # Opening spacing center-to-center (mm)
    theta: float = 60    # Cutting angle (degrees), typically 60°
    dt: float = 0        # Top tee depth (mm) - calculated
    db: float = 0        # Bottom tee depth (mm) - calculated
    dg: float = 0        # Total expanded depth (mm) - calculated
    
    def __post_init__(self):
        if self.dt == 0:
            # Will be calculated based on parent section
            pass


@dataclass
class CellularGeometry:
    """Geometry of cellular beam (circular openings)"""
    Do: float            # Opening diameter (mm)
    S: float             # Opening spacing center-to-center (mm)
    dg: float = 0        # Total expanded depth (mm) - calculated
    dt: float = 0        # Top tee depth (mm) - calculated
    db: float = 0        # Bottom tee depth (mm) - calculated
    
    @property
    def ho(self) -> float:
        """Opening height equals diameter for circular"""
        return self.Do
    
    @property
    def e(self) -> float:
        """Equivalent half-length for circular opening"""
        return self.Do / 2


@dataclass
class MaterialProperties:
    """Steel material properties"""
    Fy: float = 345      # Yield strength (MPa)
    Fu: float = 450      # Tensile strength (MPa)
    E: float = 200000    # Elastic modulus (MPa)
    G: float = 77200     # Shear modulus (MPa)


@dataclass
class LoadingCondition:
    """Applied loads"""
    w_dead: float = 0    # Dead load (kN/m)
    w_live: float = 0    # Live load (kN/m)
    P_conc: float = 0    # Concentrated load (kN)
    a_conc: float = 0    # Distance to concentrated load from support (mm)
    span: float = 0      # Beam span (mm)
    
    @property
    def w_total(self) -> float:
        """Total uniform load"""
        return self.w_dead + self.w_live


@dataclass 
class CalculationStep:
    """Single calculation step for documentation"""
    description: str
    formula: str
    values: str
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
    status: str
    code_ref: str
    steps: List[CalculationStep] = field(default_factory=list)


# =============================================================================
# SECTION PROPERTY CALCULATIONS
# =============================================================================

def calc_expanded_section(
    parent: ParentSection,
    beam_type: BeamType,
    geometry: CastellatedGeometry | CellularGeometry
) -> Dict:
    """
    Calculate properties of expanded castellated/cellular section.
    
    Args:
        parent: Parent section properties
        beam_type: CASTELLATED or CELLULAR
        geometry: Opening geometry
        
    Returns:
        Dictionary with expanded section properties
    """
    d_parent = parent.d
    tf = parent.tf
    tw = parent.tw
    bf = parent.bf
    
    if beam_type == BeamType.CASTELLATED:
        # Castellated beam expansion
        # Total depth = parent depth + opening height / 2 (for 50% expansion)
        # Or specified by geometry
        ho = geometry.ho
        
        # Expansion ratio typically 1.5 (50% increase in depth)
        # dg = d_parent + ho/2 for symmetric cut
        if geometry.dg == 0:
            # Calculate expanded depth
            dg = d_parent + ho / 2
        else:
            dg = geometry.dg
            
        # Tee depths (assuming symmetric)
        dt = (dg - ho) / 2
        db = dt
        
        # Update geometry
        geometry.dg = dg
        geometry.dt = dt
        geometry.db = db
        
    else:  # CELLULAR
        # Cellular beam expansion
        Do = geometry.Do
        
        if geometry.dg == 0:
            # Typical expansion
            dg = d_parent + Do / 2
        else:
            dg = geometry.dg
            
        dt = (dg - Do) / 2
        db = dt
        
        geometry.dg = dg
        geometry.dt = dt
        geometry.db = db
        ho = Do
    
    # Gross section properties of expanded beam
    # Area remains same as parent (material conservation)
    Ag = parent.A
    
    # Gross moment of inertia (using parallel axis theorem)
    # I_gross = 2 * [I_flange + A_flange * y_flange²] + I_web
    A_flange = bf * tf
    I_flange = bf * tf**3 / 12
    y_flange = dg/2 - tf/2
    
    # Web contribution (two tees)
    h_web = dt - tf  # Web height in each tee
    A_web_tee = h_web * tw
    I_web_tee = tw * h_web**3 / 12
    y_web_top = dg/2 - tf - h_web/2
    
    # Total gross moment of inertia
    Ix_gross = 2 * (I_flange + A_flange * y_flange**2 + 
                    I_web_tee + A_web_tee * y_web_top**2)
    
    # Section modulus
    Sx_gross = Ix_gross / (dg / 2)
    
    # Net section properties (at centerline of opening)
    # Only flanges contribute
    Ix_net = 2 * (I_flange + A_flange * y_flange**2)
    Sx_net = Ix_net / (dg / 2)
    
    # Tee section properties (for Vierendeel analysis)
    A_tee = A_flange + A_web_tee
    
    # Tee centroid from outer fiber
    y_bar_tee = (A_flange * tf/2 + A_web_tee * (tf + h_web/2)) / A_tee
    
    # Tee moment of inertia about its own centroid
    I_tee = (I_flange + A_flange * (y_bar_tee - tf/2)**2 + 
             I_web_tee + A_web_tee * (y_bar_tee - tf - h_web/2)**2)
    
    # Plastic section modulus (approximate)
    Zx_gross = Sx_gross * 1.12  # Approximate shape factor
    
    return {
        'dg': dg,
        'dt': dt,
        'db': db,
        'ho': ho,
        'Ag': Ag,
        'Ix_gross': Ix_gross,
        'Sx_gross': Sx_gross,
        'Zx_gross': Zx_gross,
        'Ix_net': Ix_net,
        'Sx_net': Sx_net,
        'A_tee': A_tee,
        'I_tee': I_tee,
        'y_bar_tee': y_bar_tee,
        'h_tee': dt
    }


# =============================================================================
# DIMENSIONAL CHECKS - AISC DG31 CHAPTER 3
# =============================================================================

def check_dimensional_limits(
    parent: ParentSection,
    beam_type: BeamType,
    geometry,  # CastellatedGeometry or CellularGeometry
    span: float,
    section_props: Dict
) -> DesignCheckResult:
    """
    Check geometric limits per AISC DG31 Chapter 3.
    
    Ensures proper structural behavior and fabrication feasibility.
    
    Args:
        parent: Parent section properties
        beam_type: CASTELLATED or CELLULAR
        geometry: Opening geometry
        span: Beam span (mm)
        section_props: Calculated section properties
        
    Returns:
        DesignCheckResult with all dimensional checks
        
    Reference:
        AISC DG31 Chapter 3 - Geometric Considerations
    """
    steps = []
    all_pass = True
    
    d = parent.d
    tf = parent.tf
    tw = parent.tw
    bf = parent.bf
    
    dg = section_props['dg']
    dt = section_props['dt']
    ho = section_props['ho']
    
    if beam_type == BeamType.CASTELLATED:
        e = geometry.e
        b = geometry.b
        S = geometry.S
        theta = geometry.theta
    else:  # CELLULAR
        e = geometry.Do / 2
        S = geometry.S
        b = S - geometry.Do
        theta = 0  # Not applicable for cellular
    
    # =========================
    # 1. Opening Height Ratio (ho/dg)
    # =========================
    # Per DG31 §3.2: Recommended 0.5 ≤ ho/dg ≤ 0.7
    ho_dg_ratio = ho / dg if dg > 0 else 0
    ho_dg_min, ho_dg_max = 0.4, 0.75
    ho_dg_pass = ho_dg_min <= ho_dg_ratio <= ho_dg_max
    all_pass = all_pass and ho_dg_pass
    
    steps.append(CalculationStep(
        description=f"Opening height ratio ho/dg: {ho_dg_min} ≤ ho/dg ≤ {ho_dg_max}",
        formula="ho/dg",
        values=f"{ho:.0f}/{dg:.0f} = {ho_dg_ratio:.3f}",
        result=ho_dg_ratio,
        unit="-",
        code_ref=f"DG31 §3.2 - {'OK' if ho_dg_pass else 'FAIL'}"
    ))
    
    # =========================
    # 2. Tee Depth Check
    # =========================
    # Per DG31 §3.3: dt ≥ tf + 25mm (minimum for stability)
    dt_min = tf + 25
    dt_pass = dt >= dt_min
    all_pass = all_pass and dt_pass
    
    steps.append(CalculationStep(
        description=f"Minimum tee depth: dt ≥ tf + 25mm = {dt_min:.1f}mm",
        formula="dt ≥ tf + 25",
        values=f"dt = {dt:.1f} mm",
        result=dt,
        unit="mm",
        code_ref=f"DG31 §3.3 - {'OK' if dt_pass else 'FAIL'}"
    ))
    
    # =========================
    # 3. Web Post Width
    # =========================
    if beam_type == BeamType.CASTELLATED:
        # Per DG31 §3.4: b ≥ max(3×tw, 50mm)
        b_min = max(3 * tw, 50)
        b_pass = b >= b_min
        all_pass = all_pass and b_pass
        
        steps.append(CalculationStep(
            description=f"Web post width: b ≥ max(3tw, 50) = {b_min:.1f}mm",
            formula="b ≥ max(3×tw, 50)",
            values=f"b = {b:.1f} mm",
            result=b,
            unit="mm",
            code_ref=f"DG31 §3.4 - {'OK' if b_pass else 'FAIL'}"
        ))
        
        # Cutting angle check: 45° ≤ θ ≤ 70°
        theta_min, theta_max = 45, 70
        theta_pass = theta_min <= theta <= theta_max
        all_pass = all_pass and theta_pass
        
        steps.append(CalculationStep(
            description=f"Cutting angle: {theta_min}° ≤ θ ≤ {theta_max}°",
            formula="θ",
            values=f"θ = {theta}°",
            result=theta,
            unit="°",
            code_ref=f"DG31 §3.4 - {'OK' if theta_pass else 'FAIL'}"
        ))
    else:
        # Cellular: b = S - Do ≥ 0.25×Do
        b_min_cell = max(0.25 * ho, 3 * tw)
        b_pass_cell = b >= b_min_cell
        all_pass = all_pass and b_pass_cell
        
        steps.append(CalculationStep(
            description=f"Web post width (cellular): b ≥ 0.25Do = {0.25*ho:.1f}mm",
            formula="b = S - Do ≥ 0.25×Do",
            values=f"b = {b:.1f} mm",
            result=b,
            unit="mm",
            code_ref=f"DG31 §3.5 - {'OK' if b_pass_cell else 'FAIL'}"
        ))
    
    # =========================
    # 4. Spacing Consistency
    # =========================
    if beam_type == BeamType.CASTELLATED:
        S_calc = 2 * e + b
        S_check = abs(S - S_calc) < 5  # Allow 5mm tolerance
        all_pass = all_pass and S_check
        
        steps.append(CalculationStep(
            description=f"Spacing consistency: S = 2e + b = {S_calc:.1f}mm",
            formula="S = 2e + b",
            values=f"S = {S:.1f} mm, calc = {S_calc:.1f} mm",
            result=S,
            unit="mm",
            code_ref=f"DG31 §3.4 - {'OK' if S_check else 'CHECK'}"
        ))
    else:
        S_min = 1.25 * ho
        S_check = S >= S_min
        all_pass = all_pass and S_check
        
        steps.append(CalculationStep(
            description=f"Minimum spacing (cellular): S ≥ 1.25Do = {S_min:.1f}mm",
            formula="S ≥ 1.25×Do",
            values=f"S = {S:.1f} mm",
            result=S,
            unit="mm",
            code_ref=f"DG31 §3.5 - {'OK' if S_check else 'FAIL'}"
        ))
    
    # =========================
    # 5. End Distance
    # =========================
    # Minimum solid web at supports: dg/2
    end_dist_min = dg / 2
    n_openings = int((span - 2 * end_dist_min) / S) if S > 0 else 0
    end_dist_actual = (span - n_openings * S) / 2 if n_openings > 0 else span / 2
    end_dist_pass = end_dist_actual >= end_dist_min * 0.8
    all_pass = all_pass and end_dist_pass
    
    steps.append(CalculationStep(
        description=f"End distance: ≥ dg/2 = {end_dist_min:.0f}mm",
        formula="End dist ≥ dg/2",
        values=f"Available = {end_dist_actual:.0f} mm ({n_openings} openings)",
        result=end_dist_actual,
        unit="mm",
        code_ref=f"DG31 §3.6 - {'OK' if end_dist_pass else 'FAIL'}"
    ))
    
    # =========================
    # 6. Tee Stem Slenderness
    # =========================
    h_stem = dt - tf
    stem_slenderness = h_stem / tw if tw > 0 else 0
    E = 200000
    Fy = 345  # Default, should be passed as parameter
    stem_limit = 0.84 * math.sqrt(E / Fy)
    stem_pass = stem_slenderness <= stem_limit * 1.5
    all_pass = all_pass and stem_pass
    
    steps.append(CalculationStep(
        description=f"Tee stem slenderness: (dt-tf)/tw ≤ 0.84√(E/Fy) = {stem_limit:.1f}",
        formula="(dt-tf)/tw",
        values=f"λ = {h_stem:.1f}/{tw} = {stem_slenderness:.1f}",
        result=stem_slenderness,
        unit="-",
        code_ref=f"DG31 §3.7 - {'OK' if stem_pass else 'CHECK'}"
    ))
    
    # =========================
    # 7. Expansion Ratio
    # =========================
    expansion = dg / d if d > 0 else 0
    exp_min, exp_max = 1.2, 1.7
    exp_pass = exp_min <= expansion <= exp_max
    all_pass = all_pass and exp_pass
    
    steps.append(CalculationStep(
        description=f"Expansion ratio: {exp_min} ≤ dg/d ≤ {exp_max}",
        formula="dg/d",
        values=f"{dg:.0f}/{d:.0f} = {expansion:.2f}",
        result=expansion,
        unit="-",
        code_ref=f"DG31 §3.2 - {'OK' if exp_pass else 'CHECK'}"
    ))
    
    # =========================
    # 8. Maximum Opening Height
    # =========================
    # ho ≤ 0.7 × dg typically
    ho_max = 0.7 * dg
    ho_max_pass = ho <= ho_max
    all_pass = all_pass and ho_max_pass
    
    steps.append(CalculationStep(
        description=f"Maximum opening height: ho ≤ 0.7dg = {ho_max:.0f}mm",
        formula="ho ≤ 0.7×dg",
        values=f"ho = {ho:.0f} mm",
        result=ho,
        unit="mm",
        code_ref=f"DG31 §3.2 - {'OK' if ho_max_pass else 'FAIL'}"
    ))
    
    # Count passes
    n_checks = len(steps)
    n_pass = sum(1 for s in steps if 'OK' in s.code_ref)
    n_fail = n_checks - n_pass
    
    return DesignCheckResult(
        check_name="Dimensional Limits",
        demand=n_fail,
        capacity=n_checks,
        ratio=n_fail / n_checks if n_checks > 0 else 0,
        status="PASS" if all_pass else "FAIL",
        code_ref="AISC DG31 Ch. 3",
        steps=steps
    )


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_castellated_sketch(
    parent: ParentSection,
    geometry: CastellatedGeometry,
    section_props: Dict
):
    """
    Create a detailed sketch of castellated beam with dimensions.
    
    Args:
        parent: Parent section
        geometry: Castellated geometry
        section_props: Calculated section properties
        
    Returns:
        Matplotlib figure
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Polygon
    import numpy as np
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Extract dimensions
    dg = section_props['dg']
    ho = geometry.ho
    e = geometry.e
    b = geometry.b
    S = geometry.S
    dt = section_props['dt']
    tf = parent.tf
    tw = parent.tw
    bf = parent.bf
    theta = geometry.theta
    
    # ===== LEFT PLOT: Elevation View =====
    ax1.set_xlim(-50, 3*S + 100)
    ax1.set_ylim(-80, dg + 100)
    ax1.set_aspect('equal')
    ax1.set_title('CASTELLATED BEAM - Elevation', fontsize=12, fontweight='bold')
    
    beam_length = 3 * S
    
    # Calculate hex point offset
    hex_offset = ho / (2 * math.tan(math.radians(theta))) if theta > 0 else e/2
    
    # Top flange
    ax1.fill([0, beam_length, beam_length, 0], 
             [dg-tf, dg-tf, dg, dg], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Bottom flange
    ax1.fill([0, beam_length, beam_length, 0], 
             [0, 0, tf, tf], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Web with hexagonal openings
    # Left solid end
    ax1.fill([0, S/2 - e, S/2 - e + hex_offset, S/2 - e + hex_offset, S/2 - e, 0], 
             [tf, tf, dt, dt+ho, dg-tf, dg-tf], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Draw 3 openings and web posts
    for i in range(3):
        x_c = S/2 + i * S  # Opening center
        
        # Hexagonal opening outline (thick red)
        hex_pts = [
            (x_c - e, dt + ho/2),
            (x_c - e + hex_offset, dt + ho),
            (x_c + e - hex_offset, dt + ho),
            (x_c + e, dt + ho/2),
            (x_c + e - hex_offset, dt),
            (x_c - e + hex_offset, dt),
        ]
        hex_x = [p[0] for p in hex_pts] + [hex_pts[0][0]]
        hex_y = [p[1] for p in hex_pts] + [hex_pts[0][1]]
        ax1.plot(hex_x, hex_y, 'r-', linewidth=2)
        
        # Web post after opening (if not last)
        if i < 2:
            # Upper web post
            ax1.fill([x_c + e - hex_offset, x_c + e, x_c + S - e, x_c + S - e + hex_offset],
                    [dt + ho, dt + ho/2, dt + ho/2, dt + ho], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
            ax1.fill([x_c + e - hex_offset, x_c + S - e + hex_offset, x_c + S - e + hex_offset, x_c + e - hex_offset],
                    [dt + ho, dt + ho, dg - tf, dg - tf], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
            # Lower web post
            ax1.fill([x_c + e - hex_offset, x_c + e, x_c + S - e, x_c + S - e + hex_offset],
                    [dt, dt + ho/2, dt + ho/2, dt], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
            ax1.fill([x_c + e - hex_offset, x_c + S - e + hex_offset, x_c + S - e + hex_offset, x_c + e - hex_offset],
                    [dt, dt, tf, tf], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Right solid end
    x_last = 2.5 * S
    ax1.fill([x_last + e - hex_offset, x_last + e, 3*S, 3*S, x_last + e, x_last + e - hex_offset],
             [dt + ho, dt + ho/2, tf, dg-tf, dt + ho/2, dt], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Dimension lines
    dim_off = 40
    
    # dg - Total depth
    ax1.annotate('', xy=(beam_length + dim_off, 0), xytext=(beam_length + dim_off, dg),
                arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax1.text(beam_length + dim_off + 5, dg/2, f'dg = {dg:.0f}', fontsize=10, va='center', color='red', fontweight='bold')
    
    # ho - Opening height
    ax1.annotate('', xy=(-dim_off, dt), xytext=(-dim_off, dt + ho),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax1.text(-dim_off - 5, dt + ho/2, f'ho = {ho:.0f}', fontsize=10, va='center', ha='right', color='green', fontweight='bold')
    
    # S - Spacing
    ax1.annotate('', xy=(S/2, -dim_off), xytext=(1.5*S, -dim_off),
                arrowprops=dict(arrowstyle='<->', color='purple', lw=1.5))
    ax1.text(S, -dim_off - 15, f'S = {S:.0f}', fontsize=10, ha='center', color='purple', fontweight='bold')
    
    # e - Half length
    ax1.annotate('', xy=(S/2 - e, dg + dim_off/2), xytext=(S/2, dg + dim_off/2),
                arrowprops=dict(arrowstyle='<->', color='orange', lw=1.5))
    ax1.text(S/2 - e/2, dg + dim_off/2 + 12, f'e = {e:.0f}', fontsize=9, ha='center', color='orange')
    
    # b - Web post
    ax1.annotate('', xy=(S/2 + e, dt + ho + 20), xytext=(1.5*S - e, dt + ho + 20),
                arrowprops=dict(arrowstyle='<->', color='brown', lw=1.5))
    ax1.text(S, dt + ho + 32, f'b = {b:.0f}', fontsize=9, ha='center', color='brown')
    
    # dt - Tee depth
    ax1.annotate('', xy=(S/2, tf), xytext=(S/2, dt),
                arrowprops=dict(arrowstyle='<->', color='cyan', lw=1.5))
    ax1.text(S/2 + 10, (tf + dt)/2, f'dt = {dt:.0f}', fontsize=9, va='center', color='darkcyan')
    
    ax1.set_xlabel('Length (mm)', fontsize=10)
    ax1.set_ylabel('Height (mm)', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # ===== RIGHT PLOT: Cross Section =====
    ax2.set_xlim(-bf - 80, bf + 80)
    ax2.set_ylim(-50, dg + 80)
    ax2.set_aspect('equal')
    ax2.set_title('Cross Section at Opening', fontsize=12, fontweight='bold')
    
    # Top tee
    ax2.fill([-bf/2, bf/2, bf/2, -bf/2], [dg-tf, dg-tf, dg, dg], 
            color='steelblue', alpha=0.9, edgecolor='navy', linewidth=2)
    ax2.fill([-tw/2, tw/2, tw/2, -tw/2], [dt+ho, dt+ho, dg-tf, dg-tf], 
            color='steelblue', alpha=0.9, edgecolor='navy', linewidth=2)
    
    # Bottom tee
    ax2.fill([-bf/2, bf/2, bf/2, -bf/2], [0, 0, tf, tf], 
            color='steelblue', alpha=0.9, edgecolor='navy', linewidth=2)
    ax2.fill([-tw/2, tw/2, tw/2, -tw/2], [tf, tf, dt, dt], 
            color='steelblue', alpha=0.9, edgecolor='navy', linewidth=2)
    
    # Opening region
    ax2.fill([-tw/2-5, tw/2+5, tw/2+5, -tw/2-5], [dt, dt, dt+ho, dt+ho], 
            color='lightyellow', edgecolor='red', linewidth=2, linestyle='--')
    ax2.text(0, dt + ho/2, 'OPENING\nho', fontsize=9, ha='center', va='center', color='red', fontweight='bold')
    
    # Dimension lines
    # bf
    ax2.annotate('', xy=(-bf/2, dg + 25), xytext=(bf/2, dg + 25),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=1.5))
    ax2.text(0, dg + 40, f'bf = {bf:.0f}', fontsize=10, ha='center', color='blue', fontweight='bold')
    
    # tf
    ax2.annotate('', xy=(bf/2 + 25, dg-tf), xytext=(bf/2 + 25, dg),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax2.text(bf/2 + 40, dg - tf/2, f'tf = {tf:.1f}', fontsize=9, va='center', color='green')
    
    # tw
    ax2.annotate('', xy=(-tw/2, -25), xytext=(tw/2, -25),
                arrowprops=dict(arrowstyle='<->', color='purple', lw=1.5))
    ax2.text(0, -40, f'tw = {tw:.1f}', fontsize=9, ha='center', color='purple')
    
    # dt
    ax2.annotate('', xy=(-bf/2 - 30, dg - tf), xytext=(-bf/2 - 30, dt + ho),
                arrowprops=dict(arrowstyle='<->', color='orange', lw=1.5))
    ax2.text(-bf/2 - 45, (dg - tf + dt + ho)/2, f'dt = {dt:.0f}', fontsize=9, va='center', ha='right', color='orange')
    
    ax2.set_xlabel('Width (mm)', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=dt, color='gray', linestyle=':', alpha=0.5)
    ax2.axhline(y=dt+ho, color='gray', linestyle=':', alpha=0.5)
    
    plt.tight_layout()
    return fig


def create_cellular_sketch(
    parent: ParentSection,
    geometry: CellularGeometry,
    section_props: Dict
):
    """
    Create a detailed sketch of cellular beam with dimensions.
    
    Args:
        parent: Parent section
        geometry: Cellular geometry
        section_props: Calculated section properties
        
    Returns:
        Matplotlib figure
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    import numpy as np
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Extract dimensions
    dg = section_props['dg']
    Do = geometry.Do
    S = geometry.S
    dt = section_props['dt']
    tf = parent.tf
    tw = parent.tw
    bf = parent.bf
    b = S - Do  # Web post width
    
    # ===== LEFT PLOT: Elevation View =====
    ax1.set_xlim(-50, 3*S + 100)
    ax1.set_ylim(-80, dg + 100)
    ax1.set_aspect('equal')
    ax1.set_title('CELLULAR BEAM - Elevation', fontsize=12, fontweight='bold')
    
    beam_length = 3 * S
    
    # Top flange
    ax1.fill([0, beam_length, beam_length, 0], 
             [dg-tf, dg-tf, dg, dg], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Bottom flange
    ax1.fill([0, beam_length, beam_length, 0], 
             [0, 0, tf, tf], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Left solid end
    ax1.fill([0, S/2 - Do/2, S/2 - Do/2, 0], [tf, tf, dg-tf, dg-tf], 
            color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Draw circular openings and web posts
    for i in range(3):
        x_c = S/2 + i * S
        y_c = dg / 2
        
        # Draw circle (opening)
        circle = Circle((x_c, y_c), Do/2, fill=True, facecolor='white',
                        edgecolor='red', linewidth=2.5)
        ax1.add_patch(circle)
        
        # Web post between openings
        if i < 2:
            x_post_left = x_c + Do/2
            x_post_right = (i+1) * S + S/2 - Do/2
            ax1.fill([x_post_left, x_post_right, x_post_right, x_post_left],
                    [tf, tf, dg-tf, dg-tf], color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Right solid end
    ax1.fill([2.5*S + Do/2, 3*S, 3*S, 2.5*S + Do/2], [tf, tf, dg-tf, dg-tf], 
            color='steelblue', alpha=0.8, edgecolor='navy', lw=1)
    
    # Dimension lines
    dim_off = 40
    
    # dg - Total depth
    ax1.annotate('', xy=(beam_length + dim_off, 0), xytext=(beam_length + dim_off, dg),
                arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax1.text(beam_length + dim_off + 5, dg/2, f'dg = {dg:.0f}', fontsize=10, va='center', color='red', fontweight='bold')
    
    # Do - Opening diameter
    ax1.annotate('', xy=(S/2 - Do/2, dg/2), xytext=(S/2 + Do/2, dg/2),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax1.text(S/2, dg/2 + Do/2 + 20, f'Do = {Do:.0f}', fontsize=10, ha='center', color='green', fontweight='bold')
    
    # S - Spacing
    ax1.annotate('', xy=(S/2, -dim_off), xytext=(1.5*S, -dim_off),
                arrowprops=dict(arrowstyle='<->', color='purple', lw=1.5))
    ax1.text(S, -dim_off - 15, f'S = {S:.0f}', fontsize=10, ha='center', color='purple', fontweight='bold')
    
    # b - Web post
    ax1.annotate('', xy=(S/2 + Do/2, dg + dim_off/2), xytext=(1.5*S - Do/2, dg + dim_off/2),
                arrowprops=dict(arrowstyle='<->', color='brown', lw=1.5))
    ax1.text(S, dg + dim_off/2 + 15, f'b = {b:.0f}', fontsize=9, ha='center', color='brown')
    
    # dt - Tee depth
    ax1.annotate('', xy=(S/2, dg-tf), xytext=(S/2, dg/2 + Do/2),
                arrowprops=dict(arrowstyle='<->', color='cyan', lw=1.5))
    ax1.text(S/2 + 15, (dg - tf + dg/2 + Do/2)/2, f'dt = {dt:.0f}', fontsize=9, va='center', color='darkcyan')
    
    ax1.set_xlabel('Length (mm)', fontsize=10)
    ax1.set_ylabel('Height (mm)', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # ===== RIGHT PLOT: Cross Section =====
    ax2.set_xlim(-bf - 80, bf + 80)
    ax2.set_ylim(-50, dg + 80)
    ax2.set_aspect('equal')
    ax2.set_title('Cross Section at Opening', fontsize=12, fontweight='bold')
    
    # Top tee
    ax2.fill([-bf/2, bf/2, bf/2, -bf/2], [dg-tf, dg-tf, dg, dg], 
            color='steelblue', alpha=0.9, edgecolor='navy', linewidth=2)
    ax2.fill([-tw/2, tw/2, tw/2, -tw/2], [dt+Do, dt+Do, dg-tf, dg-tf], 
            color='steelblue', alpha=0.9, edgecolor='navy', linewidth=2)
    
    # Bottom tee
    ax2.fill([-bf/2, bf/2, bf/2, -bf/2], [0, 0, tf, tf], 
            color='steelblue', alpha=0.9, edgecolor='navy', linewidth=2)
    ax2.fill([-tw/2, tw/2, tw/2, -tw/2], [tf, tf, dt, dt], 
            color='steelblue', alpha=0.9, edgecolor='navy', linewidth=2)
    
    # Opening region (circle)
    circle_sec = Circle((0, dg/2), Do/2, fill=True, facecolor='lightyellow',
                        edgecolor='red', linewidth=2.5, linestyle='--')
    ax2.add_patch(circle_sec)
    ax2.text(0, dg/2, f'OPENING\nDo={Do:.0f}', fontsize=9, ha='center', va='center', color='red', fontweight='bold')
    
    # Dimension lines
    # bf
    ax2.annotate('', xy=(-bf/2, dg + 25), xytext=(bf/2, dg + 25),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=1.5))
    ax2.text(0, dg + 40, f'bf = {bf:.0f}', fontsize=10, ha='center', color='blue', fontweight='bold')
    
    # tf
    ax2.annotate('', xy=(bf/2 + 25, dg-tf), xytext=(bf/2 + 25, dg),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax2.text(bf/2 + 40, dg - tf/2, f'tf = {tf:.1f}', fontsize=9, va='center', color='green')
    
    # tw
    ax2.annotate('', xy=(-tw/2, -25), xytext=(tw/2, -25),
                arrowprops=dict(arrowstyle='<->', color='purple', lw=1.5))
    ax2.text(0, -40, f'tw = {tw:.1f}', fontsize=9, ha='center', color='purple')
    
    # dt
    ax2.annotate('', xy=(-bf/2 - 30, dg - tf), xytext=(-bf/2 - 30, dt + Do),
                arrowprops=dict(arrowstyle='<->', color='orange', lw=1.5))
    ax2.text(-bf/2 - 45, (dg - tf + dt + Do)/2, f'dt = {dt:.0f}', fontsize=9, va='center', ha='right', color='orange')
    
    ax2.set_xlabel('Width (mm)', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def check_global_flexure(
    parent: ParentSection,
    section_props: Dict,
    material: MaterialProperties,
    Mu: float,
    Lb: float,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check global flexural strength per AISC DG31 Section 5.2.
    
    Uses gross section properties with modifications for openings.
    
    Args:
        parent: Parent section
        section_props: Expanded section properties
        material: Material properties
        Mu: Required flexural strength (kN·m)
        Lb: Unbraced length (mm)
        method: LRFD or ASD
        
    Returns:
        DesignCheckResult
    """
    steps = []
    
    Fy = material.Fy
    E = material.E
    
    Sx = section_props['Sx_gross']
    Zx = section_props['Zx_gross']
    dg = section_props['dg']
    Ix = section_props['Ix_gross']
    
    bf = parent.bf
    tf = parent.tf
    
    # Yield moment
    My = Fy * Sx / 1e6  # kN·m
    
    steps.append(CalculationStep(
        description="Yield moment",
        formula="My = Fy × Sx",
        values=f"My = {Fy} × {Sx/1e3:.0f}×10³ / 10⁶",
        result=My,
        unit="kN·m",
        code_ref="AISC DG31 §5.2"
    ))
    
    # Plastic moment
    Mp = Fy * Zx / 1e6  # kN·m
    
    steps.append(CalculationStep(
        description="Plastic moment",
        formula="Mp = Fy × Zx",
        values=f"Mp = {Fy} × {Zx/1e3:.0f}×10³ / 10⁶",
        result=Mp,
        unit="kN·m",
        code_ref="AISC 360-16 F2"
    ))
    
    # Limiting unbraced lengths - simplified approach for castellated beams
    # Use ry based on compression flange approximation
    ry = bf / math.sqrt(12)  # Approximate for compression flange
    
    Lp = 1.76 * ry * math.sqrt(E / Fy)
    
    steps.append(CalculationStep(
        description="Limiting unbraced length Lp",
        formula="Lp = 1.76 × ry × √(E/Fy)",
        values=f"Lp = 1.76 × {ry:.1f} × √({E}/{Fy})",
        result=Lp,
        unit="mm",
        code_ref="AISC 360-16 F2.5"
    ))
    
    # Simplified Lr calculation for castellated beams
    # Per DG31, use conservative approach
    # Lr ≈ 1.95 × ry × E / (0.7 × Fy) × correction factor
    
    # For castellated beams, torsional properties are reduced
    # Use simplified Lr based on section geometry
    ho = section_props['ho']
    h_tee = section_props['h_tee']
    
    # J_eff for castellated beam (approximate)
    J_approx = 2 * (bf * tf**3 / 3 + (h_tee - tf) * parent.tw**3 / 3)
    
    # rts approximation for castellated beam
    Iy_flange = tf * bf**3 / 12
    rts = math.sqrt(Iy_flange / (Sx / dg * 2))
    rts = max(rts, bf / 6)  # Ensure reasonable value
    
    # Lr calculation
    c = 1.0
    ho_factor = 1 - 0.3 * ho / dg  # Reduction for openings
    Lr = 1.95 * rts * (E / (0.7 * Fy)) * ho_factor
    Lr = max(Lr, 2 * Lp)  # Ensure Lr > Lp
    
    steps.append(CalculationStep(
        description="Limiting unbraced length Lr",
        formula="Lr (adjusted for openings)",
        values=f"Lr = {Lr:.0f} mm",
        result=Lr,
        unit="mm",
        code_ref="AISC DG31 §5.2.2"
    ))
    
    # Nominal flexural strength
    Cb = 1.0  # Conservative
    
    if Lb <= Lp:
        Mn = Mp
        gov = "yielding"
    elif Lb <= Lr:
        # Inelastic LTB
        Mn = Cb * (Mp - (Mp - 0.7 * My) * (Lb - Lp) / (Lr - Lp))
        Mn = min(Mn, Mp)
        gov = "inelastic LTB"
    else:
        # Elastic LTB
        Fcr = Cb * math.pi**2 * E / (Lb / rts)**2
        Mn = Fcr * Sx / 1e6
        Mn = min(Mn, Mp)
        gov = "elastic LTB"
    
    steps.append(CalculationStep(
        description=f"Nominal flexural strength ({gov})",
        formula="Mn per AISC 360-16 F2",
        values=f"Lb = {Lb:.0f} mm, Cb = {Cb}",
        result=Mn,
        unit="kN·m",
        code_ref="AISC 360-16 F2"
    ))
    
    # Design/allowable strength
    if method == DesignMethod.LRFD:
        phi = 0.90
        Mn_design = phi * Mn
        steps.append(CalculationStep(
            description="Design flexural strength",
            formula="φMn = 0.90 × Mn",
            values=f"φMn = 0.90 × {Mn:.2f}",
            result=Mn_design,
            unit="kN·m",
            code_ref="AISC 360-16 F1"
        ))
    else:
        omega = 1.67
        Mn_design = Mn / omega
        steps.append(CalculationStep(
            description="Allowable flexural strength",
            formula="Mn/Ω = Mn/1.67",
            values=f"Mn/Ω = {Mn:.2f}/1.67",
            result=Mn_design,
            unit="kN·m",
            code_ref="AISC 360-16 F1"
        ))
    
    ratio = Mu / Mn_design if Mn_design > 0 else float('inf')
    
    return DesignCheckResult(
        check_name="Global Flexure",
        demand=Mu,
        capacity=Mn_design,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        code_ref="AISC DG31 §5.2",
        steps=steps
    )


def check_vierendeel_bending(
    parent: ParentSection,
    section_props: Dict,
    geometry: CastellatedGeometry | CellularGeometry,
    material: MaterialProperties,
    Vu: float,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check Vierendeel bending at web openings per AISC DG31 Section 5.3.
    
    Local bending in tee sections due to shear transfer across opening.
    
    Args:
        parent: Parent section
        section_props: Expanded section properties
        geometry: Opening geometry
        material: Material properties  
        Vu: Required shear strength at opening (kN)
        method: LRFD or ASD
        
    Returns:
        DesignCheckResult
    """
    steps = []
    
    Fy = material.Fy
    E = material.E
    
    # Tee properties
    A_tee = section_props['A_tee']
    I_tee = section_props['I_tee']
    h_tee = section_props['h_tee']
    y_bar = section_props['y_bar_tee']
    
    # Opening half-length
    if hasattr(geometry, 'e'):
        e = geometry.e
    else:
        e = geometry.Do / 2
    
    ho = section_props['ho']
    dg = section_props['dg']
    
    # Vierendeel moment in tee
    # Mvr = Vu × e / 2 (moment in each tee)
    Mvr = Vu * e / 2 / 1000  # kN·m
    
    steps.append(CalculationStep(
        description="Vierendeel moment in tee",
        formula="Mvr = Vu × e / 2",
        values=f"Mvr = {Vu:.2f} × {e:.1f} / 2 / 1000",
        result=Mvr,
        unit="kN·m",
        code_ref="AISC DG31 §5.3.1"
    ))
    
    # Plastic moment capacity of tee
    # Simplified: Mp_tee ≈ Fy × Z_tee
    # Z_tee ≈ A_tee × (h_tee/4) for approximate T-shape
    
    # More accurate calculation
    tf = parent.tf
    bf = parent.bf
    tw = parent.tw
    h_stem = h_tee - tf
    
    # Plastic neutral axis location
    A_flange = bf * tf
    A_stem = h_stem * tw
    
    if A_flange >= A_stem:
        # PNA in flange
        y_pna = A_tee / (2 * bf)
        if y_pna <= tf:
            Z_tee = bf * y_pna**2 / 2 + bf * (tf - y_pna)**2 / 2 + A_stem * (tf - y_pna + h_stem/2)
        else:
            Z_tee = A_flange * (y_pna - tf/2) + tw * (y_pna - tf)**2 / 2 + tw * (h_tee - y_pna)**2 / 2
    else:
        # PNA in stem
        y_pna = (A_tee/2 - A_flange) / tw + tf
        Z_tee = A_flange * (y_pna - tf/2) + tw * (y_pna - tf)**2 / 2 + tw * (h_tee - y_pna)**2 / 2
    
    Mp_tee = Fy * Z_tee / 1e6  # kN·m
    
    steps.append(CalculationStep(
        description="Tee plastic moment capacity",
        formula="Mp_tee = Fy × Z_tee",
        values=f"Z_tee = {Z_tee:.0f} mm³",
        result=Mp_tee,
        unit="kN·m",
        code_ref="AISC DG31 §5.3.2"
    ))
    
    # Check for local buckling of tee stem
    # λ = h_stem / tw
    lambda_stem = h_stem / tw
    lambda_p = 0.84 * math.sqrt(E / Fy)
    
    if lambda_stem <= lambda_p:
        Mn_tee = Mp_tee
        gov = "yielding"
    else:
        # Reduce for local buckling
        Fcr = 0.69 * E / lambda_stem**2
        Mn_tee = min(Fcr * I_tee / (h_tee - y_bar) / 1e6, Mp_tee)
        gov = "local buckling"
    
    steps.append(CalculationStep(
        description=f"Tee nominal moment ({gov})",
        formula="Mn_tee",
        values=f"λ = {lambda_stem:.1f}, λp = {lambda_p:.1f}",
        result=Mn_tee,
        unit="kN·m",
        code_ref="AISC DG31 §5.3.3"
    ))
    
    # Design/allowable strength
    if method == DesignMethod.LRFD:
        phi = 0.90
        Mn_design = phi * Mn_tee
    else:
        omega = 1.67
        Mn_design = Mn_tee / omega
    
    ratio = Mvr / Mn_design if Mn_design > 0 else float('inf')
    
    return DesignCheckResult(
        check_name="Vierendeel Bending",
        demand=Mvr,
        capacity=Mn_design,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        code_ref="AISC DG31 §5.3",
        steps=steps
    )


def check_web_post_buckling(
    parent: ParentSection,
    section_props: Dict,
    geometry: CastellatedGeometry | CellularGeometry,
    beam_type: BeamType,
    material: MaterialProperties,
    Vuh: float,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check web post buckling per AISC DG31 Section 5.4.
    
    Web post between adjacent openings subject to horizontal shear.
    
    Args:
        parent: Parent section
        section_props: Expanded section properties
        geometry: Opening geometry
        beam_type: CASTELLATED or CELLULAR
        material: Material properties
        Vuh: Horizontal shear in web post (kN)
        method: LRFD or ASD
        
    Returns:
        DesignCheckResult
    """
    steps = []
    
    Fy = material.Fy
    E = material.E
    
    tw = parent.tw
    ho = section_props['ho']
    dg = section_props['dg']
    
    if beam_type == BeamType.CASTELLATED:
        # Web post width
        b = geometry.b  # Minimum width
        e = geometry.e
        S = geometry.S
        
        # Web post height
        h_wp = ho
        
        # Slenderness
        lambda_wp = h_wp / tw
        
    else:  # CELLULAR
        Do = geometry.Do
        S = geometry.S
        
        # Minimum web post width (at mid-height)
        b = S - Do
        
        # Effective height
        h_wp = Do
        lambda_wp = h_wp / tw
    
    steps.append(CalculationStep(
        description="Web post geometry",
        formula="b = web post width, h = height",
        values=f"b = {b:.1f} mm, h = {h_wp:.1f} mm",
        result=b,
        unit="mm",
        code_ref="AISC DG31 §5.4"
    ))
    
    # Critical buckling stress for web post
    # Per DG31, use column buckling approach
    
    # Effective length factor
    K = 0.65  # Fixed-fixed approximation
    
    # Radius of gyration of web post
    r_wp = tw / math.sqrt(12)
    
    # Slenderness ratio
    KL_r = K * h_wp / r_wp
    
    steps.append(CalculationStep(
        description="Web post slenderness",
        formula="KL/r = K × h / r",
        values=f"KL/r = {K} × {h_wp:.1f} / {r_wp:.2f}",
        result=KL_r,
        unit="-",
        code_ref="AISC DG31 §5.4.1"
    ))
    
    # Elastic buckling stress
    Fe = math.pi**2 * E / KL_r**2
    
    # Critical stress
    if KL_r <= 4.71 * math.sqrt(E / Fy):
        Fcr = 0.658**(Fy/Fe) * Fy
    else:
        Fcr = 0.877 * Fe
    
    steps.append(CalculationStep(
        description="Critical buckling stress",
        formula="Fcr per AISC 360-16 E3",
        values=f"Fe = {Fe:.1f} MPa",
        result=Fcr,
        unit="MPa",
        code_ref="AISC 360-16 E3"
    ))
    
    # Web post buckling capacity
    # Based on horizontal shear resistance
    # Vn_wp = Fcr × b × tw / √3 (shear yield)
    
    A_wp = b * tw
    Vn_wp = 0.6 * Fcr * A_wp / 1000  # kN
    
    steps.append(CalculationStep(
        description="Web post buckling capacity",
        formula="Vn = 0.6 × Fcr × b × tw",
        values=f"Vn = 0.6 × {Fcr:.1f} × {b:.1f} × {tw}",
        result=Vn_wp,
        unit="kN",
        code_ref="AISC DG31 §5.4.2"
    ))
    
    # Design/allowable strength
    if method == DesignMethod.LRFD:
        phi = 0.90
        Vn_design = phi * Vn_wp
    else:
        omega = 1.67
        Vn_design = Vn_wp / omega
    
    ratio = Vuh / Vn_design if Vn_design > 0 else float('inf')
    
    return DesignCheckResult(
        check_name="Web Post Buckling",
        demand=Vuh,
        capacity=Vn_design,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        code_ref="AISC DG31 §5.4",
        steps=steps
    )


def check_horizontal_shear(
    parent: ParentSection,
    section_props: Dict,
    geometry: CastellatedGeometry | CellularGeometry,
    beam_type: BeamType,
    material: MaterialProperties,
    Mu_left: float,
    Mu_right: float,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check horizontal shear at web post per AISC DG31 Section 5.5.
    
    Horizontal shear develops from moment gradient across opening.
    
    Args:
        parent: Parent section
        section_props: Expanded section properties
        geometry: Opening geometry
        beam_type: CASTELLATED or CELLULAR
        material: Material properties
        Mu_left: Moment at left edge of opening (kN·m)
        Mu_right: Moment at right edge of opening (kN·m)
        method: LRFD or ASD
        
    Returns:
        DesignCheckResult
    """
    steps = []
    
    Fy = material.Fy
    tw = parent.tw
    ho = section_props['ho']
    dg = section_props['dg']
    
    # Distance between tee centroids
    # Approximate as dg - h_tee
    h_tee = section_props['h_tee']
    d_eff = dg - h_tee
    
    # Horizontal shear from moment gradient
    # Vuh = ΔM / d_eff
    delta_M = abs(Mu_right - Mu_left)
    Vuh = delta_M / (d_eff / 1000)  # kN
    
    steps.append(CalculationStep(
        description="Horizontal shear from moment gradient",
        formula="Vuh = ΔM / d_eff",
        values=f"Vuh = {delta_M:.2f} / {d_eff/1000:.3f}",
        result=Vuh,
        unit="kN",
        code_ref="AISC DG31 §5.5"
    ))
    
    # Web post width
    if beam_type == BeamType.CASTELLATED:
        b = geometry.b
    else:
        b = geometry.S - geometry.Do
    
    # Horizontal shear capacity
    # Vnh = 0.6 × Fy × b × tw
    Vnh = 0.6 * Fy * b * tw / 1000  # kN
    
    steps.append(CalculationStep(
        description="Horizontal shear capacity",
        formula="Vnh = 0.6 × Fy × b × tw",
        values=f"Vnh = 0.6 × {Fy} × {b:.1f} × {tw}",
        result=Vnh,
        unit="kN",
        code_ref="AISC DG31 §5.5"
    ))
    
    # Design/allowable strength
    if method == DesignMethod.LRFD:
        phi = 1.00
        Vnh_design = phi * Vnh
    else:
        omega = 1.50
        Vnh_design = Vnh / omega
    
    ratio = Vuh / Vnh_design if Vnh_design > 0 else float('inf')
    
    return DesignCheckResult(
        check_name="Horizontal Shear",
        demand=Vuh,
        capacity=Vnh_design,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        code_ref="AISC DG31 §5.5",
        steps=steps
    )


def check_vertical_shear(
    parent: ParentSection,
    section_props: Dict,
    material: MaterialProperties,
    Vu: float,
    method: DesignMethod = DesignMethod.LRFD
) -> DesignCheckResult:
    """
    Check vertical shear at web opening per AISC DG31 Section 5.6.
    
    Shear is carried by tee sections at opening.
    
    Args:
        parent: Parent section
        section_props: Expanded section properties
        material: Material properties
        Vu: Required shear strength at opening (kN)
        method: LRFD or ASD
        
    Returns:
        DesignCheckResult
    """
    steps = []
    
    Fy = material.Fy
    E = material.E
    tw = parent.tw
    
    h_tee = section_props['h_tee']
    tf = parent.tf
    h_stem = h_tee - tf
    
    # Shear area of two tees
    Aw = 2 * h_stem * tw
    
    steps.append(CalculationStep(
        description="Shear area of tees",
        formula="Aw = 2 × h_stem × tw",
        values=f"Aw = 2 × {h_stem:.1f} × {tw}",
        result=Aw,
        unit="mm²",
        code_ref="AISC DG31 §5.6"
    ))
    
    # Web slenderness
    lambda_w = h_stem / tw
    lambda_v = 1.10 * math.sqrt(E / Fy)
    
    # Shear coefficient
    kv = 5.34  # For unstiffened webs
    
    if lambda_w <= lambda_v:
        Cv = 1.0
    elif lambda_w <= 1.37 * math.sqrt(kv * E / Fy):
        Cv = 1.10 * math.sqrt(kv * E / Fy) / lambda_w
    else:
        Cv = 1.51 * kv * E / (lambda_w**2 * Fy)
    
    steps.append(CalculationStep(
        description="Shear coefficient Cv",
        formula="Per AISC 360-16 G2.1",
        values=f"λ = {lambda_w:.1f}, Cv = {Cv:.3f}",
        result=Cv,
        unit="-",
        code_ref="AISC 360-16 G2.1"
    ))
    
    # Nominal shear strength
    Vn = 0.6 * Fy * Aw * Cv / 1000  # kN
    
    steps.append(CalculationStep(
        description="Nominal shear strength",
        formula="Vn = 0.6 × Fy × Aw × Cv",
        values=f"Vn = 0.6 × {Fy} × {Aw:.0f} × {Cv:.3f}",
        result=Vn,
        unit="kN",
        code_ref="AISC 360-16 G2.1"
    ))
    
    # Design/allowable strength
    if method == DesignMethod.LRFD:
        phi = 1.00
        Vn_design = phi * Vn
    else:
        omega = 1.50
        Vn_design = Vn / omega
    
    ratio = Vu / Vn_design if Vn_design > 0 else float('inf')
    
    return DesignCheckResult(
        check_name="Vertical Shear at Opening",
        demand=Vu,
        capacity=Vn_design,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        code_ref="AISC DG31 §5.6",
        steps=steps
    )


def check_deflection(
    section_props: Dict,
    material: MaterialProperties,
    loading: LoadingCondition,
    n_openings: int,
    opening_ratio: float = 0.7
) -> DesignCheckResult:
    """
    Check deflection with web opening effects per AISC DG31 Section 5.7.
    
    Args:
        section_props: Expanded section properties
        material: Material properties
        loading: Loading condition
        n_openings: Number of openings
        opening_ratio: Ratio of opening length to spacing
        
    Returns:
        DesignCheckResult
    """
    steps = []
    
    E = material.E  # MPa
    I_gross = section_props['Ix_gross']  # mm⁴
    
    L = loading.span  # mm
    w = loading.w_total  # kN/m = N/mm
    
    # Convert w to N/mm
    w_Nmm = w  # kN/m = N/mm
    
    # Basic deflection (no openings)
    # δ = 5wL⁴/(384EI)
    # Units: (N/mm) × mm⁴ / (MPa × mm⁴) = (N/mm) × mm⁴ / (N/mm² × mm⁴) = mm
    delta_basic = 5 * w_Nmm * L**4 / (384 * E * I_gross)  # mm
    
    steps.append(CalculationStep(
        description="Basic deflection (solid web)",
        formula="δ = 5wL⁴/(384EI)",
        values=f"δ = 5×{w_Nmm}×{L}⁴/(384×{E}×{I_gross/1e6:.2f}×10⁶)",
        result=delta_basic,
        unit="mm",
        code_ref="AISC DG31 §5.7"
    ))
    
    # Deflection increase factor for openings
    # Per DG31, increase is typically 10-30% depending on opening configuration
    ho = section_props['ho']
    
    # Effective moment of inertia reduction
    # Account for reduced stiffness at openings
    k_factor = 0.15 * n_openings * opening_ratio * ho / L
    k_factor = min(k_factor, 0.30)  # Cap at 30% increase
    
    delta_increase = 1 + k_factor
    
    steps.append(CalculationStep(
        description="Deflection increase factor",
        formula="Factor = 1 + k (for openings)",
        values=f"k = {k_factor:.3f}, n_openings = {n_openings}",
        result=delta_increase,
        unit="-",
        code_ref="AISC DG31 §5.7"
    ))
    
    # Total deflection
    delta = delta_basic * delta_increase
    
    steps.append(CalculationStep(
        description="Total deflection",
        formula="δ_total = δ_basic × factor",
        values=f"δ = {delta_basic:.2f} × {delta_increase:.3f}",
        result=delta,
        unit="mm",
        code_ref="AISC DG31 §5.7"
    ))
    
    # Deflection limits
    delta_limit = L / 240  # Total load limit
    
    steps.append(CalculationStep(
        description="Deflection limit (L/240)",
        formula="δ_limit = L/240",
        values=f"δ_limit = {L}/240",
        result=delta_limit,
        unit="mm",
        code_ref="AISC DG31 §5.7"
    ))
    
    ratio = delta / delta_limit if delta_limit > 0 else 0
    
    return DesignCheckResult(
        check_name="Deflection (L/240)",
        demand=delta,
        capacity=delta_limit,
        ratio=ratio,
        status="PASS" if ratio <= 1.0 else "FAIL",
        code_ref="AISC DG31 §5.7",
        steps=steps
    )


# =============================================================================
# COMPLETE DESIGN FUNCTION
# =============================================================================

def design_castellated_cellular_beam(
    parent: ParentSection,
    beam_type: BeamType,
    geometry: CastellatedGeometry | CellularGeometry,
    material: MaterialProperties,
    loading: LoadingCondition,
    Lb: float,
    method: DesignMethod = DesignMethod.LRFD
) -> Dict[str, DesignCheckResult]:
    """
    Complete design of castellated or cellular beam per AISC DG31.
    
    Args:
        parent: Parent section properties
        beam_type: CASTELLATED or CELLULAR
        geometry: Opening geometry
        material: Material properties
        loading: Loading condition
        Lb: Unbraced length (mm)
        method: LRFD or ASD
        
    Returns:
        Dictionary of DesignCheckResult objects
    """
    results = {}
    
    # Calculate expanded section properties
    section_props = calc_expanded_section(parent, beam_type, geometry)
    
    # =========================
    # 0. DIMENSIONAL LIMITS (First check)
    # =========================
    results['dimensional_limits'] = check_dimensional_limits(
        parent, beam_type, geometry, loading.span, section_props
    )
    
    # Load factors
    if method == DesignMethod.LRFD:
        wu = 1.2 * loading.w_dead + 1.6 * loading.w_live
    else:
        wu = loading.w_total
    
    L = loading.span / 1000  # m
    
    # Maximum moment and shear
    Mu_max = wu * L**2 / 8  # kN·m
    Vu_max = wu * L / 2     # kN
    
    # Number of openings
    if beam_type == BeamType.CASTELLATED:
        n_openings = int((loading.span - 2 * geometry.e) / geometry.S)
        opening_ratio = 2 * geometry.e / geometry.S
    else:
        n_openings = int((loading.span - geometry.Do) / geometry.S)
        opening_ratio = geometry.Do / geometry.S
    
    n_openings = max(n_openings, 1)
    
    # =========================
    # 1. GLOBAL FLEXURE
    # =========================
    results['global_flexure'] = check_global_flexure(
        parent, section_props, material, Mu_max, Lb, method
    )
    
    # =========================
    # 2. VIERENDEEL BENDING
    # =========================
    # Critical at high shear location (near supports)
    # Use maximum shear
    results['vierendeel'] = check_vierendeel_bending(
        parent, section_props, geometry, material, Vu_max, method
    )
    
    # =========================
    # 3. WEB POST BUCKLING
    # =========================
    # Horizontal shear from moment gradient
    # At critical web post near midspan where moment gradient is low
    # but also check near quarter points
    
    x_crit = L / 4  # Quarter point
    M_left = wu * x_crit * (L - x_crit) / 2 - wu * x_crit**2 / 2
    
    if beam_type == BeamType.CASTELLATED:
        delta_x = geometry.S / 1000
    else:
        delta_x = geometry.S / 1000
    
    M_right = wu * (x_crit + delta_x) * (L - x_crit - delta_x) / 2 - wu * (x_crit + delta_x)**2 / 2
    
    # Horizontal shear
    dg = section_props['dg']
    h_tee = section_props['h_tee']
    d_eff = dg - h_tee
    
    Vuh = abs(M_left - M_right) / (d_eff / 1000)
    
    results['web_post_buckling'] = check_web_post_buckling(
        parent, section_props, geometry, beam_type, material, Vuh, method
    )
    
    # =========================
    # 4. HORIZONTAL SHEAR
    # =========================
    results['horizontal_shear'] = check_horizontal_shear(
        parent, section_props, geometry, beam_type, material,
        M_left, M_right, method
    )
    
    # =========================
    # 5. VERTICAL SHEAR AT OPENING
    # =========================
    results['vertical_shear'] = check_vertical_shear(
        parent, section_props, material, Vu_max, method
    )
    
    # =========================
    # 6. DEFLECTION
    # =========================
    results['deflection'] = check_deflection(
        section_props, material, loading, n_openings, opening_ratio
    )
    
    return results


def generate_castellated_summary(
    results: Dict[str, DesignCheckResult],
    section_props: Dict,
    beam_type: BeamType
) -> str:
    """Generate text summary of castellated/cellular beam design."""
    beam_name = "CASTELLATED" if beam_type == BeamType.CASTELLATED else "CELLULAR"
    
    lines = [
        "=" * 65,
        f"{beam_name} BEAM DESIGN SUMMARY - AISC DG31",
        "=" * 65,
        "",
        f"Expanded Depth: dg = {section_props['dg']:.1f} mm",
        f"Opening Height: ho = {section_props['ho']:.1f} mm",
        f"Tee Depth: dt = {section_props['dt']:.1f} mm",
        f"Gross Ix: {section_props['Ix_gross']/1e6:.2f} × 10⁶ mm⁴",
        "",
    ]
    
    # Check pass/fail
    checks = [r for r in results.values()]
    all_pass = all(r.status == "PASS" for r in checks)
    
    lines.append(f"Overall Status: {'✓ ALL CHECKS PASS' if all_pass else '✗ DESIGN FAILS'}")
    lines.append("")
    lines.append(f"{'Check':<25} {'Demand':>10} {'Capacity':>10} {'D/C':>8} {'Status':>10}")
    lines.append("-" * 70)
    
    for name, result in results.items():
        status_sym = "✓" if result.status == "PASS" else "✗"
        lines.append(
            f"{result.check_name:<25} {result.demand:>10.2f} {result.capacity:>10.2f} "
            f"{result.ratio:>8.3f} {status_sym:>10}"
        )
    
    lines.append("-" * 70)
    
    return "\n".join(lines)


# =============================================================================
# DIMENSION LIMITS CHECK - AISC DG31 Section 3
# =============================================================================

def check_dimension_limits(
    parent: ParentSection,
    beam_type: BeamType,
    geometry: CastellatedGeometry | CellularGeometry,
    section_props: Dict
) -> DesignCheckResult:
    """
    Check geometric dimension limits per AISC DG31 Section 3.
    
    Args:
        parent: Parent section properties
        beam_type: CASTELLATED or CELLULAR
        geometry: Opening geometry
        section_props: Expanded section properties
        
    Returns:
        DesignCheckResult with all dimension checks
    """
    steps = []
    all_pass = True
    
    dg = section_props['dg']
    ho = section_props['ho']
    dt = section_props['dt']
    
    tf = parent.tf
    tw = parent.tw
    d = parent.d
    
    # =========================
    # 1. EXPANSION RATIO
    # =========================
    # Typical range: 1.3 to 1.6 times parent depth
    expansion_ratio = dg / d
    exp_min, exp_max = 1.25, 1.75
    exp_pass = exp_min <= expansion_ratio <= exp_max
    if not exp_pass:
        all_pass = False
    
    steps.append(CalculationStep(
        description=f"Expansion ratio ({exp_min}-{exp_max})",
        formula="dg/d",
        values=f"{dg:.0f}/{d:.0f} = {expansion_ratio:.2f}",
        result=expansion_ratio,
        unit="-",
        code_ref=f"{'✓ OK' if exp_pass else '✗ FAIL'}"
    ))
    
    # =========================
    # 2. OPENING HEIGHT RATIO
    # =========================
    # ho/dg should be 0.4 to 0.7 (typical 0.5-0.6)
    ho_dg_ratio = ho / dg
    ho_min, ho_max = 0.35, 0.75
    ho_pass = ho_min <= ho_dg_ratio <= ho_max
    if not ho_pass:
        all_pass = False
    
    steps.append(CalculationStep(
        description=f"Opening height ratio ({ho_min}-{ho_max})",
        formula="ho/dg",
        values=f"{ho:.0f}/{dg:.0f} = {ho_dg_ratio:.2f}",
        result=ho_dg_ratio,
        unit="-",
        code_ref=f"{'✓ OK' if ho_pass else '✗ FAIL'}"
    ))
    
    # =========================
    # 3. TEE DEPTH CHECK
    # =========================
    # Tee depth should be adequate: dt >= tf + 2*tw minimum
    dt_min = tf + 3 * tw
    dt_pass = dt >= dt_min
    if not dt_pass:
        all_pass = False
    
    steps.append(CalculationStep(
        description=f"Tee depth (min {dt_min:.0f} mm)",
        formula="dt ≥ tf + 3tw",
        values=f"{dt:.0f} ≥ {dt_min:.0f}",
        result=dt,
        unit="mm",
        code_ref=f"{'✓ OK' if dt_pass else '✗ FAIL'}"
    ))
    
    if beam_type == BeamType.CASTELLATED:
        # =========================
        # 4. CASTELLATED: e/ho RATIO
        # =========================
        # Half-length ratio: e/ho typically 0.25 to 0.5
        e = geometry.e
        e_ho_ratio = e / ho
        e_min, e_max = 0.2, 0.6
        e_pass = e_min <= e_ho_ratio <= e_max
        if not e_pass:
            all_pass = False
        
        steps.append(CalculationStep(
            description=f"Half-length ratio ({e_min}-{e_max})",
            formula="e/ho",
            values=f"{e:.0f}/{ho:.0f} = {e_ho_ratio:.2f}",
            result=e_ho_ratio,
            unit="-",
            code_ref=f"{'✓ OK' if e_pass else '✗ FAIL'}"
        ))
        
        # =========================
        # 5. CASTELLATED: WEB POST WIDTH
        # =========================
        # Minimum web post width: b >= ho/3 or 50mm
        b = geometry.b
        b_min = max(ho / 4, 50)
        b_pass = b >= b_min
        if not b_pass:
            all_pass = False
        
        steps.append(CalculationStep(
            description=f"Web post width (min {b_min:.0f} mm)",
            formula="b ≥ max(ho/4, 50)",
            values=f"{b:.0f} ≥ {b_min:.0f}",
            result=b,
            unit="mm",
            code_ref=f"{'✓ OK' if b_pass else '✗ FAIL'}"
        ))
        
        # =========================
        # 6. CASTELLATED: SPACING CHECK
        # =========================
        # S should equal 2e + b (geometric constraint)
        S = geometry.S
        S_calc = 2 * e + b
        S_diff = abs(S - S_calc) / S_calc * 100
        S_pass = S_diff < 10  # Within 10%
        if not S_pass:
            all_pass = False
        
        steps.append(CalculationStep(
            description="Spacing consistency",
            formula="S ≈ 2e + b",
            values=f"{S:.0f} ≈ {S_calc:.0f} ({S_diff:.1f}% diff)",
            result=S,
            unit="mm",
            code_ref=f"{'✓ OK' if S_pass else '✗ CHECK'}"
        ))
        
        # =========================
        # 7. CUTTING ANGLE
        # =========================
        # Typical 45° to 70°
        theta = geometry.theta
        theta_min, theta_max = 45, 70
        theta_pass = theta_min <= theta <= theta_max
        if not theta_pass:
            all_pass = False
        
        steps.append(CalculationStep(
            description=f"Cutting angle ({theta_min}°-{theta_max}°)",
            formula="θ",
            values=f"{theta}°",
            result=theta,
            unit="°",
            code_ref=f"{'✓ OK' if theta_pass else '✗ FAIL'}"
        ))
        
    else:  # CELLULAR
        # =========================
        # 4. CELLULAR: DIAMETER RATIO
        # =========================
        Do = geometry.Do
        Do_dg_ratio = Do / dg
        Do_min, Do_max = 0.35, 0.75
        Do_pass = Do_min <= Do_dg_ratio <= Do_max
        if not Do_pass:
            all_pass = False
        
        steps.append(CalculationStep(
            description=f"Diameter ratio ({Do_min}-{Do_max})",
            formula="Do/dg",
            values=f"{Do:.0f}/{dg:.0f} = {Do_dg_ratio:.2f}",
            result=Do_dg_ratio,
            unit="-",
            code_ref=f"{'✓ OK' if Do_pass else '✗ FAIL'}"
        ))
        
        # =========================
        # 5. CELLULAR: WEB POST WIDTH
        # =========================
        S = geometry.S
        b_cell = S - Do
        b_min = max(Do / 4, 50)
        b_pass = b_cell >= b_min
        if not b_pass:
            all_pass = False
        
        steps.append(CalculationStep(
            description=f"Web post width (min {b_min:.0f} mm)",
            formula="S - Do ≥ max(Do/4, 50)",
            values=f"{b_cell:.0f} ≥ {b_min:.0f}",
            result=b_cell,
            unit="mm",
            code_ref=f"{'✓ OK' if b_pass else '✗ FAIL'}"
        ))
        
        # =========================
        # 6. CELLULAR: SPACING RATIO
        # =========================
        # S/Do typically 1.2 to 1.8
        S_Do_ratio = S / Do
        S_min, S_max = 1.1, 2.0
        S_pass = S_min <= S_Do_ratio <= S_max
        if not S_pass:
            all_pass = False
        
        steps.append(CalculationStep(
            description=f"Spacing ratio ({S_min}-{S_max})",
            formula="S/Do",
            values=f"{S:.0f}/{Do:.0f} = {S_Do_ratio:.2f}",
            result=S_Do_ratio,
            unit="-",
            code_ref=f"{'✓ OK' if S_pass else '✗ FAIL'}"
        ))
    
    # =========================
    # 8. WEB SLENDERNESS
    # =========================
    # Tee stem slenderness
    h_stem = dt - tf
    stem_slenderness = h_stem / tw
    stem_limit = 60  # Practical limit for Vierendeel action
    stem_pass = stem_slenderness <= stem_limit
    if not stem_pass:
        all_pass = False
    
    steps.append(CalculationStep(
        description=f"Tee stem slenderness (max {stem_limit})",
        formula="(dt-tf)/tw",
        values=f"({dt:.0f}-{tf:.1f})/{tw:.1f} = {stem_slenderness:.1f}",
        result=stem_slenderness,
        unit="-",
        code_ref=f"{'✓ OK' if stem_pass else '✗ FAIL'}"
    ))
    
    # Count passes
    n_checks = len(steps)
    n_pass = sum(1 for s in steps if '✓' in s.code_ref)
    
    return DesignCheckResult(
        check_name="Dimension Limits",
        demand=n_checks - n_pass,
        capacity=0,
        ratio=n_pass / n_checks if n_checks > 0 else 0,
        status="PASS" if all_pass else "FAIL",
        code_ref="AISC DG31 §3",
        steps=steps
    )


def create_parent_from_dict(sec_dict: dict, name: str = "Custom") -> ParentSection:
    """
    Create ParentSection from a section dictionary (from SECTIONS database).
    
    Args:
        sec_dict: Dictionary with section properties
        name: Section designation
        
    Returns:
        ParentSection object
    """
    return ParentSection(
        designation=name,
        d=sec_dict.get('d', 500),
        bf=sec_dict.get('bf', 200),
        tf=sec_dict.get('tf', 15),
        tw=sec_dict.get('tw', 10),
        A=sec_dict.get('A', 10000),
        Ix=sec_dict.get('Ix', 500e6),
        Sx=sec_dict.get('Sx', sec_dict.get('Ix', 500e6) / (sec_dict.get('d', 500) / 2)),
        Zx=sec_dict.get('Zx', sec_dict.get('Sx', 2000e3) * 1.12),
        ry=sec_dict.get('ry', sec_dict.get('bf', 200) / 4),
        J=sec_dict.get('J', 500e3),
        Cw=sec_dict.get('Cw', 1e12)
    )


# =============================================================================
# VISUALIZATION - BEAM PROFILE SKETCH
# =============================================================================

def plot_castellated_beam(
    parent: ParentSection,
    geometry: CastellatedGeometry,
    section_props: Dict,
    n_openings: int = 5
) -> 'matplotlib.figure.Figure':
    """
    Create visualization of castellated beam with hexagonal openings.
    
    Args:
        parent: Parent section
        geometry: Castellated geometry
        section_props: Expanded section properties
        n_openings: Number of openings to show
        
    Returns:
        Matplotlib figure
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Polygon
    import numpy as np
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})
    
    # Extract dimensions
    dg = section_props['dg']
    ho = section_props['ho']
    dt = section_props['dt']
    e = geometry.e
    b = geometry.b
    S = geometry.S
    tf = parent.tf
    tw = parent.tw
    bf = parent.bf
    
    # Calculate beam length for display
    beam_length = (n_openings + 1) * S + 2 * e
    
    # ==================
    # ELEVATION VIEW
    # ==================
    ax1 = axes[0]
    ax1.set_xlim(-S/2, beam_length + S/2)
    ax1.set_ylim(-dg * 0.2, dg * 1.3)
    ax1.set_aspect('equal')
    ax1.set_title('CASTELLATED BEAM - Elevation View', fontsize=14, fontweight='bold')
    
    # Draw top flange
    top_flange = patches.Rectangle((0, dg - tf), beam_length, tf, 
                                    linewidth=1.5, edgecolor='#1f77b4', facecolor='#aec7e8')
    ax1.add_patch(top_flange)
    
    # Draw bottom flange
    bot_flange = patches.Rectangle((0, 0), beam_length, tf,
                                    linewidth=1.5, edgecolor='#1f77b4', facecolor='#aec7e8')
    ax1.add_patch(bot_flange)
    
    # Draw web with hexagonal openings
    # Start with solid web, then cut openings
    web_top = dg - tf
    web_bot = tf
    web_mid = dg / 2
    
    # Draw each web post and opening
    x_start = e  # First opening starts at e from end
    
    for i in range(n_openings):
        x_center = x_start + i * S
        
        # Hexagonal opening vertices
        hex_pts = [
            (x_center - e, web_mid),           # Left point
            (x_center - e + e/2, web_mid + ho/2),  # Top-left
            (x_center + e - e/2, web_mid + ho/2),  # Top-right
            (x_center + e, web_mid),           # Right point
            (x_center + e - e/2, web_mid - ho/2),  # Bot-right
            (x_center - e + e/2, web_mid - ho/2),  # Bot-left
        ]
        
        # Draw web post before opening (solid)
        if i == 0:
            # End section
            web_end = patches.Rectangle((0, tf), e - e/2, dg - 2*tf,
                                         linewidth=1, edgecolor='#1f77b4', facecolor='#aec7e8')
            ax1.add_patch(web_end)
        
        # Draw top tee
        top_tee_pts = [
            (x_center - e, web_mid + ho/2),
            (x_center - e + e/2, web_mid + ho/2),
            (x_center - e, web_top),
        ]
        
        # Draw bottom tee
        bot_tee_pts = [
            (x_center - e, web_mid - ho/2),
            (x_center - e + e/2, web_mid - ho/2),
            (x_center - e, web_bot),
        ]
        
        # Draw web posts between openings
        if i > 0:
            wp_x = x_center - e - b/2
            web_post = patches.Rectangle((wp_x, tf), b, dg - 2*tf,
                                          linewidth=1, edgecolor='#1f77b4', facecolor='#aec7e8')
            ax1.add_patch(web_post)
        
        # Draw hexagonal opening outline
        hex_patch = Polygon(hex_pts, closed=True, fill=True, 
                           facecolor='white', edgecolor='#d62728', linewidth=2)
        ax1.add_patch(hex_patch)
        
        # Draw tee outlines
        tee_top_l = [(x_center - e, web_top), (x_center - e, web_mid + ho/2)]
        tee_top_r = [(x_center + e, web_top), (x_center + e, web_mid + ho/2)]
        tee_bot_l = [(x_center - e, web_bot), (x_center - e, web_mid - ho/2)]
        tee_bot_r = [(x_center + e, web_bot), (x_center + e, web_mid - ho/2)]
        
        ax1.plot(*zip(*tee_top_l), 'b-', linewidth=1.5)
        ax1.plot(*zip(*tee_top_r), 'b-', linewidth=1.5)
        ax1.plot(*zip(*tee_bot_l), 'b-', linewidth=1.5)
        ax1.plot(*zip(*tee_bot_r), 'b-', linewidth=1.5)
    
    # Last web post
    wp_x = x_start + (n_openings - 1) * S + e
    web_end2 = patches.Rectangle((wp_x, tf), beam_length - wp_x, dg - 2*tf,
                                  linewidth=1, edgecolor='#1f77b4', facecolor='#aec7e8')
    ax1.add_patch(web_end2)
    
    # ==================
    # DIMENSION ANNOTATIONS
    # ==================
    # dg - total depth
    ax1.annotate('', xy=(beam_length + S*0.3, 0), xytext=(beam_length + S*0.3, dg),
                arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax1.text(beam_length + S*0.35, dg/2, f'dg = {dg:.0f}', fontsize=10, 
             color='red', va='center', fontweight='bold')
    
    # ho - opening height
    x_dim = x_start + S/2
    ax1.annotate('', xy=(x_dim + e*1.5, web_mid - ho/2), xytext=(x_dim + e*1.5, web_mid + ho/2),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax1.text(x_dim + e*1.6, web_mid, f'ho={ho:.0f}', fontsize=9, color='green', va='center')
    
    # e - half length
    ax1.annotate('', xy=(x_start - e, web_mid - ho*0.7), xytext=(x_start, web_mid - ho*0.7),
                arrowprops=dict(arrowstyle='<->', color='purple', lw=1.5))
    ax1.text(x_start - e/2, web_mid - ho*0.8, f'e={e:.0f}', fontsize=9, color='purple', ha='center')
    
    # S - spacing
    ax1.annotate('', xy=(x_start, -dg*0.1), xytext=(x_start + S, -dg*0.1),
                arrowprops=dict(arrowstyle='<->', color='orange', lw=1.5))
    ax1.text(x_start + S/2, -dg*0.15, f'S = {S:.0f}', fontsize=10, color='orange', ha='center', fontweight='bold')
    
    # b - web post width
    ax1.annotate('', xy=(x_start + e, web_mid), xytext=(x_start + S - e, web_mid),
                arrowprops=dict(arrowstyle='<->', color='brown', lw=1.5))
    ax1.text(x_start + S/2, web_mid + ho*0.1, f'b={b:.0f}', fontsize=9, color='brown', ha='center')
    
    # dt - tee depth
    ax1.annotate('', xy=(-S*0.2, web_mid + ho/2), xytext=(-S*0.2, dg - tf),
                arrowprops=dict(arrowstyle='<->', color='navy', lw=1.5))
    ax1.text(-S*0.25, web_mid + ho/2 + dt/2, f'dt={dt:.0f}', fontsize=9, color='navy', va='center', ha='right')
    
    ax1.set_xlabel('Length (mm)', fontsize=10)
    ax1.set_ylabel('Depth (mm)', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # ==================
    # CROSS-SECTION VIEW
    # ==================
    ax2 = axes[1]
    
    # Draw at solid section
    cs_x = bf * 2
    cs_scale = 1.0
    
    ax2.set_xlim(-bf, bf * 5)
    ax2.set_ylim(-dg * 0.1, dg * 1.1)
    ax2.set_aspect('equal')
    ax2.set_title('Cross-Sections (Solid vs. At Opening)', fontsize=12, fontweight='bold')
    
    # Solid section (left)
    # Top flange
    ax2.add_patch(patches.Rectangle((-bf/2, dg-tf), bf, tf, 
                  linewidth=2, edgecolor='#1f77b4', facecolor='#aec7e8'))
    # Web
    ax2.add_patch(patches.Rectangle((-tw/2, tf), tw, dg-2*tf,
                  linewidth=2, edgecolor='#1f77b4', facecolor='#aec7e8'))
    # Bottom flange
    ax2.add_patch(patches.Rectangle((-bf/2, 0), bf, tf,
                  linewidth=2, edgecolor='#1f77b4', facecolor='#aec7e8'))
    ax2.text(0, -dg*0.08, 'Solid Section', fontsize=10, ha='center', fontweight='bold')
    
    # At opening (right) - offset by 2.5*bf
    offset = bf * 3
    # Top flange
    ax2.add_patch(patches.Rectangle((offset - bf/2, dg-tf), bf, tf,
                  linewidth=2, edgecolor='#1f77b4', facecolor='#aec7e8'))
    # Top tee stem
    ax2.add_patch(patches.Rectangle((offset - tw/2, web_mid + ho/2), tw, dt - tf,
                  linewidth=2, edgecolor='#1f77b4', facecolor='#aec7e8'))
    # Bottom tee stem  
    ax2.add_patch(patches.Rectangle((offset - tw/2, tf), tw, dt - tf,
                  linewidth=2, edgecolor='#1f77b4', facecolor='#aec7e8'))
    # Bottom flange
    ax2.add_patch(patches.Rectangle((offset - bf/2, 0), bf, tf,
                  linewidth=2, edgecolor='#1f77b4', facecolor='#aec7e8'))
    # Opening indication
    ax2.add_patch(patches.Rectangle((offset - tw*2, web_mid - ho/2), tw*4, ho,
                  linewidth=2, edgecolor='#d62728', facecolor='#ffcccc', linestyle='--'))
    ax2.text(offset, -dg*0.08, 'At Opening', fontsize=10, ha='center', fontweight='bold')
    
    ax2.set_xlabel('Width (mm)', fontsize=10)
    ax2.axis('off')
    
    plt.tight_layout()
    return fig


def plot_cellular_beam(
    parent: ParentSection,
    geometry: CellularGeometry,
    section_props: Dict,
    n_openings: int = 5
) -> 'matplotlib.figure.Figure':
    """
    Create visualization of cellular beam with circular openings.
    
    Args:
        parent: Parent section
        geometry: Cellular geometry
        section_props: Expanded section properties
        n_openings: Number of openings to show
        
    Returns:
        Matplotlib figure
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import numpy as np
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})
    
    # Extract dimensions
    dg = section_props['dg']
    Do = geometry.Do
    dt = section_props['dt']
    S = geometry.S
    tf = parent.tf
    tw = parent.tw
    bf = parent.bf
    ho = Do
    
    # Calculate beam length
    beam_length = (n_openings + 1) * S
    
    # ==================
    # ELEVATION VIEW
    # ==================
    ax1 = axes[0]
    ax1.set_xlim(-S/2, beam_length + S/2)
    ax1.set_ylim(-dg * 0.2, dg * 1.3)
    ax1.set_aspect('equal')
    ax1.set_title('CELLULAR BEAM - Elevation View', fontsize=14, fontweight='bold')
    
    web_mid = dg / 2
    
    # Draw beam outline
    # Top flange
    top_flange = patches.Rectangle((0, dg - tf), beam_length, tf,
                                    linewidth=1.5, edgecolor='#2ca02c', facecolor='#98df8a')
    ax1.add_patch(top_flange)
    
    # Bottom flange
    bot_flange = patches.Rectangle((0, 0), beam_length, tf,
                                    linewidth=1.5, edgecolor='#2ca02c', facecolor='#98df8a')
    ax1.add_patch(bot_flange)
    
    # Web (solid background)
    web = patches.Rectangle((0, tf), beam_length, dg - 2*tf,
                            linewidth=1, edgecolor='#2ca02c', facecolor='#98df8a')
    ax1.add_patch(web)
    
    # Draw circular openings
    x_start = S / 2
    for i in range(n_openings):
        x_center = x_start + i * S
        
        # Circular opening
        circle = patches.Circle((x_center, web_mid), Do/2,
                                linewidth=2, edgecolor='#d62728', facecolor='white')
        ax1.add_patch(circle)
        
        # Draw tee outlines
        ax1.plot([x_center - Do/2, x_center - Do/2], [dg - tf, web_mid + Do/2], 
                'g-', linewidth=1.5)
        ax1.plot([x_center + Do/2, x_center + Do/2], [dg - tf, web_mid + Do/2],
                'g-', linewidth=1.5)
        ax1.plot([x_center - Do/2, x_center - Do/2], [tf, web_mid - Do/2],
                'g-', linewidth=1.5)
        ax1.plot([x_center + Do/2, x_center + Do/2], [tf, web_mid - Do/2],
                'g-', linewidth=1.5)
    
    # ==================
    # DIMENSION ANNOTATIONS
    # ==================
    # dg - total depth
    ax1.annotate('', xy=(beam_length + S*0.3, 0), xytext=(beam_length + S*0.3, dg),
                arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax1.text(beam_length + S*0.35, dg/2, f'dg = {dg:.0f}', fontsize=10,
             color='red', va='center', fontweight='bold')
    
    # Do - opening diameter
    x_dim = x_start
    ax1.annotate('', xy=(x_dim, web_mid - Do/2), xytext=(x_dim, web_mid + Do/2),
                arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax1.text(x_dim - Do*0.2, web_mid, f'Do={Do:.0f}', fontsize=10, color='green', 
             va='center', ha='right', fontweight='bold')
    
    # S - spacing
    ax1.annotate('', xy=(x_start, -dg*0.1), xytext=(x_start + S, -dg*0.1),
                arrowprops=dict(arrowstyle='<->', color='orange', lw=1.5))
    ax1.text(x_start + S/2, -dg*0.15, f'S = {S:.0f}', fontsize=10, color='orange', 
             ha='center', fontweight='bold')
    
    # Web post width (S - Do)
    b_wp = S - Do
    ax1.annotate('', xy=(x_start + Do/2, web_mid + Do*0.7), xytext=(x_start + S - Do/2, web_mid + Do*0.7),
                arrowprops=dict(arrowstyle='<->', color='brown', lw=1.5))
    ax1.text(x_start + S/2, web_mid + Do*0.8, f'b={b_wp:.0f}', fontsize=9, color='brown', ha='center')
    
    # dt - tee depth
    ax1.annotate('', xy=(-S*0.2, web_mid + Do/2), xytext=(-S*0.2, dg - tf),
                arrowprops=dict(arrowstyle='<->', color='navy', lw=1.5))
    ax1.text(-S*0.25, web_mid + Do/2 + dt/2, f'dt={dt:.0f}', fontsize=9, color='navy', 
             va='center', ha='right')
    
    ax1.set_xlabel('Length (mm)', fontsize=10)
    ax1.set_ylabel('Depth (mm)', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # ==================
    # CROSS-SECTION VIEW
    # ==================
    ax2 = axes[1]
    ax2.set_xlim(-bf, bf * 5)
    ax2.set_ylim(-dg * 0.1, dg * 1.1)
    ax2.set_aspect('equal')
    ax2.set_title('Cross-Sections (Solid vs. At Opening)', fontsize=12, fontweight='bold')
    
    # Solid section (left)
    ax2.add_patch(patches.Rectangle((-bf/2, dg-tf), bf, tf,
                  linewidth=2, edgecolor='#2ca02c', facecolor='#98df8a'))
    ax2.add_patch(patches.Rectangle((-tw/2, tf), tw, dg-2*tf,
                  linewidth=2, edgecolor='#2ca02c', facecolor='#98df8a'))
    ax2.add_patch(patches.Rectangle((-bf/2, 0), bf, tf,
                  linewidth=2, edgecolor='#2ca02c', facecolor='#98df8a'))
    ax2.text(0, -dg*0.08, 'Solid Section', fontsize=10, ha='center', fontweight='bold')
    
    # At opening (right)
    offset = bf * 3
    ax2.add_patch(patches.Rectangle((offset - bf/2, dg-tf), bf, tf,
                  linewidth=2, edgecolor='#2ca02c', facecolor='#98df8a'))
    ax2.add_patch(patches.Rectangle((offset - tw/2, web_mid + Do/2), tw, dt - tf,
                  linewidth=2, edgecolor='#2ca02c', facecolor='#98df8a'))
    ax2.add_patch(patches.Rectangle((offset - tw/2, tf), tw, dt - tf,
                  linewidth=2, edgecolor='#2ca02c', facecolor='#98df8a'))
    ax2.add_patch(patches.Rectangle((offset - bf/2, 0), bf, tf,
                  linewidth=2, edgecolor='#2ca02c', facecolor='#98df8a'))
    # Opening indication
    circle_cs = patches.Circle((offset, web_mid), Do/2,
                               linewidth=2, edgecolor='#d62728', facecolor='#ffcccc', linestyle='--')
    ax2.add_patch(circle_cs)
    ax2.text(offset, -dg*0.08, 'At Opening', fontsize=10, ha='center', fontweight='bold')
    
    ax2.axis('off')
    
    plt.tight_layout()
    return fig


# =============================================================================
# STANDARD PARENT SECTIONS DATABASE
# =============================================================================

PARENT_SECTIONS = {
    # W shapes (metric dimensions approximated)
    "W410x60": ParentSection("W410x60", 407, 178, 12.8, 7.7, 7610, 216e6, 1060e3, 1190e3, 39.4, 346e3, 490e9),
    "W410x67": ParentSection("W410x67", 410, 179, 14.4, 8.8, 8550, 245e6, 1200e3, 1350e3, 39.6, 486e3, 556e9),
    "W410x85": ParentSection("W410x85", 417, 181, 18.2, 10.9, 10800, 316e6, 1510e3, 1720e3, 40.4, 936e3, 720e9),
    "W460x74": ParentSection("W460x74", 457, 190, 14.5, 9.0, 9460, 333e6, 1460e3, 1630e3, 42.0, 514e3, 820e9),
    "W460x89": ParentSection("W460x89", 463, 192, 17.7, 10.5, 11400, 410e6, 1770e3, 1990e3, 43.2, 862e3, 1020e9),
    "W530x82": ParentSection("W530x82", 528, 209, 13.3, 9.5, 10500, 475e6, 1800e3, 2000e3, 45.0, 498e3, 1250e9),
    "W530x101": ParentSection("W530x101", 537, 210, 17.4, 10.9, 12900, 616e6, 2290e3, 2560e3, 47.0, 975e3, 1650e9),
    "W610x101": ParentSection("W610x101", 603, 228, 14.9, 10.5, 12900, 764e6, 2530e3, 2820e3, 49.8, 770e3, 2280e9),
    "W610x125": ParentSection("W610x125", 612, 229, 19.6, 11.9, 15900, 985e6, 3220e3, 3610e3, 51.5, 1480e3, 3020e9),
    "W690x125": ParentSection("W690x125", 678, 253, 16.3, 11.7, 15900, 1120e6, 3310e3, 3680e3, 54.9, 1010e3, 3880e9),
    "W690x152": ParentSection("W690x152", 687, 254, 21.0, 13.1, 19400, 1410e6, 4100e3, 4610e3, 56.4, 1870e3, 4990e9),
}


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing Castellated/Cellular Beam Design Module")
    print("=" * 55)
    
    # Test with W530x82 parent section
    parent = PARENT_SECTIONS["W530x82"]
    print(f"\nParent Section: {parent.designation}")
    print(f"  d = {parent.d} mm, bf = {parent.bf} mm")
    print(f"  tf = {parent.tf} mm, tw = {parent.tw} mm")
    
    # Castellated geometry (typical 1.5× expansion)
    geom_cast = CastellatedGeometry(
        ho=320,      # Opening height
        e=140,       # Half-length of opening
        b=100,       # Web post width
        S=380,       # Opening spacing
        theta=60     # Cutting angle
    )
    
    # Material
    material = MaterialProperties(Fy=345, Fu=450)
    
    # Loading
    loading = LoadingCondition(
        w_dead=15.0,   # kN/m
        w_live=25.0,   # kN/m
        span=12000     # 12m span
    )
    
    # Run design
    results = design_castellated_cellular_beam(
        parent=parent,
        beam_type=BeamType.CASTELLATED,
        geometry=geom_cast,
        material=material,
        loading=loading,
        Lb=3000,       # 3m unbraced length
        method=DesignMethod.LRFD
    )
    
    # Calculate section properties for summary
    section_props = calc_expanded_section(parent, BeamType.CASTELLATED, geom_cast)
    
    # Print summary
    print(generate_castellated_summary(results, section_props, BeamType.CASTELLATED))
