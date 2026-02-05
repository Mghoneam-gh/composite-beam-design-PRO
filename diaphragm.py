"""
Diaphragm Design Module - SDI DDM04
====================================
Phase 5 - CompositeBeam Pro

Design of steel deck diaphragms for lateral load resistance per SDI DDM04.

Design Standards:
- SDI DDM04: Steel Deck Institute Diaphragm Design Manual (4th Edition)
- AISI S310-16: North American Standard for Design of Profiled Steel Diaphragm Panels
- ASCE 7-22: Minimum Design Loads (for load combinations)

Author: CompositeBeam Pro
Version: 1.0
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum


# =============================================================================
# ENUMERATIONS
# =============================================================================

class FastenerType(Enum):
    """Types of structural fasteners for deck attachment"""
    ARC_SPOT_WELD = "arc_spot_weld"      # Puddle weld
    SCREW = "screw"                       # Self-drilling screw
    PAF = "paf"                           # Powder-actuated fastener
    WELD_WITH_WASHER = "weld_washer"      # Arc spot weld with washer


class SideLapType(Enum):
    """Types of side-lap connections"""
    SCREW = "screw"
    BUTTON_PUNCH = "button_punch"
    WELD = "weld"
    NONE = "none"


class DeckOrientation(Enum):
    """Deck orientation relative to lateral load direction"""
    PARALLEL = "parallel"          # Ribs parallel to load
    PERPENDICULAR = "perpendicular"  # Ribs perpendicular to load


class DiaphragmType(Enum):
    """Diaphragm flexibility classification"""
    RIGID = "rigid"
    FLEXIBLE = "flexible"
    SEMI_RIGID = "semi_rigid"


class DesignMethod(Enum):
    """Design methodology"""
    LRFD = "LRFD"
    ASD = "ASD"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DeckProfile:
    """Metal deck profile properties for diaphragm design"""
    hr: float              # Rib height (mm)
    pitch: float           # Rib spacing (mm)
    t: float               # Base metal thickness (mm)
    t_design: float = 0    # Design thickness after coating reduction (mm)
    fy: float = 230        # Yield strength (MPa)
    fu: float = 310        # Tensile strength (MPa)
    cover_width: float = 914  # Deck sheet cover width (mm)
    
    def __post_init__(self):
        if self.t_design == 0:
            # Design thickness = base metal - galvanizing (typically 0.04mm per side)
            self.t_design = self.t - 0.08


@dataclass
class SupportFastener:
    """Support connection fastener properties"""
    fastener_type: FastenerType
    diameter: float        # Fastener diameter (mm)
    fu: float = 450        # Fastener tensile strength (MPa)
    embedment: float = 0   # Embedment depth for PAF (mm)
    washer_dia: float = 0  # Washer diameter for weld+washer (mm)
    
    # Spacing parameters
    n_per_rib: int = 1     # Fasteners per rib at supports (36/36, 36/7, etc.)
    edge_pattern: str = "36/36"  # Pattern description
    

@dataclass
class SideLapFastener:
    """Side-lap connection fastener properties"""
    fastener_type: SideLapType
    diameter: float = 4.8   # Screw diameter (mm), typical #10
    spacing: float = 305    # Spacing along side-lap (mm)
    fu: float = 450         # Fastener tensile strength (MPa)


@dataclass
class DiaphragmGeometry:
    """Diaphragm geometry and layout"""
    length: float          # Diaphragm length in load direction (mm)
    width: float           # Diaphragm width perpendicular to load (mm)
    deck_span: float       # Deck span between supports (mm)
    orientation: DeckOrientation = DeckOrientation.PERPENDICULAR
    n_spans: int = 3       # Number of deck spans
    
    @property
    def aspect_ratio(self) -> float:
        """Length to width ratio"""
        return self.length / self.width if self.width > 0 else 0
    
    @property
    def n_panels(self) -> int:
        """Number of deck panels across width"""
        return max(1, int(self.width / 914))  # Assuming 914mm cover width


@dataclass
class DiaphragmLoads:
    """Diaphragm loading"""
    w_wind: float = 0       # Wind load (kN/m)
    w_seismic: float = 0    # Seismic load (kN/m)
    V_chord: float = 0      # Chord force if known (kN)
    
    @property
    def w_total(self) -> float:
        """Total lateral load (kN/m)"""
        return max(self.w_wind, self.w_seismic)


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
class DiaphragmResult:
    """Diaphragm design check result"""
    check_name: str
    demand: float
    capacity: float
    ratio: float
    status: str
    code_ref: str
    steps: List[CalculationStep] = field(default_factory=list)


# =============================================================================
# FASTENER CAPACITY - SDI DDM04 Chapter 4
# =============================================================================

def calc_arc_spot_weld_capacity(
    d_weld: float,
    t_deck: float,
    fu_deck: float,
    fu_weld: float = 415,
    method: DesignMethod = DesignMethod.LRFD
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate arc spot weld (puddle weld) shear capacity per SDI DDM04.
    
    Args:
        d_weld: Visible weld diameter (mm)
        t_deck: Deck design thickness (mm)
        fu_deck: Deck tensile strength (MPa)
        fu_weld: Weld metal tensile strength (MPa)
        method: LRFD or ASD
        
    Returns:
        (Qf in kN, calculation steps)
        
    Reference:
        SDI DDM04 Section 4.2
        AISI S100-16 §J2.2.2
    """
    steps = []
    
    # Effective weld diameter
    # d_e = 0.7×d - 1.5×t but not more than 0.55×d
    d_e = min(0.7 * d_weld - 1.5 * t_deck, 0.55 * d_weld)
    d_e = max(d_e, 0)  # Cannot be negative
    
    steps.append(CalculationStep(
        description="Effective weld diameter",
        formula="d_e = min(0.7d - 1.5t, 0.55d)",
        values=f"d_e = min(0.7×{d_weld} - 1.5×{t_deck}, 0.55×{d_weld})",
        result=d_e,
        unit="mm",
        code_ref="SDI DDM04 §4.2.1"
    ))
    
    # Weld shear area
    A_weld = math.pi * d_e**2 / 4
    
    # Nominal capacity - minimum of:
    # 1. Weld shear: Qf = 0.75 × Fu_weld × A_weld
    # 2. Sheet tearing: Qf = 2.2 × t × d_e × Fu_deck
    
    Q_weld_shear = 0.75 * fu_weld * A_weld / 1000  # kN
    Q_sheet_tear = 2.2 * t_deck * d_e * fu_deck / 1000  # kN
    
    Qn = min(Q_weld_shear, Q_sheet_tear)
    
    steps.append(CalculationStep(
        description="Weld shear capacity",
        formula="Qn_weld = 0.75 × Fu_weld × π×d_e²/4",
        values=f"Qn = 0.75×{fu_weld}×π×{d_e:.1f}²/4",
        result=Q_weld_shear,
        unit="kN",
        code_ref="SDI DDM04 §4.2.2"
    ))
    
    steps.append(CalculationStep(
        description="Sheet tearing capacity",
        formula="Qn_tear = 2.2 × t × d_e × Fu_deck",
        values=f"Qn = 2.2×{t_deck}×{d_e:.1f}×{fu_deck}",
        result=Q_sheet_tear,
        unit="kN",
        code_ref="SDI DDM04 §4.2.3"
    ))
    
    # Apply resistance/safety factor
    if method == DesignMethod.LRFD:
        phi = 0.60  # For welded connections
        Qf = phi * Qn
        steps.append(CalculationStep(
            description="Design capacity (LRFD)",
            formula="φQn = 0.60 × Qn",
            values=f"φQn = 0.60×{Qn:.3f}",
            result=Qf,
            unit="kN",
            code_ref="SDI DDM04 §4.2"
        ))
    else:
        omega = 2.50
        Qf = Qn / omega
        steps.append(CalculationStep(
            description="Allowable capacity (ASD)",
            formula="Qn/Ω = Qn/2.50",
            values=f"Qn/Ω = {Qn:.3f}/2.50",
            result=Qf,
            unit="kN",
            code_ref="SDI DDM04 §4.2"
        ))
    
    return Qf, steps


def calc_screw_capacity(
    d_screw: float,
    t_deck: float,
    t_support: float,
    fu_deck: float,
    fu_screw: float = 450,
    method: DesignMethod = DesignMethod.LRFD
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate screw connection shear capacity per SDI DDM04.
    
    Args:
        d_screw: Screw diameter (mm)
        t_deck: Deck design thickness (mm)
        t_support: Support thickness (mm), use large value for concrete
        fu_deck: Deck tensile strength (MPa)
        fu_screw: Screw tensile strength (MPa)
        method: LRFD or ASD
        
    Returns:
        (Qf in kN, calculation steps)
        
    Reference:
        SDI DDM04 Section 4.3
        AISI S100-16 §J4
    """
    steps = []
    
    t1 = t_deck  # Sheet in contact with screw head
    t2 = t_support
    
    # Thickness ratio
    t_ratio = t2 / t1 if t1 > 0 else 10
    
    steps.append(CalculationStep(
        description="Thickness ratio",
        formula="t2/t1",
        values=f"{t2}/{t1}",
        result=t_ratio,
        unit="-",
        code_ref="SDI DDM04 §4.3"
    ))
    
    # Nominal shear capacity per AISI S100-16 §J4.3
    # For t2/t1 ≥ 2.5: Pns = 4.2×(t1³×d)^0.5 × Fu1
    # For t2/t1 ≤ 1.0: Pns = min of tilting and bearing
    
    if t_ratio >= 2.5:
        Pns = 4.2 * math.sqrt(t1**3 * d_screw) * fu_deck / 1000  # kN
        gov = "t2/t1 ≥ 2.5"
    elif t_ratio <= 1.0:
        Pns_tilt = 4.2 * math.sqrt(t1**3 * d_screw) * fu_deck / 1000
        Pns_bear = 2.7 * t1 * d_screw * fu_deck / 1000
        Pns = min(Pns_tilt, Pns_bear)
        gov = "t2/t1 ≤ 1.0"
    else:
        # Interpolate
        Pns_low = 2.7 * t1 * d_screw * fu_deck / 1000
        Pns_high = 4.2 * math.sqrt(t1**3 * d_screw) * fu_deck / 1000
        Pns = Pns_low + (Pns_high - Pns_low) * (t_ratio - 1.0) / 1.5
        gov = "interpolated"
    
    steps.append(CalculationStep(
        description="Nominal screw capacity",
        formula="Pns per AISI S100-16 §J4.3",
        values=f"Pns ({gov})",
        result=Pns,
        unit="kN",
        code_ref="AISI S100-16 §J4.3"
    ))
    
    # Apply resistance/safety factor
    if method == DesignMethod.LRFD:
        phi = 0.50  # For screw connections
        Qf = phi * Pns
        steps.append(CalculationStep(
            description="Design capacity (LRFD)",
            formula="φPns = 0.50 × Pns",
            values=f"φPns = 0.50×{Pns:.3f}",
            result=Qf,
            unit="kN",
            code_ref="AISI S100-16 §J4"
        ))
    else:
        omega = 3.00
        Qf = Pns / omega
        steps.append(CalculationStep(
            description="Allowable capacity (ASD)",
            formula="Pns/Ω = Pns/3.00",
            values=f"Pns/Ω = {Pns:.3f}/3.00",
            result=Qf,
            unit="kN",
            code_ref="AISI S100-16 §J4"
        ))
    
    return Qf, steps


def calc_paf_capacity(
    d_paf: float,
    t_deck: float,
    fu_deck: float,
    embedment: float,
    method: DesignMethod = DesignMethod.LRFD
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate powder-actuated fastener (PAF) shear capacity.
    
    Args:
        d_paf: PAF shank diameter (mm)
        t_deck: Deck design thickness (mm)
        fu_deck: Deck tensile strength (MPa)
        embedment: Embedment into concrete/steel (mm)
        method: LRFD or ASD
        
    Returns:
        (Qf in kN, calculation steps)
        
    Reference:
        SDI DDM04 Section 4.4
        ICC-ES ESR reports for specific PAF products
    """
    steps = []
    
    # PAF capacity is typically provided by manufacturer
    # Generic formula based on AISI provisions
    
    # Sheet bearing/tilting limit
    Pns_sheet = 2.7 * t_deck * d_paf * fu_deck / 1000  # kN
    
    # Embedment limit (simplified)
    # Assumes adequate embedment in concrete or steel support
    Pns_embed = 0.8 * math.pi * d_paf * embedment * 20 / 1000  # kN, assuming ~20 MPa bond
    
    Pns = min(Pns_sheet, Pns_embed)
    
    steps.append(CalculationStep(
        description="Sheet bearing capacity",
        formula="Pns_sheet = 2.7 × t × d × Fu",
        values=f"Pns = 2.7×{t_deck}×{d_paf}×{fu_deck}",
        result=Pns_sheet,
        unit="kN",
        code_ref="SDI DDM04 §4.4"
    ))
    
    steps.append(CalculationStep(
        description="Nominal PAF capacity",
        formula="Pns = min(sheet, embedment)",
        values=f"Pns = min({Pns_sheet:.3f}, {Pns_embed:.3f})",
        result=Pns,
        unit="kN",
        code_ref="SDI DDM04 §4.4"
    ))
    
    # Apply resistance/safety factor
    if method == DesignMethod.LRFD:
        phi = 0.50
        Qf = phi * Pns
    else:
        omega = 3.00
        Qf = Pns / omega
    
    steps.append(CalculationStep(
        description=f"Design capacity ({method.value})",
        formula=f"φPns = {0.50 if method == DesignMethod.LRFD else 1/3.0:.2f} × Pns",
        values=f"Qf = {Qf:.3f}",
        result=Qf,
        unit="kN",
        code_ref="SDI DDM04 §4.4"
    ))
    
    return Qf, steps


def calc_sidelap_capacity(
    fastener: SideLapFastener,
    t_deck: float,
    fu_deck: float,
    method: DesignMethod = DesignMethod.LRFD
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate side-lap connection capacity per SDI DDM04.
    
    Args:
        fastener: Side-lap fastener properties
        t_deck: Deck design thickness (mm)
        fu_deck: Deck tensile strength (MPa)
        method: LRFD or ASD
        
    Returns:
        (Qs in kN per fastener, calculation steps)
        
    Reference:
        SDI DDM04 Section 4.5
    """
    steps = []
    
    if fastener.fastener_type == SideLapType.NONE:
        return 0, [CalculationStep(
            description="No side-lap connection",
            formula="-",
            values="-",
            result=0,
            unit="kN",
            code_ref="SDI DDM04 §4.5"
        )]
    
    if fastener.fastener_type == SideLapType.SCREW:
        # Screw side-lap: sheet-to-sheet connection
        # Both sheets are same thickness
        d = fastener.diameter
        
        # Tilting/bearing capacity
        Pns = 4.2 * math.sqrt((2*t_deck)**3 * d) * fu_deck / 1000  # kN
        
        steps.append(CalculationStep(
            description="Side-lap screw capacity",
            formula="Pns = 4.2×√((2t)³×d)×Fu",
            values=f"Pns = 4.2×√((2×{t_deck})³×{d})×{fu_deck}",
            result=Pns,
            unit="kN",
            code_ref="SDI DDM04 §4.5.1"
        ))
        
        if method == DesignMethod.LRFD:
            Qs = 0.50 * Pns
        else:
            Qs = Pns / 3.00
            
    elif fastener.fastener_type == SideLapType.BUTTON_PUNCH:
        # Button punch: typically 50-70% of screw capacity
        d_equiv = 6.35  # Equivalent diameter (mm)
        Pns = 0.6 * 4.2 * math.sqrt((2*t_deck)**3 * d_equiv) * fu_deck / 1000
        
        steps.append(CalculationStep(
            description="Button punch capacity",
            formula="Pns = 0.6 × screw equivalent",
            values=f"Pns = 0.6 × screw",
            result=Pns,
            unit="kN",
            code_ref="SDI DDM04 §4.5.2"
        ))
        
        if method == DesignMethod.LRFD:
            Qs = 0.50 * Pns
        else:
            Qs = Pns / 3.00
            
    else:  # Weld
        # Side-lap weld
        d_weld = 12.7  # Typical 1/2" weld
        Qs, weld_steps = calc_arc_spot_weld_capacity(
            d_weld, t_deck, fu_deck, method=method
        )
        steps.extend(weld_steps)
        return Qs, steps
    
    steps.append(CalculationStep(
        description=f"Side-lap design capacity ({method.value})",
        formula="Qs",
        values=f"Qs = {Qs:.3f}",
        result=Qs,
        unit="kN",
        code_ref="SDI DDM04 §4.5"
    ))
    
    return Qs, steps


# =============================================================================
# DIAPHRAGM SHEAR STRENGTH - SDI DDM04 Chapter 5
# =============================================================================

def calc_diaphragm_shear_strength(
    deck: DeckProfile,
    geometry: DiaphragmGeometry,
    support_fastener: SupportFastener,
    sidelap_fastener: SideLapFastener,
    method: DesignMethod = DesignMethod.LRFD
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate diaphragm nominal shear strength Sn per SDI DDM04.
    
    The diaphragm strength is governed by:
    1. Fastener capacity at supports
    2. Fastener capacity at side-laps
    3. Deck panel shear buckling
    
    Args:
        deck: Deck profile properties
        geometry: Diaphragm geometry
        support_fastener: Support connection fasteners
        sidelap_fastener: Side-lap fasteners
        method: LRFD or ASD
        
    Returns:
        (Sn in kN/m, calculation steps)
        
    Reference:
        SDI DDM04 Section 5.2
    """
    steps = []
    
    # Calculate individual fastener capacities
    if support_fastener.fastener_type == FastenerType.ARC_SPOT_WELD:
        Qf, qf_steps = calc_arc_spot_weld_capacity(
            support_fastener.diameter, deck.t_design, deck.fu, method=method
        )
    elif support_fastener.fastener_type == FastenerType.SCREW:
        Qf, qf_steps = calc_screw_capacity(
            support_fastener.diameter, deck.t_design, 10.0, deck.fu, method=method
        )
    else:  # PAF
        Qf, qf_steps = calc_paf_capacity(
            support_fastener.diameter, deck.t_design, deck.fu,
            support_fastener.embedment, method=method
        )
    
    steps.append(CalculationStep(
        description="Support fastener capacity",
        formula="Qf per fastener",
        values=f"Type: {support_fastener.fastener_type.value}",
        result=Qf,
        unit="kN",
        code_ref="SDI DDM04 §4"
    ))
    
    # Side-lap capacity
    Qs, qs_steps = calc_sidelap_capacity(
        sidelap_fastener, deck.t_design, deck.fu, method=method
    )
    
    steps.append(CalculationStep(
        description="Side-lap fastener capacity",
        formula="Qs per fastener",
        values=f"Type: {sidelap_fastener.fastener_type.value}",
        result=Qs,
        unit="kN",
        code_ref="SDI DDM04 §4.5"
    ))
    
    # Diaphragm shear strength calculation per SDI DDM04 Eq. 5.2-1
    # Sn = (Qf × n_f + Qs × n_s) / L_panel
    
    # Number of support fasteners per panel width
    n_ribs_per_panel = deck.cover_width / deck.pitch
    n_f = support_fastener.n_per_rib * n_ribs_per_panel * 2  # Both ends
    
    steps.append(CalculationStep(
        description="Support fasteners per panel",
        formula="n_f = n_per_rib × (cover/pitch) × 2",
        values=f"n_f = {support_fastener.n_per_rib}×({deck.cover_width}/{deck.pitch})×2",
        result=n_f,
        unit="fasteners",
        code_ref="SDI DDM04 §5.2"
    ))
    
    # Number of side-lap fasteners per span
    if sidelap_fastener.fastener_type != SideLapType.NONE:
        n_s = geometry.deck_span / sidelap_fastener.spacing
    else:
        n_s = 0
    
    steps.append(CalculationStep(
        description="Side-lap fasteners per span",
        formula="n_s = span / spacing",
        values=f"n_s = {geometry.deck_span}/{sidelap_fastener.spacing if sidelap_fastener.spacing > 0 else 1}",
        result=n_s,
        unit="fasteners",
        code_ref="SDI DDM04 §5.2"
    ))
    
    # Panel length (deck span)
    L_panel = geometry.deck_span
    
    # Nominal shear strength per unit length
    # Using simplified DDM04 approach
    Sn_fasteners = (Qf * n_f + Qs * n_s * 2) / (L_panel / 1000)  # kN/m
    
    steps.append(CalculationStep(
        description="Fastener-controlled strength",
        formula="Sn = (Qf×n_f + Qs×n_s×2) / L",
        values=f"Sn = ({Qf:.3f}×{n_f:.0f} + {Qs:.3f}×{n_s:.0f}×2) / {L_panel/1000:.2f}",
        result=Sn_fasteners,
        unit="kN/m",
        code_ref="SDI DDM04 Eq. 5.2-1"
    ))
    
    # Check deck shear buckling (simplified per SDI DDM04 §5.3)
    # For profiled steel deck, shear buckling is typically not critical
    # τcr = 0.6 × Fy for compact sections
    # Sn_buckling = τcr × t × (effective shear path)
    
    # Effective shear stress capacity
    tau_cr = 0.6 * deck.fy  # MPa (shear yield)
    
    # Shear capacity per unit width
    # Using simplified approach: Sn = τ × t × (panel factor)
    panel_factor = 0.8  # Account for profile geometry
    Sn_buckling = tau_cr * deck.t_design * panel_factor  # N/mm = kN/m
    
    steps.append(CalculationStep(
        description="Deck shear buckling strength",
        formula="Sn_buckle = 0.6×Fy×t×0.8",
        values=f"Sn = 0.6×{deck.fy}×{deck.t_design}×0.8",
        result=Sn_buckling,
        unit="kN/m",
        code_ref="SDI DDM04 §5.3"
    ))
    
    # Governing strength
    Sn = min(Sn_fasteners, Sn_buckling)
    gov = "fasteners" if Sn == Sn_fasteners else "buckling"
    
    steps.append(CalculationStep(
        description="Nominal diaphragm shear strength",
        formula="Sn = min(Sn_fasteners, Sn_buckling)",
        values=f"Sn = min({Sn_fasteners:.2f}, {Sn_buckling:.2f}) - {gov}",
        result=Sn,
        unit="kN/m",
        code_ref="SDI DDM04 §5.2"
    ))
    
    return Sn, steps


# =============================================================================
# DIAPHRAGM STIFFNESS - SDI DDM04 Chapter 6
# =============================================================================

def calc_diaphragm_stiffness(
    deck: DeckProfile,
    geometry: DiaphragmGeometry,
    support_fastener: SupportFastener,
    sidelap_fastener: SideLapFastener
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate diaphragm shear stiffness G' per SDI DDM04.
    
    G' is used for:
    - Flexible/rigid diaphragm classification
    - Deflection calculations
    - Load distribution analysis
    
    Args:
        deck: Deck profile properties
        geometry: Diaphragm geometry
        support_fastener: Support connection fasteners
        sidelap_fastener: Side-lap fasteners
        
    Returns:
        (G' in kN/mm, calculation steps)
        
    Reference:
        SDI DDM04 Section 6.2
    """
    steps = []
    
    # Shear stiffness components:
    # 1/G' = 1/G'_deck + 1/G'_fasteners + 1/G'_sidelap
    
    # Deck panel shear stiffness
    E = 200000  # Steel modulus (MPa)
    G = E / 2.6  # Shear modulus (MPa)
    t = deck.t_design
    
    # Simplified deck stiffness
    # G'_deck = G × t / (K × s) where K is profile factor, s is span
    K_profile = 1 + 0.5 * (deck.hr / deck.pitch)  # Profile factor
    G_deck = G * t / (K_profile * geometry.deck_span)  # N/mm per mm width
    G_deck_kN = G_deck * 1000  # kN/mm per m width
    
    steps.append(CalculationStep(
        description="Deck panel stiffness",
        formula="G'_deck = G×t / (K×s)",
        values=f"G'_deck = {G}×{t} / ({K_profile:.2f}×{geometry.deck_span})",
        result=G_deck_kN,
        unit="kN/mm/m",
        code_ref="SDI DDM04 §6.2.1"
    ))
    
    # Fastener slip stiffness (support connections)
    # Sf = slip per fastener under unit load
    # Typical values: welds ~0.05mm/kN, screws ~0.15mm/kN, PAF ~0.10mm/kN
    if support_fastener.fastener_type == FastenerType.ARC_SPOT_WELD:
        Sf = 0.05  # mm/kN
    elif support_fastener.fastener_type == FastenerType.SCREW:
        Sf = 0.15  # mm/kN
    else:
        Sf = 0.10  # mm/kN
    
    n_ribs = deck.cover_width / deck.pitch
    n_f = support_fastener.n_per_rib * n_ribs
    
    # Stiffness contribution from support fasteners
    G_fastener = 1 / (Sf * geometry.deck_span / (n_f * 1000))  # kN/mm per m
    
    steps.append(CalculationStep(
        description="Support fastener stiffness",
        formula="G'_f = n_f / (Sf × L)",
        values=f"G'_f = {n_f:.0f} / ({Sf}×{geometry.deck_span})",
        result=G_fastener,
        unit="kN/mm/m",
        code_ref="SDI DDM04 §6.2.2"
    ))
    
    # Side-lap stiffness
    if sidelap_fastener.fastener_type != SideLapType.NONE:
        Ss = 0.20  # Typical side-lap slip (mm/kN)
        n_s = geometry.deck_span / sidelap_fastener.spacing
        n_panels = geometry.width / deck.cover_width
        G_sidelap = n_panels / (Ss * geometry.deck_span / (n_s * 1000))
    else:
        G_sidelap = float('inf')
        n_s = 0
    
    steps.append(CalculationStep(
        description="Side-lap stiffness",
        formula="G'_s = n_panels / (Ss × L / n_s)",
        values=f"G'_s based on {n_s:.0f} fasteners",
        result=G_sidelap if G_sidelap != float('inf') else 0,
        unit="kN/mm/m",
        code_ref="SDI DDM04 §6.2.3"
    ))
    
    # Combined stiffness (series combination)
    if G_sidelap == float('inf'):
        G_prime = 1 / (1/G_deck_kN + 1/G_fastener)
    else:
        G_prime = 1 / (1/G_deck_kN + 1/G_fastener + 1/G_sidelap)
    
    steps.append(CalculationStep(
        description="Combined diaphragm stiffness",
        formula="1/G' = 1/G'_deck + 1/G'_f + 1/G'_s",
        values=f"G' = {G_prime:.3f}",
        result=G_prime,
        unit="kN/mm/m",
        code_ref="SDI DDM04 §6.2"
    ))
    
    return G_prime, steps


def classify_diaphragm(
    G_prime: float,
    geometry: DiaphragmGeometry,
    w_load: float
) -> Tuple[DiaphragmType, float, List[CalculationStep]]:
    """
    Classify diaphragm as flexible, rigid, or semi-rigid per ASCE 7-22.
    
    Args:
        G_prime: Diaphragm stiffness (kN/mm/m)
        geometry: Diaphragm geometry
        w_load: Lateral load intensity (kN/m)
        
    Returns:
        (classification, deflection in mm, calculation steps)
        
    Reference:
        ASCE 7-22 Section 12.3.1
    """
    steps = []
    
    # Mid-span deflection for uniformly loaded diaphragm
    # δ = w × L² / (8 × G' × B)
    L = geometry.length  # mm
    B = geometry.width   # mm
    
    if G_prime > 0 and B > 0:
        delta = w_load * (L/1000)**2 / (8 * G_prime * (B/1000))  # mm
    else:
        delta = float('inf')
    
    steps.append(CalculationStep(
        description="Diaphragm mid-span deflection",
        formula="δ = w×L² / (8×G'×B)",
        values=f"δ = {w_load}×{L/1000:.1f}² / (8×{G_prime:.3f}×{B/1000:.1f})",
        result=delta,
        unit="mm",
        code_ref="SDI DDM04 §6.3"
    ))
    
    # Story drift (assuming typical story height of 4000mm)
    story_height = 4000  # mm
    story_drift = delta / story_height
    
    # ASCE 7-22 classification
    # Flexible: δ_diaphragm > 2 × δ_story_drift
    # Rigid: δ_diaphragm < 0.5 × δ_story_drift
    # Semi-rigid: between
    
    # Simplified approach: use deflection limits
    L_ratio = delta / L * 1000  # deflection / span ratio
    
    if L_ratio > 1/240:  # Greater than L/240
        classification = DiaphragmType.FLEXIBLE
    elif L_ratio < 1/1000:  # Less than L/1000
        classification = DiaphragmType.RIGID
    else:
        classification = DiaphragmType.SEMI_RIGID
    
    steps.append(CalculationStep(
        description="Diaphragm classification",
        formula="δ/L ratio check",
        values=f"δ/L = {L_ratio:.6f} ({classification.value})",
        result=L_ratio * 1000,
        unit="×10⁻³",
        code_ref="ASCE 7-22 §12.3.1"
    ))
    
    return classification, delta, steps


# =============================================================================
# CHORD AND COLLECTOR FORCES - SDI DDM04 Chapter 7
# =============================================================================

def calc_chord_force(
    geometry: DiaphragmGeometry,
    w_load: float,
    method: DesignMethod = DesignMethod.LRFD
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate diaphragm chord force per SDI DDM04.
    
    Chord force = M_diaphragm / d
    where M = w×L²/8 for simple span
    
    Args:
        geometry: Diaphragm geometry
        w_load: Factored lateral load (kN/m)
        method: LRFD or ASD
        
    Returns:
        (T_chord in kN, calculation steps)
        
    Reference:
        SDI DDM04 Section 7.2
    """
    steps = []
    
    L = geometry.length / 1000  # m
    B = geometry.width / 1000   # m (chord arm)
    
    # Maximum moment at mid-span
    M_max = w_load * L**2 / 8  # kN·m
    
    steps.append(CalculationStep(
        description="Maximum diaphragm moment",
        formula="M = w×L²/8",
        values=f"M = {w_load}×{L:.1f}²/8",
        result=M_max,
        unit="kN·m",
        code_ref="SDI DDM04 §7.2"
    ))
    
    # Chord force
    T_chord = M_max / B  # kN
    
    steps.append(CalculationStep(
        description="Chord tension/compression",
        formula="T = M / B",
        values=f"T = {M_max:.1f} / {B:.1f}",
        result=T_chord,
        unit="kN",
        code_ref="SDI DDM04 §7.2"
    ))
    
    return T_chord, steps


def calc_collector_force(
    geometry: DiaphragmGeometry,
    w_load: float,
    collector_length: float,  # Length tributary to collector (mm)
    method: DesignMethod = DesignMethod.LRFD
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate collector (drag strut) force.
    
    Args:
        geometry: Diaphragm geometry
        w_load: Factored lateral load (kN/m)
        collector_length: Tributary length to collector (mm)
        method: LRFD or ASD
        
    Returns:
        (F_collector in kN, calculation steps)
        
    Reference:
        SDI DDM04 Section 7.3
    """
    steps = []
    
    # Collector force = unit shear × tributary length
    V_unit = w_load  # kN/m (unit shear at support)
    F_collector = V_unit * (collector_length / 1000)  # kN
    
    steps.append(CalculationStep(
        description="Collector force",
        formula="F = v × L_trib",
        values=f"F = {V_unit:.2f} × {collector_length/1000:.1f}",
        result=F_collector,
        unit="kN",
        code_ref="SDI DDM04 §7.3"
    ))
    
    return F_collector, steps


# =============================================================================
# COMPLETE DIAPHRAGM DESIGN
# =============================================================================

def design_diaphragm(
    deck: DeckProfile,
    geometry: DiaphragmGeometry,
    support_fastener: SupportFastener,
    sidelap_fastener: SideLapFastener,
    loads: DiaphragmLoads,
    method: DesignMethod = DesignMethod.LRFD
) -> Dict[str, DiaphragmResult]:
    """
    Complete diaphragm design per SDI DDM04.
    
    Args:
        deck: Deck profile properties
        geometry: Diaphragm geometry
        support_fastener: Support connection fasteners
        sidelap_fastener: Side-lap fasteners
        loads: Diaphragm loading
        method: LRFD or ASD
        
    Returns:
        Dictionary of DiaphragmResult objects
    """
    results = {}
    
    # Load factors
    if method == DesignMethod.LRFD:
        load_factor = 1.0  # Loads already factored
    else:
        load_factor = 1.0
    
    w_design = loads.w_total * load_factor
    
    # =========================
    # 1. SHEAR STRENGTH CHECK
    # =========================
    Sn, shear_steps = calc_diaphragm_shear_strength(
        deck, geometry, support_fastener, sidelap_fastener, method
    )
    
    # Shear demand (kN/m)
    V_demand = w_design * (geometry.length / 1000) / 2  # Reaction at support
    v_demand = V_demand / (geometry.width / 1000)  # kN/m
    
    shear_steps.insert(0, CalculationStep(
        description="Shear demand",
        formula="v = V / B = (w×L/2) / B",
        values=f"v = ({w_design}×{geometry.length/1000:.1f}/2) / {geometry.width/1000:.1f}",
        result=v_demand,
        unit="kN/m",
        code_ref="SDI DDM04 §5.1"
    ))
    
    ratio_shear = v_demand / Sn if Sn > 0 else float('inf')
    
    results['shear_strength'] = DiaphragmResult(
        check_name="Diaphragm Shear",
        demand=v_demand,
        capacity=Sn,
        ratio=ratio_shear,
        status="PASS" if ratio_shear <= 1.0 else "FAIL",
        code_ref="SDI DDM04 §5.2",
        steps=shear_steps
    )
    
    # =========================
    # 2. STIFFNESS & DEFLECTION
    # =========================
    G_prime, stiff_steps = calc_diaphragm_stiffness(
        deck, geometry, support_fastener, sidelap_fastener
    )
    
    classification, delta, class_steps = classify_diaphragm(
        G_prime, geometry, w_design
    )
    stiff_steps.extend(class_steps)
    
    # Deflection limit (typically L/240 to L/480)
    delta_limit = geometry.length / 360  # mm
    ratio_defl = delta / delta_limit if delta_limit > 0 else float('inf')
    
    results['deflection'] = DiaphragmResult(
        check_name="Deflection (L/360)",
        demand=delta,
        capacity=delta_limit,
        ratio=ratio_defl,
        status="PASS" if ratio_defl <= 1.0 else "FAIL",
        code_ref="SDI DDM04 §6.3",
        steps=stiff_steps
    )
    
    # =========================
    # 3. CHORD FORCE
    # =========================
    T_chord, chord_steps = calc_chord_force(geometry, w_design, method)
    
    # Chord capacity (assuming steel angle or beam)
    # Simplified: assume chord is adequate if designed separately
    T_chord_capacity = T_chord * 1.5  # Placeholder - user should verify
    ratio_chord = T_chord / T_chord_capacity
    
    results['chord_force'] = DiaphragmResult(
        check_name="Chord Force",
        demand=T_chord,
        capacity=T_chord_capacity,
        ratio=ratio_chord,
        status="INFO",  # Requires separate chord design
        code_ref="SDI DDM04 §7.2",
        steps=chord_steps
    )
    
    # =========================
    # 4. CLASSIFICATION
    # =========================
    results['classification'] = DiaphragmResult(
        check_name="Diaphragm Type",
        demand=0,
        capacity=0,
        ratio=0,
        status=classification.value.upper(),
        code_ref="ASCE 7-22 §12.3.1",
        steps=[CalculationStep(
            description="Diaphragm classification",
            formula="Based on stiffness analysis",
            values=classification.value,
            result=G_prime,
            unit="kN/mm/m",
            code_ref="ASCE 7-22 §12.3.1"
        )]
    )
    
    return results


def generate_diaphragm_summary(results: Dict[str, DiaphragmResult]) -> str:
    """Generate text summary of diaphragm design results."""
    lines = [
        "=" * 60,
        "DIAPHRAGM DESIGN SUMMARY - SDI DDM04",
        "=" * 60,
        ""
    ]
    
    # Check pass/fail (excluding INFO status)
    checks = [r for r in results.values() if r.status not in ["INFO", "FLEXIBLE", "RIGID", "SEMI_RIGID"]]
    all_pass = all(r.status == "PASS" for r in checks) if checks else True
    
    lines.append(f"Overall Status: {'✓ ALL CHECKS PASS' if all_pass else '✗ DESIGN FAILS'}")
    lines.append("")
    lines.append(f"{'Check':<25} {'Demand':>10} {'Capacity':>10} {'D/C':>8} {'Status':>10}")
    lines.append("-" * 70)
    
    for name, result in results.items():
        if result.status in ["FLEXIBLE", "RIGID", "SEMI_RIGID"]:
            lines.append(f"{result.check_name:<25} {'-':>10} {'-':>10} {'-':>8} {result.status:>10}")
        elif result.status == "INFO":
            lines.append(f"{result.check_name:<25} {result.demand:>10.2f} {'verify':>10} {'-':>8} {result.status:>10}")
        else:
            status_sym = "✓" if result.status == "PASS" else "✗"
            lines.append(
                f"{result.check_name:<25} {result.demand:>10.2f} {result.capacity:>10.2f} "
                f"{result.ratio:>8.3f} {status_sym:>10}"
            )
    
    lines.append("-" * 70)
    
    return "\n".join(lines)


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing Diaphragm Design Module")
    print("=" * 50)
    
    # Test deck profile
    deck = DeckProfile(
        hr=50.8,
        pitch=152.4,
        t=0.9,
        fy=230,
        fu=310,
        cover_width=914
    )
    
    # Test geometry
    geom = DiaphragmGeometry(
        length=30000,      # 30m diaphragm length
        width=15000,       # 15m width
        deck_span=2400,    # 2.4m deck span
        orientation=DeckOrientation.PERPENDICULAR,
        n_spans=3
    )
    
    # Support fasteners - arc spot welds
    support = SupportFastener(
        fastener_type=FastenerType.ARC_SPOT_WELD,
        diameter=19,       # 3/4" weld
        n_per_rib=1,
        edge_pattern="36/36"
    )
    
    # Side-lap fasteners - screws
    sidelap = SideLapFastener(
        fastener_type=SideLapType.SCREW,
        diameter=4.8,      # #10 screw
        spacing=305        # 12" spacing
    )
    
    # Loads
    loads = DiaphragmLoads(
        w_wind=5.0,        # kN/m wind load
        w_seismic=8.0      # kN/m seismic load (governs)
    )
    
    # Run design
    results = design_diaphragm(
        deck=deck,
        geometry=geom,
        support_fastener=support,
        sidelap_fastener=sidelap,
        loads=loads,
        method=DesignMethod.LRFD
    )
    
    # Print summary
    print(generate_diaphragm_summary(results))
