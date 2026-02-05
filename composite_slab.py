"""
Composite Slab Design Module - ACI 318-19
==========================================
Phase 4 - CompositeBeam Pro

Design of composite concrete slab on metal deck per ACI 318-19.
Integrates with Phase 2 metal deck module for construction stage.

Design Standards:
- ACI 318-19: Building Code Requirements for Structural Concrete
- SDI C-2017: Standard for Composite Steel Floor Deck-Slabs
- ASCE 7-22: Minimum Design Loads

Author: CompositeBeam Pro
Version: 1.0
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum


class SpanCondition(Enum):
    """Slab span condition"""
    SIMPLE = "simple"
    TWO_SPAN = "two_span"
    THREE_PLUS = "three_plus"
    CANTILEVER = "cantilever"


class FireRating(Enum):
    """Fire resistance rating"""
    NONE = "none"
    ONE_HOUR = "1_hour"
    ONE_HALF_HOUR = "1.5_hour"  
    TWO_HOUR = "2_hour"
    THREE_HOUR = "3_hour"


@dataclass
class ConcreteProperties:
    """Concrete material properties per ACI 318-19"""
    fc: float                    # Specified compressive strength (MPa)
    wc: float = 2400             # Unit weight (kg/m³), normal weight default
    
    @property
    def is_lightweight(self) -> bool:
        return self.wc < 2160
    
    @property
    def lambda_factor(self) -> float:
        """Lightweight concrete factor λ per ACI 318-19 §19.2.4"""
        if self.wc >= 2160:
            return 1.0  # Normal weight
        elif self.wc <= 1440:
            return 0.75  # All-lightweight
        else:
            return 0.85  # Sand-lightweight
    
    @property
    def Ec(self) -> float:
        """Modulus of elasticity per ACI 318-19 §19.2.2 (MPa)"""
        # Ec = wc^1.5 × 0.043 × √f'c  (for wc in kg/m³, fc in MPa)
        return (self.wc ** 1.5) * 0.043 * math.sqrt(self.fc)
    
    @property
    def fr(self) -> float:
        """Modulus of rupture per ACI 318-19 §19.2.3 (MPa)"""
        return 0.62 * self.lambda_factor * math.sqrt(self.fc)
    
    @property
    def beta1(self) -> float:
        """Stress block factor β1 per ACI 318-19 §22.2.2.4.3"""
        if self.fc <= 28:
            return 0.85
        elif self.fc >= 55:
            return 0.65
        else:
            return 0.85 - 0.05 * (self.fc - 28) / 7


@dataclass
class SlabGeometry:
    """Composite slab geometry"""
    tc: float                    # Total slab thickness (mm)
    hr: float                    # Deck rib height (mm)
    wr_top: float               # Rib opening at top (mm)
    wr_bot: float               # Rib width at bottom (mm)
    pitch: float                # Rib spacing/pitch (mm)
    span: float                 # Clear span (mm)
    span_condition: SpanCondition = SpanCondition.SIMPLE
    
    @property
    def tc_above_deck(self) -> float:
        """Concrete thickness above deck (mm)"""
        return self.tc - self.hr
    
    @property
    def avg_depth(self) -> float:
        """Average slab depth for weight calculation (mm)"""
        # Account for ribs
        rib_area = 0.5 * (self.wr_top + self.wr_bot) * self.hr
        rib_volume_ratio = rib_area / (self.pitch * self.hr)
        return self.tc_above_deck + self.hr * rib_volume_ratio
    
    @property
    def effective_depth(self) -> float:
        """Effective depth d for flexure (mm) - from top to tension reinforcement"""
        # For composite slab, tension zone is typically at deck level
        # d = tc - cover - bar/2, but for deck slab, d ≈ tc - hr/2
        return self.tc - self.hr / 2
    
    def get_moment_coefficients(self) -> Tuple[float, float]:
        """
        Get moment coefficients per ACI 318-19 §6.5 (simplified method)
        
        Returns:
            (positive_coef, negative_coef) for wL²
        """
        if self.span_condition == SpanCondition.SIMPLE:
            return (1/8, 0)
        elif self.span_condition == SpanCondition.TWO_SPAN:
            return (1/14, 1/9)  # End span
        elif self.span_condition == SpanCondition.THREE_PLUS:
            return (1/14, 1/10)  # Interior span
        else:  # Cantilever
            return (0, 1/2)


@dataclass
class ReinforcementProperties:
    """Reinforcement properties"""
    fy: float                    # Yield strength (MPa)
    As_provided: float = 0       # Area provided (mm²/m)
    bar_size: str = "WWF"        # Bar designation
    spacing: float = 0           # Spacing (mm)
    cover_top: float = 20        # Top cover (mm)
    cover_bot: float = 20        # Bottom cover (mm)
    
    @property
    def Es(self) -> float:
        """Steel modulus of elasticity (MPa)"""
        return 200000


@dataclass
class DeckContribution:
    """Metal deck contribution to composite section"""
    Ag_deck: float              # Deck gross area (mm²/m)
    Ig_deck: float              # Deck moment of inertia (mm⁴/m)
    Fy_deck: float              # Deck yield strength (MPa)
    t_deck: float               # Deck thickness (mm)
    
    @property
    def As_deck(self) -> float:
        """Deck area acting as tension reinforcement (mm²/m)"""
        return self.Ag_deck
    
    @property
    def Mn_deck(self) -> float:
        """Deck contribution to moment capacity (kN·m/m)"""
        # Simplified - deck acts as tension reinforcement
        return self.Ag_deck * self.Fy_deck / 1e6


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
class DesignResult:
    """Design check result"""
    check_name: str
    demand: float
    capacity: float
    ratio: float
    status: str
    code_ref: str
    steps: List[CalculationStep] = field(default_factory=list)


# =============================================================================
# FLEXURAL DESIGN - ACI 318-19 Chapter 7 & 22
# =============================================================================

def calculate_flexural_capacity(
    geometry: SlabGeometry,
    concrete: ConcreteProperties,
    reinforcement: ReinforcementProperties,
    deck: Optional[DeckContribution] = None,
    width: float = 1000  # Per meter width
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate nominal flexural capacity Mn per ACI 318-19 §22.2
    
    Uses rectangular stress block method for positive moment.
    
    Args:
        geometry: Slab geometry
        concrete: Concrete properties
        reinforcement: Reinforcement properties  
        deck: Optional deck contribution
        width: Analysis width (mm), default 1000mm
        
    Returns:
        (Mn in kN·m/m, calculation steps)
        
    Reference:
        ACI 318-19 §22.2 - Flexural Strength
        SDI C-2017 §3.2 - Composite Section Strength
    """
    steps = []
    
    b = width  # mm
    d = geometry.effective_depth  # mm
    fc = concrete.fc  # MPa
    beta1 = concrete.beta1
    
    # Total tension reinforcement area
    As_rebar = reinforcement.As_provided  # mm²/m
    As_deck = deck.As_deck if deck else 0  # mm²/m
    
    # For composite slab, use deck Fy for deck contribution
    fy_rebar = reinforcement.fy
    fy_deck = deck.Fy_deck if deck else fy_rebar
    
    steps.append(CalculationStep(
        description="Effective depth",
        formula="d = tc - hr/2",
        values=f"d = {geometry.tc} - {geometry.hr}/2",
        result=d,
        unit="mm",
        code_ref="ACI 318-19 §22.2"
    ))
    
    # Calculate tension force
    if deck:
        # Combined reinforcement with different yield strengths
        T_rebar = As_rebar * fy_rebar  # N/m
        T_deck = As_deck * fy_deck     # N/m
        T_total = T_rebar + T_deck
        
        # Equivalent yield strength
        As_total = As_rebar + As_deck
        fy_eq = T_total / As_total if As_total > 0 else fy_deck
        
        steps.append(CalculationStep(
            description="Total tension force",
            formula="T = As_rebar×fy + As_deck×Fy_deck",
            values=f"T = {As_rebar:.0f}×{fy_rebar} + {As_deck:.0f}×{fy_deck}",
            result=T_total/1000,
            unit="kN/m",
            code_ref="ACI 318-19 §22.2.1"
        ))
    else:
        As_total = As_rebar
        fy_eq = fy_rebar
        T_total = As_total * fy_eq
    
    # Compression block depth
    # C = T, where C = 0.85×f'c×a×b
    if As_total > 0:
        a = T_total / (0.85 * fc * b)  # mm
    else:
        a = 0
    
    steps.append(CalculationStep(
        description="Compression block depth",
        formula="a = As×fy / (0.85×f'c×b)",
        values=f"a = {T_total:.0f} / (0.85×{fc}×{b})",
        result=a,
        unit="mm",
        code_ref="ACI 318-19 §22.2.2.4.1"
    ))
    
    # Check neutral axis depth
    c = a / beta1
    c_d_ratio = c / d if d > 0 else 0
    
    steps.append(CalculationStep(
        description="Neutral axis depth",
        formula="c = a/β₁",
        values=f"c = {a:.1f}/{beta1:.3f}",
        result=c,
        unit="mm",
        code_ref="ACI 318-19 §22.2.2.4.3"
    ))
    
    # Nominal moment capacity
    # Mn = As×fy×(d - a/2) for single layer
    if deck and As_rebar > 0:
        # Two layers of reinforcement at different levels
        d_deck = geometry.tc - geometry.hr / 2  # Deck at bottom
        d_rebar = geometry.tc - reinforcement.cover_top  # Top rebar
        
        Mn = (As_rebar * fy_rebar * (d_rebar - a/2) + 
              As_deck * fy_deck * (d_deck - a/2)) / 1e6  # kN·m/m
    else:
        Mn = As_total * fy_eq * (d - a/2) / 1e6  # kN·m/m
    
    steps.append(CalculationStep(
        description="Nominal moment capacity",
        formula="Mn = As×fy×(d - a/2)",
        values=f"Mn = {As_total:.0f}×{fy_eq:.0f}×({d:.1f} - {a:.1f}/2)",
        result=Mn,
        unit="kN·m/m",
        code_ref="ACI 318-19 §22.2.1"
    ))
    
    return Mn, steps


def calculate_negative_moment_capacity(
    geometry: SlabGeometry,
    concrete: ConcreteProperties,
    reinforcement: ReinforcementProperties,
    width: float = 1000
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate negative moment capacity (hogging) over supports.
    
    For negative moment, deck is in compression (ineffective).
    Only top reinforcement contributes.
    
    Args:
        geometry: Slab geometry
        concrete: Concrete properties
        reinforcement: Top reinforcement properties
        width: Analysis width (mm)
        
    Returns:
        (Mn_neg in kN·m/m, calculation steps)
        
    Reference:
        ACI 318-19 §22.2
    """
    steps = []
    
    b = width
    fc = concrete.fc
    beta1 = concrete.beta1
    
    # Effective depth for negative moment (from bottom of slab to top rebar)
    d_neg = geometry.tc - reinforcement.cover_top
    
    As = reinforcement.As_provided
    fy = reinforcement.fy
    
    steps.append(CalculationStep(
        description="Effective depth (negative)",
        formula="d = tc - cover_top",
        values=f"d = {geometry.tc} - {reinforcement.cover_top}",
        result=d_neg,
        unit="mm",
        code_ref="ACI 318-19 §22.2"
    ))
    
    # Compression block
    T = As * fy
    a = T / (0.85 * fc * b) if fc > 0 else 0
    
    steps.append(CalculationStep(
        description="Compression block depth",
        formula="a = As×fy / (0.85×f'c×b)",
        values=f"a = {As:.0f}×{fy} / (0.85×{fc}×{b})",
        result=a,
        unit="mm",
        code_ref="ACI 318-19 §22.2.2.4.1"
    ))
    
    # Nominal capacity
    Mn_neg = As * fy * (d_neg - a/2) / 1e6  # kN·m/m
    
    steps.append(CalculationStep(
        description="Negative moment capacity",
        formula="Mn⁻ = As×fy×(d - a/2)",
        values=f"Mn⁻ = {As:.0f}×{fy}×({d_neg:.1f} - {a:.1f}/2)",
        result=Mn_neg,
        unit="kN·m/m",
        code_ref="ACI 318-19 §22.2.1"
    ))
    
    return Mn_neg, steps


# =============================================================================
# SHEAR DESIGN - ACI 318-19 §7.6
# =============================================================================

def calculate_shear_capacity(
    geometry: SlabGeometry,
    concrete: ConcreteProperties,
    width: float = 1000
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate one-way shear capacity Vc per ACI 318-19 §22.5
    
    Args:
        geometry: Slab geometry
        concrete: Concrete properties
        width: Analysis width (mm)
        
    Returns:
        (Vc in kN/m, calculation steps)
        
    Reference:
        ACI 318-19 §22.5.5.1 - Vc for members without shear reinforcement
    """
    steps = []
    
    b = width  # mm
    d = geometry.effective_depth  # mm
    fc = concrete.fc  # MPa
    lambda_c = concrete.lambda_factor
    
    # Vc = 0.17×λ×√f'c×b×d  per ACI 318-19 §22.5.5.1
    Vc = 0.17 * lambda_c * math.sqrt(fc) * b * d / 1000  # kN/m
    
    steps.append(CalculationStep(
        description="Concrete shear strength",
        formula="Vc = 0.17×λ×√f'c×b×d",
        values=f"Vc = 0.17×{lambda_c}×√{fc}×{b}×{d}",
        result=Vc,
        unit="kN/m",
        code_ref="ACI 318-19 §22.5.5.1"
    ))
    
    return Vc, steps


def calculate_punching_shear(
    geometry: SlabGeometry,
    concrete: ConcreteProperties,
    P_conc: float,  # Concentrated load (kN)
    load_area: Tuple[float, float] = (100, 100)  # Load area dimensions (mm)
) -> Tuple[float, float, List[CalculationStep]]:
    """
    Calculate punching shear capacity at concentrated load.
    
    Args:
        geometry: Slab geometry
        concrete: Concrete properties
        P_conc: Concentrated load (kN)
        load_area: Load dimensions (length, width) in mm
        
    Returns:
        (Vu, Vc, calculation steps)
        
    Reference:
        ACI 318-19 §22.6.5 - Two-way shear strength
    """
    steps = []
    
    d = geometry.effective_depth
    fc = concrete.fc
    lambda_c = concrete.lambda_factor
    
    # Critical perimeter at d/2 from load
    c1, c2 = load_area
    b0 = 2 * (c1 + d) + 2 * (c2 + d)  # Critical perimeter (mm)
    
    steps.append(CalculationStep(
        description="Critical perimeter",
        formula="b₀ = 2(c₁ + d) + 2(c₂ + d)",
        values=f"b₀ = 2({c1} + {d:.0f}) + 2({c2} + {d:.0f})",
        result=b0,
        unit="mm",
        code_ref="ACI 318-19 §22.6.4.1"
    ))
    
    # Shear stress capacity
    # vc = 0.33×λ×√f'c  (for interior column)
    vc = 0.33 * lambda_c * math.sqrt(fc)  # MPa
    
    # Punching capacity
    Vc = vc * b0 * d / 1000  # kN
    
    steps.append(CalculationStep(
        description="Punching shear capacity",
        formula="Vc = 0.33×λ×√f'c×b₀×d",
        values=f"Vc = 0.33×{lambda_c}×√{fc}×{b0:.0f}×{d:.0f}",
        result=Vc,
        unit="kN",
        code_ref="ACI 318-19 §22.6.5.2"
    ))
    
    return P_conc, Vc, steps


# =============================================================================
# SERVICEABILITY - ACI 318-19 §7.7 & §24.2
# =============================================================================

def calculate_cracked_moment_of_inertia(
    geometry: SlabGeometry,
    concrete: ConcreteProperties,
    reinforcement: ReinforcementProperties,
    deck: Optional[DeckContribution] = None,
    width: float = 1000
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate cracked moment of inertia Icr.
    
    Args:
        geometry: Slab geometry
        concrete: Concrete properties
        reinforcement: Reinforcement properties
        deck: Optional deck contribution
        width: Analysis width (mm)
        
    Returns:
        (Icr in mm⁴/m, calculation steps)
        
    Reference:
        ACI 318-19 §24.2.3.5
    """
    steps = []
    
    b = width
    d = geometry.effective_depth
    Ec = concrete.Ec
    Es = reinforcement.Es
    
    # Modular ratio
    n = Es / Ec
    
    steps.append(CalculationStep(
        description="Modular ratio",
        formula="n = Es/Ec",
        values=f"n = {Es}/{Ec:.0f}",
        result=n,
        unit="-",
        code_ref="ACI 318-19 §24.2.3.5"
    ))
    
    # Transformed steel area
    As_total = reinforcement.As_provided
    if deck:
        As_total += deck.As_deck
    
    # Neutral axis depth (cracked section)
    # From equilibrium: b×c²/2 = n×As×(d-c)
    # Solving quadratic: c = (-n×As + √((n×As)² + 2×b×n×As×d)) / b
    nAs = n * As_total
    c = (-nAs + math.sqrt(nAs**2 + 2 * b * nAs * d)) / b
    
    steps.append(CalculationStep(
        description="Neutral axis depth (cracked)",
        formula="c from b×c²/2 = n×As×(d-c)",
        values=f"n×As = {nAs:.0f}, d = {d:.1f}",
        result=c,
        unit="mm",
        code_ref="ACI 318-19 §24.2.3.5"
    ))
    
    # Cracked moment of inertia
    Icr = b * c**3 / 3 + nAs * (d - c)**2
    
    steps.append(CalculationStep(
        description="Cracked moment of inertia",
        formula="Icr = b×c³/3 + n×As×(d-c)²",
        values=f"Icr = {b}×{c:.1f}³/3 + {nAs:.0f}×({d:.1f}-{c:.1f})²",
        result=Icr,
        unit="mm⁴/m",
        code_ref="ACI 318-19 §24.2.3.5"
    ))
    
    return Icr, steps


def calculate_effective_moment_of_inertia(
    geometry: SlabGeometry,
    concrete: ConcreteProperties,
    reinforcement: ReinforcementProperties,
    Ma: float,  # Applied moment (kN·m/m)
    deck: Optional[DeckContribution] = None,
    width: float = 1000
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate effective moment of inertia Ie per ACI 318-19 §24.2.3.5
    
    Uses Branson's equation (modified).
    
    Args:
        geometry: Slab geometry
        concrete: Concrete properties
        reinforcement: Reinforcement properties
        Ma: Service moment (kN·m/m)
        deck: Optional deck contribution
        width: Analysis width (mm)
        
    Returns:
        (Ie in mm⁴/m, calculation steps)
    """
    steps = []
    
    b = width
    tc = geometry.tc
    fr = concrete.fr
    
    # Gross moment of inertia
    Ig = b * tc**3 / 12
    
    steps.append(CalculationStep(
        description="Gross moment of inertia",
        formula="Ig = b×tc³/12",
        values=f"Ig = {b}×{tc}³/12",
        result=Ig,
        unit="mm⁴/m",
        code_ref="ACI 318-19 §24.2.3.5"
    ))
    
    # Cracking moment
    yt = tc / 2  # Distance to tension face
    Mcr = fr * Ig / yt / 1e6  # kN·m/m
    
    steps.append(CalculationStep(
        description="Cracking moment",
        formula="Mcr = fr×Ig/yt",
        values=f"Mcr = {fr:.3f}×{Ig:.0f}/{yt:.1f}",
        result=Mcr,
        unit="kN·m/m",
        code_ref="ACI 318-19 §24.2.3.5"
    ))
    
    # Cracked moment of inertia
    Icr, icr_steps = calculate_cracked_moment_of_inertia(
        geometry, concrete, reinforcement, deck, width
    )
    
    # Effective moment of inertia per ACI 318-19 Eq. 24.2.3.5a
    if Ma <= 0:
        Ie = Ig
    elif Mcr >= Ma:
        # Section uncracked
        Ie = Ig
    else:
        # Branson's equation
        ratio = Mcr / Ma
        Ie = (ratio**3 * Ig + (1 - ratio**3) * Icr)
        Ie = min(Ie, Ig)
    
    steps.append(CalculationStep(
        description="Effective moment of inertia",
        formula="Ie = (Mcr/Ma)³×Ig + [1-(Mcr/Ma)³]×Icr",
        values=f"Mcr/Ma = {Mcr:.3f}/{Ma:.3f} = {Mcr/Ma if Ma > 0 else 0:.3f}",
        result=Ie,
        unit="mm⁴/m",
        code_ref="ACI 318-19 §24.2.3.5"
    ))
    
    return Ie, steps


def calculate_deflection(
    geometry: SlabGeometry,
    concrete: ConcreteProperties,
    reinforcement: ReinforcementProperties,
    w_service: float,  # Service load (kN/m²)
    deck: Optional[DeckContribution] = None
) -> Tuple[float, float, List[CalculationStep]]:
    """
    Calculate immediate and long-term deflection.
    
    Args:
        geometry: Slab geometry
        concrete: Concrete properties
        reinforcement: Reinforcement properties
        w_service: Total service load (kN/m²)
        deck: Optional deck contribution
        
    Returns:
        (immediate_defl, total_defl, calculation steps) in mm
        
    Reference:
        ACI 318-19 §24.2
    """
    steps = []
    
    L = geometry.span
    Ec = concrete.Ec
    
    # Get moment coefficient based on span condition
    pos_coef, neg_coef = geometry.get_moment_coefficients()
    
    # Service moment (per meter width)
    w_line = w_service  # kN/m per meter width
    Ma = pos_coef * w_line * (L/1000)**2  # kN·m/m
    
    steps.append(CalculationStep(
        description="Service moment",
        formula=f"Ma = {pos_coef:.4f}×w×L²",
        values=f"Ma = {pos_coef:.4f}×{w_line:.2f}×{L/1000:.2f}²",
        result=Ma,
        unit="kN·m/m",
        code_ref="ACI 318-19 §6.5"
    ))
    
    # Effective moment of inertia
    Ie, ie_steps = calculate_effective_moment_of_inertia(
        geometry, concrete, reinforcement, Ma, deck
    )
    steps.extend(ie_steps)
    
    # Immediate deflection (using appropriate coefficient)
    # For uniform load: δ = 5×w×L⁴ / (384×E×I) for simple span
    if geometry.span_condition == SpanCondition.SIMPLE:
        defl_coef = 5 / 384
    elif geometry.span_condition == SpanCondition.TWO_SPAN:
        defl_coef = 1 / 185  # Approximate for end span
    else:
        defl_coef = 1 / 384  # Approximate for interior
    
    # Convert units: w in N/mm, L in mm, E in MPa, I in mm⁴
    w_Nmm = w_service / 1000  # kN/m² = N/mm per mm width
    delta_i = defl_coef * w_Nmm * L**4 / (Ec * Ie) * 1000  # mm, per meter width
    
    steps.append(CalculationStep(
        description="Immediate deflection",
        formula="δi = k×w×L⁴/(E×Ie)",
        values=f"δi = {defl_coef:.6f}×{w_Nmm:.4f}×{L}⁴/({Ec:.0f}×{Ie:.0f})",
        result=delta_i,
        unit="mm",
        code_ref="ACI 318-19 §24.2.2"
    ))
    
    # Long-term deflection multiplier per ACI 318-19 §24.2.4.1
    # λΔ = ξ / (1 + 50×ρ')
    # ξ = 2.0 for 5 years or more
    xi = 2.0
    rho_prime = 0  # Compression reinforcement ratio (typically 0 for slabs)
    lambda_delta = xi / (1 + 50 * rho_prime)
    
    steps.append(CalculationStep(
        description="Long-term multiplier",
        formula="λΔ = ξ/(1 + 50×ρ')",
        values=f"λΔ = {xi}/(1 + 50×{rho_prime})",
        result=lambda_delta,
        unit="-",
        code_ref="ACI 318-19 §24.2.4.1"
    ))
    
    # Total long-term deflection
    delta_total = delta_i * (1 + lambda_delta)
    
    steps.append(CalculationStep(
        description="Total deflection",
        formula="δtotal = δi×(1 + λΔ)",
        values=f"δtotal = {delta_i:.2f}×(1 + {lambda_delta:.1f})",
        result=delta_total,
        unit="mm",
        code_ref="ACI 318-19 §24.2.4"
    ))
    
    return delta_i, delta_total, steps


# =============================================================================
# CRACK CONTROL - ACI 318-19 §24.3
# =============================================================================

def check_crack_control(
    geometry: SlabGeometry,
    reinforcement: ReinforcementProperties,
    fs: float  # Steel stress at service (MPa)
) -> Tuple[float, float, List[CalculationStep]]:
    """
    Check crack control per ACI 318-19 §24.3.2
    
    Args:
        geometry: Slab geometry
        reinforcement: Reinforcement properties
        fs: Steel stress at service load (MPa)
        
    Returns:
        (s_provided, s_max, calculation steps)
        
    Reference:
        ACI 318-19 §24.3.2 - Maximum spacing
    """
    steps = []
    
    cc = reinforcement.cover_bot  # Clear cover (mm)
    
    # Maximum spacing per ACI 318-19 Eq. 24.3.2.1
    # s_max = min(380×(280/fs) - 2.5×cc, 300×(280/fs))
    s_max_1 = 380 * (280 / fs) - 2.5 * cc
    s_max_2 = 300 * (280 / fs)
    s_max = min(s_max_1, s_max_2)
    
    steps.append(CalculationStep(
        description="Maximum spacing for crack control",
        formula="s_max = min(380×(280/fs) - 2.5×cc, 300×(280/fs))",
        values=f"s_max = min(380×(280/{fs:.0f}) - 2.5×{cc}, 300×(280/{fs:.0f}))",
        result=s_max,
        unit="mm",
        code_ref="ACI 318-19 §24.3.2.1"
    ))
    
    s_provided = reinforcement.spacing if reinforcement.spacing > 0 else 150
    
    return s_provided, s_max, steps


# =============================================================================
# FIRE RATING - IBC/UL Requirements
# =============================================================================

@dataclass 
class FireRequirements:
    """Fire rating requirements"""
    rating: FireRating
    min_thickness: float      # Minimum slab thickness (mm)
    min_cover: float         # Minimum cover to reinforcement (mm)
    notes: str = ""


def get_fire_requirements(rating: FireRating, is_restrained: bool = True) -> FireRequirements:
    """
    Get fire rating requirements per IBC Table 722.2.2.1 and UL assemblies.
    
    Args:
        rating: Desired fire rating
        is_restrained: Whether slab is restrained (typical for composite)
        
    Returns:
        FireRequirements with minimum dimensions
        
    Reference:
        IBC 2021 Table 722.2.2.1
        UL Design No. D916, D925 (typical composite deck assemblies)
    """
    # Minimum thickness requirements (normal weight concrete)
    # Based on IBC Table 722.2.2.1 and typical UL assemblies
    requirements = {
        FireRating.NONE: FireRequirements(
            rating=FireRating.NONE,
            min_thickness=0,
            min_cover=20,
            notes="No fire rating required"
        ),
        FireRating.ONE_HOUR: FireRequirements(
            rating=FireRating.ONE_HOUR,
            min_thickness=90 if is_restrained else 115,
            min_cover=20,
            notes="1-hour restrained/unrestrained per IBC Table 722.2.2.1"
        ),
        FireRating.ONE_HALF_HOUR: FireRequirements(
            rating=FireRating.ONE_HALF_HOUR,
            min_thickness=115 if is_restrained else 140,
            min_cover=25,
            notes="1.5-hour per IBC Table 722.2.2.1"
        ),
        FireRating.TWO_HOUR: FireRequirements(
            rating=FireRating.TWO_HOUR,
            min_thickness=125 if is_restrained else 165,
            min_cover=25,
            notes="2-hour per IBC Table 722.2.2.1"
        ),
        FireRating.THREE_HOUR: FireRequirements(
            rating=FireRating.THREE_HOUR,
            min_thickness=165 if is_restrained else 190,
            min_cover=32,
            notes="3-hour per IBC Table 722.2.2.1"
        ),
    }
    
    return requirements.get(rating, requirements[FireRating.NONE])


def check_fire_rating(
    geometry: SlabGeometry,
    reinforcement: ReinforcementProperties,
    rating: FireRating,
    is_restrained: bool = True
) -> Tuple[bool, List[CalculationStep]]:
    """
    Check if slab meets fire rating requirements.
    
    Args:
        geometry: Slab geometry
        reinforcement: Reinforcement properties
        rating: Required fire rating
        is_restrained: Whether assembly is restrained
        
    Returns:
        (passes, calculation steps)
    """
    steps = []
    
    req = get_fire_requirements(rating, is_restrained)
    
    # Check thickness
    thickness_ok = geometry.tc >= req.min_thickness
    
    steps.append(CalculationStep(
        description="Minimum thickness check",
        formula=f"tc ≥ tc_min ({rating.value})",
        values=f"{geometry.tc:.0f} ≥ {req.min_thickness:.0f}",
        result=geometry.tc,
        unit="mm",
        code_ref="IBC Table 722.2.2.1"
    ))
    
    # Check cover
    cover_ok = reinforcement.cover_bot >= req.min_cover
    
    steps.append(CalculationStep(
        description="Minimum cover check",
        formula="cover ≥ cover_min",
        values=f"{reinforcement.cover_bot:.0f} ≥ {req.min_cover:.0f}",
        result=reinforcement.cover_bot,
        unit="mm",
        code_ref="IBC §722.2.2"
    ))
    
    passes = thickness_ok and cover_ok
    
    return passes, steps


# =============================================================================
# MINIMUM REINFORCEMENT - ACI 318-19 §7.6.1
# =============================================================================

def calculate_minimum_reinforcement(
    geometry: SlabGeometry,
    reinforcement: ReinforcementProperties,
    width: float = 1000
) -> Tuple[float, List[CalculationStep]]:
    """
    Calculate minimum reinforcement per ACI 318-19 §7.6.1
    
    Args:
        geometry: Slab geometry
        reinforcement: Reinforcement properties
        width: Analysis width (mm)
        
    Returns:
        (As_min in mm²/m, calculation steps)
        
    Reference:
        ACI 318-19 §7.6.1.1 - Temperature and shrinkage reinforcement
        ACI 318-19 §24.4.3.2 - Minimum flexural reinforcement
    """
    steps = []
    
    b = width
    tc = geometry.tc
    fy = reinforcement.fy
    
    # Temperature and shrinkage per ACI 318-19 Table 24.4.3.2
    if fy <= 420:
        rho_min = 0.0020
    elif fy >= 520:
        rho_min = 0.0014
    else:
        rho_min = 0.0020 - (fy - 420) * 0.0006 / 100
    
    As_min = rho_min * b * tc
    
    steps.append(CalculationStep(
        description="Minimum reinforcement ratio",
        formula="ρ_min per Table 24.4.3.2",
        values=f"ρ_min = {rho_min:.4f} for fy = {fy} MPa",
        result=rho_min * 100,
        unit="%",
        code_ref="ACI 318-19 Table 24.4.3.2"
    ))
    
    steps.append(CalculationStep(
        description="Minimum reinforcement area",
        formula="As_min = ρ_min × b × tc",
        values=f"As_min = {rho_min:.4f} × {b} × {tc}",
        result=As_min,
        unit="mm²/m",
        code_ref="ACI 318-19 §7.6.1.1"
    ))
    
    return As_min, steps


# =============================================================================
# COMPLETE DESIGN FUNCTION
# =============================================================================

def design_composite_slab(
    geometry: SlabGeometry,
    concrete: ConcreteProperties,
    reinforcement: ReinforcementProperties,
    deck: Optional[DeckContribution],
    w_dead: float,           # Dead load including self-weight (kN/m²)
    w_live: float,           # Live load (kN/m²)
    w_SDL: float = 0,        # Superimposed dead load (kN/m²)
    fire_rating: FireRating = FireRating.NONE,
    check_punching: bool = False,
    P_concentrated: float = 0,  # Concentrated load for punching (kN)
    phi_flexure: float = 0.9,
    phi_shear: float = 0.75
) -> Dict[str, DesignResult]:
    """
    Complete composite slab design per ACI 318-19.
    
    Args:
        geometry: Slab geometry
        concrete: Concrete properties
        reinforcement: Reinforcement properties
        deck: Metal deck contribution
        w_dead: Dead load (kN/m²)
        w_live: Live load (kN/m²)
        w_SDL: Superimposed dead load (kN/m²)
        fire_rating: Required fire rating (optional)
        check_punching: Whether to check punching shear
        P_concentrated: Concentrated load for punching (kN)
        phi_flexure: Strength reduction factor for flexure
        phi_shear: Strength reduction factor for shear
        
    Returns:
        Dictionary of DesignResult objects for each check
    """
    results = {}
    
    # Factored loads per ACI 318-19 §5.3.1
    # U = 1.2D + 1.6L
    w_factored = 1.2 * (w_dead + w_SDL) + 1.6 * w_live  # kN/m²
    w_service = w_dead + w_SDL + w_live
    
    # Get moment coefficients
    pos_coef, neg_coef = geometry.get_moment_coefficients()
    L = geometry.span / 1000  # Convert to m
    
    # =========================
    # 1. POSITIVE FLEXURE CHECK
    # =========================
    Mu_pos = pos_coef * w_factored * L**2  # kN·m/m
    Mn_pos, flex_steps = calculate_flexural_capacity(
        geometry, concrete, reinforcement, deck
    )
    phi_Mn_pos = phi_flexure * Mn_pos
    
    ratio_flex_pos = Mu_pos / phi_Mn_pos if phi_Mn_pos > 0 else float('inf')
    
    results['flexure_positive'] = DesignResult(
        check_name="Positive Flexure",
        demand=Mu_pos,
        capacity=phi_Mn_pos,
        ratio=ratio_flex_pos,
        status="PASS" if ratio_flex_pos <= 1.0 else "FAIL",
        code_ref="ACI 318-19 §22.2",
        steps=flex_steps
    )
    
    # =========================
    # 2. NEGATIVE FLEXURE CHECK (if continuous)
    # =========================
    if neg_coef > 0:
        Mu_neg = neg_coef * w_factored * L**2  # kN·m/m
        Mn_neg, neg_steps = calculate_negative_moment_capacity(
            geometry, concrete, reinforcement
        )
        phi_Mn_neg = phi_flexure * Mn_neg
        
        ratio_flex_neg = Mu_neg / phi_Mn_neg if phi_Mn_neg > 0 else float('inf')
        
        results['flexure_negative'] = DesignResult(
            check_name="Negative Flexure",
            demand=Mu_neg,
            capacity=phi_Mn_neg,
            ratio=ratio_flex_neg,
            status="PASS" if ratio_flex_neg <= 1.0 else "FAIL",
            code_ref="ACI 318-19 §22.2",
            steps=neg_steps
        )
    
    # =========================
    # 3. ONE-WAY SHEAR CHECK
    # =========================
    # Shear at d from support
    Vu = 0.5 * w_factored * L * (1 - 2 * geometry.effective_depth / geometry.span)  # kN/m
    Vc, shear_steps = calculate_shear_capacity(geometry, concrete)
    phi_Vc = phi_shear * Vc
    
    ratio_shear = Vu / phi_Vc if phi_Vc > 0 else float('inf')
    
    results['shear'] = DesignResult(
        check_name="One-Way Shear",
        demand=Vu,
        capacity=phi_Vc,
        ratio=ratio_shear,
        status="PASS" if ratio_shear <= 1.0 else "FAIL",
        code_ref="ACI 318-19 §22.5",
        steps=shear_steps
    )
    
    # =========================
    # 4. PUNCHING SHEAR (Optional)
    # =========================
    if check_punching and P_concentrated > 0:
        Vu_punch, Vc_punch, punch_steps = calculate_punching_shear(
            geometry, concrete, P_concentrated
        )
        phi_Vc_punch = phi_shear * Vc_punch
        
        ratio_punch = Vu_punch / phi_Vc_punch if phi_Vc_punch > 0 else float('inf')
        
        results['punching_shear'] = DesignResult(
            check_name="Punching Shear",
            demand=Vu_punch,
            capacity=phi_Vc_punch,
            ratio=ratio_punch,
            status="PASS" if ratio_punch <= 1.0 else "FAIL",
            code_ref="ACI 318-19 §22.6",
            steps=punch_steps
        )
    
    # =========================
    # 5. DEFLECTION CHECK
    # =========================
    delta_i, delta_total, defl_steps = calculate_deflection(
        geometry, concrete, reinforcement, w_service, deck
    )
    
    # Deflection limits per ACI 318-19 Table 24.2.2
    # L/360 for floors supporting nonstructural elements
    delta_limit = geometry.span / 360
    
    ratio_defl = delta_total / delta_limit if delta_limit > 0 else float('inf')
    
    results['deflection'] = DesignResult(
        check_name="Deflection (L/360)",
        demand=delta_total,
        capacity=delta_limit,
        ratio=ratio_defl,
        status="PASS" if ratio_defl <= 1.0 else "FAIL",
        code_ref="ACI 318-19 Table 24.2.2",
        steps=defl_steps
    )
    
    # =========================
    # 6. MINIMUM REINFORCEMENT
    # =========================
    As_min, min_rebar_steps = calculate_minimum_reinforcement(
        geometry, reinforcement
    )
    As_total = reinforcement.As_provided
    if deck:
        As_total += deck.As_deck
    
    ratio_min_rebar = As_min / As_total if As_total > 0 else float('inf')
    
    results['min_reinforcement'] = DesignResult(
        check_name="Minimum Reinforcement",
        demand=As_min,
        capacity=As_total,
        ratio=ratio_min_rebar,
        status="PASS" if ratio_min_rebar <= 1.0 else "FAIL",
        code_ref="ACI 318-19 §7.6.1",
        steps=min_rebar_steps
    )
    
    # =========================
    # 7. FIRE RATING (Optional)
    # =========================
    if fire_rating != FireRating.NONE:
        fire_ok, fire_steps = check_fire_rating(
            geometry, reinforcement, fire_rating
        )
        
        results['fire_rating'] = DesignResult(
            check_name=f"Fire Rating ({fire_rating.value})",
            demand=1.0 if not fire_ok else 0,
            capacity=1.0,
            ratio=0 if fire_ok else 1.1,
            status="PASS" if fire_ok else "FAIL",
            code_ref="IBC Table 722.2.2.1",
            steps=fire_steps
        )
    
    return results


def generate_slab_summary(results: Dict[str, DesignResult]) -> str:
    """Generate text summary of slab design results."""
    lines = [
        "=" * 60,
        "COMPOSITE SLAB DESIGN SUMMARY - ACI 318-19",
        "=" * 60,
        ""
    ]
    
    all_pass = all(r.status == "PASS" for r in results.values())
    lines.append(f"Overall Status: {'✓ ALL CHECKS PASS' if all_pass else '✗ DESIGN FAILS'}")
    lines.append("")
    lines.append(f"{'Check':<25} {'Demand':>10} {'Capacity':>10} {'D/C':>8} {'Status':>8}")
    lines.append("-" * 65)
    
    for name, result in results.items():
        status_sym = "✓" if result.status == "PASS" else "✗"
        lines.append(
            f"{result.check_name:<25} {result.demand:>10.3f} {result.capacity:>10.3f} "
            f"{result.ratio:>8.3f} {status_sym:>8}"
        )
    
    lines.append("-" * 65)
    
    return "\n".join(lines)


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing Composite Slab Design Module")
    print("=" * 50)
    
    # Test geometry
    geom = SlabGeometry(
        tc=130,           # 130mm total thickness
        hr=50,            # 50mm deck height
        wr_top=114,
        wr_bot=38,
        pitch=152,
        span=2400,        # 2.4m span
        span_condition=SpanCondition.TWO_SPAN
    )
    
    # Concrete
    conc = ConcreteProperties(fc=25)  # C25 concrete
    
    # Reinforcement
    rebar = ReinforcementProperties(
        fy=500,
        As_provided=142,  # WWF 6x6 - 142 mm²/m
        cover_top=20,
        cover_bot=20
    )
    
    # Deck contribution
    deck = DeckContribution(
        Ag_deck=1200,     # mm²/m
        Ig_deck=450000,   # mm⁴/m
        Fy_deck=230,
        t_deck=0.9
    )
    
    # Run design
    results = design_composite_slab(
        geometry=geom,
        concrete=conc,
        reinforcement=rebar,
        deck=deck,
        w_dead=3.5,       # kN/m²
        w_live=2.5,       # kN/m²
        w_SDL=1.0,        # kN/m²
        fire_rating=FireRating.ONE_HOUR
    )
    
    # Print summary
    print(generate_slab_summary(results))
