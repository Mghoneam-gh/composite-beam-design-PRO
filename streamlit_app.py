"""
CompositeBeam Pro v3.0 - Professional Composite & Non-Composite Beam Design
AISC 360-16 Steel Design | AISI S100-16 Metal Deck | ACI 318-19 Concrete Design

Features:
- Composite Mode: Full composite beam design with shear studs
- Non-Composite Mode: Bare steel beam + one-way RC slab (NEW)
- Auto-calculated effective width (beff) per AISC 360-16 §I3.1a
- Complete load inputs: Dead, Superimposed Dead, Live, Construction
- Pre-composite (construction stage) checks
- Composite stage checks / Non-composite steel beam checks
- Asymmetric built-up sections, custom shear studs
- Metal Deck DXF Import and Design Checks (Phase 2)
- Composite Slab Design with ACI 318-19 (Phase 4)
- One-Way Slab Design with ACI 318-19 (NEW)
- Non-Composite Steel Beam - Full AISC 360-16 Checks (NEW):
  * Section Classification (Table B4.1b)
  * Flexural Strength (Chapter F) - Yielding, LTB, FLB
  * Shear Strength (Chapter G)
  * Web Local Yielding (J10.2)
  * Web Crippling (J10.3)
  * Deflection (Chapter L)
"""
import streamlit as st
import math
import numpy as np
from datetime import datetime
import tempfile
import os
import sys

# Matplotlib for profile visualization
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

# Add parent directory to path for imports (handles running from app/ or root)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# Phase 2 Metal Deck Module Imports
METAL_DECK_AVAILABLE = False
METAL_DECK_ERROR = ""
try:
    from core.utils.dxf_parser import (
        parse_deck_dxf, parse_deck_from_vertices, 
        calculate_gross_properties, create_standard_profile,
        validate_profile_limits, DXFParseResult
    )
    from core.utils.effective_width import (
        effective_width_stiffened, calculate_effective_deck_properties
    )
    from core.design.metal_deck import (
        DeckGeometry, DeckMaterial, DeckSectionProperties,
        design_metal_deck, DesignMethod, generate_design_summary
    )
    METAL_DECK_AVAILABLE = True
except ImportError as e:
    METAL_DECK_ERROR = str(e)

# Phase 4 Composite Slab Module Imports
COMPOSITE_SLAB_AVAILABLE = False
COMPOSITE_SLAB_ERROR = ""
try:
    from core.design.composite_slab import (
        SlabGeometry, ConcreteProperties, ReinforcementProperties,
        DeckContribution, SpanCondition, FireRating,
        design_composite_slab, generate_slab_summary,
        calculate_minimum_reinforcement
    )
    COMPOSITE_SLAB_AVAILABLE = True
except ImportError as e:
    COMPOSITE_SLAB_ERROR = str(e)

# Phase 5 Diaphragm Module Imports
DIAPHRAGM_AVAILABLE = False
DIAPHRAGM_ERROR = ""
try:
    from core.design.diaphragm import (
        DeckProfile as DiaphragmDeckProfile,
        SupportFastener, SideLapFastener,
        DiaphragmGeometry, DiaphragmLoads,
        FastenerType, SideLapType, DeckOrientation,
        DesignMethod as DiaphragmDesignMethod,
        design_diaphragm, generate_diaphragm_summary
    )
    DIAPHRAGM_AVAILABLE = True
except ImportError as e:
    DIAPHRAGM_ERROR = str(e)

# Phase 6 Castellated/Cellular Beam Module Imports
CASTELLATED_AVAILABLE = False
CASTELLATED_ERROR = ""
try:
    from core.design.castellated_cellular import (
        BeamType, ParentSection, CastellatedGeometry, CellularGeometry,
        MaterialProperties as CastellatedMaterial,
        LoadingCondition as CastellatedLoading,
        DesignMethod as CastellatedDesignMethod,
        calc_expanded_section,
        design_castellated_cellular_beam,
        generate_castellated_summary,
        check_dimension_limits,
        plot_castellated_beam,
        plot_cellular_beam,
        PARENT_SECTIONS,
        CASTELLATED_LIMITS,
        CELLULAR_LIMITS
    )
    from core.design.castellated_detailed_calcs import (
        design_castellated_detailed,
        format_detailed_report,
        DetailedDesignReport
    )
    CASTELLATED_AVAILABLE = True
except ImportError as e:
    CASTELLATED_ERROR = str(e)

# Composite Beam Detailed Calculations
COMPOSITE_DETAILED_AVAILABLE = False
COMPOSITE_DETAILED_ERROR = ""
try:
    from core.design.composite_detailed_calcs import (
        design_composite_detailed,
        format_composite_report,
        CompositeDesignReport
    )
    COMPOSITE_DETAILED_AVAILABLE = True
except ImportError as e:
    COMPOSITE_DETAILED_ERROR = str(e)

# Pre-Composite Steel Beam Detailed Calculations
PRECOMP_DETAILED_AVAILABLE = False
PRECOMP_DETAILED_ERROR = ""
try:
    from core.design.precomp_detailed_calcs import (
        design_precomposite_detailed,
        format_precomp_report,
        PreCompositeDesignReport
    )
    PRECOMP_DETAILED_AVAILABLE = True
except ImportError as e:
    PRECOMP_DETAILED_ERROR = str(e)

# Non-Composite Steel Beam Design (AISC 360-16)
NONCOMP_BEAM_AVAILABLE = False
NONCOMP_BEAM_ERROR = ""
try:
    from core.design.noncomposite_beam import (
        SectionClassification,
        FlexuralStrength,
        ShearStrength,
        WebLocalYielding,
        WebCrippling,
        NonCompositeBeamResults,
        AxialTensionStrength,
        AxialCompressionStrength,
        CombinedLoadingResults,
        NonCompositeBeamColumnResults,
        classify_section,
        calc_Cb,
        calc_flexural_strength,
        calc_web_local_yielding,
        calc_tension_strength,
        calc_compression_strength,
        check_combined_loading,
        design_noncomposite_beam,
        design_noncomposite_beam_column
    )
    NONCOMP_BEAM_AVAILABLE = True
except ImportError as e:
    NONCOMP_BEAM_ERROR = str(e)

# One-Way Slab Design (ACI 318-19)
ONEWAY_SLAB_AVAILABLE = False
ONEWAY_SLAB_ERROR = ""
try:
    from core.design.oneway_slab import (
        SlabMaterials,
        MomentCoefficients,
        FlexuralDesign,
        ShrinkageTempReinf,
        OneWaySlabResults,
        calc_materials,
        get_moment_coefficients,
        calc_shrinkage_temp,
        design_oneway_slab
    )
    ONEWAY_SLAB_AVAILABLE = True
except ImportError as e:
    ONEWAY_SLAB_ERROR = str(e)


def plot_deck_profile(parse_result, thickness, show_dimensions=True, title="Metal Deck Profile",
                      input_hr=None, input_wr_top=None, input_wr_bot=None, input_pitch=None):
    """
    Generate matplotlib figure of the metal deck profile with dimensions.
    
    Parameters:
        parse_result: DXFParseResult with vertices and detected dimensions
        thickness: Base metal thickness (mm)
        show_dimensions: Whether to display dimension annotations
        title: Plot title
        input_hr: Per-rib height override for dimension display (mm)
        input_wr_top: Per-rib top opening override for dimension display (mm)
        input_wr_bot: Per-rib bottom width override for dimension display (mm)
        input_pitch: Per-rib pitch override for dimension display (mm)
    
    Returns:
        matplotlib Figure object
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 5))
    
    vertices = parse_result.vertices
    if not vertices:
        ax.text(0.5, 0.5, "No profile data", ha='center', va='center', fontsize=14)
        return fig
    
    x_coords = [v[0] for v in vertices]
    y_coords = [v[1] for v in vertices]
    
    # Plot centerline
    ax.plot(x_coords, y_coords, 'b-', linewidth=2, label='Centerline')
    
    # Generate offset lines for thickness visualization
    if thickness > 0 and len(vertices) > 1:
        # Simple offset approximation (perpendicular to segments)
        t_half = thickness / 2
        
        # Upper and lower profile lines
        x_upper, y_upper = [], []
        x_lower, y_lower = [], []
        
        for i in range(len(vertices)):
            if i == 0:
                # First point - use first segment direction
                dx = vertices[1][0] - vertices[0][0]
                dy = vertices[1][1] - vertices[0][1]
            elif i == len(vertices) - 1:
                # Last point - use last segment direction
                dx = vertices[-1][0] - vertices[-2][0]
                dy = vertices[-1][1] - vertices[-2][1]
            else:
                # Middle points - average of adjacent segments
                dx1 = vertices[i][0] - vertices[i-1][0]
                dy1 = vertices[i][1] - vertices[i-1][1]
                dx2 = vertices[i+1][0] - vertices[i][0]
                dy2 = vertices[i+1][1] - vertices[i][1]
                dx = (dx1 + dx2) / 2
                dy = (dy1 + dy2) / 2
            
            # Perpendicular unit vector
            length = np.sqrt(dx**2 + dy**2)
            if length > 0:
                nx, ny = -dy / length, dx / length
            else:
                nx, ny = 0, 1
            
            x_upper.append(vertices[i][0] + nx * t_half)
            y_upper.append(vertices[i][1] + ny * t_half)
            x_lower.append(vertices[i][0] - nx * t_half)
            y_lower.append(vertices[i][1] - ny * t_half)
        
        # Plot thickness lines
        ax.plot(x_upper, y_upper, 'b-', linewidth=1, alpha=0.6)
        ax.plot(x_lower, y_lower, 'b-', linewidth=1, alpha=0.6)
        
        # Fill between for visual effect
        ax.fill(x_upper + x_lower[::-1], y_upper + y_lower[::-1], 
                color='steelblue', alpha=0.3, label=f't = {thickness:.2f} mm')
    
    # Dimension annotations
    if show_dimensions and parse_result.hr > 0:
        # Use input values if provided, otherwise fall back to parse_result
        hr = input_hr if input_hr is not None else parse_result.hr
        wr_top = input_wr_top if input_wr_top is not None else parse_result.wr_top
        wr_bot = input_wr_bot if input_wr_bot is not None else parse_result.wr_bot
        pitch = input_pitch if input_pitch is not None else (parse_result.pitch if parse_result.pitch > 0 else 152.4)
        
        # Find a representative rib for dimensioning
        y_min = min(y_coords)
        y_max = max(y_coords)
        x_min = min(x_coords)
        x_max = max(x_coords)
        
        # Height dimension (hr) - vertical arrow on left
        dim_x = x_min - 15
        ax.annotate('', xy=(dim_x, y_max), xytext=(dim_x, y_min),
                    arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
        ax.text(dim_x - 8, (y_max + y_min) / 2, f'hr\n{hr:.1f}', 
                ha='right', va='center', fontsize=9, color='red', fontweight='bold')
        
        # Pitch dimension - horizontal arrow at bottom
        if pitch > 0 and x_max - x_min > pitch:
            dim_y = y_min - 12
            # Find first rib center
            x_pitch_start = x_min + wr_bot / 2
            x_pitch_end = x_pitch_start + pitch
            ax.annotate('', xy=(x_pitch_end, dim_y), xytext=(x_pitch_start, dim_y),
                        arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
            ax.text((x_pitch_start + x_pitch_end) / 2, dim_y - 8, f'pitch = {pitch:.1f}', 
                    ha='center', va='top', fontsize=9, color='green', fontweight='bold')
        
        # Top opening (wr_top) - at top of first rib
        if wr_top > 0:
            # Find top points
            top_points = [(x, y) for x, y in vertices if abs(y - y_max) < 1]
            if len(top_points) >= 2:
                dim_y_top = y_max + 8
                x_top_start = top_points[0][0]
                x_top_end = x_top_start + wr_top
                ax.annotate('', xy=(x_top_end, dim_y_top), xytext=(x_top_start, dim_y_top),
                            arrowprops=dict(arrowstyle='<->', color='purple', lw=1.5))
                ax.text((x_top_start + x_top_end) / 2, dim_y_top + 5, f'wr_top = {wr_top:.1f}', 
                        ha='center', va='bottom', fontsize=9, color='purple', fontweight='bold')
        
        # Bottom width (wr_bot) - at bottom of first rib
        if wr_bot > 0:
            # Find bottom points
            bot_points = [(x, y) for x, y in vertices if abs(y - y_min) < 1]
            if len(bot_points) >= 2:
                dim_y_bot = y_min - 5
                x_bot_start = bot_points[0][0]
                x_bot_end = x_bot_start + wr_bot
                ax.annotate('', xy=(x_bot_end, dim_y_bot), xytext=(x_bot_start, dim_y_bot),
                            arrowprops=dict(arrowstyle='<->', color='orange', lw=1.5))
                ax.text((x_bot_start + x_bot_end) / 2, dim_y_bot - 8, f'wr_bot = {wr_bot:.1f}', 
                        ha='center', va='top', fontsize=9, color='orange', fontweight='bold')
    
    # Mark vertices
    ax.scatter(x_coords, y_coords, color='red', s=20, zorder=5, label='Vertices')
    
    # Grid and styling
    ax.set_xlabel('Width (mm)', fontsize=10)
    ax.set_ylabel('Height (mm)', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=8)
    
    # Add padding
    x_range = max(x_coords) - min(x_coords)
    y_range = max(y_coords) - min(y_coords)
    ax.set_xlim(min(x_coords) - 0.15 * x_range, max(x_coords) + 0.1 * x_range)
    ax.set_ylim(min(y_coords) - 0.25 * y_range, max(y_coords) + 0.2 * y_range)
    
    plt.tight_layout()
    return fig

st.set_page_config(page_title="CompositeBeam Pro", page_icon="🏗️", layout="wide")

STEEL_GRADES = {
    "A36": {"Fy": 250, "Fu": 400}, "A572 Gr.50": {"Fy": 345, "Fu": 450}, "A992": {"Fy": 345, "Fu": 450},
    "A529 Gr.50": {"Fy": 345, "Fu": 485}, "A529 Gr.55": {"Fy": 380, "Fu": 485},
    "S235": {"Fy": 235, "Fu": 360}, "S275": {"Fy": 275, "Fu": 430}, "S355": {"Fy": 355, "Fu": 510},
    "S420": {"Fy": 420, "Fu": 520}, "S450": {"Fy": 450, "Fu": 550}, "S460": {"Fy": 460, "Fu": 540},
    "Grade 43": {"Fy": 275, "Fu": 430}, "Grade 50": {"Fy": 355, "Fu": 490}, "Grade 55": {"Fy": 450, "Fu": 550},
}

# COMPLETE SECTION DATABASE - 202 SECTIONS
SECTIONS = {
"AISC W-Shapes": {
"W10x12":{"d":251,"bf":102,"tf":5.3,"tw":4.8,"A":1550,"Ix":17.1e6,"Sx":136e3,"Zx":155e3,"wt":12},
"W10x15":{"d":254,"bf":102,"tf":6.9,"tw":5.8,"A":1940,"Ix":22.8e6,"Sx":179e3,"Zx":203e3,"wt":15},
"W10x22":{"d":262,"bf":146,"tf":6.9,"tw":6.1,"A":2850,"Ix":37.1e6,"Sx":283e3,"Zx":313e3,"wt":22},
"W10x26":{"d":262,"bf":147,"tf":8.8,"tw":6.6,"A":3350,"Ix":44.5e6,"Sx":340e3,"Zx":379e3,"wt":26},
"W10x30":{"d":266,"bf":148,"tf":10.5,"tw":7.6,"A":3870,"Ix":53.8e6,"Sx":404e3,"Zx":451e3,"wt":30},
"W10x39":{"d":262,"bf":203,"tf":9.7,"tw":7.9,"A":5060,"Ix":71.1e6,"Sx":543e3,"Zx":598e3,"wt":39},
"W10x45":{"d":267,"bf":204,"tf":11.2,"tw":8.9,"A":5810,"Ix":85.1e6,"Sx":637e3,"Zx":704e3,"wt":45},
"W10x54":{"d":257,"bf":254,"tf":10.0,"tw":9.4,"A":6970,"Ix":99.1e6,"Sx":771e3,"Zx":849e3,"wt":54},
"W10x68":{"d":264,"bf":257,"tf":13.0,"tw":11.4,"A":8840,"Ix":134e6,"Sx":1020e3,"Zx":1130e3,"wt":68},
"W10x88":{"d":274,"bf":261,"tf":16.8,"tw":14.7,"A":11400,"Ix":179e6,"Sx":1310e3,"Zx":1470e3,"wt":88},
"W10x112":{"d":284,"bf":267,"tf":21.1,"tw":19.1,"A":14500,"Ix":236e6,"Sx":1660e3,"Zx":1900e3,"wt":112},
"W12x14":{"d":302,"bf":102,"tf":5.7,"tw":4.3,"A":1810,"Ix":24.5e6,"Sx":162e3,"Zx":186e3,"wt":14},
"W12x19":{"d":309,"bf":102,"tf":8.9,"tw":5.6,"A":2480,"Ix":37.1e6,"Sx":240e3,"Zx":276e3,"wt":19},
"W12x26":{"d":310,"bf":165,"tf":9.7,"tw":5.8,"A":3350,"Ix":85.1e6,"Sx":549e3,"Zx":614e3,"wt":26},
"W12x35":{"d":318,"bf":167,"tf":13.2,"tw":7.6,"A":4550,"Ix":78.2e6,"Sx":492e3,"Zx":553e3,"wt":35},
"W12x45":{"d":307,"bf":204,"tf":11.9,"tw":8.1,"A":5810,"Ix":103e6,"Sx":671e3,"Zx":742e3,"wt":45},
"W12x53":{"d":312,"bf":254,"tf":10.2,"tw":8.8,"A":6840,"Ix":123e6,"Sx":789e3,"Zx":867e3,"wt":53},
"W12x65":{"d":318,"bf":305,"tf":10.9,"tw":9.9,"A":8390,"Ix":156e6,"Sx":981e3,"Zx":1070e3,"wt":65},
"W12x79":{"d":323,"bf":307,"tf":13.5,"tw":11.9,"A":10200,"Ix":194e6,"Sx":1200e3,"Zx":1320e3,"wt":79},
"W12x96":{"d":330,"bf":309,"tf":16.3,"tw":14.5,"A":12400,"Ix":244e6,"Sx":1480e3,"Zx":1650e3,"wt":96},
"W12x120":{"d":340,"bf":313,"tf":20.1,"tw":18.0,"A":15500,"Ix":317e6,"Sx":1860e3,"Zx":2100e3,"wt":120},
"W12x152":{"d":351,"bf":318,"tf":25.4,"tw":22.1,"A":19600,"Ix":415e6,"Sx":2360e3,"Zx":2700e3,"wt":152},
"W12x190":{"d":363,"bf":323,"tf":31.2,"tw":27.9,"A":24500,"Ix":540e6,"Sx":2980e3,"Zx":3450e3,"wt":190},
"W12x230":{"d":376,"bf":328,"tf":37.1,"tw":33.5,"A":29700,"Ix":680e6,"Sx":3620e3,"Zx":4250e3,"wt":230},
"W12x279":{"d":389,"bf":333,"tf":44.5,"tw":40.4,"A":36000,"Ix":854e6,"Sx":4390e3,"Zx":5230e3,"wt":279},
"W12x336":{"d":404,"bf":340,"tf":52.6,"tw":48.8,"A":43400,"Ix":1070e6,"Sx":5300e3,"Zx":6430e3,"wt":336},
"W14x22":{"d":349,"bf":127,"tf":8.5,"tw":5.8,"A":2840,"Ix":82.8e6,"Sx":475e3,"Zx":542e3,"wt":22},
"W14x30":{"d":352,"bf":171,"tf":9.8,"tw":6.9,"A":3870,"Ix":123e6,"Sx":699e3,"Zx":782e3,"wt":30},
"W14x38":{"d":358,"bf":172,"tf":13.1,"tw":7.9,"A":4910,"Ix":93.2e6,"Sx":521e3,"Zx":590e3,"wt":38},
"W14x48":{"d":353,"bf":204,"tf":13.5,"tw":7.9,"A":6190,"Ix":125e6,"Sx":708e3,"Zx":784e3,"wt":48},
"W14x61":{"d":353,"bf":254,"tf":13.1,"tw":9.5,"A":7870,"Ix":163e6,"Sx":923e3,"Zx":1020e3,"wt":61},
"W14x74":{"d":358,"bf":255,"tf":16.4,"tw":11.1,"A":9550,"Ix":204e6,"Sx":1140e3,"Zx":1260e3,"wt":74},
"W14x90":{"d":356,"bf":369,"tf":11.2,"tw":11.2,"A":11600,"Ix":252e6,"Sx":1420e3,"Zx":1560e3,"wt":90},
"W14x109":{"d":363,"bf":371,"tf":14.0,"tw":13.3,"A":14100,"Ix":315e6,"Sx":1740e3,"Zx":1920e3,"wt":109},
"W14x132":{"d":371,"bf":374,"tf":16.8,"tw":16.4,"A":17000,"Ix":394e6,"Sx":2120e3,"Zx":2360e3,"wt":132},
"W14x159":{"d":381,"bf":396,"tf":19.1,"tw":18.5,"A":20500,"Ix":487e6,"Sx":2560e3,"Zx":2860e3,"wt":159},
"W14x193":{"d":394,"bf":400,"tf":22.6,"tw":22.6,"A":24900,"Ix":620e6,"Sx":3150e3,"Zx":3560e3,"wt":193},
"W14x233":{"d":406,"bf":406,"tf":27.2,"tw":26.9,"A":30100,"Ix":784e6,"Sx":3860e3,"Zx":4400e3,"wt":233},
"W14x283":{"d":422,"bf":411,"tf":32.8,"tw":32.3,"A":36500,"Ix":991e6,"Sx":4700e3,"Zx":5420e3,"wt":283},
"W14x342":{"d":437,"bf":417,"tf":39.1,"tw":39.1,"A":44100,"Ix":1240e6,"Sx":5680e3,"Zx":6640e3,"wt":342},
"W14x426":{"d":460,"bf":424,"tf":47.6,"tw":47.6,"A":54800,"Ix":1640e6,"Sx":7130e3,"Zx":8450e3,"wt":426},
"W14x550":{"d":489,"bf":437,"tf":60.5,"tw":60.5,"A":71000,"Ix":2290e6,"Sx":9370e3,"Zx":11300e3,"wt":550},
"W14x730":{"d":526,"bf":452,"tf":78.0,"tw":78.0,"A":94200,"Ix":3290e6,"Sx":12500e3,"Zx":15500e3,"wt":730},
"W16x26":{"d":399,"bf":140,"tf":8.8,"tw":6.4,"A":3390,"Ix":71.1e6,"Sx":357e3,"Zx":402e3,"wt":26},
"W16x36":{"d":403,"bf":178,"tf":10.9,"tw":7.5,"A":4650,"Ix":105e6,"Sx":521e3,"Zx":581e3,"wt":36},
"W16x45":{"d":409,"bf":179,"tf":14.0,"tw":8.9,"A":5810,"Ix":137e6,"Sx":670e3,"Zx":751e3,"wt":45},
"W16x57":{"d":417,"bf":181,"tf":18.2,"tw":10.9,"A":7350,"Ix":181e6,"Sx":868e3,"Zx":981e3,"wt":57},
"W16x77":{"d":414,"bf":256,"tf":16.3,"tw":12.7,"A":9930,"Ix":251e6,"Sx":1210e3,"Zx":1350e3,"wt":77},
"W16x100":{"d":427,"bf":266,"tf":20.6,"tw":15.7,"A":12900,"Ix":348e6,"Sx":1630e3,"Zx":1830e3,"wt":100},
"W18x35":{"d":450,"bf":152,"tf":10.8,"tw":7.6,"A":4520,"Ix":127e6,"Sx":565e3,"Zx":639e3,"wt":35},
"W18x46":{"d":459,"bf":154,"tf":14.6,"tw":9.1,"A":5940,"Ix":174e6,"Sx":758e3,"Zx":858e3,"wt":46},
"W18x55":{"d":459,"bf":191,"tf":16.0,"tw":9.9,"A":7100,"Ix":219e6,"Sx":954e3,"Zx":1070e3,"wt":55},
"W18x65":{"d":466,"bf":192,"tf":19.1,"tw":11.4,"A":8390,"Ix":271e6,"Sx":1160e3,"Zx":1310e3,"wt":65},
"W18x76":{"d":459,"bf":267,"tf":14.4,"tw":11.1,"A":9800,"Ix":305e6,"Sx":1330e3,"Zx":1470e3,"wt":76},
"W18x97":{"d":472,"bf":270,"tf":18.5,"tw":14.0,"A":12500,"Ix":406e6,"Sx":1720e3,"Zx":1920e3,"wt":97},
"W18x119":{"d":480,"bf":274,"tf":22.4,"tw":16.5,"A":15400,"Ix":516e6,"Sx":2150e3,"Zx":2420e3,"wt":119},
"W18x143":{"d":490,"bf":279,"tf":27.0,"tw":19.3,"A":18500,"Ix":640e6,"Sx":2610e3,"Zx":2970e3,"wt":143},
"W18x175":{"d":505,"bf":284,"tf":32.5,"tw":23.4,"A":22600,"Ix":814e6,"Sx":3220e3,"Zx":3700e3,"wt":175},
"W18x211":{"d":523,"bf":290,"tf":38.9,"tw":28.2,"A":27200,"Ix":1020e6,"Sx":3900e3,"Zx":4540e3,"wt":211},
"W21x44":{"d":525,"bf":165,"tf":11.4,"tw":8.9,"A":5680,"Ix":199e6,"Sx":758e3,"Zx":857e3,"wt":44},
"W21x57":{"d":535,"bf":166,"tf":16.5,"tw":10.3,"A":7350,"Ix":289e6,"Sx":1080e3,"Zx":1220e3,"wt":57},
"W21x68":{"d":537,"bf":210,"tf":17.4,"tw":10.9,"A":8770,"Ix":373e6,"Sx":1390e3,"Zx":1550e3,"wt":68},
"W21x83":{"d":544,"bf":212,"tf":21.2,"tw":13.0,"A":10700,"Ix":469e6,"Sx":1720e3,"Zx":1940e3,"wt":83},
"W21x101":{"d":549,"bf":305,"tf":16.5,"tw":12.7,"A":13100,"Ix":583e6,"Sx":2120e3,"Zx":2370e3,"wt":101},
"W21x122":{"d":559,"bf":309,"tf":19.8,"tw":15.2,"A":15700,"Ix":730e6,"Sx":2610e3,"Zx":2930e3,"wt":122},
"W21x147":{"d":569,"bf":312,"tf":24.0,"tw":17.8,"A":19000,"Ix":902e6,"Sx":3170e3,"Zx":3580e3,"wt":147},
"W21x182":{"d":582,"bf":318,"tf":29.5,"tw":21.8,"A":23500,"Ix":1150e6,"Sx":3950e3,"Zx":4500e3,"wt":182},
"W24x55":{"d":599,"bf":178,"tf":12.8,"tw":10.0,"A":7100,"Ix":301e6,"Sx":1010e3,"Zx":1140e3,"wt":55},
"W24x68":{"d":603,"bf":228,"tf":14.9,"tw":10.5,"A":8770,"Ix":419e6,"Sx":1390e3,"Zx":1550e3,"wt":68},
"W24x84":{"d":612,"bf":229,"tf":19.6,"tw":11.9,"A":10800,"Ix":592e6,"Sx":1940e3,"Zx":2180e3,"wt":84},
"W24x103":{"d":623,"bf":229,"tf":24.9,"tw":14.0,"A":13300,"Ix":784e6,"Sx":2520e3,"Zx":2840e3,"wt":103},
"W24x117":{"d":617,"bf":327,"tf":19.1,"tw":14.0,"A":15100,"Ix":892e6,"Sx":2890e3,"Zx":3230e3,"wt":117},
"W24x146":{"d":628,"bf":330,"tf":23.9,"tw":17.0,"A":18800,"Ix":1140e6,"Sx":3630e3,"Zx":4080e3,"wt":146},
"W24x176":{"d":640,"bf":334,"tf":28.7,"tw":19.8,"A":22700,"Ix":1420e6,"Sx":4440e3,"Zx":5030e3,"wt":176},
"W24x207":{"d":653,"bf":339,"tf":33.5,"tw":23.1,"A":26700,"Ix":1720e6,"Sx":5270e3,"Zx":6010e3,"wt":207},
"W24x250":{"d":668,"bf":345,"tf":39.9,"tw":27.7,"A":32300,"Ix":2160e6,"Sx":6470e3,"Zx":7440e3,"wt":250},
"W24x306":{"d":688,"bf":352,"tf":48.3,"tw":33.3,"A":39500,"Ix":2750e6,"Sx":8000e3,"Zx":9310e3,"wt":306},
"W24x370":{"d":706,"bf":360,"tf":57.7,"tw":39.6,"A":47700,"Ix":3450e6,"Sx":9780e3,"Zx":11500e3,"wt":370},
"W27x84":{"d":678,"bf":253,"tf":16.3,"tw":11.7,"A":10800,"Ix":620e6,"Sx":1830e3,"Zx":2060e3,"wt":84},
"W27x102":{"d":688,"bf":255,"tf":20.1,"tw":14.0,"A":13200,"Ix":788e6,"Sx":2290e3,"Zx":2590e3,"wt":102},
"W27x146":{"d":706,"bf":261,"tf":29.5,"tw":18.5,"A":18800,"Ix":1190e6,"Sx":3370e3,"Zx":3840e3,"wt":146},
"W27x194":{"d":729,"bf":269,"tf":38.4,"tw":24.1,"A":25000,"Ix":1680e6,"Sx":4610e3,"Zx":5320e3,"wt":194},
"W27x258":{"d":757,"bf":279,"tf":50.0,"tw":31.5,"A":33200,"Ix":2360e6,"Sx":6240e3,"Zx":7320e3,"wt":258},
"W27x336":{"d":787,"bf":290,"tf":64.3,"tw":40.6,"A":43400,"Ix":3260e6,"Sx":8290e3,"Zx":9870e3,"wt":336},
"W30x90":{"d":753,"bf":267,"tf":14.7,"tw":11.2,"A":11600,"Ix":791e6,"Sx":2100e3,"Zx":2380e3,"wt":90},
"W30x116":{"d":762,"bf":268,"tf":19.8,"tw":14.0,"A":15000,"Ix":1060e6,"Sx":2780e3,"Zx":3150e3,"wt":116},
"W30x148":{"d":777,"bf":272,"tf":25.7,"tw":17.0,"A":19100,"Ix":1410e6,"Sx":3630e3,"Zx":4130e3,"wt":148},
"W30x191":{"d":795,"bf":279,"tf":33.0,"tw":21.6,"A":24600,"Ix":1910e6,"Sx":4810e3,"Zx":5530e3,"wt":191},
"W30x261":{"d":826,"bf":290,"tf":45.0,"tw":28.7,"A":33700,"Ix":2780e6,"Sx":6730e3,"Zx":7830e3,"wt":261},
"W30x357":{"d":864,"bf":305,"tf":60.5,"tw":38.6,"A":46100,"Ix":4030e6,"Sx":9330e3,"Zx":11000e3,"wt":357},
"W33x118":{"d":835,"bf":292,"tf":18.8,"tw":14.0,"A":15200,"Ix":1310e6,"Sx":3140e3,"Zx":3560e3,"wt":118},
"W33x152":{"d":851,"bf":295,"tf":24.9,"tw":17.3,"A":19600,"Ix":1780e6,"Sx":4180e3,"Zx":4760e3,"wt":152},
"W33x201":{"d":874,"bf":302,"tf":32.8,"tw":22.1,"A":25900,"Ix":2470e6,"Sx":5650e3,"Zx":6500e3,"wt":201},
"W33x263":{"d":902,"bf":312,"tf":42.4,"tw":28.4,"A":33900,"Ix":3410e6,"Sx":7560e3,"Zx":8810e3,"wt":263},
"W33x354":{"d":940,"bf":325,"tf":56.1,"tw":37.6,"A":45700,"Ix":4850e6,"Sx":10300e3,"Zx":12200e3,"wt":354},
"W36x135":{"d":903,"bf":304,"tf":20.1,"tw":15.2,"A":17400,"Ix":1640e6,"Sx":3630e3,"Zx":4130e3,"wt":135},
"W36x182":{"d":925,"bf":308,"tf":27.4,"tw":20.1,"A":23500,"Ix":2310e6,"Sx":5000e3,"Zx":5720e3,"wt":182},
"W36x232":{"d":943,"bf":312,"tf":34.8,"tw":25.1,"A":29900,"Ix":3040e6,"Sx":6450e3,"Zx":7440e3,"wt":232},
"W36x302":{"d":968,"bf":318,"tf":44.7,"tw":32.5,"A":39000,"Ix":4150e6,"Sx":8580e3,"Zx":10000e3,"wt":302},
"W36x395":{"d":1003,"bf":328,"tf":57.4,"tw":41.9,"A":51000,"Ix":5680e6,"Sx":11300e3,"Zx":13400e3,"wt":395},
"W36x529":{"d":1048,"bf":340,"tf":75.4,"tw":55.4,"A":68300,"Ix":8040e6,"Sx":15300e3,"Zx":18400e3,"wt":529},
"W40x149":{"d":983,"bf":305,"tf":21.1,"tw":16.0,"A":19200,"Ix":2040e6,"Sx":4150e3,"Zx":4740e3,"wt":149},
"W40x199":{"d":1003,"bf":307,"tf":28.4,"tw":21.1,"A":25700,"Ix":2820e6,"Sx":5630e3,"Zx":6470e3,"wt":199},
"W40x264":{"d":1028,"bf":312,"tf":37.3,"tw":27.7,"A":34100,"Ix":3890e6,"Sx":7570e3,"Zx":8780e3,"wt":264},
"W40x331":{"d":1048,"bf":315,"tf":46.2,"tw":34.3,"A":42700,"Ix":5040e6,"Sx":9620e3,"Zx":11300e3,"wt":331},
"W40x397":{"d":1073,"bf":320,"tf":54.9,"tw":40.9,"A":51200,"Ix":6230e6,"Sx":11600e3,"Zx":13700e3,"wt":397},
"W40x503":{"d":1108,"bf":328,"tf":68.3,"tw":51.3,"A":64900,"Ix":8210e6,"Sx":14800e3,"Zx":17700e3,"wt":503},
"W40x593":{"d":1137,"bf":335,"tf":79.2,"tw":60.5,"A":76500,"Ix":9960e6,"Sx":17500e3,"Zx":21100e3,"wt":593},
},
"European HEA": {
"HEA 100":{"d":96,"bf":100,"tf":8,"tw":5,"A":2124,"Ix":3.49e6,"Sx":72.8e3,"Zx":83.0e3,"wt":16.7},
"HEA 120":{"d":114,"bf":120,"tf":8,"tw":5,"A":2534,"Ix":6.06e6,"Sx":106e3,"Zx":119e3,"wt":19.9},
"HEA 140":{"d":133,"bf":140,"tf":8.5,"tw":5.5,"A":3142,"Ix":10.3e6,"Sx":155e3,"Zx":173e3,"wt":24.7},
"HEA 160":{"d":152,"bf":160,"tf":9,"tw":6,"A":3877,"Ix":16.7e6,"Sx":220e3,"Zx":245e3,"wt":30.4},
"HEA 180":{"d":171,"bf":180,"tf":9.5,"tw":6,"A":4525,"Ix":25.1e6,"Sx":294e3,"Zx":325e3,"wt":35.5},
"HEA 200":{"d":190,"bf":200,"tf":10,"tw":6.5,"A":5383,"Ix":36.9e6,"Sx":389e3,"Zx":429e3,"wt":42.3},
"HEA 220":{"d":210,"bf":220,"tf":11,"tw":7,"A":6434,"Ix":54.1e6,"Sx":515e3,"Zx":568e3,"wt":50.5},
"HEA 240":{"d":230,"bf":240,"tf":12,"tw":7.5,"A":7684,"Ix":77.6e6,"Sx":675e3,"Zx":744e3,"wt":60.3},
"HEA 260":{"d":250,"bf":260,"tf":12.5,"tw":7.5,"A":8682,"Ix":104e6,"Sx":836e3,"Zx":919e3,"wt":68.2},
"HEA 280":{"d":270,"bf":280,"tf":13,"tw":8,"A":9726,"Ix":137e6,"Sx":1010e3,"Zx":1110e3,"wt":76.4},
"HEA 300":{"d":290,"bf":300,"tf":14,"tw":8.5,"A":11253,"Ix":183e6,"Sx":1260e3,"Zx":1380e3,"wt":88.3},
"HEA 320":{"d":310,"bf":300,"tf":15.5,"tw":9,"A":12444,"Ix":229e6,"Sx":1480e3,"Zx":1630e3,"wt":97.6},
"HEA 340":{"d":330,"bf":300,"tf":16.5,"tw":9.5,"A":13347,"Ix":277e6,"Sx":1680e3,"Zx":1850e3,"wt":105},
"HEA 360":{"d":350,"bf":300,"tf":17.5,"tw":10,"A":14286,"Ix":331e6,"Sx":1890e3,"Zx":2090e3,"wt":112},
"HEA 400":{"d":390,"bf":300,"tf":19,"tw":11,"A":15902,"Ix":451e6,"Sx":2310e3,"Zx":2560e3,"wt":125},
"HEA 450":{"d":440,"bf":300,"tf":21,"tw":11.5,"A":17794,"Ix":637e6,"Sx":2900e3,"Zx":3220e3,"wt":140},
"HEA 500":{"d":490,"bf":300,"tf":23,"tw":12,"A":19782,"Ix":869e6,"Sx":3550e3,"Zx":3950e3,"wt":155},
"HEA 550":{"d":540,"bf":300,"tf":24,"tw":12.5,"A":21180,"Ix":1120e6,"Sx":4150e3,"Zx":4620e3,"wt":166},
"HEA 600":{"d":590,"bf":300,"tf":25,"tw":13,"A":22646,"Ix":1410e6,"Sx":4790e3,"Zx":5350e3,"wt":178},
"HEA 650":{"d":640,"bf":300,"tf":26,"tw":13.5,"A":24158,"Ix":1750e6,"Sx":5470e3,"Zx":6140e3,"wt":190},
"HEA 700":{"d":690,"bf":300,"tf":27,"tw":14.5,"A":26042,"Ix":2150e6,"Sx":6240e3,"Zx":7030e3,"wt":204},
"HEA 800":{"d":790,"bf":300,"tf":28,"tw":15,"A":28572,"Ix":3034e6,"Sx":7680e3,"Zx":8700e3,"wt":224},
"HEA 900":{"d":890,"bf":300,"tf":30,"tw":16,"A":32122,"Ix":4222e6,"Sx":9490e3,"Zx":10800e3,"wt":252},
"HEA 1000":{"d":990,"bf":300,"tf":31,"tw":16.5,"A":34682,"Ix":5538e6,"Sx":11200e3,"Zx":12800e3,"wt":272},
},
"European HEB": {
"HEB 100":{"d":100,"bf":100,"tf":10,"tw":6,"A":2604,"Ix":4.50e6,"Sx":89.9e3,"Zx":104e3,"wt":20.4},
"HEB 120":{"d":120,"bf":120,"tf":11,"tw":6.5,"A":3401,"Ix":8.64e6,"Sx":144e3,"Zx":165e3,"wt":26.7},
"HEB 140":{"d":140,"bf":140,"tf":12,"tw":7,"A":4296,"Ix":15.1e6,"Sx":216e3,"Zx":246e3,"wt":33.7},
"HEB 160":{"d":160,"bf":160,"tf":13,"tw":8,"A":5425,"Ix":24.9e6,"Sx":311e3,"Zx":354e3,"wt":42.6},
"HEB 180":{"d":180,"bf":180,"tf":14,"tw":8.5,"A":6525,"Ix":38.3e6,"Sx":426e3,"Zx":481e3,"wt":51.2},
"HEB 200":{"d":200,"bf":200,"tf":15,"tw":9,"A":7808,"Ix":56.9e6,"Sx":570e3,"Zx":642e3,"wt":61.3},
"HEB 220":{"d":220,"bf":220,"tf":16,"tw":9.5,"A":9104,"Ix":80.9e6,"Sx":736e3,"Zx":827e3,"wt":71.5},
"HEB 240":{"d":240,"bf":240,"tf":17,"tw":10,"A":10596,"Ix":112e6,"Sx":938e3,"Zx":1050e3,"wt":83.2},
"HEB 260":{"d":260,"bf":260,"tf":17.5,"tw":10,"A":11845,"Ix":149e6,"Sx":1150e3,"Zx":1280e3,"wt":93.0},
"HEB 280":{"d":280,"bf":280,"tf":18,"tw":10.5,"A":13142,"Ix":193e6,"Sx":1380e3,"Zx":1530e3,"wt":103},
"HEB 300":{"d":300,"bf":300,"tf":19,"tw":11,"A":14908,"Ix":252e6,"Sx":1680e3,"Zx":1870e3,"wt":117},
"HEB 320":{"d":320,"bf":300,"tf":20.5,"tw":11.5,"A":16129,"Ix":308e6,"Sx":1930e3,"Zx":2150e3,"wt":127},
"HEB 340":{"d":340,"bf":300,"tf":21.5,"tw":12,"A":17090,"Ix":367e6,"Sx":2160e3,"Zx":2410e3,"wt":134},
"HEB 360":{"d":360,"bf":300,"tf":22.5,"tw":12.5,"A":18064,"Ix":432e6,"Sx":2400e3,"Zx":2680e3,"wt":142},
"HEB 400":{"d":400,"bf":300,"tf":24,"tw":13.5,"A":19782,"Ix":577e6,"Sx":2880e3,"Zx":3230e3,"wt":155},
"HEB 450":{"d":450,"bf":300,"tf":26,"tw":14,"A":21830,"Ix":799e6,"Sx":3550e3,"Zx":3980e3,"wt":171},
"HEB 500":{"d":500,"bf":300,"tf":28,"tw":14.5,"A":23948,"Ix":1072e6,"Sx":4290e3,"Zx":4820e3,"wt":188},
"HEB 550":{"d":550,"bf":300,"tf":29,"tw":15,"A":25438,"Ix":1367e6,"Sx":4970e3,"Zx":5590e3,"wt":200},
"HEB 600":{"d":600,"bf":300,"tf":30,"tw":15.5,"A":27000,"Ix":1710e6,"Sx":5700e3,"Zx":6420e3,"wt":212},
"HEB 650":{"d":650,"bf":300,"tf":31,"tw":16,"A":28616,"Ix":2107e6,"Sx":6480e3,"Zx":7320e3,"wt":225},
"HEB 700":{"d":700,"bf":300,"tf":32,"tw":17,"A":30642,"Ix":2569e6,"Sx":7340e3,"Zx":8330e3,"wt":241},
"HEB 800":{"d":800,"bf":300,"tf":33,"tw":17.5,"A":33428,"Ix":3591e6,"Sx":8980e3,"Zx":10200e3,"wt":262},
"HEB 900":{"d":900,"bf":300,"tf":35,"tw":18.5,"A":37118,"Ix":4942e6,"Sx":10980e3,"Zx":12600e3,"wt":291},
"HEB 1000":{"d":1000,"bf":300,"tf":36,"tw":19,"A":40048,"Ix":6446e6,"Sx":12900e3,"Zx":14860e3,"wt":314},
},
"European IPE": {
"IPE 80":{"d":80,"bf":46,"tf":5.2,"tw":3.8,"A":764,"Ix":0.80e6,"Sx":20.0e3,"Zx":23.2e3,"wt":6.0},
"IPE 100":{"d":100,"bf":55,"tf":5.7,"tw":4.1,"A":1032,"Ix":1.71e6,"Sx":34.2e3,"Zx":39.4e3,"wt":8.1},
"IPE 120":{"d":120,"bf":64,"tf":6.3,"tw":4.4,"A":1321,"Ix":3.18e6,"Sx":53.0e3,"Zx":60.7e3,"wt":10.4},
"IPE 140":{"d":140,"bf":73,"tf":6.9,"tw":4.7,"A":1643,"Ix":5.41e6,"Sx":77.3e3,"Zx":88.3e3,"wt":12.9},
"IPE 160":{"d":160,"bf":82,"tf":7.4,"tw":5.0,"A":2009,"Ix":8.69e6,"Sx":109e3,"Zx":124e3,"wt":15.8},
"IPE 180":{"d":180,"bf":91,"tf":8.0,"tw":5.3,"A":2395,"Ix":13.2e6,"Sx":146e3,"Zx":166e3,"wt":18.8},
"IPE 200":{"d":200,"bf":100,"tf":8.5,"tw":5.6,"A":2848,"Ix":19.4e6,"Sx":194e3,"Zx":221e3,"wt":22.4},
"IPE 220":{"d":220,"bf":110,"tf":9.2,"tw":5.9,"A":3337,"Ix":27.7e6,"Sx":252e3,"Zx":285e3,"wt":26.2},
"IPE 240":{"d":240,"bf":120,"tf":9.8,"tw":6.2,"A":3912,"Ix":38.9e6,"Sx":324e3,"Zx":367e3,"wt":30.7},
"IPE 270":{"d":270,"bf":135,"tf":10.2,"tw":6.6,"A":4594,"Ix":57.9e6,"Sx":429e3,"Zx":484e3,"wt":36.1},
"IPE 300":{"d":300,"bf":150,"tf":10.7,"tw":7.1,"A":5381,"Ix":83.6e6,"Sx":557e3,"Zx":628e3,"wt":42.2},
"IPE 330":{"d":330,"bf":160,"tf":11.5,"tw":7.5,"A":6261,"Ix":118e6,"Sx":713e3,"Zx":804e3,"wt":49.1},
"IPE 360":{"d":360,"bf":170,"tf":12.7,"tw":8.0,"A":7273,"Ix":163e6,"Sx":904e3,"Zx":1020e3,"wt":57.1},
"IPE 400":{"d":400,"bf":180,"tf":13.5,"tw":8.6,"A":8446,"Ix":231e6,"Sx":1160e3,"Zx":1310e3,"wt":66.3},
"IPE 450":{"d":450,"bf":190,"tf":14.6,"tw":9.4,"A":9882,"Ix":337e6,"Sx":1500e3,"Zx":1700e3,"wt":77.6},
"IPE 500":{"d":500,"bf":200,"tf":16.0,"tw":10.2,"A":11552,"Ix":482e6,"Sx":1930e3,"Zx":2190e3,"wt":90.7},
"IPE 550":{"d":550,"bf":210,"tf":17.2,"tw":11.1,"A":13442,"Ix":671e6,"Sx":2440e3,"Zx":2780e3,"wt":106},
"IPE 600":{"d":600,"bf":220,"tf":19.0,"tw":12.0,"A":15598,"Ix":921e6,"Sx":3070e3,"Zx":3510e3,"wt":122},
},
"British UB": {
"UB 152x89x16":{"d":152.4,"bf":88.7,"tf":7.7,"tw":4.5,"A":2032,"Ix":8.34e6,"Sx":109e3,"Zx":123e3,"wt":16},
"UB 178x102x19":{"d":177.8,"bf":101.2,"tf":7.9,"tw":4.8,"A":2426,"Ix":13.6e6,"Sx":153e3,"Zx":171e3,"wt":19},
"UB 203x102x23":{"d":203.2,"bf":101.8,"tf":9.3,"tw":5.4,"A":2942,"Ix":21.0e6,"Sx":207e3,"Zx":234e3,"wt":23},
"UB 203x133x25":{"d":203.2,"bf":133.2,"tf":7.8,"tw":5.7,"A":3200,"Ix":23.5e6,"Sx":232e3,"Zx":258e3,"wt":25},
"UB 203x133x30":{"d":206.8,"bf":133.9,"tf":9.6,"tw":6.4,"A":3820,"Ix":29.3e6,"Sx":284e3,"Zx":314e3,"wt":30},
"UB 254x102x28":{"d":260.4,"bf":102.2,"tf":10.0,"tw":6.3,"A":3600,"Ix":40.0e6,"Sx":307e3,"Zx":353e3,"wt":28},
"UB 254x146x31":{"d":251.4,"bf":146.1,"tf":8.6,"tw":6.0,"A":3968,"Ix":44.5e6,"Sx":354e3,"Zx":393e3,"wt":31},
"UB 254x146x37":{"d":256.0,"bf":146.4,"tf":10.9,"tw":6.3,"A":4718,"Ix":55.6e6,"Sx":434e3,"Zx":483e3,"wt":37},
"UB 305x102x33":{"d":312.7,"bf":102.4,"tf":10.8,"tw":6.6,"A":4200,"Ix":64.9e6,"Sx":415e3,"Zx":481e3,"wt":33},
"UB 305x165x40":{"d":303.4,"bf":165.0,"tf":10.2,"tw":6.0,"A":5130,"Ix":85.0e6,"Sx":560e3,"Zx":623e3,"wt":40},
"UB 356x171x51":{"d":355.0,"bf":171.5,"tf":11.5,"tw":7.4,"A":6490,"Ix":142e6,"Sx":800e3,"Zx":895e3,"wt":51},
"UB 406x178x60":{"d":406.4,"bf":177.9,"tf":12.8,"tw":7.9,"A":7640,"Ix":215e6,"Sx":1060e3,"Zx":1190e3,"wt":60},
"UB 457x191x67":{"d":453.4,"bf":189.9,"tf":12.7,"tw":8.5,"A":8550,"Ix":294e6,"Sx":1300e3,"Zx":1450e3,"wt":67},
"UB 457x191x82":{"d":460.0,"bf":191.3,"tf":16.0,"tw":9.9,"A":10400,"Ix":371e6,"Sx":1610e3,"Zx":1810e3,"wt":82},
"UB 533x210x92":{"d":533.1,"bf":209.3,"tf":15.6,"tw":10.1,"A":11700,"Ix":554e6,"Sx":2080e3,"Zx":2360e3,"wt":92},
"UB 610x229x113":{"d":607.6,"bf":228.2,"tf":17.3,"tw":11.1,"A":14400,"Ix":874e6,"Sx":2880e3,"Zx":3280e3,"wt":113},
"UB 686x254x140":{"d":683.5,"bf":253.7,"tf":19.0,"tw":12.4,"A":17800,"Ix":1360e6,"Sx":3990e3,"Zx":4560e3,"wt":140},
"UB 762x267x173":{"d":762.2,"bf":266.7,"tf":21.6,"tw":14.3,"A":22100,"Ix":2050e6,"Sx":5390e3,"Zx":6200e3,"wt":173},
"UB 914x419x388":{"d":921.0,"bf":420.5,"tf":36.6,"tw":21.4,"A":49400,"Ix":7200e6,"Sx":15600e3,"Zx":17700e3,"wt":388},
},
"British UC": {
"UC 152x152x23":{"d":152.4,"bf":152.2,"tf":6.8,"tw":5.8,"A":2940,"Ix":12.5e6,"Sx":164e3,"Zx":182e3,"wt":23},
"UC 152x152x30":{"d":157.6,"bf":152.9,"tf":9.4,"tw":6.5,"A":3830,"Ix":17.5e6,"Sx":222e3,"Zx":248e3,"wt":30},
"UC 152x152x37":{"d":161.8,"bf":154.4,"tf":11.5,"tw":8.0,"A":4720,"Ix":22.2e6,"Sx":274e3,"Zx":309e3,"wt":37},
"UC 203x203x46":{"d":203.2,"bf":203.6,"tf":11.0,"tw":7.2,"A":5870,"Ix":45.8e6,"Sx":451e3,"Zx":497e3,"wt":46},
"UC 203x203x60":{"d":209.6,"bf":205.8,"tf":14.2,"tw":9.4,"A":7640,"Ix":61.2e6,"Sx":584e3,"Zx":652e3,"wt":60},
"UC 254x254x73":{"d":254.1,"bf":254.6,"tf":14.2,"tw":8.6,"A":9320,"Ix":114e6,"Sx":898e3,"Zx":992e3,"wt":73},
"UC 254x254x89":{"d":260.3,"bf":256.3,"tf":17.3,"tw":10.3,"A":11400,"Ix":143e6,"Sx":1100e3,"Zx":1220e3,"wt":89},
"UC 305x305x97":{"d":307.9,"bf":305.3,"tf":15.4,"tw":9.9,"A":12300,"Ix":222e6,"Sx":1440e3,"Zx":1590e3,"wt":97},
"UC 305x305x118":{"d":314.5,"bf":307.4,"tf":18.7,"tw":12.0,"A":15000,"Ix":277e6,"Sx":1760e3,"Zx":1950e3,"wt":118},
"UC 356x406x235":{"d":381.0,"bf":394.8,"tf":30.2,"tw":18.4,"A":29900,"Ix":790e6,"Sx":4150e3,"Zx":4690e3,"wt":235},
},
}

total_sections = sum(len(s) for s in SECTIONS.values())

def calc_buildup(d, bf_top, tf_top, bf_bot, tf_bot, tw):
    """Calculate built-up asymmetric I-section properties"""
    hw = d - tf_top - tf_bot
    A_top = bf_top * tf_top
    A_bot = bf_bot * tf_bot
    A_web = hw * tw
    A = A_top + A_bot + A_web
    # Centroid from bottom fiber
    y_bot = (A_bot*tf_bot/2 + A_web*(tf_bot+hw/2) + A_top*(d-tf_top/2)) / A
    # Moment of inertia about centroidal axis
    Ix = (bf_bot*tf_bot**3/12 + A_bot*(y_bot-tf_bot/2)**2 +
          tw*hw**3/12 + A_web*(y_bot-tf_bot-hw/2)**2 +
          bf_top*tf_top**3/12 + A_top*(d-tf_top/2-y_bot)**2)
    Sx = min(Ix/y_bot, Ix/(d-y_bot))
    # Plastic modulus (approximate for asymmetric)
    Zx = A_bot*(y_bot-tf_bot/2) + A_web*abs(y_bot-tf_bot-hw/2)/2*2 + A_top*(d-tf_top/2-y_bot)
    return {"d":d,"bf":bf_bot,"tf":tf_bot,"tw":tw,"A":A,"Ix":Ix,"Sx":Sx,"Zx":Zx*1.1,"wt":A*7850/1e6,
            "bf_top":bf_top,"tf_top":tf_top,"y_bar":y_bot,"is_buildup":True}

def calc_beff(L, spacing, edge_dist, beam_position):
    """
    Calculate effective slab width per AISC 360-16 §I3.1a
    
    Parameters:
    - L: beam span (m)
    - spacing: beam spacing (m)
    - edge_dist: distance to slab edge for exterior beams (m)
    - beam_position: "Interior" or "Exterior"
    
    Returns: beff in mm
    
    Per AISC 360-16 §I3.1a:
    For interior beams: beff = min(L/4, so) on each side, total = 2 × min(L/4, so/2)
    For exterior beams: beff = min(L/8, edge_dist) on edge + min(L/8, so/2) on interior
    
    Simplified for typical cases:
    Interior: beff = min(L/4, spacing)
    Exterior: beff = min(L/8 + spacing/2, L/4, spacing/2 + edge_dist)
    """
    L_mm = L * 1000  # Convert to mm
    spacing_mm = spacing * 1000
    edge_mm = edge_dist * 1000
    
    if beam_position == "Interior":
        # Each side: min(L/8, spacing/2)
        b_each_side = min(L_mm/8, spacing_mm/2)
        beff = 2 * b_each_side
    else:  # Exterior
        # Interior side: min(L/8, spacing/2)
        b_interior = min(L_mm/8, spacing_mm/2)
        # Edge side: min(L/8, edge distance)
        b_edge = min(L_mm/8, edge_mm)
        beff = b_interior + b_edge
    
    return beff

def calc_stud(dia, height, Fu, fc, Rg, Rp):
    """Calculate shear stud capacity per AISC 360-16 §I8.2a"""
    Asa = math.pi * dia**2 / 4
    Ec = 4700 * math.sqrt(fc)  # ACI 318 normal weight
    Qn_conc = 0.5 * Asa * math.sqrt(fc * Ec)  # Eq. I8-1
    Qn_steel = Rg * Rp * Asa * Fu  # Eq. I8-2
    Qn = min(Qn_conc, Qn_steel)
    return {"Asa":Asa, "Qn":Qn, "Qn_conc":Qn_conc, "Qn_steel":Qn_steel, 
            "gov":"Concrete" if Qn_conc < Qn_steel else "Steel", "Hd":height/dia}

def check_precomposite(sec, Fy, w_precomp, L, method, phi_b):
    """
    Pre-composite (construction stage) check
    Steel beam alone under wet concrete + construction load
    
    Returns dict with Mu, Mn, DCR, status, deflection
    """
    Ix = sec["Ix"]
    Zx = sec["Zx"]
    Sx = sec["Sx"]
    d = sec["d"]
    tw = sec["tw"]
    tf = sec.get("tf", sec.get("tf_top", 10))
    hw = d - 2*tf
    
    # Demands
    Mu_pre = w_precomp * L**2 / 8  # kN-m
    Vu_pre = w_precomp * L / 2  # kN
    
    # Capacities (assuming compact section for simplicity)
    Mp = Zx * Fy / 1e6  # kN-m (Zx in mm³, Fy in MPa)
    Mn_pre = Mp  # Nominal for compact
    
    # Shear
    Vn_pre = 0.6 * Fy * hw * tw / 1000  # kN
    
    # Apply resistance factor
    phi_Mn = phi_b * Mn_pre
    phi_v = 1.0 if method == "LRFD" else 1/1.50
    phi_Vn = phi_v * Vn_pre
    
    # Deflection under wet concrete (unfactored)
    # Assume wet concrete load = self-weight + slab weight portion of DL
    delta_pre = 5 * w_precomp * L**4 / (384 * 200000 * Ix) * 1e9  # mm
    delta_limit_pre = L * 1000 / 360  # mm
    
    DCR_flex_pre = Mu_pre / phi_Mn
    DCR_shear_pre = Vu_pre / phi_Vn
    DCR_defl_pre = delta_pre / delta_limit_pre
    
    return {
        "Mu_pre": Mu_pre,
        "Vu_pre": Vu_pre,
        "phi_Mn_pre": phi_Mn,
        "phi_Vn_pre": phi_Vn,
        "delta_pre": delta_pre,
        "delta_limit_pre": delta_limit_pre,
        "DCR_flex_pre": DCR_flex_pre,
        "DCR_shear_pre": DCR_shear_pre,
        "DCR_defl_pre": DCR_defl_pre,
        "flex_ok": DCR_flex_pre <= 1.0,
        "shear_ok": DCR_shear_pre <= 1.0,
        "defl_ok": DCR_defl_pre <= 1.0
    }

def run_composite_analysis(sec, Fy, fc, tc, beff, L, w_DL, w_SDL, w_LL, studs, method, phi_b, phi_v):
    """
    Composite stage analysis per AISC 360-16 Chapter I
    
    Loads:
    - w_DL: Dead load (beam self-weight + slab) - applied pre-composite
    - w_SDL: Superimposed dead load - applied composite
    - w_LL: Live load - applied composite
    """
    d = sec["d"]
    A = sec["A"]
    Ix = sec["Ix"]
    Zx = sec["Zx"]
    tw = sec["tw"]
    tf = sec.get("tf", sec.get("tf_top", 10))
    
    # Material properties
    Ec = 4700 * math.sqrt(fc)  # MPa (ACI 318)
    Es = 200000  # MPa
    n = Es / Ec  # Modular ratio
    
    # Composite section properties
    Ac = beff * tc  # mm²
    
    # Compression forces
    Cc = 0.85 * fc * Ac / 1000  # kN - Concrete compression
    Ts = Fy * A / 1000  # kN - Steel tension
    
    # Shear connection
    Qn_total = studs["n"] * studs["Qn"] / 1000  # kN - Total stud capacity
    
    # Composite action
    C_min = min(Cc, Ts, Qn_total)
    comp_ratio = min(1.0, Qn_total / min(Cc, Ts))
    comp_type = "Partial" if comp_ratio < 1 else "Full"
    
    # Composite moment capacity (plastic stress distribution)
    if C_min == Cc or C_min == Qn_total:
        # Concrete or studs govern - PNA in steel
        a = C_min * 1000 / (0.85 * fc * beff)  # mm - stress block depth
        Mn = C_min * (d/2 + tc - a/2) / 1000  # kN-m
    else:
        # Steel governs
        Mn = (Zx * Fy / 1e6) + C_min * (d/2 + tc/2) / 1000  # kN-m
    
    # Steel beam plastic moment
    Mp_steel = Zx * Fy / 1e6  # kN-m
    
    # Transformed moment of inertia (lower bound for deflections)
    Y1 = d/2  # Distance to steel centroid
    Itr = Ix + A*(Y1 + tc/2)**2 + (beff*tc**3/12 + beff*tc*(tc/2)**2)/n
    
    # Effective moment of inertia (AISC 360-16 §I3.2)
    Ieff = Ix + (Itr - Ix) * comp_ratio**0.5
    
    # Load combinations
    # LRFD: 1.2D + 1.6L (ASCE 7-22)
    # ASD: D + L
    if method == "LRFD":
        w_u = 1.2 * (w_DL + w_SDL) + 1.6 * w_LL
    else:
        w_u = w_DL + w_SDL + w_LL
    
    # Demands (composite stage: SDL + LL on composite section)
    w_composite = w_SDL + w_LL
    if method == "LRFD":
        w_composite_factored = 1.2 * w_SDL + 1.6 * w_LL
    else:
        w_composite_factored = w_SDL + w_LL
    
    # Total factored moment (DL on steel, SDL+LL on composite)
    Mu_DL = (1.2 if method == "LRFD" else 1.0) * w_DL * L**2 / 8
    Mu_comp = w_composite_factored * L**2 / 8
    Mu_total = Mu_DL + Mu_comp  # This is simplified; actual should use superposition
    
    # For simplicity, use total factored load
    Mu = w_u * L**2 / 8
    Vu = w_u * L / 2
    
    # Shear capacity (steel web only)
    hw = d - 2*tf
    Vn = 0.6 * Fy * hw * tw / 1000  # kN
    
    # Deflections (unfactored, service loads)
    # Dead load: on steel section alone (pre-composite)
    delta_DL = 5 * w_DL * L**4 / (384 * Es * Ix) * 1e9  # mm
    # SDL: on composite section
    delta_SDL = 5 * w_SDL * L**4 / (384 * Es * Ieff) * 1e9  # mm
    # Live load: on composite section
    delta_LL = 5 * w_LL * L**4 / (384 * Es * Ieff) * 1e9  # mm
    
    # Limits
    delta_total = delta_DL + delta_SDL + delta_LL
    delta_limit_total = L * 1000 / 240  # L/240 for total
    delta_limit_LL = L * 1000 / 360  # L/360 for live load
    
    # DCRs
    phi_Mn = phi_b * Mn
    phi_Vn = phi_v * Vn
    
    DCR_flex = Mu / phi_Mn
    DCR_shear = Vu / phi_Vn
    DCR_defl_LL = delta_LL / delta_limit_LL
    DCR_defl_total = delta_total / delta_limit_total
    
    return {
        "Mn": Mn, "Mp_steel": Mp_steel, "Mu": Mu,
        "Vn": Vn, "Vu": Vu,
        "delta_DL": delta_DL, "delta_SDL": delta_SDL, "delta_LL": delta_LL,
        "delta_total": delta_total,
        "delta_limit_LL": delta_limit_LL, "delta_limit_total": delta_limit_total,
        "comp_type": comp_type, "comp_ratio": comp_ratio,
        "Ieff": Ieff, "Itr": Itr,
        "Cc": Cc, "Ts": Ts, "Qn_total": Qn_total,
        "DCR_flex": DCR_flex, "DCR_shear": DCR_shear,
        "DCR_defl_LL": DCR_defl_LL, "DCR_defl_total": DCR_defl_total,
        "phi_Mn": phi_Mn, "phi_Vn": phi_Vn
    }

# ============== UI ==============
st.markdown('<h1 style="text-align:center;color:#1E3A5F;">🏗️ CompositeBeam Pro v3.0</h1>', unsafe_allow_html=True)
st.caption(f"AISC 360-16 Composite Beam Design | AISI S100-16 Metal Deck | {total_sections} sections")

with st.sidebar:
    st.header("📐 Design Parameters")
    
    # ============== DESIGN MODE TOGGLE ==============
    with st.expander("🔄 DESIGN MODE", expanded=True):
        design_mode = st.radio(
            "Floor System Type",
            ["Composite", "Non-Composite"],
            horizontal=True,
            help="Composite: Beam + slab act together via shear studs\nNon-Composite: Beam and slab designed independently"
        )
        
        if design_mode == "Composite":
            st.success("✅ **Composite Action** - Shear studs transfer forces between beam and slab")
        else:
            st.info("ℹ️ **Non-Composite** - Steel beam carries all loads, slab is one-way RC slab")
    
    with st.expander("🔧 Method", expanded=True):
        method = st.radio("Design Method", ["LRFD", "ASD"], horizontal=True)
        phi_b = 0.90 if method == "LRFD" else 1/1.67
        phi_v = 1.00 if method == "LRFD" else 1/1.50
    
    with st.expander("📏 Geometry", expanded=True):
        L = st.number_input("Span L (m)", 4.0, 20.0, 9.0, 0.5)
        spacing = st.number_input("Beam Spacing (m)", 1.5, 5.0, 3.0, 0.25)
        beam_position = st.radio("Beam Position", ["Interior", "Exterior"], horizontal=True)
        if beam_position == "Exterior":
            edge_dist = st.number_input("Edge Distance (m)", 0.1, 3.0, 0.5, 0.1)
        else:
            edge_dist = spacing / 2  # Not used for interior
    
    with st.expander("🏗️ Steel Section", expanded=True):
        sec_type = st.radio("Section Type", ["Standard", "Built-up Asymmetric", "Castellated/Cellular"])
        
        # Initialize castellated variables
        castellated_enabled = False
        cast_beam_type = "Castellated"
        cast_parent_name = "W530x82"
        cast_ho, cast_e, cast_b, cast_S = 320, 140, 100, 380
        cast_Do = 300
        
        if sec_type == "Standard":
            family = st.selectbox("Section Family", list(SECTIONS.keys()))
            sec_name = st.selectbox("Section", list(SECTIONS[family].keys()))
            sec = SECTIONS[family][sec_name].copy()
            sec["is_buildup"] = False
            grade = st.selectbox("Steel Grade", list(STEEL_GRADES.keys()), index=2)
            Fy = STEEL_GRADES[grade]["Fy"]
            Fu = STEEL_GRADES[grade]["Fu"]
            st.caption(f"Fy = {Fy} MPa | Fu = {Fu} MPa")
            
        elif sec_type == "Built-up Asymmetric":
            d_bu = st.number_input("Depth d (mm)", 200, 1500, 500, 10)
            tw_bu = st.number_input("Web tw (mm)", 6, 40, 10, 1)
            st.markdown("**Top Flange (compression)**")
            bf_top = st.number_input("bf_top (mm)", 100, 600, 200, 10)
            tf_top = st.number_input("tf_top (mm)", 8, 60, 12, 1)
            st.markdown("**Bottom Flange (tension)**")
            bf_bot = st.number_input("bf_bot (mm)", 100, 600, 250, 10)
            tf_bot = st.number_input("tf_bot (mm)", 8, 60, 16, 1)
            grade = st.selectbox("Steel Grade", list(STEEL_GRADES.keys()), index=2)
            Fy = STEEL_GRADES[grade]["Fy"]
            Fu = STEEL_GRADES[grade]["Fu"]
            sec = calc_buildup(d_bu, bf_top, tf_top, bf_bot, tf_bot, tw_bu)
            sec_name = f"Built-up {d_bu}×{bf_bot}×{tf_bot}/{tw_bu}/{bf_top}×{tf_top}"
            st.caption(f"A = {sec['A']:.0f} mm² | Ix = {sec['Ix']/1e6:.2f}×10⁶ mm⁴")
            
        else:  # Castellated/Cellular
            if not CASTELLATED_AVAILABLE:
                st.warning(f"Castellated module not available: {CASTELLATED_ERROR}")
            else:
                castellated_enabled = True
                cast_beam_type = st.radio("Beam Type", ["Castellated", "Cellular"], horizontal=True, key="cast_type")
                
                st.markdown("**Parent Section**")
                parent_source = st.radio("Parent Section Source", 
                                        ["Standard Section", "Built-up Section"], 
                                        horizontal=True, key="cast_parent_source")
                
                if parent_source == "Standard Section":
                    cast_family = st.selectbox("Section Family", list(SECTIONS.keys()), key="cast_family")
                    cast_parent_name = st.selectbox("Section", list(SECTIONS[cast_family].keys()), key="cast_sec")
                    cast_parent_dict = SECTIONS[cast_family][cast_parent_name]
                    
                    # Create ParentSection from dict - handle all section types
                    cast_parent = ParentSection.from_dict(cast_parent_name, cast_parent_dict)
                    
                else:  # Built-up section for castellated/cellular
                    st.markdown("*Define symmetric built-up I-section:*")
                    bu_d = st.number_input("Depth d (mm)", 200, 1500, 500, 10, key="cast_bu_d")
                    bu_bf = st.number_input("Flange width bf (mm)", 80, 600, 200, 10, key="cast_bu_bf")
                    bu_tf = st.number_input("Flange thickness tf (mm)", 6, 60, 16, 1, key="cast_bu_tf")
                    bu_tw = st.number_input("Web thickness tw (mm)", 4, 40, 10, 1, key="cast_bu_tw")
                    
                    # Calculate properties for built-up section
                    bu_A = 2 * bu_bf * bu_tf + (bu_d - 2*bu_tf) * bu_tw
                    bu_Ix = (bu_bf * bu_d**3 - (bu_bf - bu_tw) * (bu_d - 2*bu_tf)**3) / 12
                    bu_Sx = bu_Ix / (bu_d / 2)
                    bu_Zx = bu_Sx * 1.12  # Approximate shape factor
                    bu_ry = bu_bf / 4  # Approximate
                    bu_wt = bu_A * 7850 / 1e6  # Calculate weight from area
                    
                    cast_parent_name = f"Built-up {bu_d}×{bu_bf}×{bu_tf}/{bu_tw}"
                    cast_parent = ParentSection(
                        designation=cast_parent_name,
                        d=bu_d, bf=bu_bf, tf=bu_tf, tw=bu_tw,
                        A=bu_A, Ix=bu_Ix, Sx=bu_Sx, Zx=bu_Zx,
                        ry=bu_ry, J=0, Cw=0, wt=bu_wt
                    )
                    st.caption(f"A = {bu_A:.0f} mm² | Ix = {bu_Ix/1e6:.2f}×10⁶ mm⁴")
                
                grade = st.selectbox("Steel Grade", list(STEEL_GRADES.keys()), index=2, key="cast_grade")
                Fy = STEEL_GRADES[grade]["Fy"]
                Fu = STEEL_GRADES[grade]["Fu"]
                
                # Display parent properties
                st.caption(f"Parent: d={cast_parent.d:.0f}mm, bf={cast_parent.bf:.0f}mm, tf={cast_parent.tf:.1f}mm, tw={cast_parent.tw:.1f}mm")
                
                # Check minimum parent depth for castellated/cellular
                min_parent_depth = 150  # mm - practical minimum for castellated beams
                if cast_parent.d < min_parent_depth:
                    st.warning(f"⚠️ Parent depth ({cast_parent.d:.0f}mm) is below recommended minimum ({min_parent_depth}mm) for castellated/cellular beams")
                
                st.markdown("**Opening Geometry**")
                
                # Calculate dynamic limits based on parent section
                d_parent = cast_parent.d
                tf_parent = cast_parent.tf
                tw_parent = cast_parent.tw
                
                # Min opening height: ensure tee depth > tf + 2*tw (stability requirement)
                min_tee_depth = tf_parent + 3 * tw_parent
                min_ho_for_tee = d_parent - 2 * min_tee_depth  # Ensure adequate tee
                
                # Practical limits for openings
                ho_min = max(50, int(d_parent * 0.35))  # At least 35% of depth or 50mm
                ho_max = min(int(d_parent * 0.9), int(d_parent - 2 * min_tee_depth))  # Leave room for tees
                ho_max = max(ho_max, ho_min + 20)  # Ensure valid range
                
                if cast_beam_type == "Castellated":
                    # Default values based on parent depth (targeting ~50% expansion)
                    default_ho = max(ho_min, min(int(d_parent * 0.55), ho_max))
                    default_e = max(30, int(default_ho * 0.4))
                    default_b = max(int(3 * tw_parent + 5), int(default_ho * 0.25), 40)
                    
                    cast_ho = st.number_input(
                        "Opening Height ho (mm)", 
                        value=default_ho, 
                        min_value=ho_min, 
                        max_value=ho_max, 
                        step=10, 
                        key="cast_ho",
                        help=f"Recommended: {int(d_parent*0.5)}-{int(d_parent*0.7)}mm for typical 1.3-1.5× expansion"
                    )
                    
                    # Half-length limits
                    e_min = max(30, int(cast_ho * 0.2))
                    e_max = max(int(cast_ho * 0.6), e_min + 20)
                    default_e = max(e_min, min(int(cast_ho * 0.4), e_max))
                    
                    cast_e = st.number_input(
                        "Half-length e (mm)", 
                        value=default_e, 
                        min_value=e_min, 
                        max_value=e_max, 
                        step=10, 
                        key="cast_e",
                        help="Horizontal projection of opening (e/ho typically 0.25-0.50)"
                    )
                    
                    # Web post width limits
                    b_min = max(int(3 * tw_parent), 30)
                    b_max = max(int(cast_ho * 0.5), b_min + 50)
                    default_b = max(b_min, min(int(cast_ho * 0.3), b_max))
                    
                    cast_b = st.number_input(
                        "Web Post Width b (mm)", 
                        value=default_b, 
                        min_value=b_min, 
                        max_value=b_max, 
                        step=10, 
                        key="cast_b",
                        help=f"Minimum: 3×tw = {int(3*tw_parent)}mm"
                    )
                    
                    cast_theta = st.number_input("Cutting Angle θ (°)", value=60, min_value=45, max_value=70, step=5, key="cast_theta")
                    cast_S = 2 * cast_e + cast_b  # Auto-calculate spacing
                    cast_Do = 0  # Not used for castellated beams
                    st.caption(f"Spacing S = 2e + b = {cast_S:.0f} mm")
                    
                    # Calculate expanded depth
                    cast_dg = d_parent + cast_ho / 2
                    expansion_ratio = cast_dg / d_parent
                    st.info(f"**Expanded depth: dg = {cast_dg:.0f} mm** ({expansion_ratio:.2f}× parent)")
                    
                    # Quick dimension checks with traffic light indicators
                    ho_dg_ratio = cast_ho / cast_dg
                    dt = (cast_dg - cast_ho) / 2
                    
                    col_check1, col_check2 = st.columns(2)
                    with col_check1:
                        if 0.4 <= ho_dg_ratio <= 0.7:
                            st.success(f"✓ ho/dg = {ho_dg_ratio:.2f}")
                        elif 0.35 <= ho_dg_ratio <= 0.75:
                            st.warning(f"⚠️ ho/dg = {ho_dg_ratio:.2f}")
                        else:
                            st.error(f"✗ ho/dg = {ho_dg_ratio:.2f}")
                    with col_check2:
                        if 1.3 <= expansion_ratio <= 1.6:
                            st.success(f"✓ Exp = {expansion_ratio:.2f}×")
                        elif 1.2 <= expansion_ratio <= 1.7:
                            st.warning(f"⚠️ Exp = {expansion_ratio:.2f}×")
                        else:
                            st.error(f"✗ Exp = {expansion_ratio:.2f}×")
                    
                else:  # Cellular
                    # Default values for cellular beam
                    default_Do = max(ho_min, min(int(d_parent * 0.55), ho_max))
                    
                    cast_Do = st.number_input(
                        "Opening Diameter Do (mm)", 
                        value=default_Do, 
                        min_value=ho_min, 
                        max_value=ho_max, 
                        step=10, 
                        key="cast_Do",
                        help=f"Recommended: {int(d_parent*0.5)}-{int(d_parent*0.7)}mm"
                    )
                    
                    # Spacing limits for cellular
                    S_min = max(int(cast_Do * 1.1), cast_Do + int(3 * tw_parent))
                    S_max = max(int(cast_Do * 2.0), S_min + 50)
                    default_S = max(S_min, min(int(cast_Do * 1.3), S_max))
                    
                    cast_S = st.number_input(
                        "Opening Spacing S (mm)", 
                        value=default_S, 
                        min_value=S_min, 
                        max_value=S_max, 
                        step=10, 
                        key="cast_S_cell",
                        help="S/Do typically 1.1-1.8"
                    )
                    
                    cast_ho = cast_Do
                    cast_e = cast_Do / 2
                    cast_b = cast_S - cast_Do
                    cast_theta = 0  # Not applicable for cellular
                    
                    # Calculate expanded depth
                    cast_dg = d_parent + cast_Do / 2
                    expansion_ratio = cast_dg / d_parent
                    st.info(f"**Expanded depth: dg = {cast_dg:.0f} mm** ({expansion_ratio:.2f}× parent)")
                    
                    # Quick dimension checks
                    ho_dg_ratio = cast_Do / cast_dg
                    S_Do_ratio = cast_S / cast_Do
                    
                    col_check1, col_check2 = st.columns(2)
                    with col_check1:
                        if 0.4 <= ho_dg_ratio <= 0.7:
                            st.success(f"✓ Do/dg = {ho_dg_ratio:.2f}")
                        elif 0.35 <= ho_dg_ratio <= 0.8:
                            st.warning(f"⚠️ Do/dg = {ho_dg_ratio:.2f}")
                        else:
                            st.error(f"✗ Do/dg = {ho_dg_ratio:.2f}")
                    with col_check2:
                        if cast_b >= 0.25 * cast_Do:
                            st.success(f"✓ b = {cast_b:.0f}mm")
                        else:
                            st.error(f"✗ b = {cast_b:.0f}mm < {0.25*cast_Do:.0f}")
                
                # Use expanded section for composite analysis
                sec = {
                    'd': cast_dg,
                    'bf': cast_parent.bf,
                    'tf': cast_parent.tf,
                    'tw': cast_parent.tw,
                    'A': cast_parent.A,
                    'Ix': cast_parent.Ix * (cast_dg / cast_parent.d)**2,  # Scale approximately
                    'Sx': cast_parent.Sx * (cast_dg / cast_parent.d)**1.5,
                    'Zx': cast_parent.Zx * (cast_dg / cast_parent.d)**1.5,
                    'ry': cast_parent.ry,
                    'wt': cast_parent.wt,
                    'is_buildup': False
                }
                sec_name = f"{cast_beam_type} from {cast_parent_name}"
    
    with st.expander("🧱 Concrete Slab", expanded=True):
        fc = st.number_input("f'c (MPa)", 20, 50, 28, 1)
        tc = st.number_input("Slab Thickness tc (mm)", 75, 200, 130, 5)
        # Auto-calculate beff
        beff = calc_beff(L, spacing, edge_dist, beam_position)
        st.info(f"**beff = {beff:.0f} mm** (auto per §I3.1a)")
        st.caption(f"L/4 = {L*1000/4:.0f} mm | spacing = {spacing*1000:.0f} mm")
    
    # ============== SHEAR STUDS (Composite Only) ==============
    if design_mode == "Composite":
        with st.expander("🔩 Shear Studs", expanded=True):
            stud_dia = st.number_input("Diameter (mm)", 10, 30, 19, 1)
            stud_ht = st.number_input("Height (mm)", 50, 200, 100, 5)
            stud_Fu = st.number_input("Fu (MPa)", 400, 550, 450, 10)
            st.caption(f"Asa = {math.pi*stud_dia**2/4:.1f} mm² | H/d = {stud_ht/stud_dia:.2f}")
            
            deck = st.selectbox("Deck Orientation", ["Perpendicular", "Parallel"])
            spr = st.selectbox("Studs per Rib", [1, 2, 3])
            Rg = [1.0, 0.85, 0.7][spr-1] if deck == "Perpendicular" else 1.0
            Rp = 0.75 if deck == "Perpendicular" or stud_ht/stud_dia >= 4 else 0.6
            st.caption(f"Rg = {Rg} | Rp = {Rp}")
            
            stud_r = calc_stud(stud_dia, stud_ht, stud_Fu, fc, Rg, Rp)
            n_studs = st.number_input("Studs per Half Span", 5, 100, 20, 1)
            st.success(f"**Qn = {stud_r['Qn']/1000:.2f} kN** ({stud_r['gov']})")
    else:
        # Non-composite - set default values (not used but needed for variable consistency)
        stud_dia, stud_ht, stud_Fu = 19, 100, 450
        Rg, Rp = 1.0, 0.75
        stud_r = {'Qn': 0, 'gov': 'N/A'}
        n_studs = 0
    
    # ============== UNIFIED LOAD INPUTS ==============
    with st.expander("📊 LOADS (All Design Stages)", expanded=True):
        st.markdown("### Area Loads (kN/m²)")
        st.caption("Enter loads per unit area - automatically converted to line loads using beam spacing")
        
        col_ld1, col_ld2 = st.columns(2)
        
        with col_ld1:
            st.markdown("**Dead Loads**")
            w_slab = st.number_input("Slab + Deck Weight (kN/m²)", 1.0, 10.0, 3.5, 0.1, 
                                     help="Wet concrete + metal deck self-weight")
            w_SDL_area = st.number_input("Superimposed DL (kN/m²)", 0.0, 10.0, 1.0, 0.25,
                                         help="Finishes, partitions, MEP, ceilings")
        
        with col_ld2:
            st.markdown("**Live Loads**")
            w_LL_area = st.number_input("Live Load (kN/m²)", 1.0, 25.0, 5.0, 0.5,
                                        help="Occupancy load per floor use")
            w_const_area = st.number_input("Construction LL (kN/m²)", 0.5, 5.0, 1.0, 0.25,
                                           help="Workers, equipment during concrete pour")
        
        st.markdown("---")
        
        # Auto-calculate beam self-weight
        w_beam = sec.get("wt", sec["A"]*7850/1e6) * 9.81 / 1000  # kN/m
        
        # Convert area loads to line loads (kN/m) for beam design
        w_slab_line = w_slab * spacing
        w_SDL = w_SDL_area * spacing
        w_LL = w_LL_area * spacing
        w_const = w_const_area * spacing
        
        # Total dead load on beam
        w_DL = w_beam + w_slab_line
        
        # Display calculated line loads
        st.markdown("### Line Loads on Beam (kN/m)")
        st.caption(f"Beam spacing = {spacing:.2f} m")
        
        col_ld3, col_ld4 = st.columns(2)
        with col_ld3:
            st.markdown(f"""
| Load Component | Value |
|----------------|-------|
| Beam self-weight | {w_beam:.2f} kN/m |
| Slab tributary ({w_slab:.1f} × {spacing:.2f}) | {w_slab_line:.2f} kN/m |
| **Total DL** | **{w_DL:.2f} kN/m** |
| Construction LL | {w_const:.2f} kN/m |
            """)
        
        with col_ld4:
            st.markdown(f"""
| Load Component | Value |
|----------------|-------|
| Superimposed DL | {w_SDL:.2f} kN/m |
| Live Load | {w_LL:.2f} kN/m |
| **Pre-Composite** | **{w_DL + w_const:.2f} kN/m** |
| **Composite** | **{w_DL + w_SDL + w_LL:.2f} kN/m** |
            """)
        
        # Store for use in metal deck (area loads)
        deck_DL = w_slab  # Wet concrete + deck (kN/m²)
        deck_const_LL = w_const_area  # Construction LL (kN/m²)
        deck_w_const = deck_DL + deck_const_LL  # Total for deck design
        
        # ============== AXIAL LOAD (Temperature Effects) ==============
        st.markdown("---")
        st.markdown("### Axial Force on Steel Beam (Optional)")
        st.caption("For temperature straining, frame action, or other axial effects")
        
        col_ax1, col_ax2 = st.columns(2)
        with col_ax1:
            P_temp = st.number_input("Axial Force P (kN)", -5000.0, 5000.0, 0.0, 10.0,
                                     help="Positive = Compression, Negative = Tension")
        with col_ax2:
            axial_load_case = st.selectbox("Load Case", 
                                           ["Permanent (DL)", "Transient (Temp)", "Seismic"],
                                           help="Affects load factor application")
        
        if P_temp != 0:
            if P_temp > 0:
                st.warning(f"⚠️ **Compression: P = {P_temp:.1f} kN** - Beam-column interaction will be checked")
            else:
                st.info(f"ℹ️ **Tension: P = {abs(P_temp):.1f} kN** - Combined tension + bending will be checked")
            
            # Calculate factored axial force
            if axial_load_case == "Permanent (DL)":
                P_factor = 1.4 if method == "LRFD" else 1.0
            elif axial_load_case == "Transient (Temp)":
                P_factor = 1.2 if method == "LRFD" else 1.0  # Treat as DL for temperature
            else:  # Seismic
                P_factor = 1.0  # Seismic already factored
            
            Pu_temp = P_temp * P_factor
            st.caption(f"Factored: Pu = {P_temp:.1f} × {P_factor:.2f} = {Pu_temp:.1f} kN ({method})")
        else:
            Pu_temp = 0.0
    
    # ============== METAL DECK INPUTS (Phase 2) ==============
    with st.expander("🏭 Metal Deck Profile", expanded=False):
        if not METAL_DECK_AVAILABLE:
            st.warning("Metal Deck module not available")
            deck_enabled = False
            # Set defaults - use beam spacing for deck span
            deck_hr, deck_wr_top, deck_wr_bot, deck_pitch = 50.8, 114, 38, 152.4
            deck_t, deck_theta = 0.9, 80
            deck_Fy = 230
            deck_span = int(spacing * 1000)  # Link to beam spacing
            deck_P_conc = 1.0
            deck_span_type = "Single"
            deck_input_method, deck_dxf_file = "Manual", None
        else:
            deck_enabled = st.checkbox("Enable Metal Deck Design", value=True)
            
            if deck_enabled:
                deck_input_method = st.radio(
                    "Profile Input",
                    ["Manual", "Standard", "DXF Import"],
                    horizontal=True,
                    key="sidebar_deck_input"
                )
                
                if deck_input_method == "Manual":
                    deck_hr = st.number_input("Rib Height hr (mm)", value=50.8, min_value=20.0, max_value=150.0, step=1.0, key="sb_deck_hr")
                    deck_wr_top = st.number_input("Top Opening (mm)", value=114.0, min_value=50.0, max_value=250.0, step=1.0, key="sb_deck_wr_top")
                    deck_wr_bot = st.number_input("Bottom Width (mm)", value=38.0, min_value=20.0, max_value=150.0, step=1.0, key="sb_deck_wr_bot")
                    deck_pitch = st.number_input("Rib Pitch (mm)", value=152.4, min_value=100.0, max_value=350.0, step=1.0, key="sb_deck_pitch")
                    deck_t = st.number_input("Thickness (mm)", value=0.9, min_value=0.4, max_value=2.5, step=0.05, key="sb_deck_t")
                    deck_theta = st.number_input("Web Angle θ (deg)", value=80.0, min_value=45.0, max_value=90.0, step=1.0, key="sb_deck_theta")
                    deck_dxf_file = None
                    
                elif deck_input_method == "Standard":
                    std_profiles = {
                        "1.5\" × 6\" (38×152)": {"hr": 38.1, "wr_top": 127, "wr_bot": 51, "pitch": 152.4, "theta": 78},
                        "2\" × 6\" (51×152)": {"hr": 50.8, "wr_top": 114, "wr_bot": 38, "pitch": 152.4, "theta": 80},
                        "2\" × 12\" (51×305)": {"hr": 50.8, "wr_top": 241, "wr_bot": 64, "pitch": 304.8, "theta": 82},
                        "3\" × 6\" (76×152)": {"hr": 76.2, "wr_top": 102, "wr_bot": 25, "pitch": 152.4, "theta": 75},
                        "3\" × 12\" (76×305)": {"hr": 76.2, "wr_top": 229, "wr_bot": 51, "pitch": 304.8, "theta": 78},
                    }
                    std_choice = st.selectbox("Standard Profile", list(std_profiles.keys()), key="sb_std_profile")
                    std_p = std_profiles[std_choice]
                    deck_hr, deck_wr_top, deck_wr_bot = std_p["hr"], std_p["wr_top"], std_p["wr_bot"]
                    deck_pitch, deck_theta = std_p["pitch"], std_p["theta"]
                    deck_t = st.number_input("Thickness (mm)", value=0.9, min_value=0.4, max_value=2.5, step=0.05, key="sb_std_t")
                    deck_dxf_file = None
                    st.caption(f"hr={deck_hr}, pitch={deck_pitch}")
                    
                else:  # DXF Import
                    deck_t = st.number_input("Thickness (mm)", value=0.9, min_value=0.4, max_value=2.5, step=0.05, key="sb_dxf_t")
                    deck_dxf_file = st.file_uploader("Upload DXF", type=['dxf'], key="sb_dxf_upload")
                    deck_hr, deck_wr_top, deck_wr_bot, deck_pitch, deck_theta = 50.8, 114, 38, 152.4, 80  # Defaults
                
                st.markdown("**Material**")
                deck_Fy = st.selectbox("Deck Fy (MPa)", [230, 250, 275, 345], index=0, key="sb_deck_fy")
                
                st.markdown("**Span & Loading**")
                # Deck span = beam spacing (deck spans between beams)
                deck_span = int(spacing * 1000)  # Convert beam spacing (m) to mm
                st.info(f"📐 Deck Span = Beam Spacing = {deck_span} mm")
                
                # Display loads from unified section (read-only)
                st.markdown(f"""
**Construction Stage Loads** *(from Loads section)*:
- Wet Concrete + Deck: **{deck_DL:.2f} kN/m²**
- Construction LL: **{deck_const_LL:.2f} kN/m²**
- **Total: {deck_w_const:.2f} kN/m²**
                """)
                
                deck_P_conc = st.number_input("Point Load (kN)", value=1.0, min_value=0.0, max_value=5.0, step=0.25, key="sb_deck_P")
                deck_span_type = st.selectbox("Span Type", ["Single", "2-Span", "3+ Span"], key="sb_deck_span_type")
            else:
                # Defaults when disabled - use beam spacing for deck span
                deck_hr, deck_wr_top, deck_wr_bot, deck_pitch = 50.8, 114, 38, 152.4
                deck_t, deck_theta = 0.9, 80
                deck_Fy = 230
                deck_span = int(spacing * 1000)  # Link to beam spacing
                # deck_DL and deck_const_LL already defined from unified loads section
                deck_P_conc = 1.0
                deck_span_type = "Single"
                deck_input_method, deck_dxf_file = "Manual", None
    
    # ============== SLAB DESIGN INPUTS ==============
    if design_mode == "Composite":
        # Composite slab - deck acts as formwork and bottom reinforcement
        with st.expander("🔗 Composite Slab Reinforcement", expanded=False):
            if not COMPOSITE_SLAB_AVAILABLE:
                st.warning("Composite Slab module not available")
                slab_enabled = False
                # Defaults - use unified loads
                slab_tc, slab_fc, slab_wc = 130, 25, 2400
                slab_span_type = "Simple"
                rebar_fy, rebar_As, slab_cover = 500, 142, 20
                slab_wDL, slab_wSDL, slab_wLL = w_slab, w_SDL_area, w_LL_area
                fire_check, fire_rating_choice = False, "1-Hour"
            else:
                slab_enabled = st.checkbox("Enable Composite Slab Design", value=True)
                
                if slab_enabled:
                    st.markdown("**Slab Geometry**")
                    slab_tc = st.number_input("Total Thickness (mm)", value=130, min_value=90, max_value=250, step=5, key="sb_slab_tc")
                    slab_span_type = st.selectbox("Span Condition", ["Simple", "Two-Span", "Three+ Span"], key="sb_slab_span")
                    
                    st.markdown("**Concrete**")
                    slab_fc = st.number_input("f'c (MPa)", value=25, min_value=20, max_value=50, step=5, key="sb_slab_fc")
                    slab_wc = st.number_input("Unit Wt (kg/m³)", value=2400, min_value=1800, max_value=2500, step=50, key="sb_slab_wc")
                    
                    st.markdown("**Reinforcement**")
                    rebar_fy = st.number_input("fy (MPa)", value=500, min_value=400, max_value=600, step=20, key="sb_rebar_fy")
                    rebar_type = st.selectbox("Type", ["WWF", "Rebar"], key="sb_rebar_type")
                    
                    if rebar_type == "WWF":
                        wwf_opts = {"6×6-W1.4": 90, "6×6-W2.0": 129, "6×6-W2.9": 187, "6×6-W4.0": 258, "4×4-W1.4": 135, "4×4-W2.0": 194}
                        wwf_sel = st.selectbox("WWF Size", list(wwf_opts.keys()), key="sb_wwf")
                        rebar_As = wwf_opts[wwf_sel]
                    else:
                        rebar_opts = {"T10@200": 393, "T10@150": 524, "T12@200": 566, "T12@150": 754, "T16@200": 1005}
                        rebar_sel = st.selectbox("Rebar", list(rebar_opts.keys()), key="sb_rebar")
                        rebar_As = rebar_opts[rebar_sel]
                    
                    slab_cover = st.number_input("Cover (mm)", value=20, min_value=15, max_value=50, step=5, key="sb_slab_cover")
                    st.caption(f"As = {rebar_As} mm²/m")
                    
                    st.markdown("**Loads** *(from Loads section)*")
                    st.markdown(f"""
- Slab DL: **{w_slab:.2f} kN/m²**
- SDL: **{w_SDL_area:.2f} kN/m²**
- Live Load: **{w_LL_area:.2f} kN/m²**
                    """)
                    # Use unified area loads
                    slab_wDL = w_slab
                    slab_wSDL = w_SDL_area
                    slab_wLL = w_LL_area
                    
                    st.markdown("**Fire Rating (Optional)**")
                    fire_check = st.checkbox("Check Fire Rating", value=False, key="sb_fire_check")
                    if fire_check:
                        fire_rating_choice = st.selectbox("Rating", ["1-Hour", "1.5-Hour", "2-Hour", "3-Hour"], key="sb_fire_rating")
                    else:
                        fire_rating_choice = "1-Hour"  # Default
                else:
                    # Defaults when disabled - use unified loads
                    slab_tc, slab_fc, slab_wc = 130, 25, 2400
                    slab_span_type = "Simple"
                    rebar_fy, rebar_As, slab_cover = 500, 142, 20
                    slab_wDL, slab_wSDL, slab_wLL = w_slab, w_SDL_area, w_LL_area
                    fire_check, fire_rating_choice = False, "1-Hour"
        
        # Initialize one-way slab variables for consistency
        ow_slab_enabled = False
        ow_tc, ow_fc, ow_fy = 150, 25, 500
        ow_cover, ow_bar_dia = 25, 12
        ow_span_type = "Simple"
        ow_deck_as_reinf = False
    
    else:
        # Non-Composite Mode - One-Way RC Slab Design
        with st.expander("🧱 One-Way Slab Design (ACI 318-19)", expanded=True):
            ow_slab_enabled = st.checkbox("Enable One-Way Slab Design", value=True, key="ow_slab_enable")
            
            if ow_slab_enabled:
                st.markdown("**Slab Geometry**")
                ow_tc = st.number_input("Total Thickness tc (mm)", value=150, min_value=100, max_value=300, step=10, key="ow_tc")
                ow_span_type = st.selectbox("Span Condition", 
                                           ["Simple", "One End Continuous", "Both Ends Continuous", "Cantilever"],
                                           key="ow_span_type")
                
                # Minimum thickness check per ACI Table 7.3.1.1
                slab_span_mm = spacing * 1000  # Slab spans between beams
                if ow_span_type == "Simple":
                    h_min = slab_span_mm / 20
                elif ow_span_type == "One End Continuous":
                    h_min = slab_span_mm / 24
                elif ow_span_type == "Both Ends Continuous":
                    h_min = slab_span_mm / 28
                else:  # Cantilever
                    h_min = slab_span_mm / 10
                
                if ow_tc >= h_min:
                    st.success(f"✓ tc = {ow_tc} mm ≥ h_min = {h_min:.0f} mm (ACI Table 7.3.1.1)")
                else:
                    st.warning(f"⚠️ tc = {ow_tc} mm < h_min = {h_min:.0f} mm - Check deflection")
                
                st.markdown("**Materials**")
                col_mat1, col_mat2 = st.columns(2)
                with col_mat1:
                    ow_fc = st.number_input("f'c (MPa)", value=25, min_value=20, max_value=50, step=5, key="ow_fc")
                with col_mat2:
                    ow_fy = st.number_input("fy (MPa)", value=500, min_value=400, max_value=600, step=20, key="ow_fy")
                
                st.markdown("**Reinforcement**")
                col_reinf1, col_reinf2 = st.columns(2)
                with col_reinf1:
                    ow_cover = st.number_input("Clear Cover (mm)", value=25, min_value=20, max_value=50, step=5, key="ow_cover")
                with col_reinf2:
                    ow_bar_dia = st.selectbox("Main Bar Dia (mm)", [10, 12, 14, 16, 20], index=1, key="ow_bar_dia")
                
                # Calculate effective depth
                ow_d_eff = ow_tc - ow_cover - ow_bar_dia / 2
                st.caption(f"d = {ow_d_eff:.0f} mm (effective depth)")
                
                st.markdown("**Metal Deck Option**")
                ow_deck_as_reinf = st.checkbox("Use deck as positive reinforcement (SDI)", value=False, key="ow_deck_reinf",
                                               help="If checked, metal deck contributes to positive moment capacity")
                
                st.markdown("**Loads** *(from Loads section)*")
                st.markdown(f"""
- Slab DL: **{w_slab:.2f} kN/m²**
- SDL: **{w_SDL_area:.2f} kN/m²**
- Live Load: **{w_LL_area:.2f} kN/m²**
- **Total:** {w_slab + w_SDL_area + w_LL_area:.2f} kN/m²
                """)
            else:
                ow_tc, ow_fc, ow_fy = 150, 25, 500
                ow_cover, ow_bar_dia = 25, 12
                ow_span_type = "Simple"
                ow_deck_as_reinf = False
        
        # Set composite slab variables to defaults for consistency
        slab_enabled = False
        slab_tc, slab_fc, slab_wc = 130, 25, 2400
        slab_span_type = "Simple"
        rebar_fy, rebar_As, slab_cover = 500, 142, 20
        slab_wDL, slab_wSDL, slab_wLL = w_slab, w_SDL_area, w_LL_area
        fire_check, fire_rating_choice = False, "1-Hour"
    
    # ============== DIAPHRAGM INPUTS (Phase 5) ==============
    with st.expander("🔲 Diaphragm Design", expanded=False):
        if not DIAPHRAGM_AVAILABLE:
            st.warning("Diaphragm module not available")
            diaph_enabled = False
            # Defaults
            diaph_length, diaph_width = 30000, 15000
            diaph_support_type, diaph_support_dia = "Arc Spot Weld", 19
            diaph_sidelap_type, diaph_sidelap_spacing = "Screw", 305
            diaph_n_per_rib = 1
            diaph_w_wind, diaph_w_seismic = 5.0, 8.0
        else:
            diaph_enabled = st.checkbox("Enable Diaphragm Design", value=False)
            
            if diaph_enabled:
                st.markdown("**Diaphragm Geometry**")
                diaph_length = st.number_input("Length (mm)", value=30000, min_value=5000, max_value=100000, step=1000, key="sb_diaph_L")
                diaph_width = st.number_input("Width (mm)", value=15000, min_value=5000, max_value=50000, step=1000, key="sb_diaph_W")
                
                st.markdown("**Support Fasteners**")
                diaph_support_type = st.selectbox(
                    "Type", ["Arc Spot Weld", "Screw", "PAF"],
                    key="sb_diaph_support_type"
                )
                diaph_support_dia = st.number_input("Diameter (mm)", value=19, min_value=10, max_value=25, step=1, key="sb_diaph_support_dia")
                diaph_n_per_rib = st.number_input("Fasteners/Rib", value=1, min_value=1, max_value=3, step=1, key="sb_diaph_n_rib")
                
                st.markdown("**Side-Lap Fasteners**")
                diaph_sidelap_type = st.selectbox(
                    "Type", ["Screw", "Button Punch", "Weld", "None"],
                    key="sb_diaph_sidelap_type"
                )
                diaph_sidelap_spacing = st.number_input("Spacing (mm)", value=305, min_value=150, max_value=600, step=25, key="sb_diaph_sl_space")
                
                st.markdown("**Lateral Loads (kN/m)**")
                diaph_w_wind = st.number_input("Wind Load", value=5.0, min_value=0.0, max_value=30.0, step=0.5, key="sb_diaph_wind")
                diaph_w_seismic = st.number_input("Seismic Load", value=8.0, min_value=0.0, max_value=50.0, step=0.5, key="sb_diaph_seismic")
            else:
                # Defaults
                diaph_length, diaph_width = 30000, 15000
                diaph_support_type, diaph_support_dia = "Arc Spot Weld", 19
                diaph_sidelap_type, diaph_sidelap_spacing = "Screw", 305
                diaph_n_per_rib = 1
                diaph_w_wind, diaph_w_seismic = 5.0, 8.0

    # ============== VIBRATION OPTIONS ==============
    with st.expander("📳 Vibration Check", expanded=False):
        vibration_enabled = st.checkbox("Enable Vibration Analysis", value=False, 
                                        help="Per AISC Design Guide 11")
        if vibration_enabled:
            st.markdown("**Occupancy Category**")
            vib_occupancy = st.selectbox("Select Occupancy", 
                                         ["Office/Residential", "Shopping Mall", "Rhythmic Activities"],
                                         key="sb_vib_occupancy")
            vib_damping = st.slider("Damping Ratio (%)", 2.0, 5.0, 3.0, 0.5, key="sb_vib_damping")
        else:
            vib_occupancy = "Office/Residential"
            vib_damping = 3.0

# ============== ANALYSIS ==============
studs_data = {"n": n_studs * 2, "Qn": stud_r["Qn"]}

# Pre-composite check (same for both modes - construction stage)
w_precomp = w_DL + w_const
precomp = check_precomposite(sec, Fy, w_precomp, L, method, phi_b)

if design_mode == "Composite":
    # Composite analysis with shear studs
    comp = run_composite_analysis(sec, Fy, fc, tc, beff, L, w_DL, w_SDL, w_LL, studs_data, method, phi_b, phi_v)
    noncomp_results = None
    beam_column_results = None
else:
    # Non-composite steel beam analysis (bare steel carries all loads)
    comp = None  # Not used in non-composite mode
    
    if NONCOMP_BEAM_AVAILABLE:
        # Calculate non-composite beam design using full AISC 360-16
        Lb_default = L * 1000 / 4  # Quarter-span unbraced length
        Cb_uniform = 1.14  # Uniform load moment gradient factor
        lb_bearing = 100  # Bearing length (mm)
        
        # Tensile strength (approximate if not provided)
        Fu = 450 if Fy == 345 else 400 if Fy == 250 else int(Fy * 1.25)
        
        # Check if axial load is present
        if abs(Pu_temp) > 0.1:
            # Use beam-column design (combined axial + bending)
            Lc_default = L * 1000  # Full span for compression buckling
            K_default = 1.0  # Effective length factor
            
            beam_column_results = design_noncomposite_beam_column(
                sec=sec,
                sec_name=sec_name,
                Fy=Fy,
                Fu=Fu,
                L=L,
                w_DL=w_DL,
                w_SDL=w_SDL,
                w_LL=w_LL,
                Pu=Pu_temp,
                Lb=Lb_default,
                Cb=Cb_uniform,
                Lc=Lc_default,
                K=K_default,
                lb=lb_bearing,
                method=method
            )
            # Extract beam results from beam-column results
            noncomp_results = beam_column_results.beam_results
        else:
            # Pure bending (no axial)
            beam_column_results = None
            noncomp_results = design_noncomposite_beam(
                sec=sec,
                sec_name=sec_name,
                Fy=Fy,
                L=L,
                w_DL=w_DL,
                w_SDL=w_SDL,
                w_LL=w_LL,
                Lb=Lb_default,
                Cb=Cb_uniform,
                lb=lb_bearing,
                method=method
            )
    else:
        # Fallback if module not available - create simple results dict
        beam_column_results = None
        # Using bare steel section for all calculations
        w_total = w_DL + w_SDL + w_LL
        if method == "LRFD":
            w_u = 1.2 * (w_DL + w_SDL) + 1.6 * w_LL
        else:
            w_u = w_total
        
        Mu_nc = w_u * L**2 / 8
        Vu_nc = w_u * L / 2
        
        # Bare steel capacities
        Zx = sec.get('Zx', sec['Sx'] * 1.12 if 'Sx' in sec else sec['Ix'] / (sec['d']/2) * 1.12)
        Mn_nc = Fy * Zx / 1e6  # kN-m
        phi_Mn_nc = 0.90 * Mn_nc if method == "LRFD" else Mn_nc / 1.67
        
        Aw = sec['d'] * sec['tw']
        Vn_nc = 0.6 * Fy * Aw / 1000  # kN
        phi_Vn_nc = 1.0 * Vn_nc if method == "LRFD" else Vn_nc / 1.50
        
        # Deflection using bare Ix
        delta_DL_nc = 5 * (w_DL + w_SDL) * (L*1000)**4 / (384 * 200000 * sec['Ix'])
        delta_LL_nc = 5 * w_LL * (L*1000)**4 / (384 * 200000 * sec['Ix'])
        
        noncomp_results = {
            'Mu': Mu_nc,
            'Vu': Vu_nc,
            'phi_Mn': phi_Mn_nc,
            'phi_Vn': phi_Vn_nc,
            'DCR_flex': Mu_nc / phi_Mn_nc if phi_Mn_nc > 0 else 999,
            'DCR_shear': Vu_nc / phi_Vn_nc if phi_Vn_nc > 0 else 999,
            'delta_DL': delta_DL_nc,
            'delta_LL': delta_LL_nc,
            'delta_total': delta_DL_nc + delta_LL_nc,
            'delta_limit_LL': L * 1000 / 360,
            'delta_limit_total': L * 1000 / 240,
            'DCR_defl_LL': delta_LL_nc / (L * 1000 / 360),
            'DCR_defl_total': (delta_DL_nc + delta_LL_nc) / (L * 1000 / 240),
            'all_pass': True  # Will be determined below
        }
        
        # Check if all pass
        noncomp_results['all_pass'] = (
            noncomp_results['DCR_flex'] <= 1.0 and
            noncomp_results['DCR_shear'] <= 1.0 and
            noncomp_results['DCR_defl_LL'] <= 1.0 and
            noncomp_results['DCR_defl_total'] <= 1.0
        )

# One-way slab analysis (only for non-composite mode)
oneway_slab_results = None
if design_mode == "Non-Composite" and ONEWAY_SLAB_AVAILABLE and ow_slab_enabled:
    slab_span_mm = spacing * 1000  # Slab spans between beams
    ow_d_eff = ow_tc - ow_cover - ow_bar_dia / 2
    
    oneway_slab_results = design_oneway_slab(
        Ln=slab_span_mm,
        tc=ow_tc,
        cover=ow_cover,
        bar_dia=ow_bar_dia,
        fc=ow_fc,
        fy=ow_fy,
        w_DL=w_slab,
        w_SDL=w_SDL_area,
        w_LL=w_LL_area,
        span_type=ow_span_type,
        As_provided_pos=None,  # Will calculate required
        As_provided_neg=None,
        method=method,
        wc=2400
    )

# Initialize and process deck variables (before tabs for scope)
deck_parse_result = None
deck_gross_props = None

if METAL_DECK_AVAILABLE and deck_enabled:
    try:
        if deck_input_method == "DXF Import" and deck_dxf_file is not None:
            # Parse DXF file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp:
                tmp.write(deck_dxf_file.getbuffer())
                tmp_path = tmp.name
            
            deck_parse_result = parse_deck_dxf(tmp_path)
            os.unlink(tmp_path)
            
            if deck_parse_result.is_valid:
                # Update dimensions from DXF
                deck_hr = deck_parse_result.hr
                deck_wr_top = deck_parse_result.wr_top
                deck_wr_bot = deck_parse_result.wr_bot
                deck_pitch = deck_parse_result.pitch if deck_parse_result.pitch > 0 else 152.4
                deck_theta = deck_parse_result.web_angle
                deck_gross_props = calculate_gross_properties(deck_parse_result, deck_t)
        else:
            # Create profile from manual/standard inputs
            vertices = create_standard_profile(
                hr=deck_hr,
                wr_top=deck_wr_top,
                wr_bot=deck_wr_bot,
                pitch=deck_pitch
            )
            deck_parse_result = parse_deck_from_vertices(vertices)
            deck_gross_props = calculate_gross_properties(deck_parse_result, deck_t)
    except Exception as e:
        deck_parse_result = None
        deck_gross_props = None

# ============== RESULTS ==============
if design_mode == "Composite":
    # Composite design tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📊 Summary", "🔧 Pre-Composite", "🏗️ Composite", "🔩 Studs", 
        "📳 Vibration", "🏭 Metal Deck", "🧱 Composite Slab", "🔲 Diaphragm", 
        "🔶 Castellated/Cellular", "📋 Report"
    ])
else:
    # Non-Composite design tabs
    tab1, tab2, tab3, tab5, tab6, tab7_ow, tab8, tab9, tab10 = st.tabs([
        "📊 Summary", "🔧 Pre-Composite", "🏗️ Steel Beam",
        "📳 Vibration", "🏭 Metal Deck", "🧱 One-Way Slab", "🔲 Diaphragm", 
        "🔶 Castellated/Cellular", "📋 Report"
    ])
    # Create dummy tab4 for shear studs (not used in non-composite)
    tab4 = None
    tab7 = None  # Composite slab not used

with tab1:
    st.subheader("Design Summary")
    st.info(f"**Design Mode:** {design_mode}")
    
    # Quick vibration check with defaults for summary
    E_vib = 200000
    g_vib = 9810
    L_mm_vib = L * 1000
    w_sustained_vib = w_slab + w_SDL_area  # kN/m² (area loads)
    w_floor_vib = w_sustained_vib * spacing  # kN/m (line load)
    
    # Use appropriate moment of inertia for vibration
    if design_mode == "Composite" and comp is not None:
        Ix_vib = comp["Ieff"]
    else:
        Ix_vib = sec['Ix']  # Bare steel for non-composite
    
    fn_quick = (math.pi / (2 * L_mm_vib**2)) * math.sqrt(E_vib * Ix_vib * g_vib / w_floor_vib) if w_floor_vib > 0 else 10
    B_eff_vib = min(0.6 * L_mm_vib, spacing * 1000)
    W_eff_vib = w_sustained_vib * B_eff_vib * L_mm_vib / 1e6  # kN
    ap_g_quick = 0.29 * math.exp(-0.35 * fn_quick) / (0.03 * W_eff_vib) if W_eff_vib > 0 else 0
    vib_ok = fn_quick >= 4.0 and ap_g_quick <= 0.005
    
    if design_mode == "Composite":
        # Overall status for composite mode
        all_ok = (precomp["flex_ok"] and precomp["shear_ok"] and precomp["defl_ok"] and
                  comp["DCR_flex"] <= 1.0 and comp["DCR_shear"] <= 1.0 and 
                  comp["DCR_defl_LL"] <= 1.0 and comp["DCR_defl_total"] <= 1.0 and vib_ok)
    else:
        # Overall status for non-composite mode
        if noncomp_results is not None:
            if hasattr(noncomp_results, 'all_pass'):
                # Full NonCompositeBeamResults object
                nc_ok = noncomp_results.all_pass
            else:
                # Fallback dict
                nc_ok = noncomp_results.get('all_pass', True)
        else:
            nc_ok = True
        
        all_ok = (precomp["flex_ok"] and precomp["shear_ok"] and precomp["defl_ok"] and 
                  nc_ok and vib_ok)
    
    if all_ok:
        st.success("✅ **ALL CHECKS PASS**")
    else:
        st.error("❌ **DESIGN FAILS** - Review individual checks")
    
    st.markdown("---")
    st.markdown("### Pre-Composite Stage (Construction)")
    c1, c2, c3 = st.columns(3)
    with c1:
        color = "normal" if precomp["flex_ok"] else "inverse"
        st.metric("Flexure DCR", f"{precomp['DCR_flex_pre']:.3f}", 
                  "OK" if precomp["flex_ok"] else "NG", delta_color=color)
    with c2:
        color = "normal" if precomp["shear_ok"] else "inverse"
        st.metric("Shear DCR", f"{precomp['DCR_shear_pre']:.3f}", 
                  "OK" if precomp["shear_ok"] else "NG", delta_color=color)
    with c3:
        color = "normal" if precomp["defl_ok"] else "inverse"
        st.metric("Deflection DCR", f"{precomp['DCR_defl_pre']:.3f}", 
                  "OK" if precomp["defl_ok"] else "NG", delta_color=color)
    
    st.markdown("---")
    
    if design_mode == "Composite":
        st.markdown("### Composite Stage (Service)")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ok = comp["DCR_flex"] <= 1.0
            st.metric("Flexure DCR", f"{comp['DCR_flex']:.3f}", "OK" if ok else "NG",
                      delta_color="normal" if ok else "inverse")
        with c2:
            ok = comp["DCR_shear"] <= 1.0
            st.metric("Shear DCR", f"{comp['DCR_shear']:.3f}", "OK" if ok else "NG",
                      delta_color="normal" if ok else "inverse")
        with c3:
            ok = comp["DCR_defl_LL"] <= 1.0
            st.metric("δ_LL DCR", f"{comp['DCR_defl_LL']:.3f}", "OK" if ok else "NG",
                      delta_color="normal" if ok else "inverse")
        with c4:
            ok = comp["DCR_defl_total"] <= 1.0
            st.metric("δ_Total DCR", f"{comp['DCR_defl_total']:.3f}", "OK" if ok else "NG",
                      delta_color="normal" if ok else "inverse")
    else:
        st.markdown("### Steel Beam - Service Stage (Non-Composite)")
        st.caption("Bare steel section carries all loads - AISC 360-16")
        
        if noncomp_results is not None:
            if hasattr(noncomp_results, 'DCR_flex'):
                # Full NonCompositeBeamResults object
                dcr_flex = noncomp_results.DCR_flex
                dcr_shear = noncomp_results.DCR_shear
                dcr_web_yield = noncomp_results.DCR_web_yielding
                dcr_defl_ll = noncomp_results.deflection.DCR_LL
                dcr_defl_tot = noncomp_results.deflection.DCR_total
            else:
                # Fallback dict
                dcr_flex = noncomp_results.get('DCR_flex', 0)
                dcr_shear = noncomp_results.get('DCR_shear', 0)
                dcr_web_yield = 0
                dcr_defl_ll = noncomp_results.get('DCR_defl_LL', 0)
                dcr_defl_tot = noncomp_results.get('DCR_defl_total', 0)
            
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                ok = dcr_flex <= 1.0
                st.metric("Flexure DCR", f"{dcr_flex:.3f}", "OK" if ok else "NG",
                          delta_color="normal" if ok else "inverse")
            with c2:
                ok = dcr_shear <= 1.0
                st.metric("Shear DCR", f"{dcr_shear:.3f}", "OK" if ok else "NG",
                          delta_color="normal" if ok else "inverse")
            with c3:
                ok = dcr_web_yield <= 1.0
                st.metric("Web Yield DCR", f"{dcr_web_yield:.3f}", "OK" if ok else "NG",
                          delta_color="normal" if ok else "inverse")
            with c4:
                ok = dcr_defl_ll <= 1.0
                st.metric("δ_LL DCR", f"{dcr_defl_ll:.3f}", "OK" if ok else "NG",
                          delta_color="normal" if ok else "inverse")
            with c5:
                ok = dcr_defl_tot <= 1.0
                st.metric("δ_Total DCR", f"{dcr_defl_tot:.3f}", "OK" if ok else "NG",
                          delta_color="normal" if ok else "inverse")
            
            # Show combined axial + bending interaction if axial load is present
            if beam_column_results is not None and beam_column_results.combined is not None:
                st.markdown("---")
                st.markdown("### Combined Axial + Bending (AISC Chapter H)")
                comb = beam_column_results.combined
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Axial Type", comb.axial_type)
                with c2:
                    st.metric("Pr/Pc", f"{comb.Pr_Pc:.3f}")
                with c3:
                    st.metric("Mr/Mc", f"{comb.Mrx_Mcx:.3f}")
                with c4:
                    ok = comb.DCR <= 1.0
                    st.metric(f"Interaction ({comb.equation_used})", f"{comb.DCR:.3f}", 
                              "OK" if ok else "NG", delta_color="normal" if ok else "inverse")
                
                if not ok:
                    st.error(f"⚠️ **Combined Axial + Bending FAILS** — DCR = {comb.DCR:.3f} > 1.0")
        else:
            st.warning("Non-composite beam module not available")
    
    st.markdown("---")
    st.markdown("### Vibration Check (AISC DG11)")
    c1, c2, c3 = st.columns(3)
    with c1:
        ok = fn_quick >= 4.0
        st.metric("Natural Freq.", f"{fn_quick:.2f} Hz", "OK" if ok else "NG",
                  delta_color="normal" if ok else "inverse")
    with c2:
        ok = ap_g_quick <= 0.005
        st.metric("Peak Accel.", f"{ap_g_quick*100:.3f}% g", "OK" if ok else "NG",
                  delta_color="normal" if ok else "inverse")
    with c3:
        st.metric("Vibration Status", "✅ PASS" if vib_ok else "❌ FAIL")
    
    # Show composite info only in composite mode
    if design_mode == "Composite" and comp is not None:
        st.info(f"**{comp['comp_type']} Composite** ({comp['comp_ratio']*100:.0f}%) | I_eff = {comp['Ieff']/1e6:.2f}×10⁶ mm⁴")
    else:
        st.info(f"**Non-Composite** | I_x = {sec['Ix']/1e6:.2f}×10⁶ mm⁴ (bare steel)")

with tab2:
    st.subheader("Pre-Composite Stage Design - Steel Beam Alone")
    st.markdown("**Reference:** AISC 360-16 Chapter F (Flexure), Chapter G (Shear)")
    
    # ===========================================================================
    # SECTION 1: DESIGN DATA
    # ===========================================================================
    st.markdown("---")
    st.markdown("## 1. DESIGN DATA")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 1.1 Steel Section Properties")
        st.markdown(f"**Section:** {sec.get('name', 'Steel Section')}")
        st.code(f"""
    ┌─────────────────────────────────────────────────────┐
    │              STEEL W-SECTION                        │
    │                                                     │
    │            ◄────── bf = {sec['bf']:.1f} mm ──────►           │
    │         ┌──────────────────────────────┐  ─┬─       │
    │         │██████████████████████████████│   │ tf     │
    │         │██████████████████████████████│   │={sec['tf']:.2f}  │
    │         └────────────┬─────────────────┘  ─┴─       │
    │                      │                              │
    │                      │ tw = {sec['tw']:.2f} mm               │
    │                      │                              │   d = {sec['d']:.1f} mm
    │                      │                              │
    │                      │                              │
    │         ┌────────────┴─────────────────┐  ─┬─       │
    │         │██████████████████████████████│   │ tf     │
    │         │██████████████████████████████│   │={sec['tf']:.2f}  │
    │         └──────────────────────────────┘  ─┴─       │
    └─────────────────────────────────────────────────────┘
        """, language=None)
    
    with col2:
        st.markdown("### 1.2 Section Properties (AISC Manual Table 1-1)")
        st.code(f"""
    GEOMETRIC PROPERTIES:
    ─────────────────────────────────────────
    Depth                    d   = {sec['d']:.1f} mm
    Flange width             bf  = {sec['bf']:.1f} mm
    Flange thickness         tf  = {sec['tf']:.2f} mm
    Web thickness            tw  = {sec['tw']:.2f} mm
    
    SECTION PROPERTIES:
    ─────────────────────────────────────────
    Cross-sectional area     A   = {sec['A']:.0f} mm²
    Moment of inertia        Ix  = {sec['Ix']/1e6:.2f} × 10⁶ mm⁴
    Elastic section modulus  Sx  = {sec['Sx']/1e3:.2f} × 10³ mm³
    Plastic section modulus  Zx  = {sec['Zx']/1e3:.2f} × 10³ mm³
    
    MATERIAL (ASTM A992):
    ─────────────────────────────────────────
    Yield strength           Fy  = {Fy:.0f} MPa
    Tensile strength         Fu  = 450 MPa
    Elastic modulus          E   = 200,000 MPa
        """, language=None)
    
    # ===========================================================================
    # SECTION 2: SECTION CLASSIFICATION
    # ===========================================================================
    st.markdown("---")
    st.markdown("## 2. SECTION CLASSIFICATION")
    st.markdown("**Reference:** AISC 360-16 Table B4.1b - Compact Limits for Flexure")
    
    st.markdown("""
    For a section to develop its full plastic moment capacity (Mp), both the flange 
    and web must be **compact**. This prevents local buckling before the section 
    fully yields.
    """)
    
    lambda_f = sec['bf'] / (2 * sec['tf'])
    lambda_pf = 0.38 * math.sqrt(200000 / Fy)
    h = sec['d'] - 2 * sec['tf']
    lambda_w = h / sec['tw']
    lambda_pw = 3.76 * math.sqrt(200000 / Fy)
    
    st.markdown("### 2.1 Flange Compactness Check")
    st.latex(r"\lambda_f = \frac{b_f}{2t_f} \leq \lambda_{pf} = 0.38\sqrt{\frac{E}{F_y}}")
    
    st.code(f"""
    Flange slenderness:
    λf = bf / (2 × tf)
    λf = {sec['bf']:.1f} / (2 × {sec['tf']:.2f})
    λf = {lambda_f:.2f}
    
    Compact limit:
    λpf = 0.38 × √(E / Fy)
    λpf = 0.38 × √(200,000 / {Fy:.0f})
    λpf = 0.38 × {math.sqrt(200000/Fy):.2f}
    λpf = {lambda_pf:.2f}
    
    Check: λf = {lambda_f:.2f} {'≤' if lambda_f <= lambda_pf else '>'} λpf = {lambda_pf:.2f}  →  {'COMPACT ✅' if lambda_f <= lambda_pf else 'NON-COMPACT ❌'}
    """, language=None)
    
    st.markdown("### 2.2 Web Compactness Check")
    st.latex(r"\lambda_w = \frac{h}{t_w} \leq \lambda_{pw} = 3.76\sqrt{\frac{E}{F_y}}")
    
    st.code(f"""
    Web slenderness:
    h = d - 2×tf = {sec['d']:.1f} - 2×{sec['tf']:.2f} = {h:.1f} mm
    λw = h / tw
    λw = {h:.1f} / {sec['tw']:.2f}
    λw = {lambda_w:.2f}
    
    Compact limit:
    λpw = 3.76 × √(E / Fy)
    λpw = 3.76 × √(200,000 / {Fy:.0f})
    λpw = 3.76 × {math.sqrt(200000/Fy):.2f}
    λpw = {lambda_pw:.2f}
    
    Check: λw = {lambda_w:.2f} {'≤' if lambda_w <= lambda_pw else '>'} λpw = {lambda_pw:.2f}  →  {'COMPACT ✅' if lambda_w <= lambda_pw else 'NON-COMPACT ❌'}
    """, language=None)
    
    flange_compact = lambda_f <= lambda_pf
    web_compact = lambda_w <= lambda_pw
    classification = "COMPACT" if flange_compact and web_compact else "NON-COMPACT"
    
    if classification == "COMPACT":
        st.success(f"**Section Classification: {classification}** - Full plastic moment Mp can be developed")
    else:
        st.warning(f"**Section Classification: {classification}** - Reduced moment capacity")
    
    # ===========================================================================
    # SECTION 3: PRE-COMPOSITE LOADING
    # ===========================================================================
    st.markdown("---")
    st.markdown("## 3. PRE-COMPOSITE LOADING")
    
    st.markdown("""
    During the pre-composite (construction) stage, the steel beam alone supports:
    - Weight of wet concrete
    - Weight of steel deck
    - Construction live loads (workers, equipment)
    
    The concrete has not yet cured and provides NO structural contribution.
    """)
    
    st.code(f"""
    LOAD DIAGRAM (Simply Supported Beam):
    
            w = {w_precomp:.2f} kN/m (uniformly distributed)
            ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓
        ════════════════════════════════════════════════
        △                                              △
        ├──────────────────────────────────────────────┤
                        L = {L:.2f} m
    
    LOAD BREAKDOWN:
    ─────────────────────────────────────────────────────
    Dead Load (steel beam + deck + wet concrete)  = {w_DL:.2f} kN/m
    Construction Live Load                        = {w_const:.2f} kN/m
    ─────────────────────────────────────────────────────
    TOTAL SERVICE LOAD                        w   = {w_precomp:.2f} kN/m
    """, language=None)
    
    if method == "LRFD":
        wu_pre = 1.4 * w_precomp
        st.markdown("### 3.1 Factored Load (LRFD)")
        st.latex(r"w_u = 1.4 \times (D + C)")
        st.code(f"""
    Per ASCE 7, for construction loads:
    wu = 1.4 × w_service
    wu = 1.4 × {w_precomp:.2f} kN/m
    wu = {wu_pre:.2f} kN/m
        """, language=None)
    else:
        wu_pre = w_precomp
        st.markdown("### 3.1 Service Load (ASD)")
        st.code(f"wa = {w_precomp:.2f} kN/m", language=None)
    
    # ===========================================================================
    # SECTION 4: FLEXURAL STRENGTH
    # ===========================================================================
    st.markdown("---")
    st.markdown("## 4. FLEXURAL STRENGTH CHECK")
    st.markdown("**Reference:** AISC 360-16 Section F2 - Doubly Symmetric Compact I-Shaped Members")
    
    st.markdown("### 4.1 Required Flexural Strength")
    st.markdown("For a simply supported beam with uniform load:")
    st.latex(r"M_u = \frac{w_u \times L^2}{8}")
    
    Mu_pre = wu_pre * L**2 / 8
    
    st.code(f"""
    Mu = wu × L² / 8
    Mu = {wu_pre:.2f} kN/m × ({L:.2f} m)² / 8
    Mu = {wu_pre:.2f} × {L**2:.2f} / 8
    Mu = {Mu_pre:.2f} kN⋅m
    """, language=None)
    
    st.markdown("### 4.2 Nominal Flexural Strength")
    st.markdown("""
    For a **compact section** with adequate lateral bracing, the nominal flexural 
    strength equals the **plastic moment Mp**:
    """)
    st.latex(r"M_n = M_p = F_y \times Z_x")
    
    Mp = Fy * sec['Zx'] / 1e6  # kN⋅m
    
    st.code(f"""
    PLASTIC MOMENT CALCULATION:
    
    Mn = Mp = Fy × Zx
    Mn = {Fy:.0f} MPa × {sec['Zx']/1e3:.2f} × 10³ mm³
    Mn = {Fy:.0f} N/mm² × {sec['Zx']:.0f} mm³ × (1 kN⋅m / 10⁶ N⋅mm)
    Mn = {Fy * sec['Zx']:.0f} N⋅mm × (1 kN⋅m / 10⁶ N⋅mm)
    Mn = {Mp:.2f} kN⋅m
    """, language=None)
    
    st.markdown("### 4.3 Plastic Stress Distribution")
    st.code(f"""
    PLASTIC STRESS DISTRIBUTION AT Mp:
    
    ┌──────────────────────────────────────────┐
    │██████████████████████████████████████████│  Compression: Fy = {Fy:.0f} MPa
    │██████████  COMPRESSION  █████████████████│  (above PNA)
    │██████████████████████████████████████████│
    ├ ─ ─ ─ ─ ─ ─ ─ PNA ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤  ← Plastic Neutral Axis (at centroid for symmetric section)
    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│  Tension: Fy = {Fy:.0f} MPa
    │░░░░░░░░░░  TENSION  ░░░░░░░░░░░░░░░░░░░░░│  (below PNA)
    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
    └──────────────────────────────────────────┘
    
    At plastic moment:
    • Entire section yields (stress = Fy everywhere)
    • PNA divides section into equal areas (for symmetric section)
    • C = T = Fy × A/2 = {Fy:.0f} × {sec['A']:.0f}/2 / 1000 = {Fy * sec['A'] / 2000:.1f} kN
    • Moment arm = distance between centroids of compression and tension areas
    """, language=None)
    
    st.markdown("### 4.4 Design Flexural Strength")
    if method == "LRFD":
        st.latex(r"\phi_b M_n = 0.90 \times M_n")
        phi_Mn_pre = 0.90 * Mp
        st.code(f"""
    φb = 0.90 (AISC 360-16 §F1)
    
    φbMn = 0.90 × {Mp:.2f} kN⋅m
    φbMn = {phi_Mn_pre:.2f} kN⋅m
        """, language=None)
    else:
        phi_Mn_pre = Mp / 1.67
        st.latex(r"\frac{M_n}{\Omega_b} = \frac{M_n}{1.67}")
        st.code(f"""
    Ωb = 1.67 (AISC 360-16 §F1)
    
    Mn/Ωb = {Mp:.2f} / 1.67
    Mn/Ωb = {phi_Mn_pre:.2f} kN⋅m
        """, language=None)
    
    st.markdown("### 4.5 Flexural Capacity Check")
    st.latex(r"\text{DCR} = \frac{M_u}{\phi_b M_n} \leq 1.0")
    
    dcr_flex = precomp['Mu_pre'] / precomp['phi_Mn_pre']
    
    st.code(f"""
    DCR = Mu / φbMn
    DCR = {precomp['Mu_pre']:.2f} / {precomp['phi_Mn_pre']:.2f}
    DCR = {dcr_flex:.3f}
    """, language=None)
    
    if dcr_flex <= 1.0:
        st.success(f"✅ **DCR = {dcr_flex:.3f} ≤ 1.0  →  FLEXURE OK**")
    else:
        st.error(f"❌ **DCR = {dcr_flex:.3f} > 1.0  →  FLEXURE FAILS**")
    
    # ===========================================================================
    # SECTION 5: SHEAR STRENGTH
    # ===========================================================================
    st.markdown("---")
    st.markdown("## 5. SHEAR STRENGTH CHECK")
    st.markdown("**Reference:** AISC 360-16 Section G2 - I-Shaped Members")
    
    st.markdown("### 5.1 Required Shear Strength")
    st.markdown("Maximum shear at supports for simply supported beam:")
    st.latex(r"V_u = \frac{w_u \times L}{2}")
    
    Vu_pre = wu_pre * L / 2
    
    st.code(f"""
    Vu = wu × L / 2
    Vu = {wu_pre:.2f} kN/m × {L:.2f} m / 2
    Vu = {Vu_pre:.2f} kN
    """, language=None)
    
    st.markdown("### 5.2 Web Shear Area")
    st.latex(r"A_w = d \times t_w")
    Aw = sec['d'] * sec['tw']
    
    st.code(f"""
    Aw = d × tw
    Aw = {sec['d']:.1f} mm × {sec['tw']:.2f} mm
    Aw = {Aw:.0f} mm²
    """, language=None)
    
    st.markdown("### 5.3 Web Shear Buckling Coefficient")
    kv = 5.34
    h_tw = h / sec['tw']
    limit_shear = 1.10 * math.sqrt(kv * 200000 / Fy)
    
    st.latex(r"C_{v1} = 1.0 \quad \text{when} \quad \frac{h}{t_w} \leq 1.10\sqrt{\frac{k_v E}{F_y}}")
    
    st.code(f"""
    For unstiffened webs: kv = 5.34
    
    Web slenderness:
    h/tw = {h:.1f} / {sec['tw']:.2f} = {h_tw:.1f}
    
    Limit for yielding (Cv1 = 1.0):
    1.10 × √(kv × E / Fy) = 1.10 × √(5.34 × 200,000 / {Fy:.0f})
                         = 1.10 × √({5.34 * 200000 / Fy:.1f})
                         = 1.10 × {math.sqrt(5.34 * 200000 / Fy):.1f}
                         = {limit_shear:.1f}
    
    Check: h/tw = {h_tw:.1f} {'≤' if h_tw <= limit_shear else '>'} {limit_shear:.1f}
    → Cv1 = {'1.0 (web yields in shear)' if h_tw <= limit_shear else f'{limit_shear/h_tw:.3f} (web buckles before yielding)'}
    """, language=None)
    
    Cv1 = 1.0 if h_tw <= limit_shear else limit_shear / h_tw
    
    st.markdown("### 5.4 Nominal Shear Strength")
    st.latex(r"V_n = 0.6 \times F_y \times A_w \times C_{v1}")
    
    Vn = 0.6 * Fy * Aw * Cv1 / 1000
    
    st.code(f"""
    Vn = 0.6 × Fy × Aw × Cv1
    Vn = 0.6 × {Fy:.0f} MPa × {Aw:.0f} mm² × {Cv1:.3f}
    Vn = 0.6 × {Fy:.0f} × {Aw:.0f} × {Cv1:.3f} × (1 kN / 1000 N)
    Vn = {0.6 * Fy * Aw * Cv1:.0f} N × (1 kN / 1000 N)
    Vn = {Vn:.2f} kN
    """, language=None)
    
    st.markdown("### 5.5 Design Shear Strength")
    if method == "LRFD":
        st.latex(r"\phi_v V_n = 1.0 \times V_n")
        phi_Vn_pre = 1.0 * Vn
        st.code(f"""
    φv = 1.0 (AISC 360-16 §G1)
    
    φvVn = 1.0 × {Vn:.2f} kN
    φvVn = {phi_Vn_pre:.2f} kN
        """, language=None)
    else:
        phi_Vn_pre = Vn / 1.50
        st.latex(r"\frac{V_n}{\Omega_v} = \frac{V_n}{1.50}")
        st.code(f"""
    Ωv = 1.50 (AISC 360-16 §G1)
    
    Vn/Ωv = {Vn:.2f} / 1.50
    Vn/Ωv = {phi_Vn_pre:.2f} kN
        """, language=None)
    
    st.markdown("### 5.6 Shear Capacity Check")
    st.latex(r"\text{DCR} = \frac{V_u}{\phi_v V_n} \leq 1.0")
    
    dcr_shear = precomp['DCR_shear_pre']
    
    st.code(f"""
    DCR = Vu / φvVn
    DCR = {precomp['Vu_pre']:.2f} / {precomp['phi_Vn_pre']:.2f}
    DCR = {dcr_shear:.3f}
    """, language=None)
    
    if dcr_shear <= 1.0:
        st.success(f"✅ **DCR = {dcr_shear:.3f} ≤ 1.0  →  SHEAR OK**")
    else:
        st.error(f"❌ **DCR = {dcr_shear:.3f} > 1.0  →  SHEAR FAILS**")
    
    # ===========================================================================
    # SECTION 6: DEFLECTION CHECK
    # ===========================================================================
    st.markdown("---")
    st.markdown("## 6. DEFLECTION SERVICEABILITY CHECK")
    st.markdown("**Reference:** AISC 360-16 Chapter L - Serviceability")
    
    st.markdown("### 6.1 Deflection Formula")
    st.markdown("Maximum deflection for simply supported beam with uniform load:")
    st.latex(r"\delta = \frac{5 w L^4}{384 E I_x}")
    
    L_mm = L * 1000
    delta_pre = 5 * w_precomp * L_mm**4 / (384 * 200000 * sec['Ix'])
    
    st.code(f"""
    DEFLECTION DIAGRAM:
    
    Original position:  ─────────────────────────────────
                              ↓ δmax at midspan
    Deflected shape:    ╲                              ╱
                          ╲                          ╱
                            ╲                      ╱
                              ╲                  ╱
                                ╲──────────────╱
    
    δ = 5 × w × L⁴ / (384 × E × Ix)
    
    Where:
    w  = {w_precomp:.2f} kN/m = {w_precomp:.2f} N/mm (service load)
    L  = {L:.2f} m = {L_mm:.0f} mm
    E  = 200,000 MPa = 200,000 N/mm²
    Ix = {sec['Ix']/1e6:.2f} × 10⁶ mm⁴ = {sec['Ix']:.0f} mm⁴
    
    δ = 5 × {w_precomp:.2f} × ({L_mm:.0f})⁴ / (384 × 200,000 × {sec['Ix']:.0f})
    δ = 5 × {w_precomp:.2f} × {L_mm**4:.2e} / (384 × 200,000 × {sec['Ix']:.0f})
    δ = {5 * w_precomp * L_mm**4:.2e} / {384 * 200000 * sec['Ix']:.2e}
    δ = {delta_pre:.2f} mm
    """, language=None)
    
    st.markdown("### 6.2 Deflection Limit")
    st.latex(r"\delta_{limit} = \frac{L}{360}")
    
    delta_limit = L_mm / 360
    
    st.code(f"""
    For floor beams supporting non-structural elements:
    
    δ_limit = L / 360
    δ_limit = {L_mm:.0f} mm / 360
    δ_limit = {delta_limit:.2f} mm
    """, language=None)
    
    st.markdown("### 6.3 Deflection Check")
    st.latex(r"\text{DCR} = \frac{\delta}{\delta_{limit}} \leq 1.0")
    
    dcr_defl = precomp['DCR_defl_pre']
    
    st.code(f"""
    DCR = δ / δ_limit
    DCR = {precomp['delta_pre']:.2f} / {precomp['delta_limit_pre']:.2f}
    DCR = {dcr_defl:.3f}
    """, language=None)
    
    if dcr_defl <= 1.0:
        st.success(f"✅ **DCR = {dcr_defl:.3f} ≤ 1.0  →  DEFLECTION OK**")
    else:
        st.error(f"❌ **DCR = {dcr_defl:.3f} > 1.0  →  DEFLECTION FAILS**")
    
    # ===========================================================================
    # SECTION 7: DESIGN SUMMARY
    # ===========================================================================
    st.markdown("---")
    st.markdown("## 7. PRE-COMPOSITE DESIGN SUMMARY")
    
    st.code(f"""
    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║                    PRE-COMPOSITE STAGE DESIGN SUMMARY                         ║
    ║                    Per AISC 360-16 Chapters F & G                             ║
    ╠═══════════════════════════════════════════════════════════════════════════════╣
    ║ Section: {sec.get('name', 'Steel Section'):<20} Span: {L:.2f} m                         ║
    ║ Classification: {classification:<12}         Method: {method}                              ║
    ╠═══════════════════════════════════════════════════════════════════════════════╣
    ║ CHECK              │ DEMAND          │ CAPACITY        │ DCR    │ STATUS     ║
    ╠════════════════════╪═════════════════╪═════════════════╪════════╪════════════╣
    ║ Flexure            │ {precomp['Mu_pre']:>10.2f} kN⋅m │ {precomp['phi_Mn_pre']:>10.2f} kN⋅m │ {precomp['DCR_flex_pre']:>6.3f} │ {'✅ PASS' if precomp['flex_ok'] else '❌ FAIL':>10} ║
    ║ Shear              │ {precomp['Vu_pre']:>10.2f} kN   │ {precomp['phi_Vn_pre']:>10.2f} kN   │ {precomp['DCR_shear_pre']:>6.3f} │ {'✅ PASS' if precomp['shear_ok'] else '❌ FAIL':>10} ║
    ║ Deflection         │ {precomp['delta_pre']:>10.2f} mm   │ {precomp['delta_limit_pre']:>10.2f} mm   │ {precomp['DCR_defl_pre']:>6.3f} │ {'✅ PASS' if precomp['defl_ok'] else '❌ FAIL':>10} ║
    ╠═══════════════════════════════════════════════════════════════════════════════╣
    """, language=None)
    
    all_ok = precomp['flex_ok'] and precomp['shear_ok'] and precomp['defl_ok']
    
    if all_ok:
        st.success("## ✅ PRE-COMPOSITE STAGE: ALL CHECKS PASS")
    else:
        st.error("## ❌ PRE-COMPOSITE STAGE: DESIGN FAILS - REVISE SECTION")
    
    # ==========================================
    # DETAILED PROFESSIONAL CALCULATIONS - Pre-Composite
    # ==========================================
    st.markdown("---")
    if PRECOMP_DETAILED_AVAILABLE:
        with st.expander("📖 **DETAILED PROFESSIONAL CALCULATIONS** - AISC 360-16 Chapters F & G", expanded=False):
            st.markdown("*Complete step-by-step calculations with equations, substitutions, and code references*")
            
            try:
                # Run detailed pre-composite design
                precomp_detailed = design_precomposite_detailed(
                    section_name=sec.get('name', 'Steel Section'),
                    d=sec['d'], bf=sec['bf'], tf=sec['tf'], tw=sec['tw'],
                    A=sec['A'], Ix=sec['Ix'], Sx=sec['Sx'], Zx=sec['Zx'],
                    Fy=Fy, E=200000,
                    Lb=L * 1000,  # Unbraced length = span in mm
                    Cb=1.0,  # Conservative value
                    L=L * 1000,  # Span in mm
                    w_precomp=w_precomp,  # kN/m
                    method=method
                )
                
                # Display summary
                st.code(precomp_detailed.summary, language=None)
                
                # Display each section in tabs
                section_tabs = st.tabs([f"§{s.section_number}" for s in precomp_detailed.sections])
                
                for i, (sec_tab, calc_sec) in enumerate(zip(section_tabs, precomp_detailed.sections)):
                    with sec_tab:
                        st.markdown(f"### {calc_sec.title}")
                        st.markdown(f"**Reference:** {calc_sec.code_ref}")
                        st.markdown(f"*{calc_sec.description}*")
                        st.markdown("---")
                        
                        for step in calc_sec.steps:
                            # Format step with proper styling
                            status_color = "green" if step.status == "PASS" else "red" if step.status == "FAIL" else "blue"
                            
                            st.markdown(f"**Step {step.step_number}: {step.title}**")
                            st.caption(step.description)
                            
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.markdown(f"📐 **Equation:** `{step.equation}`")
                                st.markdown(f"🔢 **Substitution:** `{step.substitution}`")
                            with col2:
                                if step.unit:
                                    st.metric(label="Result", value=f"{step.result:.4f}", delta=step.unit)
                                else:
                                    st.metric(label="Result", value=f"{step.result:.4f}")
                            
                            if step.code_ref:
                                st.caption(f"📚 Reference: {step.code_ref}")
                            if step.notes:
                                st.info(f"📝 {step.notes}")
                            
                            st.markdown("---")
                        
                        # Section conclusion
                        if calc_sec.status == "PASS":
                            st.success(f"✅ **{calc_sec.conclusion}**")
                        elif calc_sec.status == "FAIL":
                            st.error(f"❌ **{calc_sec.conclusion}**")
                        else:
                            st.info(f"ℹ️ **{calc_sec.conclusion}**")
                
                # Download button for full report
                st.markdown("---")
                full_report = format_precomp_report(precomp_detailed)
                st.download_button(
                    label="📥 Download Complete Pre-Composite Calculation Report",
                    data=full_report,
                    file_name=f"PreComposite_Detailed_Calculations_{sec.get('name', 'Beam')}.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"Error generating detailed calculations: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.info("📝 Detailed calculations module not available")

with tab3:
    if design_mode == "Composite":
        # ============== COMPOSITE BEAM DESIGN ==============
        st.subheader("Composite Beam Design - Plastic Stress Distribution Method")
        st.markdown("**Reference:** AISC 360-16 Chapter I - Design of Composite Members")
        
        # Assign local variable for rib height
        hr = deck_hr
        
        # ===========================================================================
        # SECTION 1: DESIGN DATA
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 1. DESIGN DATA")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 1.1 Steel Section Properties")
            st.markdown(f"**Section:** {sec.get('name', 'Steel Section')}")
            st.markdown("```")
            st.text(f"  Depth                    d  = {sec['d']:.1f} mm")
            st.text(f"  Flange width            bf  = {sec['bf']:.1f} mm")
            st.text(f"  Flange thickness        tf  = {sec['tf']:.2f} mm")
            st.text(f"  Web thickness           tw  = {sec['tw']:.2f} mm")
            st.text(f"  Cross-sectional area    As  = {sec['A']:.0f} mm²")
            st.text(f"  Moment of inertia       Ix  = {sec['Ix']/1e6:.2f} × 10⁶ mm⁴")
            st.text(f"  Elastic section modulus Sx  = {sec['Sx']/1e3:.2f} × 10³ mm³")
            st.text(f"  Plastic section modulus Zx  = {sec['Zx']/1e3:.2f} × 10³ mm³")
            st.markdown("```")
        
        with col2:
            st.markdown("### 1.2 Material Properties")
            st.markdown("**Steel (ASTM A992):**")
            st.text(f"  Yield strength          Fy  = {Fy:.0f} MPa")
            st.text(f"  Elastic modulus         Es  = 200,000 MPa")
            st.markdown("")
            st.markdown("**Concrete:**")
            Ec = 4700 * math.sqrt(fc)
            st.text(f"  Compressive strength    f'c = {fc:.0f} MPa")
            st.text(f"  Elastic modulus         Ec  = 4700√f'c = {Ec:.0f} MPa")
            st.text(f"  Modular ratio           n   = Es/Ec = {200000/Ec:.2f}")
        
        # ===========================================================================
        # SECTION 2: EFFECTIVE SLAB WIDTH
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 2. EFFECTIVE CONCRETE SLAB WIDTH")
        st.markdown("**Reference:** AISC 360-16 Section I3.1a")
        
        st.markdown("""
        The effective width of the concrete slab is limited to prevent shear lag effects. 
        Per AISC 360-16 §I3.1a, the effective width on **each side** of the beam centerline 
        shall be the **minimum** of:
        """)
        
        L_mm = L * 1000
        t_above = tc - hr
        n = 200000 / Ec
        
        st.latex(r"b_{eff,each\ side} = \min \begin{cases} L/8 & \text{(one-eighth of beam span)} \\ s/2 & \text{(one-half distance to adjacent beam)} \\ \text{edge dist.} & \text{(distance to slab edge, if edge beam)} \end{cases}")
        
        st.markdown("**Calculation:**")
        limit1 = L_mm / 8
        limit2 = spacing * 1000 / 2
        
        calc_text = f"""
        Limit 1:  L/8 = {L_mm:.0f} mm / 8 = {limit1:.0f} mm (each side)
        Limit 2:  s/2 = {spacing*1000:.0f} mm / 2 = {limit2:.0f} mm (each side)
        """
        if beam_position == "edge":
            calc_text += f"    Limit 3:  Edge distance governs for edge beam\n"
        
        st.code(calc_text, language=None)
        
        governing = min(limit1, limit2)
        st.markdown(f"**Governing each side:** min({limit1:.0f}, {limit2:.0f}) = **{governing:.0f} mm**")
        st.markdown(f"**Total effective width:** beff = 2 × {governing:.0f} = **{beff:.0f} mm**")
        
        # ===========================================================================
        # SECTION 3: SLAB GEOMETRY
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 3. COMPOSITE SLAB GEOMETRY")
        
        st.code(f"""
        ┌─────────────────────────────────────────────────────────────────┐
        │                        beff = {beff:.0f} mm                          │
        │◄────────────────────────────────────────────────────────────────►│
        ├─────────────────────────────────────────────────────────────────┤ ─┬─
        │                                                                 │  │ tc = {tc:.0f} mm
        │                    CONCRETE SLAB                                │  │ (total slab)
        │                    f'c = {fc:.0f} MPa                              │  │
        ├────────┬─────────┬─────────┬─────────┬─────────┬────────────────┤ ─┼─ ─┬─
        │        │░░░░░░░░░│         │░░░░░░░░░│         │                │  │   │
        │        │░ DECK ░░│         │░ RIB  ░░│         │                │  │   │ hr = {hr:.0f} mm
        │        │░ RIB  ░░│         │░░░░░░░░░│         │                │  │   │ (rib height)
        └────────┴─────────┴─────────┴─────────┴─────────┴────────────────┘ ─┴─ ─┴─
                                  │         │
                            ┌─────┴─────────┴─────┐
                            │                     │
                            │    STEEL BEAM       │ d = {sec['d']:.0f} mm
                            │    {sec.get('name', 'W section'):<18}│
                            │                     │
                            └─────────────────────┘
        
        Concrete above deck ribs (effective for compression):
        t_above = tc - hr = {tc:.0f} - {hr:.0f} = {t_above:.0f} mm
        """, language=None)
        
        # ===========================================================================
        # SECTION 4: PLASTIC FLEXURAL STRENGTH - THE KEY SECTION
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 4. COMPOSITE FLEXURAL STRENGTH (Plastic Stress Distribution)")
        st.markdown("**Reference:** AISC 360-16 Section I3.2a")
        
        st.markdown("""
        ### 4.1 Theory: Plastic Stress Distribution Method
        
        At ultimate strength, we assume:
        - Steel yields completely (stress = Fy throughout)
        - Concrete crushes at 0.85f'c (Whitney stress block)
        - Horizontal equilibrium: **Total Compression = Total Tension**
        
        The **Plastic Neutral Axis (PNA)** is the horizontal line where compression above equals tension below.
        """)
        
        # Calculate forces
        Ts = sec['A'] * Fy / 1000  # kN
        Cc_max = 0.85 * fc * beff * t_above / 1000  # kN
        Qn_total = comp['Qn_total']  # kN
        
        st.markdown("### 4.2 Maximum Force Capacities")
        
        st.markdown("**Step 1: Steel Tensile Capacity (if entire steel section yields in tension)**")
        st.latex(r"T_s = A_s \times F_y")
        st.code(f"""
        Ts = As × Fy
        Ts = {sec['A']:.0f} mm² × {Fy:.0f} MPa × (1 kN / 1000 N)
        Ts = {sec['A'] * Fy:.0f} N × (1 kN / 1000 N)
        Ts = {Ts:.2f} kN
        """, language=None)
        
        st.markdown("**Step 2: Maximum Concrete Compression Capacity**")
        st.latex(r"C_{c,max} = 0.85 \times f'_c \times b_{eff} \times t_{above}")
        st.code(f"""
        Cc,max = 0.85 × f'c × beff × t_above
        Cc,max = 0.85 × {fc:.0f} MPa × {beff:.0f} mm × {t_above:.0f} mm × (1 kN / 1000 N)
        Cc,max = {0.85 * fc * beff * t_above:.0f} N × (1 kN / 1000 N)
        Cc,max = {Cc_max:.2f} kN
        """, language=None)
        
        st.markdown("**Step 3: Shear Connector Capacity (limits force transfer)**")
        st.latex(r"\Sigma Q_n = n_{studs} \times Q_n")
        st.code(f"""
        ΣQn = {n_studs} studs × {stud_r['Qn']/1000:.2f} kN/stud = {Qn_total:.2f} kN (per half span)
        """, language=None)
        
        st.markdown("### 4.3 Governing Compression Force")
        st.markdown("""
        The compression force that can actually develop is limited by the **minimum** of:
        1. Steel tensile capacity (equilibrium)
        2. Concrete compression capacity (material strength)
        3. Shear connector capacity (force transfer between steel and concrete)
        """)
        
        st.latex(r"C = \min(T_s, \; C_{c,max}, \; \Sigma Q_n)")
        
        C = min(Ts, Cc_max, Qn_total)
        
        st.code(f"""
        C = min(Ts, Cc,max, ΣQn)
        C = min({Ts:.2f} kN, {Cc_max:.2f} kN, {Qn_total:.2f} kN)
        C = {C:.2f} kN  ← GOVERNS
        """, language=None)
        
        # Determine what governs
        if C == Qn_total and Qn_total < min(Ts, Cc_max):
            gov_text = "**Shear Connector Capacity** → PARTIAL COMPOSITE ACTION"
            comp_type = "Partial"
        elif C == Cc_max:
            gov_text = "**Concrete Compression** → Full composite, concrete controls"
            comp_type = "Full"
        else:
            gov_text = "**Steel Tension** → Full composite, steel controls"
            comp_type = "Full"
        
        st.info(f"Governing: {gov_text}")
        
        comp_ratio = Qn_total / min(Ts, Cc_max) * 100
        st.markdown(f"**Degree of Composite Action:** ΣQn / min(Ts, Cc) = {Qn_total:.2f} / {min(Ts, Cc_max):.2f} = **{comp_ratio:.0f}%**")
        
        # ===========================================================================
        # SECTION 4.4: PNA LOCATION - CRITICAL EXPLANATION
        # ===========================================================================
        st.markdown("---")
        st.markdown("### 4.4 Plastic Neutral Axis (PNA) Location")
        
        st.markdown("""
        **The PNA location determines the stress distribution in the composite section.**
        
        We first calculate the depth of the concrete compression block required to resist the compression force C:
        """)
        
        st.latex(r"a = \frac{C}{0.85 \times f'_c \times b_{eff}}")
        
        a = C * 1000 / (0.85 * fc * beff)  # mm
        
        st.code(f"""
        a = C / (0.85 × f'c × beff)
        a = {C:.2f} kN × 1000 / (0.85 × {fc:.0f} MPa × {beff:.0f} mm)
        a = {C * 1000:.0f} N / {0.85 * fc * beff:.0f} N/mm
        a = {a:.2f} mm
        """, language=None)
        
        st.markdown("**Now compare 'a' to the concrete thickness above deck ribs:**")
        
        if a <= t_above:
            pna_location = "concrete"
            st.success(f"""
            ✅ **a = {a:.2f} mm  <  t_above = {t_above:.0f} mm**
            
            **RESULT: PNA is located WITHIN THE CONCRETE SLAB**
            
            This means:
            - The entire concrete compression block fits within the slab above the deck ribs
            - The entire steel section is in TENSION
            - This is the most common and efficient case for composite beams
            """)
            
            # Show stress diagram
            st.code(f"""
            PLASTIC STRESS DISTRIBUTION (PNA in Concrete Slab):
            
            ════════════════════════════════════════════════════════════════════
                                     beff = {beff:.0f} mm
            ┌───────────────────────────────────────────────────────────────────┐
            │█████████████████████████████████████████████████████████████████████│ ─┬─ a = {a:.2f} mm
            │█████████████  0.85f'c = {0.85*fc:.1f} MPa (COMPRESSION)  ████████████│ ─┴─ ← Concrete stress block
            │                                                                   │
            │                   CONCRETE (unstressed)                           │     t_above = {t_above:.0f} mm
            ├───────────────────────────────────────────────────────────────────┤ ─── Top of steel
            │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
            │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
            │░░░░░░░░░░░░░░░░  Fy = {Fy:.0f} MPa (TENSION)  ░░░░░░░░░░░░░░░░░░░│     d = {sec['d']:.0f} mm
            │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│     (entire steel in tension)
            │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
            └───────────────────────────────────────────────────────────────────┘ ─── Bottom of steel
            
            █ = Compression (0.85f'c)     ░ = Tension (Fy)
            
            FORCE EQUILIBRIUM:
            C (concrete compression) = {C:.2f} kN
            T (steel tension)        = {C:.2f} kN  (equal by equilibrium)
            ════════════════════════════════════════════════════════════════════
            """, language=None)
            
        else:
            pna_location = "steel"
            # PNA in steel - more complex calculation
            st.warning(f"""
            ⚠️ **a = {a:.2f} mm  >  t_above = {t_above:.0f} mm**
            
            **RESULT: PNA is located WITHIN THE STEEL SECTION**
            
            This means:
            - The concrete slab alone cannot provide enough compression
            - Part of the steel section must also be in compression
            - The PNA lies somewhere in the steel section
            """)
            
            # Calculate how much steel is in compression
            Cc_slab = 0.85 * fc * beff * t_above / 1000  # Full slab compression
            Cs_needed = C - Cc_slab  # Additional compression from steel
            As_comp = Cs_needed * 1000 / Fy  # Area of steel in compression
            
            st.code(f"""
            PNA IN STEEL - DETAILED CALCULATION:
            
            Step 1: Full slab provides compression
            Cc (slab) = 0.85 × f'c × beff × t_above
            Cc (slab) = 0.85 × {fc:.0f} × {beff:.0f} × {t_above:.0f} / 1000 = {Cc_slab:.2f} kN
            
            Step 2: Remaining compression needed from steel
            Cs (steel) = C - Cc (slab) = {C:.2f} - {Cc_slab:.2f} = {Cs_needed:.2f} kN
            
            Step 3: Steel area required in compression
            As,comp = Cs / Fy = {Cs_needed:.2f} × 1000 / {Fy:.0f} = {As_comp:.0f} mm²
            
            Step 4: Steel area in tension
            As,tension = As - As,comp = {sec['A']:.0f} - {As_comp:.0f} = {sec['A'] - As_comp:.0f} mm²
            """, language=None)
            
            st.code(f"""
            PLASTIC STRESS DISTRIBUTION (PNA in Steel Section):
            
            ════════════════════════════════════════════════════════════════════
            ┌───────────────────────────────────────────────────────────────────┐
            │████████████████████████████████████████████████████████████████████│ Full slab: 0.85f'c
            │████████████  Cc = {Cc_slab:.2f} kN (slab compression)  ████████████│ t_above = {t_above:.0f} mm
            ├───────────────────────────────────────────────────────────────────┤ 
            │███████████████████████████████████████████████████████████████████│ ← Steel compression zone
            │██████████  Cs = {Cs_needed:.2f} kN (steel compression)  ██████████│    As,comp = {As_comp:.0f} mm²
            ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ PNA ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┤ ← PLASTIC NEUTRAL AXIS
            │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│ ← Steel tension zone
            │░░░░░░░░░░░░  T = {C:.2f} kN (steel tension)  ░░░░░░░░░░░░░░░░░░░░│    As,tens = {sec['A']-As_comp:.0f} mm²
            │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
            └───────────────────────────────────────────────────────────────────┘
            
            EQUILIBRIUM CHECK:
            Total Compression = Cc + Cs = {Cc_slab:.2f} + {Cs_needed:.2f} = {C:.2f} kN
            Total Tension = T = {C:.2f} kN ✓
            ════════════════════════════════════════════════════════════════════
            """, language=None)
        
        # ===========================================================================
        # SECTION 4.5: MOMENT ARM AND NOMINAL STRENGTH
        # ===========================================================================
        st.markdown("---")
        st.markdown("### 4.5 Moment Arm and Nominal Flexural Strength")
        
        if pna_location == "concrete":
            st.markdown("""
            **When PNA is in concrete slab**, the moment arm is the distance from:
            - Centroid of concrete compression block (at depth a/2 from top)
            - To centroid of steel section (at depth d/2 from top of steel)
            """)
            
            st.latex(r"d_1 = \frac{d}{2} + (t_c - \frac{a}{2})")
            st.markdown("*Or equivalently:*")
            st.latex(r"d_1 = \frac{d}{2} + h_r + t_{above} - \frac{a}{2}")
            
            d1 = sec['d']/2 + tc - a/2
            
            st.code(f"""
            Moment Arm Calculation:
            
            d₁ = d/2 + tc - a/2
            d₁ = {sec['d']:.1f}/2 + {tc:.0f} - {a:.2f}/2
            d₁ = {sec['d']/2:.2f} + {tc:.0f} - {a/2:.2f}
            d₁ = {d1:.2f} mm
            """, language=None)
            
            st.code(f"""
            MOMENT ARM DIAGRAM:
            
            ─────────────────────────────────────── Top of slab
                   │
                   │  a/2 = {a/2:.2f} mm
                   ▼
            ─ ─ ─ ● ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ Centroid of concrete compression (C)
                   │
                   │  (tc - a/2) = {tc - a/2:.2f} mm
                   │                                               ┐
            ═══════╪═══════════════════════════════ Top of steel   │
                   │                                               │
                   │  d/2 = {sec['d']/2:.2f} mm                    │ d₁ = {d1:.2f} mm
                   │                                               │
            ─ ─ ─ ─● ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ Centroid of steel (T)
                   │                                               │
                   │  d/2 = {sec['d']/2:.2f} mm                    │
                   │                                               ┘
            ═══════╪═══════════════════════════════ Bottom of steel
            """, language=None)
            
        else:
            # PNA in steel - more complex moment calculation
            Cc_slab = 0.85 * fc * beff * t_above / 1000
            Cs_needed = C - Cc_slab
            As_comp = Cs_needed * 1000 / Fy
            
            # Simplified - assume compression in top flange
            y_Cc = t_above / 2  # Centroid of slab compression from top of slab
            y_Cs = tc + As_comp / (2 * sec['bf'])  # Approximate centroid of steel compression
            y_T = tc + sec['d'] / 2  # Centroid of steel tension (approximate)
            
            # Weighted centroid of compression
            y_C = (Cc_slab * y_Cc + Cs_needed * y_Cs) / C
            
            d1 = y_T - y_C + (sec['d'] - sec['d']/2)  # Approximate
            d1 = comp.get('d1', sec['d']/2 + tc - a/2)  # Use computed value if available
            
            st.markdown("**When PNA is in steel**, the calculation is more complex:")
            st.code(f"""
            Moment is sum of:
            1. Concrete compression × distance to steel centroid
            2. Steel compression × distance to steel tension centroid
            
            Approximate moment arm: d₁ ≈ {d1:.2f} mm
            (Exact calculation requires finding PNA location in steel)
            """, language=None)
        
        # Nominal Moment
        st.markdown("**Nominal Flexural Strength:**")
        st.latex(r"M_n = C \times d_1")
        
        Mn = C * d1 / 1000  # kN⋅m
        
        st.code(f"""
        Mn = C × d₁
        Mn = {C:.2f} kN × {d1:.2f} mm × (1 m / 1000 mm)
        Mn = {Mn:.2f} kN⋅m
        """, language=None)
        
        # Design Strength
        st.markdown("**Design Flexural Strength:**")
        if method == "LRFD":
            st.latex(r"\phi_b M_n = 0.90 \times M_n")
            phi_Mn = 0.90 * Mn
            st.code(f"""
        φbMn = 0.90 × {Mn:.2f} kN⋅m
        φbMn = {phi_Mn:.2f} kN⋅m
            """, language=None)
        else:
            st.latex(r"\frac{M_n}{\Omega_b} = \frac{M_n}{1.67}")
            phi_Mn = Mn / 1.67
            st.code(f"""
        Mn/Ωb = {Mn:.2f} / 1.67
        Mn/Ωb = {phi_Mn:.2f} kN⋅m
            """, language=None)
        
        # ===========================================================================
        # SECTION 5: REQUIRED STRENGTH AND CHECK
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 5. FLEXURAL DEMAND AND CAPACITY CHECK")
        
        st.markdown("### 5.1 Factored Loading")
        if method == "LRFD":
            st.latex(r"w_u = 1.2(D + SDL) + 1.6L")
            wu = 1.2 * (w_DL + w_SDL) + 1.6 * w_LL
            st.code(f"""
        wu = 1.2 × ({w_DL:.2f} + {w_SDL:.2f}) + 1.6 × {w_LL:.2f}
        wu = 1.2 × {w_DL + w_SDL:.2f} + 1.6 × {w_LL:.2f}
        wu = {1.2*(w_DL + w_SDL):.2f} + {1.6*w_LL:.2f}
        wu = {wu:.2f} kN/m
            """, language=None)
        else:
            wu = w_DL + w_SDL + w_LL
            st.code(f"wa = {w_DL:.2f} + {w_SDL:.2f} + {w_LL:.2f} = {wu:.2f} kN/m", language=None)
        
        st.markdown("### 5.2 Required Flexural Strength")
        st.latex(r"M_u = \frac{w_u \times L^2}{8}")
        Mu_calc = wu * L**2 / 8
        st.code(f"""
        Mu = wu × L² / 8
        Mu = {wu:.2f} kN/m × ({L:.2f} m)² / 8
        Mu = {wu:.2f} × {L**2:.2f} / 8
        Mu = {Mu_calc:.2f} kN⋅m
        """, language=None)
        
        st.markdown("### 5.3 Flexural Capacity Check")
        st.latex(r"\text{DCR} = \frac{M_u}{\phi_b M_n} \leq 1.0")
        
        dcr_flex = comp['Mu'] / comp['phi_Mn']
        
        st.code(f"""
        DCR = Mu / φbMn
        DCR = {comp['Mu']:.2f} / {comp['phi_Mn']:.2f}
        DCR = {dcr_flex:.3f}
        """, language=None)
        
        if dcr_flex <= 1.0:
            st.success(f"✅ **DCR = {dcr_flex:.3f} ≤ 1.0  →  FLEXURE OK**")
        else:
            st.error(f"❌ **DCR = {dcr_flex:.3f} > 1.0  →  FLEXURE FAILS**")
        
        # ===========================================================================
        # SECTION 6: SHEAR STRENGTH
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 6. SHEAR STRENGTH CHECK")
        st.markdown("**Reference:** AISC 360-16 Section G2.1")
        
        st.markdown("""
        Per AISC 360-16 §I4.2, the steel section alone resists all vertical shear 
        in a composite beam. The concrete slab does not contribute to shear resistance.
        """)
        
        st.markdown("### 6.1 Web Shear Area")
        st.latex(r"A_w = d \times t_w")
        Aw = sec['d'] * sec['tw']
        st.code(f"""
        Aw = d × tw
        Aw = {sec['d']:.1f} mm × {sec['tw']:.2f} mm
        Aw = {Aw:.0f} mm²
        """, language=None)
        
        st.markdown("### 6.2 Web Shear Coefficient Cv1")
        kv = 5.34  # No transverse stiffeners
        h = sec['d'] - 2 * sec['tf']
        h_tw = h / sec['tw']
        limit_shear = 1.10 * math.sqrt(kv * 200000 / Fy)
        
        st.latex(r"C_{v1} = 1.0 \quad \text{when} \quad \frac{h}{t_w} \leq 1.10\sqrt{\frac{k_v E}{F_y}}")
        st.code(f"""
        kv = 5.34 (no transverse stiffeners)
        h/tw = ({sec['d']:.1f} - 2×{sec['tf']:.2f}) / {sec['tw']:.2f} = {h_tw:.1f}
        Limit = 1.10 × √(5.34 × 200,000 / {Fy:.0f}) = {limit_shear:.1f}
        
        Since h/tw = {h_tw:.1f} {'≤' if h_tw <= limit_shear else '>'} {limit_shear:.1f}
        → Cv1 = {'1.0' if h_tw <= limit_shear else f'{limit_shear/h_tw:.3f}'} (web yields in shear)
        """, language=None)
        
        Cv1 = 1.0 if h_tw <= limit_shear else limit_shear / h_tw
        
        st.markdown("### 6.3 Nominal Shear Strength")
        st.latex(r"V_n = 0.6 \times F_y \times A_w \times C_{v1}")
        Vn = 0.6 * Fy * Aw * Cv1 / 1000
        st.code(f"""
        Vn = 0.6 × Fy × Aw × Cv1
        Vn = 0.6 × {Fy:.0f} MPa × {Aw:.0f} mm² × {Cv1:.3f} × (1 kN / 1000 N)
        Vn = {0.6 * Fy * Aw * Cv1:.0f} N × (1 kN / 1000 N)
        Vn = {Vn:.2f} kN
        """, language=None)
        
        st.markdown("### 6.4 Design Shear Strength")
        if method == "LRFD":
            st.latex(r"\phi_v V_n = 1.0 \times V_n")
            phi_Vn = 1.0 * Vn
            st.code(f"""
        φv = 1.0 (AISC 360-16 §G1)
        φvVn = 1.0 × {Vn:.2f} kN = {phi_Vn:.2f} kN
            """, language=None)
        else:
            st.latex(r"\frac{V_n}{\Omega_v} = \frac{V_n}{1.50}")
            phi_Vn = Vn / 1.50
            st.code(f"""
        Ωv = 1.50 (AISC 360-16 §G1)
        Vn/Ωv = {Vn:.2f} / 1.50 = {phi_Vn:.2f} kN
            """, language=None)
        
        st.markdown("### 6.5 Required Shear Strength")
        st.latex(r"V_u = \frac{w_u \times L}{2}")
        Vu_calc = wu * L / 2
        st.code(f"""
        Vu = wu × L / 2
        Vu = {wu:.2f} kN/m × {L:.2f} m / 2
        Vu = {Vu_calc:.2f} kN
        """, language=None)
        
        st.markdown("### 6.6 Shear Capacity Check")
        st.latex(r"\text{DCR} = \frac{V_u}{\phi_v V_n} \leq 1.0")
        dcr_shear = comp['DCR_shear']
        st.code(f"""
        DCR = Vu / φvVn
        DCR = {comp['Vu']:.2f} / {comp['phi_Vn']:.2f}
        DCR = {dcr_shear:.3f}
        """, language=None)
        
        if dcr_shear <= 1.0:
            st.success(f"✅ **DCR = {dcr_shear:.3f} ≤ 1.0  →  SHEAR OK**")
        else:
            st.error(f"❌ **DCR = {dcr_shear:.3f} > 1.0  →  SHEAR FAILS**")
        
        # ===========================================================================
        # SECTION 7: DEFLECTION CHECK
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 7. DEFLECTION SERVICEABILITY CHECK")
        st.markdown("**Reference:** AISC 360-16 Section L")
        
        st.markdown("### 7.1 Lower-Bound Moment of Inertia (Partial Composite)")
        st.markdown("""
        For partial composite action, the effective moment of inertia is calculated using 
        the lower-bound formula per AISC 360-16 Commentary §I3.2:
        """)
        
        st.latex(r"I_{eff} = I_x + \sqrt{\eta}(I_{tr} - I_x)")
        st.markdown("where η = ΣQn / min(Ts, Cc) is the degree of composite action")
        
        eta = comp['Qn_total'] / min(Ts, Cc_max)
        st.code(f"""
        η = ΣQn / min(Ts, Cc) = {comp['Qn_total']:.1f} / {min(Ts, Cc_max):.1f} = {eta:.3f}
        
        Ieff = Ix + √η × (Itr - Ix)
        Ieff = {sec['Ix']/1e6:.2f}×10⁶ + √{eta:.3f} × (Itr - {sec['Ix']/1e6:.2f}×10⁶)
        Ieff = {comp['Ieff']/1e6:.2f}×10⁶ mm⁴
        """, language=None)
        
        st.markdown("### 7.2 Deflection Calculations")
        st.latex(r"\delta = \frac{5 w L^4}{384 E I}")
        
        st.code(f"""
        ┌─────────────────────────────────────────────────────────────────────────────┐
        │ LOAD CASE          │ MOMENT OF INERTIA │ DEFLECTION                         │
        ├─────────────────────────────────────────────────────────────────────────────┤
        │ Pre-composite (DL) │ Ix = {sec['Ix']/1e6:.2f}×10⁶ mm⁴  │ δDL = {comp['delta_DL']:.2f} mm         │
        │ Post-composite(SDL)│ Ieff = {comp['Ieff']/1e6:.2f}×10⁶ mm⁴│ δSDL = {comp['delta_SDL']:.2f} mm        │
        │ Live Load (LL)     │ Ieff = {comp['Ieff']/1e6:.2f}×10⁶ mm⁴│ δLL = {comp['delta_LL']:.2f} mm         │
        ├─────────────────────────────────────────────────────────────────────────────┤
        │ TOTAL              │                   │ δtotal = {comp['delta_total']:.2f} mm      │
        └─────────────────────────────────────────────────────────────────────────────┘
        """, language=None)
        
        st.markdown("### 7.3 Deflection Limits Check")
        L_mm = L * 1000
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Live Load Deflection:**")
            st.latex(r"\delta_{LL} \leq \frac{L}{360}")
            delta_limit_LL = L_mm / 360
            dcr_LL = comp['delta_LL'] / delta_limit_LL
            st.code(f"""
        δLL = {comp['delta_LL']:.2f} mm
        Limit = L/360 = {L_mm:.0f}/360 = {delta_limit_LL:.2f} mm
        DCR = {comp['delta_LL']:.2f} / {delta_limit_LL:.2f} = {dcr_LL:.3f}
            """, language=None)
            if dcr_LL <= 1.0:
                st.success(f"✅ Live Load Deflection OK")
            else:
                st.error(f"❌ Live Load Deflection FAILS")
        
        with col2:
            st.markdown("**Total Deflection:**")
            st.latex(r"\delta_{total} \leq \frac{L}{240}")
            delta_limit_tot = L_mm / 240
            dcr_tot = comp['delta_total'] / delta_limit_tot
            st.code(f"""
        δtotal = {comp['delta_total']:.2f} mm
        Limit = L/240 = {L_mm:.0f}/240 = {delta_limit_tot:.2f} mm
        DCR = {comp['delta_total']:.2f} / {delta_limit_tot:.2f} = {dcr_tot:.3f}
            """, language=None)
            if dcr_tot <= 1.0:
                st.success(f"✅ Total Deflection OK")
            else:
                st.error(f"❌ Total Deflection FAILS")
        
        # ===========================================================================
        # SECTION 8: DESIGN SUMMARY
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 8. COMPOSITE BEAM DESIGN SUMMARY")
        
        st.code(f"""
        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║                    COMPOSITE BEAM DESIGN SUMMARY                              ║
        ║                    Per AISC 360-16 Chapter I                                  ║
        ╠═══════════════════════════════════════════════════════════════════════════════╣
        ║ Section: {sec.get('name', 'Steel Section'):<20} Span: {L:.2f} m                         ║
        ║ Composite: {comp_type} ({comp_ratio:.0f}%)           Method: {method}                              ║
        ╠═══════════════════════════════════════════════════════════════════════════════╣
        ║ CHECK              │ DEMAND          │ CAPACITY        │ DCR    │ STATUS     ║
        ╠════════════════════╪═════════════════╪═════════════════╪════════╪════════════╣
        ║ Flexure            │ {comp['Mu']:>10.2f} kN⋅m │ {comp['phi_Mn']:>10.2f} kN⋅m │ {comp['DCR_flex']:>6.3f} │ {'✅ PASS' if comp['DCR_flex'] <= 1.0 else '❌ FAIL':>10} ║
        ║ Shear              │ {comp['Vu']:>10.2f} kN   │ {comp['phi_Vn']:>10.2f} kN   │ {comp['DCR_shear']:>6.3f} │ {'✅ PASS' if comp['DCR_shear'] <= 1.0 else '❌ FAIL':>10} ║
        ║ Deflection (LL)    │ {comp['delta_LL']:>10.2f} mm   │ {comp['delta_limit_LL']:>10.2f} mm   │ {comp['DCR_defl_LL']:>6.3f} │ {'✅ PASS' if comp['DCR_defl_LL'] <= 1.0 else '❌ FAIL':>10} ║
        ║ Deflection (Total) │ {comp['delta_total']:>10.2f} mm   │ {comp['delta_limit_total']:>10.2f} mm   │ {comp['DCR_defl_total']:>6.3f} │ {'✅ PASS' if comp['DCR_defl_total'] <= 1.0 else '❌ FAIL':>10} ║
        ╠═══════════════════════════════════════════════════════════════════════════════╣
        """, language=None)
        
        all_pass = (comp['DCR_flex'] <= 1.0 and comp['DCR_shear'] <= 1.0 and 
                    comp['DCR_defl_LL'] <= 1.0 and comp['DCR_defl_total'] <= 1.0)
        
        if all_pass:
            st.success("## ✅ COMPOSITE BEAM DESIGN: ALL CHECKS PASS")
        else:
            st.error("## ❌ COMPOSITE BEAM DESIGN: FAILS - REVISE SECTION")
    
    else:
        # ============== NON-COMPOSITE STEEL BEAM DESIGN ==============
        st.subheader("Non-Composite Steel Beam Design - AISC 360-16")
        st.markdown("**Reference:** AISC 360-16 Chapters F, G, J, L")
        st.info("🏗️ **Design Approach:** Bare steel section carries all loads (no composite action with slab)")
        
        if noncomp_results is None:
            st.error("Non-composite beam design module not available")
        else:
            # Check if we have full results object or fallback dict
            is_full_results = hasattr(noncomp_results, 'classification')
            
            # ===========================================================================
            # SECTION 1: DESIGN DATA
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 1. DESIGN DATA")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 1.1 Steel Section Properties")
                st.markdown(f"**Section:** {sec_name}")
                st.code(f"""
  Depth                    d  = {sec['d']:.1f} mm
  Flange width            bf  = {sec['bf']:.1f} mm
  Flange thickness        tf  = {sec['tf']:.2f} mm
  Web thickness           tw  = {sec['tw']:.2f} mm
  Cross-sectional area    As  = {sec['A']:.0f} mm²
  Moment of inertia       Ix  = {sec['Ix']/1e6:.2f} × 10⁶ mm⁴
                """, language=None)
            
            with col2:
                st.markdown("### 1.2 Material Properties")
                st.markdown(f"**Steel Grade:** {grade}")
                st.code(f"""
  Yield strength          Fy  = {Fy:.0f} MPa
  Elastic modulus         Es  = 200,000 MPa
                """, language=None)
            
            # ===========================================================================
            # SECTION 2: SECTION CLASSIFICATION
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 2. SECTION CLASSIFICATION")
            st.markdown("**Reference:** AISC 360-16 Table B4.1b")
            
            if is_full_results:
                cls = noncomp_results.classification
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 2.1 Flange Slenderness")
                    st.latex(r"\lambda_f = \frac{b_f}{2t_f}")
                    st.code(f"""
  λf = {sec['bf']:.1f} / (2 × {sec['tf']:.2f}) = {cls.lambda_f:.2f}
  λpf (compact)     = 0.38√(E/Fy) = {cls.lambda_pf:.2f}
  λrf (noncompact)  = 1.0√(E/Fy) = {cls.lambda_rf:.2f}
  
  Classification: {cls.flange_class}
                    """, language=None)
                
                with col2:
                    st.markdown("### 2.2 Web Slenderness")
                    st.latex(r"\lambda_w = \frac{h}{t_w}")
                    h_web = sec['d'] - 2 * sec['tf']
                    st.code(f"""
  h = d - 2tf = {h_web:.1f} mm
  λw = {h_web:.1f} / {sec['tw']:.2f} = {cls.lambda_w:.2f}
  λpw (compact)     = 3.76√(E/Fy) = {cls.lambda_pw:.2f}
  λrw (noncompact)  = 5.70√(E/Fy) = {cls.lambda_rw:.2f}
  
  Classification: {cls.web_class}
                    """, language=None)
                
                if cls.overall_class == "Compact":
                    st.success(f"✅ **Section is COMPACT** - Full plastic capacity available")
                elif cls.overall_class == "Noncompact":
                    st.warning(f"⚠️ **Section is NONCOMPACT** - Reduced capacity")
                else:
                    st.error(f"❌ **Section is SLENDER** - Significantly reduced capacity")
            
            # ===========================================================================
            # SECTION 3: LOADS
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 3. LOADING")
            
            w_total = w_DL + w_SDL + w_LL
            if method == "LRFD":
                w_u = 1.2 * (w_DL + w_SDL) + 1.6 * w_LL
            else:
                w_u = w_total
            
            st.code(f"""
  Dead Load (beam + slab)      wDL  = {w_DL:.2f} kN/m
  Superimposed Dead Load       wSDL = {w_SDL:.2f} kN/m
  Live Load                    wLL  = {w_LL:.2f} kN/m
  ─────────────────────────────────────────────────
  Total Service Load           w    = {w_total:.2f} kN/m
  
  Factored Load ({method}):
  wu = {'1.2(DL+SDL) + 1.6LL' if method == 'LRFD' else 'DL + SDL + LL'} = {w_u:.2f} kN/m
            """, language=None)
            
            # ===========================================================================
            # SECTION 4: FLEXURAL STRENGTH
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 4. FLEXURAL STRENGTH")
            st.markdown("**Reference:** AISC 360-16 Chapter F")
            
            Mu = w_u * L**2 / 8
            st.latex(r"M_u = \frac{w_u \times L^2}{8}")
            st.code(f"Mu = {w_u:.2f} × {L:.2f}² / 8 = {Mu:.2f} kN-m", language=None)
            
            if is_full_results:
                flex = noncomp_results.flexure
                
                st.markdown("### 4.1 Plastic Moment Capacity")
                st.latex(r"M_p = F_y \times Z_x")
                Zx = sec.get('Zx', sec['Ix'] / (sec['d']/2) * 1.12)
                st.code(f"Mp = {Fy:.0f} × {Zx/1e3:.2f}×10³ / 10⁶ = {flex.Mp:.2f} kN-m", language=None)
                
                st.markdown("### 4.2 Lateral-Torsional Buckling Check")
                st.code(f"""
  Unbraced length     Lb = {flex.Lb:.0f} mm
  Limiting lengths:
    Lp (plastic)      = {flex.Lp:.0f} mm
    Lr (inelastic)    = {flex.Lr:.0f} mm
  
  Moment gradient factor Cb = {flex.Cb:.2f}
  
  Limit State: {flex.limit_state}
                """, language=None)
                
                st.markdown("### 4.3 Nominal and Design Strength")
                st.code(f"""
  Nominal moment     Mn = {flex.Mn:.2f} kN-m
  Design moment      φMn = 0.90 × {flex.Mn:.2f} = {flex.phi_Mn:.2f} kN-m
  
  DCR = Mu / φMn = {Mu:.2f} / {flex.phi_Mn:.2f} = {noncomp_results.DCR_flex:.3f}
                """, language=None)
                
                if noncomp_results.DCR_flex <= 1.0:
                    st.success(f"✅ **FLEXURE OK** — DCR = {noncomp_results.DCR_flex:.3f} ≤ 1.0")
                else:
                    st.error(f"❌ **FLEXURE NG** — DCR = {noncomp_results.DCR_flex:.3f} > 1.0")
            
            # ===========================================================================
            # SECTION 5: SHEAR STRENGTH
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 5. SHEAR STRENGTH")
            st.markdown("**Reference:** AISC 360-16 Chapter G")
            
            Vu = w_u * L / 2
            st.latex(r"V_u = \frac{w_u \times L}{2}")
            st.code(f"Vu = {w_u:.2f} × {L:.2f} / 2 = {Vu:.2f} kN", language=None)
            
            if is_full_results:
                shear = noncomp_results.shear
                
                st.latex(r"V_n = 0.6 \times F_y \times A_w \times C_{v1}")
                st.code(f"""
  Web area           Aw = d × tw = {shear.Aw:.0f} mm²
  Web coefficient    Cv1 = {shear.Cv1:.3f}
  
  Nominal shear      Vn = 0.6 × {Fy:.0f} × {shear.Aw:.0f} × {shear.Cv1:.3f} / 1000 = {shear.Vn:.2f} kN
  Design shear       φVn = {shear.phi_v:.2f} × {shear.Vn:.2f} = {shear.phi_Vn:.2f} kN
  
  DCR = Vu / φVn = {Vu:.2f} / {shear.phi_Vn:.2f} = {noncomp_results.DCR_shear:.3f}
                """, language=None)
                
                if noncomp_results.DCR_shear <= 1.0:
                    st.success(f"✅ **SHEAR OK** — DCR = {noncomp_results.DCR_shear:.3f} ≤ 1.0")
                else:
                    st.error(f"❌ **SHEAR NG** — DCR = {noncomp_results.DCR_shear:.3f} > 1.0")
            
            # ===========================================================================
            # SECTION 6: DEFLECTION
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 6. DEFLECTION")
            st.markdown("**Reference:** AISC 360-16 Chapter L")
            
            st.latex(r"\delta = \frac{5 \times w \times L^4}{384 \times E \times I_x}")
            
            if is_full_results:
                defl = noncomp_results.deflection
                
                st.code(f"""
  Using bare steel moment of inertia: Ix = {sec['Ix']/1e6:.2f} × 10⁶ mm⁴
  
  Dead + SDL deflection   δDL   = {defl.delta_DL:.2f} mm
  Live load deflection    δLL   = {defl.delta_LL:.2f} mm
  Total deflection        δtot  = {defl.delta_total:.2f} mm
  
  Limits:
    Live load limit       L/360 = {defl.limit_LL:.2f} mm
    Total load limit      L/240 = {defl.limit_total:.2f} mm
  
  DCR (LL)    = {defl.delta_LL:.2f} / {defl.limit_LL:.2f} = {defl.DCR_LL:.3f}
  DCR (Total) = {defl.delta_total:.2f} / {defl.limit_total:.2f} = {defl.DCR_total:.3f}
                """, language=None)
                
                if defl.DCR_LL <= 1.0 and defl.DCR_total <= 1.0:
                    st.success(f"✅ **DEFLECTION OK**")
                else:
                    st.error(f"❌ **DEFLECTION NG** — Exceeds limits")
            
            # ===========================================================================
            # SECTION 7: WEB LOCAL EFFECTS
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 7. WEB LOCAL EFFECTS")
            st.markdown("**Reference:** AISC 360-16 Section J10")
            
            if is_full_results:
                wly = noncomp_results.web_yielding
                wcr = noncomp_results.web_crippling
                Ru = noncomp_results.Ru
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 7.1 Web Local Yielding (J10.2)")
                    st.code(f"""
  At end reaction:
  φRn = {wly.phi_Rn_end:.2f} kN
  Ru  = {Ru:.2f} kN
  DCR = {noncomp_results.DCR_web_yielding:.3f}
                    """, language=None)
                
                with col2:
                    st.markdown("### 7.2 Web Crippling (J10.3)")
                    st.code(f"""
  At end reaction:
  φRn = {wcr.phi_Rn_end:.2f} kN
  Ru  = {Ru:.2f} kN
  DCR = {noncomp_results.DCR_web_crippling:.3f}
                    """, language=None)
            
            # ===========================================================================
            # SECTION 8: COMBINED AXIAL + BENDING (if applicable)
            # ===========================================================================
            if beam_column_results is not None and beam_column_results.combined is not None:
                st.markdown("---")
                st.markdown("## 8. COMBINED AXIAL + BENDING")
                st.markdown("**Reference:** AISC 360-16 Chapter H - Design of Members for Combined Forces")
                
                comb = beam_column_results.combined
                ax_str = beam_column_results.axial_strength
                
                st.info(f"**Axial Load Type:** {comb.axial_type} | **Pu = {beam_column_results.Pu:.1f} kN**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 8.1 Axial Strength")
                    if comb.axial_type == "Compression":
                        st.markdown("**Reference:** AISC 360-16 Chapter E")
                        st.latex(r"P_n = F_{cr} \times A_g")
                        st.code(f"""
    COMPRESSION STRENGTH (Chapter E):
    ═══════════════════════════════════════════════════════════════
    Gross Area           Ag    = {ax_str.Ag:.0f} mm²
    Effective Length     Lc    = {ax_str.Lc:.0f} mm
    Radius of Gyration   r     = {ax_str.r:.1f} mm
    Slenderness Ratio    KL/r  = {ax_str.KL_r:.1f}
    
    Elastic Buckling     Fe    = π²E/(KL/r)² = {ax_str.Fe:.1f} MPa
    Critical Stress      Fcr   = {ax_str.Fcr:.1f} MPa
    
    Nominal Strength     Pn    = Fcr × Ag = {ax_str.Pn:.1f} kN
    Design Strength      φPn   = 0.90 × {ax_str.Pn:.1f} = {ax_str.phi_Pn:.1f} kN
    
    Limit State: {ax_str.limit_state}
    ═══════════════════════════════════════════════════════════════
                        """, language=None)
                    else:  # Tension
                        st.markdown("**Reference:** AISC 360-16 Chapter D")
                        st.latex(r"P_n = F_y \times A_g")
                        st.code(f"""
    TENSION STRENGTH (Chapter D):
    ═══════════════════════════════════════════════════════════════
    Gross Area           Ag    = {ax_str.Ag:.0f} mm²
    
    Yielding on Gross Section (D2-1):
    Pn = Fy × Ag = {ax_str.Pn_yield:.1f} kN
    
    Design Strength      φPn   = 0.90 × {ax_str.Pn:.1f} = {ax_str.phi_Pn:.1f} kN
    
    Limit State: {ax_str.limit_state}
    ═══════════════════════════════════════════════════════════════
                        """, language=None)
                
                with col2:
                    st.markdown("### 8.2 Interaction Check (H1)")
                    st.markdown("**Interaction Equations:**")
                    
                    if comb.Pr_Pc >= 0.2:
                        st.latex(r"\text{H1-1a: } \frac{P_r}{P_c} + \frac{8}{9}\left(\frac{M_{rx}}{M_{cx}}\right) \leq 1.0")
                    else:
                        st.latex(r"\text{H1-1b: } \frac{P_r}{2P_c} + \left(\frac{M_{rx}}{M_{cx}}\right) \leq 1.0")
                    
                    st.code(f"""
    INTERACTION CHECK (Chapter H):
    ═══════════════════════════════════════════════════════════════
    Required axial strength    Pr  = {comb.Pr:.1f} kN
    Available axial strength   Pc  = {comb.Pc:.1f} kN
    Axial ratio               Pr/Pc = {comb.Pr_Pc:.4f}
    
    Required flexural strength Mrx = {comb.Mrx:.1f} kN-m
    Available flexural strength Mcx = {comb.Mcx:.1f} kN-m
    Moment ratio              Mrx/Mcx = {comb.Mrx_Mcx:.4f}
    
    Since Pr/Pc = {comb.Pr_Pc:.3f} {'≥' if comb.Pr_Pc >= 0.2 else '<'} 0.2:
    Use Equation {comb.equation_used}
    
    {'Pr/Pc + (8/9)(Mrx/Mcx)' if comb.equation_used == 'H1-1a' else 'Pr/(2Pc) + Mrx/Mcx'} = {comb.interaction_value:.4f}
    
    DCR = {comb.DCR:.3f} {'≤' if comb.ok else '>'} 1.0 → {'✅ OK' if comb.ok else '❌ NG'}
    ═══════════════════════════════════════════════════════════════
                    """, language=None)
                
                if comb.ok:
                    st.success(f"✅ **COMBINED AXIAL + BENDING OK** — DCR = {comb.DCR:.3f} ≤ 1.0")
                else:
                    st.error(f"❌ **COMBINED AXIAL + BENDING FAILS** — DCR = {comb.DCR:.3f} > 1.0")
                
                # Update summary section number
                summary_section = "9"
            else:
                summary_section = "8"
            
            # ===========================================================================
            # SUMMARY
            # ===========================================================================
            st.markdown("---")
            st.markdown(f"## {summary_section if 'summary_section' in dir() else '8'}. DESIGN SUMMARY")
            
            if is_full_results:
                # Build summary data
                checks_list = ["Flexure", "Shear", "Web Local Yielding", "Web Crippling", "Deflection (LL)", "Deflection (Total)"]
                dcr_list = [
                    f"{noncomp_results.DCR_flex:.3f}",
                    f"{noncomp_results.DCR_shear:.3f}",
                    f"{noncomp_results.DCR_web_yielding:.3f}",
                    f"{noncomp_results.DCR_web_crippling:.3f}",
                    f"{noncomp_results.deflection.DCR_LL:.3f}",
                    f"{noncomp_results.deflection.DCR_total:.3f}"
                ]
                status_list = [
                    "✅ OK" if noncomp_results.DCR_flex <= 1.0 else "❌ NG",
                    "✅ OK" if noncomp_results.DCR_shear <= 1.0 else "❌ NG",
                    "✅ OK" if noncomp_results.DCR_web_yielding <= 1.0 else "❌ NG",
                    "✅ OK" if noncomp_results.DCR_web_crippling <= 1.0 else "❌ NG",
                    "✅ OK" if noncomp_results.deflection.DCR_LL <= 1.0 else "❌ NG",
                    "✅ OK" if noncomp_results.deflection.DCR_total <= 1.0 else "❌ NG"
                ]
                
                # Add interaction check if applicable
                if beam_column_results is not None and beam_column_results.combined is not None:
                    comb = beam_column_results.combined
                    checks_list.append(f"Combined ({comb.equation_used})")
                    dcr_list.append(f"{comb.DCR:.3f}")
                    status_list.append("✅ OK" if comb.ok else "❌ NG")
                
                summary_data = {
                    "Check": checks_list,
                    "DCR": dcr_list,
                    "Status": status_list
                }
                st.table(summary_data)
                
                # Determine overall pass/fail
                if beam_column_results is not None:
                    overall_pass = beam_column_results.all_pass
                    governing = beam_column_results.governing_check
                else:
                    overall_pass = noncomp_results.all_pass
                    governing = noncomp_results.governing_check
                
                if overall_pass:
                    st.success("## ✅ NON-COMPOSITE STEEL BEAM: ALL CHECKS PASS")
                else:
                    st.error(f"## ❌ NON-COMPOSITE STEEL BEAM: FAILS - {governing}")

if design_mode == "Composite":
    with tab4:
        st.subheader("Shear Stud Design - Composite Action")
        st.markdown("**Reference:** AISC 360-16 Section I8 - Steel Anchors")
    
        # Assign local variable for rib height
        hr = deck_hr
        
        # ===========================================================================
        # SECTION 1: DESIGN DATA
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 1. SHEAR STUD DATA")
        
        st.code(f"""
        HEADED SHEAR STUD DETAIL:
        
                        ┌───────┐  ← Head (provides pullout resistance)
                        │███████│     Head dia ≈ 1.5 × shaft dia
                        ├───────┤
                        │       │
                        │       │     Hsa = {stud_ht} mm (height after welding)
                        │   ↑   │
                        │   │   │     d = {stud_dia} mm (shaft diameter)
                        │   │   │
                        │   │   │
                        │   │   │
                        │   ↓   │
        ════════════════╧═══════╧════════════════  ← Steel beam flange
                        │███████│
                        │███████│  ← Weld (arc stud welding)
                        └───────┘
        
        STUD PROPERTIES:
        ─────────────────────────────────────────────────────
        Shaft diameter               d    = {stud_dia} mm
        Height after welding         Hsa  = {stud_ht} mm
        Ultimate tensile strength    Fu   = {stud_Fu} MPa
        Cross-sectional area         Asa  = π × d²/4 = {stud_r['Asa']:.1f} mm²
        """, language=None)
        
        st.markdown("### 1.1 Height-to-Diameter Ratio Check")
        st.markdown("**Per AISC 360-16 §I8.1, minimum Hsa/d = 4 for full strength:**")
        st.latex(r"\frac{H_{sa}}{d} \geq 4")
        
        Hd = stud_ht / stud_dia
        
        st.code(f"""
        Hsa/d = {stud_ht} / {stud_dia} = {Hd:.2f}
        
        Check: {Hd:.2f} {'≥' if Hd >= 4 else '<'} 4.0  →  {'OK ✅' if Hd >= 4 else 'NG ❌ (reduced strength)'}
        """, language=None)
        
        # ===========================================================================
        # SECTION 2: REDUCTION FACTORS
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 2. DECK RIB REDUCTION FACTORS")
        st.markdown("**Reference:** AISC 360-16 Table I8.2a")
        
        st.markdown("""
        When shear studs are placed in the ribs of metal deck, their strength is reduced 
        due to the concrete confinement geometry. Two factors apply:
        """)
        
        st.code(f"""
        DECK RIB GEOMETRY:
        
        Deck Orientation: {deck.upper()}
        
        {'PERPENDICULAR (ribs ⊥ beam):' if deck == 'perpendicular' else 'PARALLEL (ribs ∥ beam):'}
        
            ┌─────────────────────────────────────────────────┐
            │                  CONCRETE                       │
            ├──────┬────────────┬──────┬────────────┬────────┤
            │      │░░░░░░░░░░░░│      │░░░░░░░░░░░░│        │
            │      │░░░ RIB ░░░░│      │░░░ RIB ░░░░│        │
            │      │░░░░░░░░░░░░│      │░░░░░░░░░░░░│        │
            │      │    ●●●     │      │    ●●●     │        │  ← Studs in ribs
            └──────┴────────────┴──────┴────────────┴────────┘
                     └── {spr} studs per rib ──┘
        
        REDUCTION FACTORS (Table I8.2a):
        ─────────────────────────────────────────────────────
        """, language=None)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Rg - Group Effect Factor")
            st.code(f"""
        Accounts for:
        • Number of studs in a rib
        • Stud spacing within rib
        • Concrete confinement
        
        Nr (studs per rib) = {spr}
        Deck orientation   = {deck}
        
        From Table I8.2a:
        Rg = {Rg}
            """, language=None)
        
        with col2:
            st.markdown("### Rp - Position Effect Factor")
            st.code(f"""
        Accounts for:
        • Stud position in rib
        • Favorable vs unfavorable position
        • Emax ≥ 2d for strong position
        
        Stud position: Strong (assumed)
        
        From Table I8.2a:
        Rp = {Rp}
            """, language=None)
        
        # ===========================================================================
        # SECTION 3: STUD STRENGTH
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 3. NOMINAL STUD STRENGTH CALCULATION")
        st.markdown("**Reference:** AISC 360-16 Equation I8-1")
        
        st.markdown("""
        The nominal shear strength of one stud is the **minimum** of:
        1. **Concrete-controlled** - stud pullout/pryout through concrete
        2. **Steel-controlled** - shear yielding of stud shaft
        """)
        
        st.latex(r"Q_n = \min\left(0.5 A_{sa}\sqrt{f'_c E_c}, \quad R_g R_p A_{sa} F_u\right)")
        
        Ec = 4700 * math.sqrt(fc)
        
        st.markdown("### 3.1 Concrete-Controlled Strength")
        st.latex(r"Q_{n,conc} = 0.5 \times A_{sa} \times \sqrt{f'_c \times E_c}")
        
        Qn_conc = 0.5 * stud_r['Asa'] * math.sqrt(fc * Ec)
        
        st.code(f"""
        CONCRETE STRENGTH CALCULATION:
        
        Ec = 4700 × √f'c = 4700 × √{fc:.0f} = {Ec:.0f} MPa
        
        Qn,conc = 0.5 × Asa × √(f'c × Ec)
        Qn,conc = 0.5 × {stud_r['Asa']:.1f} mm² × √({fc:.0f} MPa × {Ec:.0f} MPa)
        Qn,conc = 0.5 × {stud_r['Asa']:.1f} × √({fc * Ec:.0f})
        Qn,conc = 0.5 × {stud_r['Asa']:.1f} × {math.sqrt(fc * Ec):.1f}
        Qn,conc = {Qn_conc:.0f} N = {Qn_conc/1000:.2f} kN
        """, language=None)
        
        st.markdown("### 3.2 Steel-Controlled Strength")
        st.latex(r"Q_{n,steel} = R_g \times R_p \times A_{sa} \times F_u")
        
        Qn_steel = Rg * Rp * stud_r['Asa'] * stud_Fu
        
        st.code(f"""
        STEEL STRENGTH CALCULATION:
        
        Qn,steel = Rg × Rp × Asa × Fu
        Qn,steel = {Rg} × {Rp} × {stud_r['Asa']:.1f} mm² × {stud_Fu} MPa
        Qn,steel = {Rg * Rp * stud_r['Asa']:.1f} × {stud_Fu}
        Qn,steel = {Qn_steel:.0f} N = {Qn_steel/1000:.2f} kN
        """, language=None)
        
        st.markdown("### 3.3 Governing Strength")
        Qn = min(Qn_conc, Qn_steel)
        gov = "CONCRETE (pullout/pryout)" if Qn == Qn_conc else "STEEL (shear)"
        
        st.code(f"""
        ┌─────────────────────────────────────────────────────────────┐
        │                    STUD STRENGTH COMPARISON                 │
        ├─────────────────────────────────────────────────────────────┤
        │ Concrete-controlled:  Qn,conc  = {Qn_conc/1000:>8.2f} kN              │
        │ Steel-controlled:     Qn,steel = {Qn_steel/1000:>8.2f} kN              │
        ├─────────────────────────────────────────────────────────────┤
        │ GOVERNING:            Qn       = {Qn/1000:>8.2f} kN              │
        │                       Controlled by: {gov:<25}│
        └─────────────────────────────────────────────────────────────┘
        """, language=None)
        
        if Qn == Qn_conc:
            st.info(f"**Qn = {Qn/1000:.2f} kN** - Governed by concrete (increase f'c or stud embedment for higher capacity)")
        else:
            st.info(f"**Qn = {Qn/1000:.2f} kN** - Governed by steel (increase stud diameter for higher capacity)")
        
        # ===========================================================================
        # SECTION 4: REQUIRED VS PROVIDED STUDS
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 4. REQUIRED VS PROVIDED STUDS")
        st.markdown("**Reference:** AISC 360-16 Section I3.2d")
        
        st.markdown("### 4.1 Maximum Horizontal Shear to be Transferred")
        st.markdown("""
        For full composite action, the total horizontal shear between steel and concrete 
        at the point of maximum moment equals the **minimum** of:
        """)
        
        Ts = sec['A'] * Fy / 1000
        t_above = tc - hr
        Cc = 0.85 * fc * beff * t_above / 1000
        V_prime = min(Ts, Cc)
        
        st.latex(r"V' = \min(T_s, C_c) = \min(A_s F_y, \quad 0.85 f'_c b_{eff} t_{above})")
        
        st.code(f"""
        FORCE EQUILIBRIUM FOR FULL COMPOSITE:
        
        Steel tension capacity:
        Ts = As × Fy = {sec['A']:.0f} mm² × {Fy:.0f} MPa / 1000 = {Ts:.1f} kN
        
        Concrete compression capacity:
        t_above = tc - hr = {tc:.0f} - {hr:.0f} = {t_above:.0f} mm
        Cc = 0.85 × f'c × beff × t_above / 1000
        Cc = 0.85 × {fc:.0f} × {beff:.0f} × {t_above:.0f} / 1000 = {Cc:.1f} kN
        
        Maximum horizontal shear (per half span):
        V' = min({Ts:.1f}, {Cc:.1f}) = {V_prime:.1f} kN
        
        Governed by: {'STEEL YIELDING' if V_prime == Ts else 'CONCRETE CRUSHING'}
        """, language=None)
        
        st.markdown("### 4.2 Number of Studs Required (Full Composite)")
        st.latex(r"n_{req} = \frac{V'}{Q_n}")
        
        n_req = V_prime * 1000 / Qn
        
        st.code(f"""
        n_req = V' / Qn
        n_req = {V_prime:.1f} kN × 1000 / {Qn:.0f} N
        n_req = {V_prime * 1000:.0f} / {Qn:.0f}
        n_req = {n_req:.1f} studs (per half span, for 100% composite)
        
        → Rounded up: {math.ceil(n_req)} studs per half span
        """, language=None)
        
        st.markdown("### 4.3 Studs Provided")
        n_total = n_studs * 2
        Qn_total_prov = n_studs * Qn / 1000
        
        st.code(f"""
        STUDS PROVIDED:
        ─────────────────────────────────────────────────────
        Studs per half span (provided):     {n_studs}
        Total studs (full span):            {n_total}
        
        Total shear connector capacity:
        ΣQn = n × Qn = {n_studs} × {Qn/1000:.2f} kN = {Qn_total_prov:.1f} kN (per half span)
        """, language=None)
        
        # ===========================================================================
        # SECTION 5: DEGREE OF COMPOSITE ACTION
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 5. DEGREE OF COMPOSITE ACTION")
        
        st.markdown("""
        **Partial composite design** is permitted per AISC 360-16 §I3.2c when:
        - Minimum 25% composite action is provided
        - Reduced strength and increased deflection are accounted for
        """)
        
        st.latex(r"\eta = \frac{\Sigma Q_n}{\min(T_s, C_c)} \times 100\%")
        
        comp_ratio = comp['Qn_total'] / V_prime * 100
        
        st.code(f"""
        COMPOSITE ACTION CALCULATION:
        
        η = ΣQn / V' × 100%
        η = {comp['Qn_total']:.1f} kN / {V_prime:.1f} kN × 100%
        η = {comp_ratio:.1f}%
        
        ┌─────────────────────────────────────────────────────────────┐
        │                   COMPOSITE ACTION SUMMARY                  │
        ├─────────────────────────────────────────────────────────────┤
        │ Required for FULL composite:     {V_prime:>8.1f} kN               │
        │ Provided shear connection:       {comp['Qn_total']:>8.1f} kN               │
        │ Degree of composite action:      {comp_ratio:>8.1f} %               │
        ├─────────────────────────────────────────────────────────────┤
        │ Classification: {'FULL COMPOSITE (η ≥ 100%)' if comp_ratio >= 100 else 'PARTIAL COMPOSITE' if comp_ratio >= 25 else 'INSUFFICIENT (η < 25%)':<40}│
        └─────────────────────────────────────────────────────────────┘
        """, language=None)
        
        if comp_ratio >= 100:
            st.success(f"**✅ FULL COMPOSITE ACTION: {comp_ratio:.0f}%** - Maximum strength and stiffness")
        elif comp_ratio >= 25:
            st.info(f"**ℹ️ PARTIAL COMPOSITE ACTION: {comp_ratio:.0f}%** - Per §I3.2c (≥25% minimum)")
        else:
            st.error(f"**❌ INSUFFICIENT COMPOSITE ACTION: {comp_ratio:.0f}%** - Below 25% minimum per §I3.2c")
        
        # ===========================================================================
        # SECTION 6: STUD PLACEMENT REQUIREMENTS
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 6. STUD PLACEMENT REQUIREMENTS")
        st.markdown("**Reference:** AISC 360-16 Section I8.2d")
        
        st.code(f"""
        MINIMUM/MAXIMUM SPACING REQUIREMENTS:
        ═══════════════════════════════════════════════════════════════
        
        LONGITUDINAL SPACING (along beam length):
        • Maximum: 36 in. (914 mm) or 8 × slab thickness
                 = min(914, 8 × {tc:.0f}) = {min(914, 8*tc):.0f} mm
        • Minimum: 6 × stud diameter = 6 × {stud_dia} = {6*stud_dia} mm
        
        TRANSVERSE SPACING (across beam flange):
        • Minimum: 4 × stud diameter = 4 × {stud_dia} = {4*stud_dia} mm
        • Edge distance: ≥ 1 in. (25 mm) from flange edge
        
        CONCRETE COVER:
        • Minimum embedment in concrete: 1.5 in. (38 mm)
        • Actual embedment: tc - hr - stud base ≈ {tc:.0f} - {hr:.0f} - 5 = {tc - hr - 5:.0f} mm
        
        STUD LAYOUT FOR THIS BEAM:
        ───────────────────────────────────────────────────────────────
        Half span length:       L/2 = {L*1000/2:.0f} mm
        Studs per half span:    {n_studs}
        Average spacing:        {L*1000/2/n_studs if n_studs > 0 else 0:.0f} mm
        ═══════════════════════════════════════════════════════════════
        """, language=None)
        
        # Check spacing
        avg_spacing = L * 1000 / 2 / n_studs if n_studs > 0 else 0
        max_spacing = min(914, 8 * tc)
        spacing_ok = avg_spacing <= max_spacing
        
        st.markdown("### Code Compliance Summary")
        
        checks_data = {
            "Requirement": [
                "Hsa/d ≥ 4 (§I8.1)",
                "Composite ≥ 25% (§I3.2c)",
                f"Spacing ≤ {max_spacing:.0f} mm (§I8.2d)",
                "Embedment ≥ 38 mm (§I8.1)"
            ],
            "Actual": [
                f"{Hd:.2f}",
                f"{comp_ratio:.0f}%",
                f"{avg_spacing:.0f} mm",
                f"{tc - hr - 5:.0f} mm"
            ],
            "Status": [
                "✅ OK" if Hd >= 4 else "❌ NG",
                "✅ OK" if comp_ratio >= 25 else "❌ NG",
                "✅ OK" if spacing_ok else "❌ NG",
                "✅ OK" if (tc - hr) >= 43 else "⚠️ CHECK"
            ]
        }
        st.table(checks_data)
    
with tab5:
    st.subheader("Floor Vibration Serviceability Analysis")
    st.markdown("**Reference:** AISC Design Guide 11 - Vibrations of Steel-Framed Structural Systems Due to Human Activity")
    
    if not vibration_enabled:
        st.info("📌 Enable Vibration Analysis in the sidebar to see results")
        st.markdown("""
        **Why Vibration Analysis?**
        
        Floor vibrations caused by walking can be annoying to occupants even when structurally safe. 
        Enable this analysis to check if your floor meets human comfort criteria per AISC Design Guide 11.
        """)
    else:
        # ===========================================================================
        # SECTION 1: INTRODUCTION AND INPUTS
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 1. VIBRATION ANALYSIS PARAMETERS")
        
        st.markdown("""
        **Human Perception of Floor Vibration:**
        
        Floor vibrations caused by walking can be annoying to occupants even when 
        structurally safe. The analysis follows AISC Design Guide 11 methodology:
        
        1. Calculate natural frequency of floor system
        2. Estimate peak acceleration from walking excitation  
        3. Compare to human comfort limits
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### User Inputs")
            bay_width = st.number_input("Bay Width (m)", 3.0, 20.0, max(spacing, 3.0), 0.5, key="bay_width")
            occupancy = st.selectbox("Occupancy Type", ["Office/Residential", "Shopping Mall", "Dining/Dancing", "Rhythmic Activity"], key="occupancy")
            beta = st.number_input("Damping Ratio β", 0.01, 0.10, 0.03, 0.005, key="damping", 
                                   help="Typical: 0.02-0.03 for bare floor, 0.03-0.05 with partitions")
        
        # Acceleration limits per AISC DG11 Table 4.1
        accel_limits = {"Office/Residential": 0.005, "Shopping Mall": 0.015, "Dining/Dancing": 0.015, "Rhythmic Activity": 0.05}
        ao_g = accel_limits[occupancy]
        fn_min = 4.0 if occupancy == "Office/Residential" else 3.0 if occupancy != "Rhythmic Activity" else 9.0
        
        with col2:
            st.markdown("### Acceptance Criteria (DG11 Table 4.1)")
            st.code(f"""
    OCCUPANCY-BASED LIMITS:
    ─────────────────────────────────────────
    Occupancy Type:     {occupancy}
    Acceleration Limit: {ao_g*100:.2f}% g ({ao_g:.4f} g)
    Min. Frequency:     {fn_min:.1f} Hz
    
    TOLERANCE SCALE:
    • Office/Residential: 0.5% g (most sensitive)
    • Shopping Mall:      1.5% g (moderate)  
    • Dining/Dancing:     1.5% g (moderate)
    • Rhythmic Activity:  5.0% g (least sensitive)
            """, language=None)
        
        # ===========================================================================
        # SECTION 2: FLOOR LOADING FOR VIBRATION
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 2. EFFECTIVE FLOOR WEIGHT")
        st.markdown("**Reference:** AISC DG11 Section 4.1")
        
        # Floor loading for vibration (only sustained loads - area loads)
        w_sustained_area = w_slab + w_SDL_area  # kN/m²
        w_floor_vib = w_sustained_area * spacing  # kN/m (line load on beam)
        L_mm_vib = L * 1000  # convert to mm
        B_eff_vib = min(0.6 * L_mm_vib, spacing * 1000)
        
        st.code(f"""
    FLOOR LOADING (for vibration analysis):
    ═══════════════════════════════════════════════════════════════
    
    Note: Only sustained (dead) loads are used - live load excluded
          as occupants are the source of vibration, not additional mass.
    
    Slab DL:              {w_slab:.2f} kN/m²
    Superimposed DL:      {w_SDL_area:.2f} kN/m²  
    ───────────────────────────────────────
    Total sustained:      {w_sustained_area:.2f} kN/m²
    
    Tributary width:      {spacing:.2f} m
    
    Line load on beam:    w = {w_floor_vib:.2f} kN/m
    ═══════════════════════════════════════════════════════════════
        """, language=None)
        
        st.markdown("""
        The floor panel effective width per AISC DG11 Section 4.1 determines 
        whether the floor is susceptible to resonant vibration from walking.
        """)
        
        st.latex(r"B_{eff} = \min(0.6L, B)")
        st.markdown(f"""
        Where:
        - L = beam span = {L*1000:.0f} mm
        - B = bay width = {spacing*1000:.0f} mm
        
        **B_eff = min(0.6 × {L*1000:.0f}, {spacing*1000:.0f}) = {B_eff_vib:.0f} mm**
        """)
        
        # ===========================================================================
        # SECTION 3: FUNDAMENTAL FREQUENCY
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 3. FUNDAMENTAL NATURAL FREQUENCY")
        st.markdown("**Reference:** AISC DG11 Eq. 3.1, 3.3")
        
        st.latex(r"f_n = 0.18 \sqrt{\frac{g}{\Delta_j + \Delta_g}}")
        st.markdown("""
        **Where:**
        - g = 9810 mm/s² (gravitational acceleration)
        - Δj = beam midspan deflection due to sustained load (mm)
        - Δg = girder midspan deflection, if applicable (mm)
        
        **Reference:** AISC DG11 Eq. 3.3
        """)
        
        # Calculate deflection
        E_vib = 200000  # MPa
        
        # Use appropriate moment of inertia based on design mode
        if design_mode == "Composite" and comp is not None:
            Ix_vib = comp["Ieff"]  # Use composite moment of inertia
            Ix_label = "I_{comp}"
        else:
            Ix_vib = sec['Ix']  # Use bare steel moment of inertia
            Ix_label = "I_x"
        
        # Beam deflection (simply supported)
        delta_j_vib = 5 * w_floor_vib * (L*1000)**4 / (384 * E_vib * Ix_vib * 1e6)
        delta_g_vib = 0  # Assume no girder flexibility for now
        
        st.markdown("### 3.1 Beam Deflection")
        st.latex(r"\Delta_j = \frac{5 w L^4}{384 E " + Ix_label + r"}")
        st.markdown(f"""
        **Calculation:**
        - w = {w_floor_vib:.2f} kN/m = {w_floor_vib:.2f} N/mm
        - L = {L*1000:.0f} mm
        - E = {E_vib:,} MPa
        - I_comp = {Ix_vib:.2e} mm⁴
        
        Δj = 5 × {w_floor_vib:.2f} × ({L*1000:.0f})⁴ / (384 × {E_vib:,} × {Ix_vib:.2e})
        **Δj = {delta_j_vib:.3f} mm**
        """)
        
        st.markdown("### 3.2 Girder Deflection")
        st.markdown(f"Δg = {delta_g_vib:.3f} mm (assumed rigid girder support)")
        
        st.markdown("### 3.3 Natural Frequency")
        g_accel = 9810  # mm/s²
        fn_calc = 0.18 * math.sqrt(g_accel / (delta_j_vib + delta_g_vib + 0.001))  # +0.001 to avoid division by zero
        
        st.latex(f"f_n = 0.18 \\sqrt{{\\frac{{9810}}{{{delta_j_vib:.3f} + {delta_g_vib:.3f}}}}} = \\textbf{{{fn_calc:.2f} Hz}}")
        
        freq_ok = fn_calc >= fn_min
        if freq_ok:
            st.success(f"✅ **FREQUENCY OK** — fn = {fn_calc:.2f} Hz ≥ {fn_min:.1f} Hz minimum")
        else:
            st.error(f"❌ **FREQUENCY TOO LOW** — fn = {fn_calc:.2f} Hz < {fn_min:.1f} Hz minimum")
        
        # ===========================================================================
        # SECTION 4: EFFECTIVE PANEL WEIGHT
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 4. EFFECTIVE PANEL WEIGHT")
        st.markdown("**Reference:** AISC DG11 Section 4.1")
        
        st.markdown("""
        The effective panel weight represents the mass participating in vibration. 
        For a typical floor bay:
        """)
        
        st.latex(r"W = w \times B_{eff} \times L_j")
        st.markdown("""
        **Where:**
        - w = floor weight per unit area (kN/m²)
        - B_eff = effective panel width (mm)
        - Lj = beam span (mm)
        
        **Reference:** AISC DG11 Eq. 4.2
        """)
        
        W_panel = w_sustained_area * (B_eff_vib / 1000) * L  # kN
        
        st.markdown(f"""
        **Calculation:**
        
        W = {w_sustained_area:.2f} kN/m² × {B_eff_vib/1000:.2f} m × {L:.2f} m = **{W_panel:.2f} kN**
        """)
        
        # ===========================================================================
        # SECTION 5: PEAK ACCELERATION
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 5. PEAK ACCELERATION CALCULATION")
        st.markdown("**Reference:** AISC DG11 Eq. 4.1")
        
        st.latex(r"\frac{a_p}{g} = \frac{P_o \times e^{-0.35 f_n}}{\beta \times W}")
        st.markdown("""
        **Where:**
        - ap = peak acceleration
        - g = gravitational acceleration
        - Po = walking force constant = 0.29 kN (for quiet spaces)
        - fn = natural frequency (Hz)
        - β = damping ratio
        - W = effective panel weight (kN)
        
        **Reference:** AISC DG11 Eq. 4.1
        """)
        
        Po = 0.29  # kN, constant for walking excitation
        ap_g_calc = Po * math.exp(-0.35 * fn_calc) / (beta * W_panel) if W_panel > 0 else 999
        
        st.markdown("**Calculation:**")
        st.latex(f"\\frac{{a_p}}{{g}} = \\frac{{{Po} \\times e^{{-0.35 \\times {fn_calc:.2f}}}}}{{{beta:.3f} \\times {W_panel:.2f}}}")
        st.latex(f"\\frac{{a_p}}{{g}} = \\frac{{{Po} \\times {math.exp(-0.35 * fn_calc):.4f}}}{{{beta * W_panel:.4f}}} = \\textbf{{{ap_g_calc:.5f}}} = \\textbf{{{ap_g_calc*100:.3f}\\% g}}")
        
        accel_ok = ap_g_calc <= ao_g
        if accel_ok:
            st.success(f"✅ **ACCELERATION OK** — ap/g = {ap_g_calc*100:.3f}% ≤ {ao_g*100:.2f}% limit")
        else:
            st.error(f"❌ **ACCELERATION TOO HIGH** — ap/g = {ap_g_calc*100:.3f}% > {ao_g*100:.2f}% limit")
        
        # ===========================================================================
        # SECTION 6: DESIGN SUMMARY
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 6. VIBRATION ANALYSIS SUMMARY")
        
        vib_ok = freq_ok and accel_ok
        
        st.markdown(f"""
| Parameter | Calculated | Limit | Status |
|-----------|------------|-------|--------|
| Natural Frequency | {fn_calc:.2f} Hz | ≥ {fn_min:.1f} Hz | {"✅ OK" if freq_ok else "❌ NG"} |
| Peak Acceleration | {ap_g_calc*100:.3f}% g | ≤ {ao_g*100:.2f}% g | {"✅ OK" if accel_ok else "❌ NG"} |
        """)
        
        # Store vibration results in session state for report generation
        st.session_state['vibration_results'] = {
            'fn': fn_calc,
            'ap_g': ap_g_calc,
            'limit': ao_g * 100,
            'occupancy': occupancy,
            'freq_ok': freq_ok,
            'accel_ok': accel_ok,
            'vib_ok': vib_ok
        }
        
        if vib_ok:
            st.success("## ✅ VIBRATION CHECK: PASS")
            st.markdown("""
            The floor system satisfies the vibration serviceability criteria per AISC Design Guide 11.
            Occupants should not experience objectionable vibrations from normal walking.
            """)
        else:
            st.error("## ❌ VIBRATION CHECK: DOES NOT PASS")
            st.markdown("""
            ### Recommendations to Improve Vibration Performance:
            1. **Increase beam stiffness** — Use deeper section to reduce deflection
            2. **Reduce bay size** — Shorter spans have higher natural frequency  
            3. **Add mass** — Thicker slab increases effective weight
            4. **Add damping** — Full-height partitions increase damping ratio
            5. **Consider tuned mass damper** — For sensitive applications
            """)


with tab6:
    st.subheader("PART C: METAL DECK DESIGN")
    st.markdown("**Per ANSI/SDI C-2017, AISI S100-16 - Construction Stage Analysis**")
    
    if not METAL_DECK_AVAILABLE:
        st.error(f"⚠️ Metal Deck module not available: {METAL_DECK_ERROR}")
    elif not deck_enabled:
        st.info("📌 Enable Metal Deck Design in the sidebar to see results")
    elif deck_parse_result and deck_parse_result.is_valid and deck_gross_props:
        
        # =======================================================================
        # 12. DECK PROFILE GEOMETRY
        # =======================================================================
        st.markdown("---")
        st.markdown("## 12. DECK PROFILE GEOMETRY")
        
        st.markdown("### 12.1 Profile Definition Parameters")
        st.markdown("The metal deck profile is defined by the following geometric parameters:")
        
        # Profile visualization
        fig_profile = plot_deck_profile(
            deck_parse_result, deck_t, show_dimensions=True,
            title=f"Metal Deck Profile",
            input_hr=deck_hr, input_wr_top=deck_wr_top,
            input_wr_bot=deck_wr_bot, input_pitch=deck_pitch
        )
        st.pyplot(fig_profile)
        plt.close(fig_profile)
        
        st.markdown(f"""
| Parameter | Symbol | Value | Description |
|-----------|--------|-------|-------------|
| Rib height | hr | {deck_hr:.1f} mm | Depth of deck rib |
| Top opening | wr,top | {deck_wr_top:.1f} mm | Width at top of rib |
| Bottom width | wr,bot | {deck_wr_bot:.1f} mm | Width at bottom of rib |
| Pitch | p | {deck_pitch:.1f} mm | Center-to-center spacing of ribs |
| Base metal thickness | t | {deck_t:.2f} mm | Design thickness (95% of nominal) |
| Web angle | θ | {deck_theta:.1f}° | Angle of inclined web |
        """)
        
        st.markdown("### 12.2 Material Properties")
        st.markdown(f"""
| Property | Symbol | Value | Reference |
|----------|--------|-------|-----------|
| Yield strength | Fy | {deck_Fy:.0f} MPa | ASTM A653 SS Grade {deck_Fy} |
| Modulus of elasticity | E | 200,000 MPa | AISI S100-16 §A3.1 |
| Poisson's ratio | ν | 0.30 | AISI S100-16 §A3.1 |
        """)
        
        # =======================================================================
        # 13. GROSS SECTION PROPERTIES
        # =======================================================================
        st.markdown("---")
        st.markdown("## 13. GROSS SECTION PROPERTIES")
        st.markdown("**Reference:** SDI C-2017 Section 2.4")
        
        st.markdown("### 13.1 Cross-Sectional Area")
        st.markdown("The gross cross-sectional area per unit width:")
        st.latex(r"A_g = \frac{t \times L_{profile}}{p}")
        st.markdown("""
**Where:**
- t = base metal thickness (mm)
- L_profile = developed length of profile per rib (mm)
- p = pitch (mm)
        """)
        
        st.markdown("### 13.2 Section Properties Summary")
        st.markdown(f"""
| Property | Symbol | Value | Units |
|----------|--------|-------|-------|
| Gross area | Ag | {deck_gross_props.Ag:.0f} | mm²/m |
| Moment of inertia | Ig | {deck_gross_props.Ig:.0f} | mm⁴/m |
| Section modulus (top) | Sg,top | {deck_gross_props.Sg_top:.0f} | mm³/m |
| Section modulus (bot) | Sg,bot | {deck_gross_props.Sg_bot:.0f} | mm³/m |
| Centroid from bottom | ȳcg | {deck_gross_props.ycg:.2f} | mm |
| Self-weight | w | {deck_gross_props.weight:.2f} | kg/m² |
        """)
        
        # =======================================================================
        # 14. EFFECTIVE WIDTH METHOD
        # =======================================================================
        st.markdown("---")
        st.markdown("## 14. EFFECTIVE WIDTH METHOD")
        st.markdown("**Reference:** AISI S100-16 Section 1.1 - Effective Width of Stiffened Elements")
        
        st.markdown("""
Cold-formed steel elements may experience **local buckling** before reaching yield stress. 
The effective width method accounts for post-buckling strength by using a reduced width.
        """)
        
        st.markdown("### 14.1 Slenderness Factor")
        st.latex(r"\lambda = \frac{1.052}{\sqrt{k}} \times \frac{w}{t} \times \sqrt{\frac{f}{E}}")
        st.markdown("""
**Where:**
- k = plate buckling coefficient (k = 4.0 for stiffened elements)
- w = flat width of element (mm)
- t = thickness (mm)
- f = design stress (MPa)
- E = modulus of elasticity (MPa)

**Reference:** AISI S100-16 Eq. 1.1-2
        """)
        
        st.markdown("### 14.2 Effective Width")
        st.latex(r"b_e = \rho \times w")
        st.markdown("""
**Where:**
- ρ = reduction factor = (1 - 0.22/λ) / λ ≤ 1.0
- For λ ≤ 0.673: ρ = 1.0 (no reduction)
- For λ > 0.673: ρ = (1 - 0.22/λ) / λ

**Reference:** AISI S100-16 Eq. 1.1-3
        """)
        
        Se_reduction = 0.85
        Ae = deck_gross_props.Ag * Se_reduction
        Ie = deck_gross_props.Ig * Se_reduction
        Se_pos = deck_gross_props.Sg_top * Se_reduction
        Se_neg = deck_gross_props.Sg_bot * Se_reduction
        
        # =======================================================================
        # 15. EFFECTIVE SECTION PROPERTIES
        # =======================================================================
        st.markdown("---")
        st.markdown("## 15. EFFECTIVE SECTION PROPERTIES")
        st.markdown("**Reference:** AISI S100-16 Section B")
        
        st.markdown(f"""
Using effective width reduction factor ρ = {Se_reduction}:

| Property | Gross | Effective | Reduction |
|----------|-------|-----------|-----------|
| Area (mm²/m) | {deck_gross_props.Ag:.0f} | **{Ae:.0f}** | ×{Se_reduction} |
| Moment of Inertia (mm⁴/m) | {deck_gross_props.Ig:.0f} | **{Ie:.0f}** | ×{Se_reduction} |
| Section Modulus + (mm³/m) | {deck_gross_props.Sg_top:.0f} | **{Se_pos:.0f}** | ×{Se_reduction} |
| Section Modulus - (mm³/m) | {deck_gross_props.Sg_bot:.0f} | **{Se_neg:.0f}** | ×{Se_reduction} |
        """)
        
        st.info(f"**Note:** Effective properties used for strength calculations. Gross Ig used for deflection per SDI C-2017 §3.1.4.")
        
        # =======================================================================
        # 16. FLEXURAL STRENGTH
        # =======================================================================
        st.markdown("---")
        st.markdown("## 16. FLEXURAL STRENGTH")
        st.markdown("**Reference:** AISI S100-16 Section F - Members in Flexure")
        
        st.markdown("### 16.1 Nominal Flexural Strength (Section F2)")
        st.latex(r"M_n = S_e \times F_y")
        st.markdown("""
**Where:**
- Se = effective section modulus at extreme fiber (mm³/m)
- Fy = yield strength of steel (MPa)

**Reference:** AISI S100-16 Eq. F2-1
        """)
        
        Mn_deck = Se_pos * deck_Fy / 1e6  # kN·m/m
        
        st.markdown("**Calculation:**")
        st.latex(f"M_n = {Se_pos:.0f} \\times {deck_Fy:.0f} = {Se_pos * deck_Fy:.0f} \\text{{ N·mm/m}}")
        st.latex(f"M_n = {Mn_deck:.4f} \\text{{ kN·m/m}}")
        
        st.markdown("### 16.2 Design Flexural Strength")
        if method == "LRFD":
            phi_b = 0.90
            phi_Mn = phi_b * Mn_deck
            st.markdown("**LRFD:** φb = 0.90 (AISI S100-16 §F1)")
            st.latex(f"\\phi_b M_n = 0.90 \\times {Mn_deck:.4f} = \\boldsymbol{{{phi_Mn:.4f}}} \\text{{ kN·m/m}}")
        else:
            omega_b = 1.67
            phi_Mn = Mn_deck / omega_b
            st.markdown("**ASD:** Ωb = 1.67 (AISI S100-16 §F1)")
            st.latex(f"M_n / \\Omega_b = {Mn_deck:.4f} / 1.67 = \\boldsymbol{{{phi_Mn:.4f}}} \\text{{ kN·m/m}}")
        
        st.markdown("### 16.3 Required Flexural Strength")
        st.markdown(f"**Deck Span:** L = {deck_span} mm (= beam spacing)")
        
        # Loads come from unified Loads section
        st.markdown("**Construction Stage Loads:**")
        st.markdown(f"- Wet Concrete + Deck (DL): {deck_DL:.2f} kN/m²")
        st.markdown(f"- Construction Live Load (LL): {deck_const_LL:.2f} kN/m²")
        st.markdown(f"- **Total Service Load:** {deck_w_const:.2f} kN/m²")
        
        if method == "LRFD":
            # LRFD: 1.2D + 1.6L
            w_u = 1.2 * deck_DL + 1.6 * deck_const_LL
            load_factor_text = "1.2D + 1.6L"
            st.latex(f"w_u = 1.2 \\times {deck_DL:.2f} + 1.6 \\times {deck_const_LL:.2f} = \\boldsymbol{{{w_u:.2f}}} \\text{{ kN/m²}}")
        else:
            # ASD: D + L
            w_u = deck_DL + deck_const_LL
            load_factor_text = "D + L"
            st.latex(f"w_a = {deck_DL:.2f} + {deck_const_LL:.2f} = \\boldsymbol{{{w_u:.2f}}} \\text{{ kN/m²}}")
        
        st.latex(r"M_u = \frac{w_u \times L^2}{8}")
        st.markdown("**Reference:** Simple beam, uniform load")
        
        L_m = deck_span / 1000  # Convert to meters
        Mu_deck = w_u * L_m**2 / 8
        
        st.markdown("**Calculation:**")
        st.latex(f"M_u = \\frac{{{w_u:.2f} \\times {L_m:.3f}^2}}{{8}} = \\boldsymbol{{{Mu_deck:.4f}}} \\text{{ kN·m/m}}")
        
        st.markdown("### 16.4 Demand/Capacity Check")
        st.latex(r"\text{DCR} = \frac{M_u}{\phi_b M_n} \leq 1.0")
        
        dcr_flex = Mu_deck / phi_Mn if phi_Mn > 0 else 999
        
        st.latex(f"\\text{{DCR}} = \\frac{{{Mu_deck:.4f}}}{{{phi_Mn:.4f}}} = \\boldsymbol{{{dcr_flex:.3f}}}")
        
        if dcr_flex <= 1.0:
            st.success(f"✅ **FLEXURE OK** — DCR = {dcr_flex:.3f} ≤ 1.0")
        else:
            st.error(f"❌ **FLEXURE NG** — DCR = {dcr_flex:.3f} > 1.0")
        
        # =======================================================================
        # 17. SHEAR STRENGTH
        # =======================================================================
        st.markdown("---")
        st.markdown("## 17. SHEAR STRENGTH")
        st.markdown("**Reference:** AISI S100-16 Section G2 - Shear Strength of Webs Without Holes")
        
        st.markdown("### 17.1 Web Geometry")
        n_webs = 1000 / deck_pitch * 2  # 2 webs per rib, per meter width
        h_web = deck_hr / math.cos(math.radians(deck_theta)) if deck_theta > 0 else deck_hr
        Aw = h_web * deck_t * n_webs
        
        st.latex(r"h_{web} = \frac{h_r}{\cos\theta}")
        st.markdown(f"**Calculation:** h_web = {deck_hr:.1f} / cos({deck_theta:.0f}°) = **{h_web:.1f} mm**")
        
        st.latex(r"A_w = h_{web} \times t \times n_{webs}")
        st.markdown(f"**Calculation:** Aw = {h_web:.1f} × {deck_t:.2f} × {n_webs:.1f} = **{Aw:.0f} mm²/m**")
        
        st.markdown("### 17.2 Shear Buckling Coefficient")
        h_t_ratio = h_web / deck_t
        kv = 5.34
        limit_cv1 = 1.10 * math.sqrt(kv * 200000 / deck_Fy)
        
        st.latex(r"\frac{h}{t} = " + f"{h_t_ratio:.1f}")
        st.latex(r"1.10\sqrt{\frac{k_v E}{F_y}} = 1.10\sqrt{\frac{5.34 \times 200000}{" + f"{deck_Fy:.0f}" + "}} = " + f"{limit_cv1:.1f}")
        
        if h_t_ratio <= limit_cv1:
            Cv1 = 1.0
            st.markdown(f"Since h/t = {h_t_ratio:.1f} ≤ {limit_cv1:.1f}: **Cv1 = 1.0** (web yields before buckling)")
        else:
            Cv1 = limit_cv1 / h_t_ratio
            st.markdown(f"Since h/t = {h_t_ratio:.1f} > {limit_cv1:.1f}: **Cv1 = {Cv1:.3f}** (web buckling governs)")
        
        st.markdown("**Reference:** AISI S100-16 Eq. G2-3")
        
        st.markdown("### 17.3 Nominal Shear Strength")
        st.latex(r"V_n = 0.6 \times F_y \times A_w \times C_{v1}")
        
        Vn_deck = 0.6 * deck_Fy * Aw * Cv1 / 1000  # kN/m
        
        st.markdown("**Calculation:**")
        st.latex(f"V_n = 0.6 \\times {deck_Fy:.0f} \\times {Aw:.0f} \\times {Cv1:.2f} / 1000 = \\boldsymbol{{{Vn_deck:.2f}}} \\text{{ kN/m}}")
        
        st.markdown("**Reference:** AISI S100-16 Eq. G2-1")
        
        st.markdown("### 17.4 Design Shear Strength")
        if method == "LRFD":
            phi_v = 1.0 if h_t_ratio <= 1.10 * math.sqrt(200000/deck_Fy) else 0.90
            phi_Vn = phi_v * Vn_deck
            st.markdown(f"**LRFD:** φv = {phi_v:.2f} (AISI S100-16 §G1)")
            st.latex(f"\\phi_v V_n = {phi_v:.2f} \\times {Vn_deck:.2f} = \\boldsymbol{{{phi_Vn:.2f}}} \\text{{ kN/m}}")
        else:
            omega_v = 1.50
            phi_Vn = Vn_deck / omega_v
            st.markdown("**ASD:** Ωv = 1.50 (AISI S100-16 §G1)")
            st.latex(f"V_n / \\Omega_v = {Vn_deck:.2f} / 1.50 = \\boldsymbol{{{phi_Vn:.2f}}} \\text{{ kN/m}}")
        
        st.markdown("### 17.5 Required Shear Strength")
        st.latex(r"V_u = \frac{w_u \times L}{2}")
        
        Vu_deck = w_u * L_m / 2
        
        st.markdown("**Calculation:**")
        st.latex(f"V_u = \\frac{{{w_u:.2f} \\times {L_m:.3f}}}{{2}} = \\boldsymbol{{{Vu_deck:.2f}}} \\text{{ kN/m}}")
        
        st.markdown("### 17.6 Demand/Capacity Check")
        dcr_shear = Vu_deck / phi_Vn if phi_Vn > 0 else 999
        
        st.latex(f"\\text{{DCR}} = \\frac{{{Vu_deck:.2f}}}{{{phi_Vn:.2f}}} = \\boldsymbol{{{dcr_shear:.3f}}}")
        
        if dcr_shear <= 1.0:
            st.success(f"✅ **SHEAR OK** — DCR = {dcr_shear:.3f} ≤ 1.0")
        else:
            st.error(f"❌ **SHEAR NG** — DCR = {dcr_shear:.3f} > 1.0")
        
        # =======================================================================
        # 18. WEB CRIPPLING
        # =======================================================================
        st.markdown("---")
        st.markdown("## 18. WEB CRIPPLING")
        st.markdown("**Reference:** AISI S100-16 Section G5 - Web Crippling Strength")
        
        st.markdown("""
Web crippling is a localized failure at points of concentrated load or support reactions.
Critical for thin-walled deck webs at bearing locations.
        """)
        
        st.markdown("### 18.1 Web Crippling Formula (End One-Flange Loading)")
        st.latex(r"P_n = C \cdot t^2 \cdot F_y \cdot \sin\theta \cdot \left(1 - C_R\sqrt{\frac{R}{t}}\right) \cdot \left(1 + C_N\sqrt{\frac{N}{t}}\right) \cdot \left(1 - C_h\sqrt{\frac{h}{t}}\right)")
        
        st.markdown("""
**Where:**
- C = 4.0 (AISI Table G5-3, EOF loading, stiffened flanges)
- CR = 0.14 (inside bend radius coefficient)
- CN = 0.35 (bearing length coefficient)
- Ch = 0.02 (web depth coefficient)
- t = web thickness (mm)
- R = inside bend radius ≈ 2t (mm)
- N = bearing length, typically 25-50 mm
- h = flat web height (mm)
- θ = angle between web and bearing surface

**Reference:** AISI S100-16 Eq. G5-1, Table G5-3
        """)
        
        st.markdown("### 18.2 Web Crippling Calculation")
        
        # AISI S100-16 coefficients for EOF loading (End One-Flange)
        C_coeff = 4.0
        C_R = 0.14
        C_N = 0.35
        C_h = 0.02
        
        # Parameters
        R_bend = 2 * deck_t  # Inside bend radius, typically 2t for roll-formed deck
        N_bearing = 38  # Bearing length in mm (typical 1.5 inch = 38mm)
        h_web = deck_hr / math.cos(math.radians(90 - deck_theta))  # Flat web height
        theta_rad = math.radians(deck_theta)
        
        # Calculate reduction factors
        factor_R = 1 - C_R * math.sqrt(R_bend / deck_t)
        factor_N = 1 + C_N * math.sqrt(N_bearing / deck_t)
        factor_h = 1 - C_h * math.sqrt(h_web / deck_t)
        
        # Nominal web crippling strength per web
        Pn_per_web = C_coeff * deck_t**2 * deck_Fy * math.sin(theta_rad) * factor_R * factor_N * factor_h / 1000  # kN
        
        # Total per meter width
        Pn_cripple = Pn_per_web * n_webs
        
        col_wc1, col_wc2 = st.columns(2)
        with col_wc1:
            st.markdown("**Input Parameters:**")
            st.markdown(f"""
| Parameter | Symbol | Value |
|-----------|--------|-------|
| Web thickness | t | {deck_t:.2f} mm |
| Inside bend radius | R | {R_bend:.2f} mm |
| Bearing length | N | {N_bearing:.0f} mm |
| Flat web height | h | {h_web:.1f} mm |
| Web angle | θ | {deck_theta}° |
| Number of webs | n | {n_webs:.1f} /m |
            """)
        
        with col_wc2:
            st.markdown("**Reduction Factors:**")
            st.markdown(f"""
| Factor | Formula | Value |
|--------|---------|-------|
| Radius | 1 - CR√(R/t) | {factor_R:.4f} |
| Bearing | 1 + CN√(N/t) | {factor_N:.4f} |
| Web height | 1 - Ch√(h/t) | {factor_h:.4f} |
            """)
        
        st.markdown("**Calculation:**")
        st.latex(f"P_n = {C_coeff} \\times {deck_t:.2f}^2 \\times {deck_Fy:.0f} \\times \\sin({deck_theta}°) \\times {factor_R:.4f} \\times {factor_N:.4f} \\times {factor_h:.4f}")
        st.latex(f"P_n = {Pn_per_web:.3f} \\text{{ kN/web}} \\times {n_webs:.1f} \\text{{ webs/m}} = \\boldsymbol{{{Pn_cripple:.2f}}} \\text{{ kN/m}}")
        
        st.markdown("### 18.3 Design Web Crippling Strength")
        if method == "LRFD":
            phi_w = 0.75
            phi_Pn = phi_w * Pn_cripple
            st.markdown("**LRFD:** φw = 0.75 (AISI S100-16 §G5)")
            st.latex(f"\\phi_w P_n = 0.75 \\times {Pn_cripple:.2f} = \\boldsymbol{{{phi_Pn:.2f}}} \\text{{ kN/m}}")
        else:
            omega_w = 2.00
            phi_Pn = Pn_cripple / omega_w
            st.markdown("**ASD:** Ωw = 2.00 (AISI S100-16 §G5)")
            st.latex(f"P_n / \\Omega_w = {Pn_cripple:.2f} / 2.00 = \\boldsymbol{{{phi_Pn:.2f}}} \\text{{ kN/m}}")
        
        st.markdown("### 18.4 Demand/Capacity Check")
        Ru_cripple = Vu_deck  # Reaction at support
        dcr_cripple = Ru_cripple / phi_Pn if phi_Pn > 0 else 999
        
        st.markdown(f"**Required:** Ru = Vu = {Ru_cripple:.2f} kN/m (support reaction)")
        st.latex(f"\\text{{DCR}} = \\frac{{{Ru_cripple:.2f}}}{{{phi_Pn:.2f}}} = \\boldsymbol{{{dcr_cripple:.3f}}}")
        
        if dcr_cripple <= 1.0:
            st.success(f"✅ **WEB CRIPPLING OK** — DCR = {dcr_cripple:.3f} ≤ 1.0")
        else:
            st.error(f"❌ **WEB CRIPPLING NG** — DCR = {dcr_cripple:.3f} > 1.0")
        
        # =======================================================================
        # 19. DEFLECTION WITH PONDING CONSIDERATION
        # =======================================================================
        st.markdown("---")
        st.markdown("## 19. DEFLECTION WITH PONDING CONSIDERATION")
        st.markdown("**Reference:** SDI C-2017 Section 3.1.4")
        
        st.markdown("### 19.1 Deflection Formula")
        st.latex(r"\delta = \frac{5 w L^4}{384 E I_g}")
        st.markdown("""
**Where:**
- w = service load (kN/m²)
- L = span (mm)
- E = modulus of elasticity = 200,000 MPa
- Ig = gross moment of inertia (mm⁴/m)

**Note:** Per SDI C-2017 §3.1.4, gross section properties (not effective) are used for deflection calculations.
        """)
        
        st.markdown("### 19.2 Calculation")
        # Service load for deflection (unfactored)
        w_serv = deck_w_const  # DL + LL (unfactored)
        L_mm = deck_span
        E_deck = 200000
        Ig = deck_gross_props.Ig
        
        st.markdown(f"**Service Load:** w = DL + LL = {deck_DL:.2f} + {deck_const_LL:.2f} = {w_serv:.2f} kN/m²")
        
        delta_deck = 5 * w_serv * L_mm**4 / (384 * E_deck * Ig) if Ig > 0 else 999
        
        st.latex(f"\\delta = \\frac{{5 \\times {w_serv:.2f} \\times {L_mm:.0f}^4}}{{384 \\times {E_deck:.0f} \\times {Ig:.0f}}}")
        st.latex(f"\\delta = \\boldsymbol{{{delta_deck:.2f}}} \\text{{ mm}}")
        
        st.markdown("### 19.3 Deflection Limit")
        delta_limit = L_mm / 180
        
        st.latex(r"\delta_{limit} = \frac{L}{180}")
        st.markdown("**Reference:** SDI C-2017 §3.1.4 (Construction stage limit)")
        
        st.latex(f"\\delta_{{limit}} = \\frac{{{L_mm:.0f}}}{{180}} = \\boldsymbol{{{delta_limit:.2f}}} \\text{{ mm}}")
        
        st.markdown("### 19.4 Demand/Capacity Check")
        dcr_defl = delta_deck / delta_limit if delta_limit > 0 else 999
        
        st.latex(f"\\text{{DCR}} = \\frac{{{delta_deck:.2f}}}{{{delta_limit:.2f}}} = \\boldsymbol{{{dcr_defl:.3f}}}")
        
        if dcr_defl <= 1.0:
            st.success(f"✅ **DEFLECTION OK** — DCR = {dcr_defl:.3f} ≤ 1.0")
        else:
            st.error(f"❌ **DEFLECTION NG** — DCR = {dcr_defl:.3f} > 1.0 — Consider ponding effects")
        
        st.info("""
**Note on Ponding:** If δ > L/180, additional concrete will pond in the deflected shape, 
increasing load and deflection iteratively. Consider:
- Reducing span
- Using thicker/deeper deck
- Adding temporary shoring during construction
        """)
        
        # Deflection diagram
        fig_defl, ax_defl = plt.subplots(1, 1, figsize=(10, 3))
        x_beam = np.linspace(0, deck_span, 100)
        y_defl = -delta_deck * 16 * x_beam/deck_span * (1 - x_beam/deck_span)
        scale_factor = deck_span / (abs(min(y_defl)) * 15) if min(y_defl) != 0 else 1
        
        ax_defl.plot([0, deck_span], [0, 0], 'k--', alpha=0.5, label='Undeflected')
        ax_defl.plot(x_beam, y_defl * scale_factor, 'b-', linewidth=2, label='Deflected shape')
        ax_defl.fill_between(x_beam, 0, y_defl * scale_factor, alpha=0.2)
        ax_defl.plot([0], [0], 'k^', markersize=12)
        ax_defl.plot([deck_span], [0], 'k^', markersize=12)
        ax_defl.annotate(f'δmax = {delta_deck:.2f} mm', xy=(deck_span/2, min(y_defl)*scale_factor),
                        xytext=(deck_span/2, min(y_defl)*scale_factor*1.5), ha='center', fontsize=10,
                        arrowprops=dict(arrowstyle='->', color='red'))
        ax_defl.set_xlabel('Span (mm)')
        ax_defl.set_title('Deflected Shape (Construction Stage)', fontweight='bold')
        ax_defl.legend()
        ax_defl.grid(True, alpha=0.3)
        st.pyplot(fig_defl)
        plt.close(fig_defl)
        
        # =======================================================================
        # 20. DESIGN SUMMARY
        # =======================================================================
        st.markdown("---")
        st.markdown("## 20. DESIGN SUMMARY")
        
        all_pass = dcr_flex <= 1.0 and dcr_shear <= 1.0 and dcr_cripple <= 1.0 and dcr_defl <= 1.0
        
        st.markdown("### 20.1 Design Parameters")
        st.markdown(f"""
| Parameter | Value |
|-----------|-------|
| Deck span | {deck_span} mm ({deck_span/1000:.2f} m) |
| Design method | {method} |
| Dead Load (wet concrete + deck) | {deck_DL:.2f} kN/m² |
| Construction Live Load | {deck_const_LL:.2f} kN/m² |
| **Total Construction Load** | **{deck_w_const:.2f} kN/m²** |
| Factored Load (w_u) | {w_u:.2f} kN/m² |
| Deck thickness | {deck_t:.2f} mm |
| Deck yield strength | {deck_Fy:.0f} MPa |
        """)
        
        st.markdown("### 20.2 Capacity Summary Table")
        
        summary_data = {
            "Check": ["16. Flexure", "17. Shear", "18. Web Crippling", "19. Deflection"],
            "Demand": [f"{Mu_deck:.4f} kN-m/m", f"{Vu_deck:.2f} kN/m", f"{Ru_cripple:.2f} kN/m", f"{delta_deck:.2f} mm"],
            "Capacity": [f"{phi_Mn:.4f} kN-m/m", f"{phi_Vn:.2f} kN/m", f"{phi_Pn:.2f} kN/m", f"{delta_limit:.2f} mm"],
            "DCR": [f"{dcr_flex:.3f}", f"{dcr_shear:.3f}", f"{dcr_cripple:.3f}", f"{dcr_defl:.3f}"],
            "Status": ["✅ OK" if dcr_flex <= 1.0 else "❌ NG",
                      "✅ OK" if dcr_shear <= 1.0 else "❌ NG",
                      "✅ OK" if dcr_cripple <= 1.0 else "❌ NG",
                      "✅ OK" if dcr_defl <= 1.0 else "❌ NG"],
            "Reference": ["AISI S100 §F2", "AISI S100 §G2", "AISI S100 §G5", "SDI C-2017 §3.1.4"]
        }
        st.table(summary_data)
        
        # Store metal deck results in session state for report generation
        st.session_state['deck_results'] = {
            'type': 'Composite',
            'hr': deck_hr,
            'wr': deck_wr_top,
            't': deck_t,
            'Fy': deck_Fy,
            'deck_DL': deck_DL,
            'deck_const_LL': deck_const_LL,
            'deck_w_const': deck_w_const,
            'w_u': w_u,
            'phi_Mn': phi_Mn,
            'Mu': Mu_deck,
            'DCR_flex': dcr_flex,
            'phi_Vn': phi_Vn,
            'Vu': Vu_deck,
            'DCR_shear': dcr_shear,
            'phi_Pn': phi_Pn,
            'Ru': Ru_cripple,
            'DCR_cripple': dcr_cripple,
            'delta': delta_deck,
            'delta_limit': delta_limit,
            'DCR_defl': dcr_defl,
            'all_pass': all_pass
        }
        
        if all_pass:
            st.success("## ✅ METAL DECK DESIGN: ALL CHECKS PASS")
            st.balloons()
        else:
            st.error("## ❌ METAL DECK DESIGN: DOES NOT SATISFY REQUIREMENTS")
            st.markdown("""
**Recommendations:**
- Increase deck thickness (gage)
- Reduce span (beam spacing)
- Select deeper deck profile
- Consider 2-span or 3-span continuous configuration
            """)
    
    elif deck_input_method == "DXF Import" and deck_dxf_file is None:
        st.info("📁 Upload a DXF file in the sidebar to see deck analysis")
    else:
        st.warning("⚠️ Could not process deck geometry. Check inputs in sidebar.")


if design_mode == "Composite":
    with tab7:
        st.subheader("Composite Slab Design - One-Way Slab on Metal Deck")
        st.markdown("**Reference:** ACI 318-19, SDI C-2017")
        
        if not COMPOSITE_SLAB_AVAILABLE:
            st.error(f"⚠️ Composite Slab module not available: {COMPOSITE_SLAB_ERROR}")
        elif not slab_enabled:
            st.info("📌 Enable Composite Slab Design in the sidebar to see results")
        elif not deck_enabled:
            st.info("📌 Enable Metal Deck Design first - deck properties are required for composite slab analysis")
        else:
        # Check if we have valid deck data
            if deck_parse_result and deck_parse_result.is_valid:
                
                # ===========================================================================
                # SECTION 1: COMPOSITE SLAB GEOMETRY
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 1. COMPOSITE SLAB GEOMETRY")
                
                t_above_deck = slab_tc - deck_hr
                
                st.code(f"""
        COMPOSITE SLAB CROSS-SECTION:
        
        ════════════════════════════════════════════════════════════════════════════════
                                  CONCRETE TOPPING
        ┌───────────────────────────────────────────────────────────────────────────────┐
        │█████████████████████████████████████████████████████████████████████████████████│
        │█████████████████  CONCRETE (f'c = {slab_fc:.0f} MPa)  ██████████████████████████████│ ─┬─ t_above = {t_above_deck:.0f} mm
        │█████████████████████████████████████████████████████████████████████████████████│ ─┴─ (above deck ribs)
        ├──────────┬───────────────────┬──────────┬───────────────────┬──────────────────┤
        │██████████│░░░░░░░░░░░░░░░░░░░│██████████│░░░░░░░░░░░░░░░░░░░│██████████████████│
        │██████████│░░░ DECK RIB ░░░░░░│██████████│░░░ DECK RIB ░░░░░░│██████████████████│ ─┬─ hr = {deck_hr:.0f} mm
        │██████████│░░ (concrete) ░░░░░│██████████│░░ (concrete) ░░░░░│██████████████████│ ─┴─ (rib height)
        └──────────┴───────────────────┴──────────┴───────────────────┴──────────────────┘
        ════════════════════════════════════════════════════════════════════════════════════
                  METAL DECK (acts as positive moment reinforcement)                    tc = {slab_tc:.0f} mm
                                                                                        (total depth)
        
        GEOMETRY SUMMARY:
        ═══════════════════════════════════════════════════════════════════════════════════
        Total slab thickness        tc      = {slab_tc} mm
        Deck rib height             hr      = {deck_hr:.0f} mm
        Concrete above deck ribs    t_above = tc - hr = {slab_tc} - {deck_hr:.0f} = {t_above_deck:.0f} mm
        Top cover to rebar          cover   = {slab_cover} mm
        Deck span (slab span)       L       = {deck_span} mm
        Span condition                      = {slab_span_type}
        ═══════════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                # ===========================================================================
                # SECTION 2: MATERIAL PROPERTIES
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 2. MATERIAL PROPERTIES")
                
                Ec_slab = 4700 * math.sqrt(slab_fc)
                fr = 0.62 * math.sqrt(slab_fc)  # Modulus of rupture
                
                st.code(f"""
        CONCRETE PROPERTIES:
        ═══════════════════════════════════════════════════════════════════════════════════
        Compressive strength      f'c  = {slab_fc} MPa
        Unit weight               wc   = {slab_wc} kg/m³
        Elastic modulus           Ec   = 4700√f'c = 4700×√{slab_fc} = {Ec_slab:.0f} MPa
        Modulus of rupture        fr   = 0.62√f'c = 0.62×√{slab_fc} = {fr:.2f} MPa
        
        REINFORCEMENT PROPERTIES:
        ═══════════════════════════════════════════════════════════════════════════════════
        Rebar yield strength      fy   = {rebar_fy} MPa
        Rebar area provided       As   = {rebar_As} mm²/m
        Cover (top)                    = {slab_cover} mm
        
        METAL DECK (As Reinforcement):
        ═══════════════════════════════════════════════════════════════════════════════════
        Deck area                 Ag   = {deck_gross_props.Ag:.0f} mm²/m
        Deck yield strength       Fy   = {deck_Fy} MPa
        Deck thickness            t    = {deck_t:.2f} mm
        
        Note: Metal deck acts as positive moment reinforcement (tension at bottom).
        Top rebar provides negative moment reinforcement over supports.
        ═══════════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                # ===========================================================================
                # SECTION 3: LOADING
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 3. SLAB LOADING")
                st.markdown("**Reference:** ACI 318-19 Section 5.3")
                
                st.code(f"""
        LOAD DIAGRAM (One-Way Slab):
        
                 w_total (uniform)
              ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓   ↓
        ════════════════════════════════════════════════════════════════
        △                              │                              △
        │◄──────────────────  L = {deck_span:.0f} mm  ──────────────────►│
        
        
        SERVICE LOADS:
        ═══════════════════════════════════════════════════════════════════════════════════
        Dead load (self-weight + deck)    wDL  = {slab_wDL:.2f} kN/m²
        Superimposed dead load            wSDL = {slab_wSDL:.2f} kN/m²
        Live load                         wLL  = {slab_wLL:.2f} kN/m²
        ─────────────────────────────────────────────────────────────────────────────────
        TOTAL SERVICE LOAD                w    = {slab_wDL + slab_wSDL + slab_wLL:.2f} kN/m²
        
        
        FACTORED LOADS (LRFD - ACI 318-19 §5.3.1):
        ═══════════════════════════════════════════════════════════════════════════════════
        Load Combination: 1.2D + 1.6L
        
        wu = 1.2 × (wDL + wSDL) + 1.6 × wLL
        wu = 1.2 × ({slab_wDL:.2f} + {slab_wSDL:.2f}) + 1.6 × {slab_wLL:.2f}
        wu = 1.2 × {slab_wDL + slab_wSDL:.2f} + 1.6 × {slab_wLL:.2f}
        wu = {1.2*(slab_wDL + slab_wSDL):.2f} + {1.6*slab_wLL:.2f}
        wu = {1.2*(slab_wDL + slab_wSDL) + 1.6*slab_wLL:.2f} kN/m²
        ═══════════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                # Map span condition
                span_map = {
                    "Simple": SpanCondition.SIMPLE,
                    "Two-Span": SpanCondition.TWO_SPAN,
                    "Three+ Span": SpanCondition.THREE_PLUS,
                }
                slab_span_condition = span_map.get(slab_span_type, SpanCondition.SIMPLE)
                
                # Fire rating mapping
                if fire_check:
                    fire_map = {
                        "1-Hour": FireRating.ONE_HOUR,
                        "1.5-Hour": FireRating.ONE_HALF_HOUR,
                        "2-Hour": FireRating.TWO_HOUR,
                        "3-Hour": FireRating.THREE_HOUR,
                    }
                    selected_fire_rating = fire_map.get(fire_rating_choice, FireRating.ONE_HOUR)
                else:
                    selected_fire_rating = FireRating.NONE
                
                # Create design objects
                slab_geom = SlabGeometry(
                    tc=slab_tc, hr=deck_hr, wr_top=deck_wr_top, wr_bot=deck_wr_bot,
                    pitch=deck_pitch, span=deck_span, span_condition=slab_span_condition
                )
                slab_concrete = ConcreteProperties(fc=slab_fc, wc=slab_wc)
                slab_reinforcement = ReinforcementProperties(
                    fy=rebar_fy, As_provided=rebar_As,
                    cover_top=slab_cover, cover_bot=slab_cover
                )
                slab_deck = DeckContribution(
                    Ag_deck=deck_gross_props.Ag, Ig_deck=deck_gross_props.Ig,
                    Fy_deck=deck_Fy, t_deck=deck_t
                )
                
                # Run design
                try:
                    slab_results = design_composite_slab(
                        geometry=slab_geom, concrete=slab_concrete,
                        reinforcement=slab_reinforcement, deck=slab_deck,
                        w_dead=slab_wDL, w_live=slab_wLL, w_SDL=slab_wSDL,
                        fire_rating=selected_fire_rating
                    )
                    
                    # ===========================================================================
                    # SECTION 4: FLEXURAL STRENGTH
                    # ===========================================================================
                    st.markdown("---")
                    st.markdown("## 4. FLEXURAL STRENGTH CHECK")
                    st.markdown("**Reference:** ACI 318-19 Section 22.2")
                    
                    st.markdown("""
                    **Composite Slab Flexural Behavior:**
                    - **Positive moment** (midspan): Metal deck acts as tension reinforcement
                    - **Negative moment** (supports): Top rebar acts as tension reinforcement
                    """)
                    
                    if 'positive_moment' in slab_results:
                        pm = slab_results['positive_moment']
                        st.code(f"""
        POSITIVE MOMENT STRENGTH (Midspan):
        ═══════════════════════════════════════════════════════════════════════════════════
        Metal deck provides tensile reinforcement at bottom.
        
        Moment Coefficient (ACI 318-19 Table 6.5.2):
        • Simple span:     wuL²/8
        • Two-span:        wuL²/14 (interior support), wuL²/11 (exterior)
        • Three+ span:     wuL²/16 (interior), wuL²/11 (exterior)
        
        Required Moment:      Mu  = {pm.demand:.3f} kN⋅m/m
        Design Capacity:      φMn = {pm.capacity:.3f} kN⋅m/m
        
        DCR = Mu / φMn = {pm.demand:.3f} / {pm.capacity:.3f} = {pm.ratio:.3f}
        Status: {'✅ PASS' if pm.status == 'PASS' else '❌ FAIL'}
        ═══════════════════════════════════════════════════════════════════════════════════
                        """, language=None)
                    
                    if 'negative_moment' in slab_results:
                        nm = slab_results['negative_moment']
                        st.code(f"""
        NEGATIVE MOMENT STRENGTH (Over Supports):
        ═══════════════════════════════════════════════════════════════════════════════════
        Top reinforcement provides tensile reinforcement.
        
        Required Moment:      Mu  = {nm.demand:.3f} kN⋅m/m
        Design Capacity:      φMn = {nm.capacity:.3f} kN⋅m/m
        
        DCR = Mu / φMn = {nm.demand:.3f} / {nm.capacity:.3f} = {nm.ratio:.3f}
        Status: {'✅ PASS' if nm.status == 'PASS' else '❌ FAIL'}
        ═══════════════════════════════════════════════════════════════════════════════════
                        """, language=None)
                    
                    # ===========================================================================
                    # SECTION 5: SHEAR STRENGTH
                    # ===========================================================================
                    st.markdown("---")
                    st.markdown("## 5. SHEAR STRENGTH CHECK")
                    st.markdown("**Reference:** ACI 318-19 Section 22.5")
                    
                    if 'shear' in slab_results:
                        shear = slab_results['shear']
                        st.code(f"""
        ONE-WAY SHEAR STRENGTH:
        ═══════════════════════════════════════════════════════════════════════════════════
        Critical section at distance 'd' from face of support.
        
        Concrete shear strength (no shear reinforcement):
        Vc = 0.17 × λ × √f'c × bw × d
        
        Where:
        λ     = 1.0 (normal weight concrete)
        f'c   = {slab_fc} MPa
        bw    = 1000 mm (per meter width)
        d     = effective depth
        
        Required Shear:       Vu  = {shear.demand:.3f} kN/m
        Design Capacity:      φVc = {shear.capacity:.3f} kN/m
        
        DCR = Vu / φVc = {shear.demand:.3f} / {shear.capacity:.3f} = {shear.ratio:.3f}
        Status: {'✅ PASS' if shear.status == 'PASS' else '❌ FAIL'}
        ═══════════════════════════════════════════════════════════════════════════════════
                        """, language=None)
                    
                    # ===========================================================================
                    # SECTION 6: DEFLECTION CHECK
                    # ===========================================================================
                    st.markdown("---")
                    st.markdown("## 6. DEFLECTION SERVICEABILITY CHECK")
                    st.markdown("**Reference:** ACI 318-19 Section 24.2")
                    
                    if 'deflection' in slab_results:
                        defl = slab_results['deflection']
                        st.code(f"""
        DEFLECTION UNDER SERVICE LOADS:
        ═══════════════════════════════════════════════════════════════════════════════════
        
        Using effective moment of inertia (Ie) per ACI 318-19 Eq. 24.2.3.5:
        
        Ie = Icr + (Ig - Icr) × (Mcr/Ma)³ ≤ Ig
        
        Where:
        Ig  = Gross moment of inertia
        Icr = Cracked moment of inertia
        Mcr = Cracking moment = fr × Ig / yt
        Ma  = Service moment
        
        Calculated Deflection:   δ      = {defl.demand:.2f} mm
        Deflection Limit:        δ_limit = L/360 = {deck_span/360:.2f} mm
        
        DCR = δ / δ_limit = {defl.demand:.2f} / {defl.capacity:.2f} = {defl.ratio:.3f}
        Status: {'✅ PASS' if defl.status == 'PASS' else '❌ FAIL'}
        ═══════════════════════════════════════════════════════════════════════════════════
                        """, language=None)
                    
                    # ===========================================================================
                    # SECTION 7: MINIMUM REINFORCEMENT
                    # ===========================================================================
                    st.markdown("---")
                    st.markdown("## 7. MINIMUM REINFORCEMENT CHECK")
                    st.markdown("**Reference:** ACI 318-19 Section 7.6.1, Table 24.4.3.2")
                    
                    # Temperature & shrinkage reinforcement
                    As_min_ts = 0.0018 * 1000 * slab_tc  # mm²/m
                    
                    st.code(f"""
        TEMPERATURE & SHRINKAGE REINFORCEMENT (ACI 318-19 Table 24.4.3.2):
        ═══════════════════════════════════════════════════════════════════════════════════
        For Grade 60 (fy = 420 MPa) reinforcement:
        
        As,min = 0.0018 × b × h
        As,min = 0.0018 × 1000 mm × {slab_tc} mm
        As,min = {As_min_ts:.0f} mm²/m
        
        Provided:
        Top rebar:     As = {rebar_As} mm²/m
        Metal deck:    Ag = {deck_gross_props.Ag:.0f} mm²/m (contributes to positive moment)
        
        Check: As,provided = {rebar_As} mm²/m {'≥' if rebar_As >= As_min_ts else '<'} As,min = {As_min_ts:.0f} mm²/m
        Status: {'✅ PASS' if rebar_As >= As_min_ts else '❌ FAIL - Increase top reinforcement'}
        ═══════════════════════════════════════════════════════════════════════════════════
                    """, language=None)
                    
                    # ===========================================================================
                    # SECTION 8: FIRE RATING CHECK (if enabled)
                    # ===========================================================================
                    if fire_check and 'fire_rating' in slab_results:
                        st.markdown("---")
                        st.markdown("## 8. FIRE RESISTANCE CHECK")
                        st.markdown("**Reference:** IBC 2021 Table 722.2.2.1")
                        
                        fire_result = slab_results['fire_rating']
                        st.code(f"""
        FIRE RESISTANCE RATING CHECK:
        ═══════════════════════════════════════════════════════════════════════════════════
        Required Rating:     {fire_rating_choice}
        
        Minimum slab thickness requirements (IBC Table 722.2.2.1):
        • 1-Hour:    3.5 in. (89 mm) normal weight concrete
        • 1.5-Hour:  4.0 in. (102 mm) normal weight concrete
        • 2-Hour:    5.0 in. (127 mm) normal weight concrete
        
        Provided Thickness:  tc = {slab_tc} mm
        
        Status: {'✅ PASS' if fire_result.status == 'PASS' else '❌ FAIL - Increase slab thickness'}
        ═══════════════════════════════════════════════════════════════════════════════════
                        """, language=None)
                    
                    # ===========================================================================
                    # SECTION 9: DESIGN SUMMARY
                    # ===========================================================================
                    st.markdown("---")
                    st.markdown("## 9. COMPOSITE SLAB DESIGN SUMMARY")
                    
                    all_pass_slab = all(r.status == "PASS" for r in slab_results.values())
                    
                    st.code(f"""
        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║                    COMPOSITE SLAB DESIGN SUMMARY                              ║
        ║                    Per ACI 318-19 & SDI C-2017                                ║
        ╠═══════════════════════════════════════════════════════════════════════════════╣
        ║ Slab: tc={slab_tc}mm, f'c={slab_fc}MPa           Span: {deck_span}mm ({slab_span_type})       ║
        ║ Rebar: As={rebar_As}mm²/m, fy={rebar_fy}MPa   Fire: {fire_rating_choice if fire_check else 'N/A'}                        ║
        ╠═══════════════════════════════════════════════════════════════════════════════╣
        ║ CHECK              │ DEMAND          │ CAPACITY        │ DCR    │ STATUS     ║
        ╠════════════════════╪═════════════════╪═════════════════╪════════╪════════════╣""", language=None)
                    
                    for name, check in slab_results.items():
                        status_icon = "✅ PASS" if check.status == "PASS" else "❌ FAIL"
                        st.code(f"    ║ {check.check_name:<18} │ {check.demand:>12.3f}    │ {check.capacity:>12.3f}    │ {check.ratio:>6.3f} │ {status_icon:>10} ║", language=None)
                    
                    st.code(f"""    ╠═══════════════════════════════════════════════════════════════════════════════╣""", language=None)
                    
                    if all_pass_slab:
                        st.success("## ✅ COMPOSITE SLAB DESIGN: ALL CHECKS PASS")
                    else:
                        st.error("## ❌ COMPOSITE SLAB DESIGN: FAILS - REVISE DESIGN")
                    
                    # Code references
                    with st.expander("📚 Code References"):
                        st.markdown("""
                        **ACI 318-19 References:**
                        - §22.2 - Flexural Strength
                        - §22.5 - One-Way Shear Strength
                        - §24.2 - Deflection Control
                        - §24.3 - Crack Control
                        - §7.6.1 - Minimum Reinforcement
                        - Table 24.4.3.2 - Temperature & Shrinkage Reinforcement
                        
                        **SDI C-2017 References:**
                        - §3.2 - Composite Section Strength
                        - §3.3 - Shear-Bond Strength
                        
                        **IBC 2021 References:**
                        - Table 722.2.2.1 - Fire Resistance Ratings
                        """)
                        
                except Exception as e:
                    st.error(f"Error in slab design: {e}")
                    st.info("Check input values in the sidebar")
            else:
                st.warning("⚠️ Valid deck geometry required. Configure Metal Deck in sidebar first.")

else:
    # ============== ONE-WAY SLAB TAB (Non-Composite Mode) ==============
    with tab7_ow:
        st.subheader("One-Way Reinforced Concrete Slab Design")
        st.markdown("**Reference:** ACI 318-19 - Building Code Requirements for Structural Concrete")
        st.info("🧱 **Design Approach:** Slab spans between beams as one-way RC slab (independent of steel beam)")
        
        if not ONEWAY_SLAB_AVAILABLE:
            st.error(f"⚠️ One-Way Slab module not available: {ONEWAY_SLAB_ERROR}")
        elif not ow_slab_enabled:
            st.info("📌 Enable One-Way Slab Design in the sidebar to see results")
        else:
            if oneway_slab_results is not None:
                ow = oneway_slab_results  # Shorthand
                
                # ===========================================================================
                # SECTION 1: SLAB GEOMETRY
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 1. SLAB GEOMETRY")
                
                slab_span_mm = spacing * 1000
                ow_d_eff = ow_tc - ow_cover - ow_bar_dia / 2
                
                st.code(f"""
    ONE-WAY SLAB CONFIGURATION:
    ═══════════════════════════════════════════════════════════════════════════════
    
                    BEAM                                BEAM
                      ▼                                  ▼
        ┌─────────────┴─────────────────────────────────┴─────────────┐
        │█████████████████████████████████████████████████████████████│ ─┬─ tc = {ow_tc} mm
        │█████████████████  CONCRETE SLAB  ███████████████████████████│ ─┴─ (total thickness)
        │█████████████████  (one-way span) ███████████████████████████│
        └─────────────────────────────────────────────────────────────┘
        ◄───────────────────── Ln = {slab_span_mm:.0f} mm ─────────────────────►
                         (clear span = beam spacing)
    
    GEOMETRY SUMMARY:
    ═══════════════════════════════════════════════════════════════════════════════
    Clear span                  Ln     = {slab_span_mm:.0f} mm ({spacing:.2f} m)
    Total slab thickness        tc     = {ow_tc} mm
    Clear cover                 cover  = {ow_cover} mm
    Main bar diameter           db     = {ow_bar_dia} mm
    Effective depth             d      = tc - cover - db/2 = {ow_d_eff:.0f} mm
    Span condition                     = {ow_span_type}
    ═══════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                # ===========================================================================
                # SECTION 2: MATERIALS
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 2. MATERIAL PROPERTIES")
                
                mat = ow.materials
                st.code(f"""
    CONCRETE:
    ─────────────────────────────────────────
    Compressive strength      f'c   = {mat.fc:.0f} MPa
    Modulus of elasticity     Ec    = {mat.Ec:.0f} MPa
    Modulus of rupture        fr    = 0.62√f'c = {mat.fr:.2f} MPa
    β1 (stress block factor)        = {mat.beta1:.3f}
    
    REINFORCEMENT:
    ─────────────────────────────────────────
    Yield strength            fy    = {mat.fy:.0f} MPa
    Modulus of elasticity     Es    = {mat.Es:.0f} MPa
    Modular ratio             n     = Es/Ec = {mat.n:.2f}
                """, language=None)
                
                # ===========================================================================
                # SECTION 3: LOADING
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 3. LOADING")
                
                st.code(f"""
    SLAB LOADS (per unit area):
    ═══════════════════════════════════════════════════════════════════════════════
    Dead Load (slab + deck)        wDL   = {ow.w_DL:.2f} kN/m²
    Superimposed Dead Load         wSDL  = {ow.w_SDL:.2f} kN/m²
    Live Load                      wLL   = {ow.w_LL:.2f} kN/m²
    ─────────────────────────────────────────────────────────────────
    Total Service Load             w     = {ow.w_service:.2f} kN/m²
    
    FACTORED LOAD ({method}):
    wu = {'1.2(DL+SDL) + 1.6LL' if method == 'LRFD' else 'DL + SDL + LL'}
    wu = {ow.wu:.2f} kN/m²
    ═══════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                # ===========================================================================
                # SECTION 4: FLEXURAL DESIGN
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 4. FLEXURAL DESIGN")
                st.markdown("**Reference:** ACI 318-19 §22.2, §6.5")
                
                # Moment coefficients
                coefs = get_moment_coefficients(ow_span_type)
                
                st.markdown("### 4.1 Design Moments (Coefficient Method)")
                st.latex(r"M_u = C \times w_u \times L_n^2")
                
                st.code(f"""
    MOMENT COEFFICIENTS (ACI 318-19 §6.5):
    ─────────────────────────────────────────
    Span Type: {ow_span_type}
    Positive moment coefficient   = 1/{int(1/coefs.positive) if coefs.positive > 0 else 'N/A'}
    Negative moment coefficient   = 1/{int(1/coefs.negative_int) if coefs.negative_int > 0 else 'N/A'}
    
    FACTORED MOMENTS:
    ─────────────────────────────────────────
    Positive Mu+ = {ow.wu:.2f} × ({slab_span_mm/1000:.2f})² × {coefs.positive:.4f} = {ow.Mu_pos:.2f} kN-m/m
    Negative Mu- = {ow.Mu_neg:.2f} kN-m/m
                """, language=None)
                
                st.markdown("### 4.2 Reinforcement Design (Positive Moment)")
                flex_pos = ow.flexure_pos
                
                st.latex(r"\rho = \frac{0.85 f'_c}{f_y} \left[ 1 - \sqrt{1 - \frac{2R_n}{0.85 f'_c}} \right]")
                
                st.code(f"""
    REINFORCEMENT CALCULATION:
    ═══════════════════════════════════════════════════════════════════════════════
    Required ρ                        = {flex_pos.rho_req:.5f}
    Minimum ρ (ACI Table 7.6.1.1)     = {flex_pos.rho_min:.5f}
    Maximum ρ (tension-controlled)    = {flex_pos.rho_max:.5f}
    
    Required As = max(ρ_req, ρ_min) × b × d
               = {max(flex_pos.rho_req, flex_pos.rho_min):.5f} × 1000 × {ow_d_eff:.0f}
               = {flex_pos.As_req:.0f} mm²/m
    
    Minimum As = ρ_min × b × h = {flex_pos.rho_min:.5f} × 1000 × {ow_tc} = {flex_pos.As_min:.0f} mm²/m
    
    PROVIDED: As = {flex_pos.As_provided:.0f} mm²/m
    ═══════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                # Calculate suggested bar spacing
                Ab = math.pi * ow_bar_dia**2 / 4
                n_bars_per_m = flex_pos.As_provided / Ab
                spacing_mm = 1000 / n_bars_per_m if n_bars_per_m > 0 else 999
                
                st.markdown("### 4.3 Reinforcement Selection")
                st.code(f"""
    BOTTOM REINFORCEMENT (Positive Moment):
    ─────────────────────────────────────────
    Required As      = {flex_pos.As_req:.0f} mm²/m
    Bar diameter     = T{ow_bar_dia}
    Bar area         = {Ab:.0f} mm²
    
    SUGGESTED: T{ow_bar_dia} @ {int(spacing_mm)} mm c/c
    Provided As      = {1000/spacing_mm * Ab:.0f} mm²/m
    
    Spacing check: {spacing_mm:.0f} mm ≤ min(3h, 450) = {min(3*ow_tc, 450):.0f} mm → {'✅ OK' if spacing_mm <= min(3*ow_tc, 450) else '❌ NG'}
                """, language=None)
                
                st.markdown("### 4.4 Capacity Check")
                st.code(f"""
    MOMENT CAPACITY:
    ─────────────────────────────────────────
    Stress block depth   a = As×fy / (0.85×f'c×b) = {flex_pos.a:.2f} mm
    Neutral axis         c = a/β1 = {flex_pos.c:.2f} mm
    Steel strain         εt = 0.003(d-c)/c = {flex_pos.epsilon_t:.5f}
    Section type:        {flex_pos.section_type}
    
    φ = {flex_pos.phi:.2f}
    φMn = φ × As × fy × (d - a/2) = {flex_pos.phi_Mn:.2f} kN-m/m
    
    DCR = Mu / φMn = {ow.Mu_pos:.2f} / {flex_pos.phi_Mn:.2f} = {flex_pos.DCR:.3f}
                """, language=None)
                
                if flex_pos.DCR <= 1.0:
                    st.success(f"✅ **FLEXURE OK** — DCR = {flex_pos.DCR:.3f} ≤ 1.0")
                else:
                    st.error(f"❌ **FLEXURE NG** — DCR = {flex_pos.DCR:.3f} > 1.0")
                
                # ===========================================================================
                # SECTION 5: SHEAR CHECK
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 5. SHEAR CHECK")
                st.markdown("**Reference:** ACI 318-19 §22.5")
                
                shear = ow.shear
                
                st.latex(r"V_c = 0.17 \lambda \sqrt{f'_c} \times b_w \times d")
                
                st.code(f"""
    SHEAR CHECK:
    ═══════════════════════════════════════════════════════════════════════════════
    Critical section at d from face of support = {shear.critical_location:.0f} mm
    
    Factored shear at critical section:
    Vu = {shear.Vu:.2f} kN/m
    
    Concrete shear capacity:
    Vc = 0.17 × 1.0 × √{mat.fc:.0f} × 1000 × {ow_d_eff:.0f} / 1000 = {shear.Vc:.2f} kN/m
    
    φVc = 0.75 × {shear.Vc:.2f} = {shear.phi_Vc:.2f} kN/m
    
    DCR = Vu / φVc = {shear.Vu:.2f} / {shear.phi_Vc:.2f} = {shear.DCR:.3f}
    ═══════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                if shear.ok:
                    st.success(f"✅ **SHEAR OK** — DCR = {shear.DCR:.3f} ≤ 1.0 (No stirrups required)")
                else:
                    st.error(f"❌ **SHEAR NG** — DCR = {shear.DCR:.3f} > 1.0")
                
                # ===========================================================================
                # SECTION 6: DEFLECTION CHECK
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 6. DEFLECTION CONTROL")
                st.markdown("**Reference:** ACI 318-19 §7.3.1, §24.2")
                
                defl = ow.deflection
                
                st.markdown("### 6.1 Minimum Thickness Check")
                st.code(f"""
    MINIMUM THICKNESS (ACI Table 7.3.1.1):
    ─────────────────────────────────────────
    Span type:           {ow_span_type}
    Minimum h_min:       L/{20 if ow_span_type == 'Simple' else 24 if ow_span_type == 'One End Continuous' else 28 if ow_span_type == 'Both Ends Continuous' else 10} = {defl.h_min:.0f} mm
    Provided thickness:  {defl.h_provided:.0f} mm
    
    Check: {defl.h_provided:.0f} mm {'≥' if defl.thickness_ok else '<'} {defl.h_min:.0f} mm → {'✅ OK - Deflection calculation not required' if defl.thickness_ok else '⚠️ Calculate deflection'}
                """, language=None)
                
                if not defl.thickness_ok:
                    st.markdown("### 6.2 Calculated Deflection")
                    st.code(f"""
    IMMEDIATE DEFLECTION:
    ─────────────────────────────────────────
    Gross Ig      = {defl.Ig/1e6:.2f} × 10⁶ mm⁴/m
    Cracked Icr   = {defl.Icr/1e6:.2f} × 10⁶ mm⁴/m
    Effective Ie  = {defl.Ie/1e6:.2f} × 10⁶ mm⁴/m
    
    Cracking moment Mcr = {defl.Mcr:.2f} kN-m/m
    Service moment  Ma  = {defl.Ma:.2f} kN-m/m
    
    Immediate δ_i       = {defl.delta_i:.2f} mm
    Long-term δ_lt      = {defl.delta_lt:.2f} mm
    Total deflection    = {defl.delta_total:.2f} mm
    
    Limit (L/240)       = {defl.delta_limit:.2f} mm
    DCR                 = {defl.DCR:.3f}
                    """, language=None)
                
                # ===========================================================================
                # SECTION 7: SHRINKAGE & TEMPERATURE REINFORCEMENT
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 7. SHRINKAGE & TEMPERATURE REINFORCEMENT")
                st.markdown("**Reference:** ACI 318-19 §24.4")
                
                shrink = ow.shrinkage_temp
                
                st.code(f"""
    SHRINKAGE/TEMPERATURE STEEL (perpendicular to main reinforcement):
    ═══════════════════════════════════════════════════════════════════════════════
    Minimum ratio ρ_temp  = {shrink.rho_min:.5f}
    Required As_temp      = {shrink.rho_min:.5f} × 1000 × {ow_tc} = {shrink.As_req:.0f} mm²/m
    Maximum spacing       = min(5h, 450) = {shrink.s_max:.0f} mm
    
    SUGGESTED: T10 @ {min(int(shrink.s_max), 200)} mm c/c (As = {1000/min(shrink.s_max, 200) * 78.5:.0f} mm²/m)
    ═══════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                # ===========================================================================
                # SECTION 8: SUMMARY
                # ===========================================================================
                st.markdown("---")
                st.markdown("## 8. DESIGN SUMMARY")
                
                summary_data = {
                    "Check": ["Flexure (Positive)", "Shear", "Deflection"],
                    "Demand": [f"{ow.Mu_pos:.2f} kN-m/m", f"{shear.Vu:.2f} kN/m", f"{defl.delta_total:.2f} mm"],
                    "Capacity": [f"{flex_pos.phi_Mn:.2f} kN-m/m", f"{shear.phi_Vc:.2f} kN/m", f"{defl.delta_limit:.2f} mm"],
                    "DCR": [f"{flex_pos.DCR:.3f}", f"{shear.DCR:.3f}", f"{defl.DCR:.3f}"],
                    "Status": [
                        "✅ OK" if flex_pos.DCR <= 1.0 else "❌ NG",
                        "✅ OK" if shear.ok else "❌ NG",
                        "✅ OK" if defl.DCR <= 1.0 else "❌ NG"
                    ]
                }
                st.table(summary_data)
                
                st.markdown("### Reinforcement Summary")
                st.code(f"""
    ═══════════════════════════════════════════════════════════════════════════════
    BOTTOM STEEL (main): T{ow_bar_dia} @ {int(spacing_mm)} mm c/c (As = {flex_pos.As_provided:.0f} mm²/m)
    TOP STEEL (if req'd): T{ow_bar_dia} @ {int(spacing_mm)} mm c/c  
    TEMP/SHRINK:         T10 @ {min(int(shrink.s_max), 200)} mm c/c (perpendicular)
    ═══════════════════════════════════════════════════════════════════════════════
                """, language=None)
                
                if ow.all_pass:
                    st.success("## ✅ ONE-WAY SLAB DESIGN: ALL CHECKS PASS")
                else:
                    st.error(f"## ❌ ONE-WAY SLAB DESIGN: FAILS - {ow.governing_check}")
            else:
                st.warning("⚠️ One-way slab results not available. Check sidebar inputs.")
    
    # ============== DIAPHRAGM TAB (Phase 5) ==============
with tab8:
    st.subheader("Diaphragm Design - Lateral Load Resistance")
    st.markdown("**Reference:** SDI DDM04, AISI S310-16, ASCE 7-22")
    
    if not DIAPHRAGM_AVAILABLE:
        st.error(f"⚠️ Diaphragm module not available: {DIAPHRAGM_ERROR}")
    elif not diaph_enabled:
        st.info("📌 Enable Diaphragm Design in the sidebar to see results")
    elif not deck_enabled:
        st.info("📌 Enable Metal Deck Design first - deck properties are required for diaphragm analysis")
    elif deck_parse_result and deck_parse_result.is_valid:
        
        # ===========================================================================
        # SECTION 1: DIAPHRAGM GEOMETRY
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 1. DIAPHRAGM GEOMETRY AND LAYOUT")
        
        st.code(f"""
    FLOOR DIAPHRAGM PLAN VIEW:
    
    ◄─────────────────────────  L = {diaph_length/1000:.1f} m  ─────────────────────────►
    
    ┌─────────────────────────────────────────────────────────────────────────────────┐  ─┬─
    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │
    │░░░░░░░░░░░░░░░░░░░░░  METAL DECK DIAPHRAGM  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │
    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │ W = {diaph_width/1000:.1f} m
    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │ (width)
    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │
    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │
    └─────────────────────────────────────────────────────────────────────────────────┘  ─┴─
    △                                                                                 △
    │                                                                                 │
    LATERAL FORCE RESISTING SYSTEM                    LATERAL FORCE RESISTING SYSTEM
    (Shear Wall, Braced Frame, etc.)                 (Shear Wall, Braced Frame, etc.)
    
    
    LATERAL LOAD (Wind or Seismic):
    ────────────────────────────────────────────────────────────────────────────────────
                                      →→→→→→→→→→→→→→→→→→→→→→→→→→→→→
                                      w = {max(diaph_w_wind, diaph_w_seismic):.2f} kN/m (uniformly distributed)
    
    
    DIAPHRAGM PROPERTIES:
    ═══════════════════════════════════════════════════════════════════════════════════
    Length (parallel to load)         L        = {diaph_length:.0f} mm = {diaph_length/1000:.1f} m
    Width (perpendicular to load)     W        = {diaph_width:.0f} mm = {diaph_width/1000:.1f} m
    Aspect ratio                      L/W      = {diaph_length/diaph_width:.2f}
    Deck span (between supports)      span     = {deck_span} mm
    Deck thickness                    t        = {deck_t:.2f} mm
    ═══════════════════════════════════════════════════════════════════════════════════
        """, language=None)
        
        # ===========================================================================
        # SECTION 2: LATERAL LOADING
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 2. LATERAL LOADING")
        st.markdown("**Reference:** ASCE 7-22 Chapters 26-30 (Wind), Chapter 12 (Seismic)")
        
        governing_load = max(diaph_w_wind, diaph_w_seismic)
        load_type = "WIND" if diaph_w_wind >= diaph_w_seismic else "SEISMIC"
        
        st.code(f"""
    LATERAL LOAD COMPARISON:
    ═══════════════════════════════════════════════════════════════════════════════════
    Wind load                         w_wind   = {diaph_w_wind:.2f} kN/m
    Seismic load                      w_seis   = {diaph_w_seismic:.2f} kN/m
    ─────────────────────────────────────────────────────────────────────────────────
    GOVERNING LOAD                    w        = {governing_load:.2f} kN/m ({load_type})
    
    
    DIAPHRAGM SHEAR DEMAND:
    ═══════════════════════════════════════════════════════════════════════════════════
    
    For uniformly distributed lateral load on simple-span diaphragm:
    
    Maximum shear at supports:
    V_max = w × L / 2
    V_max = {governing_load:.2f} kN/m × {diaph_length/1000:.1f} m / 2
    V_max = {governing_load * diaph_length / 1000 / 2:.2f} kN
    
    Unit shear demand:
    v_u = V_max / W
    v_u = {governing_load * diaph_length / 1000 / 2:.2f} kN / {diaph_width/1000:.1f} m
    v_u = {governing_load * diaph_length / 1000 / 2 / (diaph_width/1000):.2f} kN/m
    ═══════════════════════════════════════════════════════════════════════════════════
        """, language=None)
        
        # ===========================================================================
        # SECTION 3: FASTENER CONFIGURATION
        # ===========================================================================
        st.markdown("---")
        st.markdown("## 3. FASTENER CONFIGURATION")
        st.markdown("**Reference:** SDI DDM04 Section 4")
        
        st.code(f"""
    DECK FASTENER LAYOUT:
    
    ═══════════════════════════════════════════════════════════════════════════════════
    SUPPORT FASTENERS (Deck to Beam):
    ─────────────────────────────────────────────────────────────────────────────────
    Type:                             {diaph_support_type}
    Diameter:                         {diaph_support_dia} mm
    Fasteners per rib:                {diaph_n_per_rib}
    
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                                  STEEL BEAM                                     │
    │═════════════════════════════════════════════════════════════════════════════════│
    │    ●           ●           ●           ●           ●           ●           ●    │
    │  (fastener)  (fastener)  (fastener)  (fastener)  (fastener)  (fastener)       │
    │    └───────────┴───────────┴───────────┴───────────┴───────────┴───────────┘    │
    │                            DECK FLANGE (on beam)                               │
    └─────────────────────────────────────────────────────────────────────────────────┘
    
    
    SIDELAP FASTENERS (Deck to Deck):
    ─────────────────────────────────────────────────────────────────────────────────
    Type:                             {diaph_sidelap_type}
    Spacing:                          {diaph_sidelap_spacing} mm
    
         Sheet 1              Sheet 2
    ┌─────────────────┐  ┌─────────────────┐
    │                 │  │                 │
    │                 ├──┼──●──●──●──●──●──┤  ← Sidelap fasteners
    │                 │  │                 │    @ {diaph_sidelap_spacing} mm spacing
    │                 │  │                 │
    └─────────────────┘  └─────────────────┘
    ═══════════════════════════════════════════════════════════════════════════════════
        """, language=None)
        
        # Map fastener types and create design objects
        support_type_map = {
            "Arc Spot Weld": FastenerType.ARC_SPOT_WELD,
            "Screw": FastenerType.SCREW,
            "PAF": FastenerType.PAF
        }
        sidelap_type_map = {
            "Screw": SideLapType.SCREW,
            "Button Punch": SideLapType.BUTTON_PUNCH,
            "Weld": SideLapType.WELD,
            "None": SideLapType.NONE
        }
        
        diaph_deck = DiaphragmDeckProfile(
            hr=deck_hr, pitch=deck_pitch, t=deck_t,
            fy=deck_Fy, fu=min(deck_Fy * 1.35, 450),
            cover_width=914
        )
        diaph_geom = DiaphragmGeometry(
            length=diaph_length, width=diaph_width,
            deck_span=deck_span, orientation=DeckOrientation.PERPENDICULAR
        )
        diaph_support = SupportFastener(
            fastener_type=support_type_map.get(diaph_support_type, FastenerType.ARC_SPOT_WELD),
            diameter=diaph_support_dia, n_per_rib=diaph_n_per_rib
        )
        diaph_sidelap = SideLapFastener(
            fastener_type=sidelap_type_map.get(diaph_sidelap_type, SideLapType.SCREW),
            diameter=4.8, spacing=diaph_sidelap_spacing
        )
        diaph_loads = DiaphragmLoads(w_wind=diaph_w_wind, w_seismic=diaph_w_seismic)
        
        # Run diaphragm design
        try:
            diaph_method = DiaphragmDesignMethod.LRFD if method == "LRFD" else DiaphragmDesignMethod.ASD
            
            diaph_results = design_diaphragm(
                deck=diaph_deck, geometry=diaph_geom,
                support_fastener=diaph_support, sidelap_fastener=diaph_sidelap,
                loads=diaph_loads, method=diaph_method
            )
            
            # ===========================================================================
            # SECTION 4: SHEAR STRENGTH CHECK
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 4. DIAPHRAGM SHEAR STRENGTH")
            st.markdown("**Reference:** SDI DDM04 Section 5, AISI S310-16 Section B")
            
            if 'shear_strength' in diaph_results:
                shear = diaph_results['shear_strength']
                st.code(f"""
    NOMINAL DIAPHRAGM SHEAR STRENGTH:
    ═══════════════════════════════════════════════════════════════════════════════════
    
    Sn = Sn,conn × α + Sn,deck
    
    Where:
    Sn,conn = Shear strength contribution from fasteners
    Sn,deck = Shear strength contribution from deck panels
    α       = Fastener pattern modification factor
    
    Design Shear Strength:
    φSn = {shear.capacity:.2f} kN/m
    
    Required Shear Strength:
    vu = {shear.demand:.2f} kN/m
    
    DCR = vu / φSn = {shear.demand:.2f} / {shear.capacity:.2f} = {shear.ratio:.3f}
    Status: {'✅ PASS' if shear.status == 'PASS' else '❌ FAIL'}
    ═══════════════════════════════════════════════════════════════════════════════════
                """, language=None)
            
            # ===========================================================================
            # SECTION 5: DIAPHRAGM STIFFNESS
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 5. DIAPHRAGM STIFFNESS AND DEFLECTION")
            st.markdown("**Reference:** SDI DDM04 Section 6, ASCE 7-22 Section 12.3.1")
            
            if 'deflection' in diaph_results:
                defl = diaph_results['deflection']
                st.code(f"""
    DIAPHRAGM DEFLECTION:
    ═══════════════════════════════════════════════════════════════════════════════════
    
    Diaphragm deflection components:
    
    Δ_total = Δ_shear + Δ_flexure + Δ_slip
    
    Where:
    Δ_shear   = Shear deformation of deck panels
    Δ_flexure = Flexural deformation (chord elongation/shortening)
    Δ_slip    = Fastener slip deformation
    
    Calculated Deflection:    Δ = {defl.demand:.2f} mm
    
    For diaphragm flexibility classification (ASCE 7-22 §12.3.1):
    Flexible:     Δ_diaph > 2 × Δ_story
    Rigid:        Δ_diaph < 0.5 × Δ_story
    Semi-rigid:   Otherwise
    ═══════════════════════════════════════════════════════════════════════════════════
                """, language=None)
            
            # ===========================================================================
            # SECTION 6: CHORD FORCES
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 6. CHORD AND COLLECTOR FORCES")
            st.markdown("**Reference:** SDI DDM04 Section 7")
            
            if 'chord_force' in diaph_results:
                chord = diaph_results['chord_force']
                st.code(f"""
    CHORD FORCE CALCULATION:
    ═══════════════════════════════════════════════════════════════════════════════════
    
    DIAPHRAGM FLEXURE MODEL:
    
                    w (lateral load)
                    ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓
    ┌──────────────────────────────────────┐
    │            COMPRESSION               │ ← Chord (compression)
    │               CHORD                  │
    │                                      │
    │            DIAPHRAGM                 │
    │             (shear)                  │
    │                                      │
    │              TENSION                 │
    │               CHORD                  │ ← Chord (tension)
    └──────────────────────────────────────┘
    
    Maximum chord force (at midspan):
    T_chord = M_max / W
    
    Where:
    M_max = w × L² / 8 (for uniform load)
    W     = Diaphragm width (moment arm between chords)
    
    T_chord = ({governing_load:.2f} × {diaph_length/1000:.1f}² / 8) / {diaph_width/1000:.1f}
    T_chord = {chord.demand:.2f} kN
    
    This force must be transferred through:
    • Perimeter beams (chord members)
    • Connections at beam splices
    • Connections to lateral force resisting system
    ═══════════════════════════════════════════════════════════════════════════════════
                """, language=None)
            
            # ===========================================================================
            # SECTION 7: DIAPHRAGM CLASSIFICATION
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 7. DIAPHRAGM FLEXIBILITY CLASSIFICATION")
            st.markdown("**Reference:** ASCE 7-22 Section 12.3.1")
            
            if 'classification' in diaph_results:
                classif = diaph_results['classification']
                st.code(f"""
    DIAPHRAGM CLASSIFICATION:
    ═══════════════════════════════════════════════════════════════════════════════════
    
    Per ASCE 7-22 Section 12.3.1:
    
    Classification:  {classif.status}
    
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │ Classification │ Criterion                     │ Design Implication            │
    ├────────────────┼───────────────────────────────┼───────────────────────────────┤
    │ RIGID          │ Δ_diaph < 0.5 × Δ_story      │ Distribute lateral loads by   │
    │                │                               │ relative stiffness of LFRS    │
    ├────────────────┼───────────────────────────────┼───────────────────────────────┤
    │ FLEXIBLE       │ Δ_diaph > 2 × Δ_story        │ Distribute lateral loads by   │
    │                │                               │ tributary area                │
    ├────────────────┼───────────────────────────────┼───────────────────────────────┤
    │ SEMI-RIGID     │ Between rigid and flexible    │ Use envelope of both methods  │
    └────────────────┴───────────────────────────────┴───────────────────────────────┘
    ═══════════════════════════════════════════════════════════════════════════════════
                """, language=None)
            
            # ===========================================================================
            # SECTION 8: DESIGN SUMMARY
            # ===========================================================================
            st.markdown("---")
            st.markdown("## 8. DIAPHRAGM DESIGN SUMMARY")
            
            checks = [r for r in diaph_results.values() if r.status not in ["INFO", "FLEXIBLE", "RIGID", "SEMI_RIGID"]]
            all_pass_diaph = all(r.status == "PASS" for r in checks) if checks else True
            
            st.code(f"""
    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║                      DIAPHRAGM DESIGN SUMMARY                                 ║
    ║                      Per SDI DDM04 & AISI S310-16                             ║
    ╠═══════════════════════════════════════════════════════════════════════════════╣
    ║ Size: {diaph_length/1000:.1f}m × {diaph_width/1000:.1f}m            Governing Load: {load_type} ({governing_load:.2f} kN/m)      ║
    ║ Deck: t={deck_t:.2f}mm, Fy={deck_Fy:.0f}MPa   Support: {diaph_support_type}, {diaph_n_per_rib}/rib         ║
    ╠═══════════════════════════════════════════════════════════════════════════════╣
    ║ CHECK              │ DEMAND          │ CAPACITY        │ DCR    │ STATUS     ║
    ╠════════════════════╪═════════════════╪═════════════════╪════════╪════════════╣""", language=None)
            
            for name, check in diaph_results.items():
                if check.status in ["FLEXIBLE", "RIGID", "SEMI_RIGID"]:
                    st.code(f"    ║ {check.check_name:<18} │        -        │        -        │    -   │ {check.status:>10} ║", language=None)
                elif check.status == "INFO":
                    st.code(f"    ║ {check.check_name:<18} │ {check.demand:>12.2f}    │      verify     │    -   │     INFO   ║", language=None)
                else:
                    status_icon = "✅ PASS" if check.status == "PASS" else "❌ FAIL"
                    st.code(f"    ║ {check.check_name:<18} │ {check.demand:>12.2f}    │ {check.capacity:>12.2f}    │ {check.ratio:>6.3f} │ {status_icon:>10} ║", language=None)
            
            st.code(f"""    ╠═══════════════════════════════════════════════════════════════════════════════╣""", language=None)
            
            if all_pass_diaph:
                st.success("## ✅ DIAPHRAGM DESIGN: ALL CHECKS PASS")
            else:
                st.error("## ❌ DIAPHRAGM DESIGN: FAILS - INCREASE FASTENER DENSITY OR DECK THICKNESS")
            
            # Code references
            with st.expander("📚 Code References"):
                st.markdown("""
                **SDI DDM04 References:**
                - §4 - Fastener Capacity
                - §5 - Diaphragm Shear Strength
                - §6 - Diaphragm Stiffness
                - §7 - Chord and Collector Forces
                
                **AISI S310-16 References:**
                - §B - Nominal Shear Strength
                - §C - Diaphragm Stiffness
                
                **ASCE 7-22 References:**
                - §12.3.1 - Diaphragm Flexibility
                - §12.10 - Diaphragm Design Forces
                """)
                
        except Exception as e:
            st.error(f"Error in diaphragm design: {e}")
            st.info("Check input values in the sidebar")
    else:
        st.warning("⚠️ Valid deck geometry required. Configure Metal Deck in sidebar first.")

# ============== CASTELLATED/CELLULAR TAB ==============
with tab9:
    st.subheader("🔶 Castellated/Cellular Beam Design - AISC DG31")
    
    if not CASTELLATED_AVAILABLE:
        st.error(f"⚠️ Castellated/Cellular module not available: {CASTELLATED_ERROR}")
    elif not castellated_enabled:
        st.info("📌 Select 'Castellated/Cellular' in Steel Section to enable this design")
    else:
        st.markdown("""
        Design of castellated and cellular beams per **AISC Design Guide 31**.
        Includes dimensional limits, global flexure, Vierendeel bending, web post buckling, and shear checks.
        """)
        
        # Create geometry object - cast_theta is always defined in sidebar
        if cast_beam_type == "Castellated":
            cast_geom = CastellatedGeometry(
                ho=cast_ho,
                e=cast_e,
                b=cast_b,
                S=cast_S,
                theta=cast_theta
            )
            beam_type_enum = BeamType.CASTELLATED
        else:
            cast_geom = CellularGeometry(
                Do=cast_Do,
                S=cast_S
            )
            beam_type_enum = BeamType.CELLULAR
        
        # Material
        cast_material = CastellatedMaterial(Fy=Fy, Fu=Fu)
        
        # Loading - use same loads as main beam
        cast_loading = CastellatedLoading(
            w_dead=w_DL,
            w_live=w_LL,
            span=L * 1000  # Convert to mm
        )
        
        # Calculate section properties
        cast_section_props = calc_expanded_section(cast_parent, beam_type_enum, cast_geom)
        
        # ==========================================
        # BEAM PROFILE VISUALIZATION
        # ==========================================
        st.markdown("### 📐 Beam Profile & Dimensions")
        
        try:
            # Import visualization functions
            from core.design.castellated_cellular import plot_castellated_beam, plot_cellular_beam
            
            if cast_beam_type == "Castellated":
                fig_profile = plot_castellated_beam(cast_parent, cast_geom, cast_section_props, n_openings=5)
            else:
                fig_profile = plot_cellular_beam(cast_parent, cast_geom, cast_section_props, n_openings=5)
            
            st.pyplot(fig_profile)
        except Exception as viz_err:
            # Fallback: Simple text-based summary if visualization fails
            st.warning(f"Could not generate beam profile visualization")
            
            st.markdown("**Beam Geometry Summary:**")
            col_geo1, col_geo2, col_geo3 = st.columns(3)
            with col_geo1:
                st.markdown(f"""
                **Parent Section:**
                - d = {cast_parent.d:.0f} mm
                - bf = {cast_parent.bf:.0f} mm
                - tf = {cast_parent.tf:.1f} mm
                - tw = {cast_parent.tw:.1f} mm
                """)
            with col_geo2:
                if cast_beam_type == "Castellated":
                    st.markdown(f"""
                    **Opening Geometry:**
                    - ho = {cast_ho:.0f} mm
                    - e = {cast_e:.0f} mm
                    - b = {cast_b:.0f} mm
                    - S = {cast_S:.0f} mm
                    - θ = {cast_theta}°
                    """)
                else:
                    st.markdown(f"""
                    **Opening Geometry:**
                    - Do = {cast_Do:.0f} mm
                    - S = {cast_S:.0f} mm
                    - b = {cast_S - cast_Do:.0f} mm
                    """)
            with col_geo3:
                st.markdown(f"""
                **Expanded Section:**
                - dg = {cast_section_props['dg']:.0f} mm
                - dt = {cast_section_props['dt']:.0f} mm
                - ho = {cast_section_props['ho']:.0f} mm
                - Expansion = {cast_section_props['dg']/cast_parent.d:.2f}×
                """)
        
        st.markdown("---")
        
        # ==========================================
        # EXPANDED SECTION PROPERTIES
        # ==========================================
        st.markdown("### 📊 Expanded Section Properties")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Parent Section", cast_parent_name[:20] + "..." if len(cast_parent_name) > 20 else cast_parent_name)
            st.metric("Beam Type", cast_beam_type)
        with col2:
            st.metric("Expanded Depth dg", f"{cast_section_props['dg']:.0f} mm")
            st.metric("Opening Height ho", f"{cast_section_props['ho']:.0f} mm")
        with col3:
            st.metric("Tee Depth dt", f"{cast_section_props['dt']:.0f} mm")
            st.metric("Gross Ix", f"{cast_section_props['Ix_gross']/1e6:.1f}×10⁶ mm⁴")
        with col4:
            st.metric("Net Ix (at opening)", f"{cast_section_props['Ix_net']/1e6:.1f}×10⁶ mm⁴")
            st.metric("Expansion Ratio", f"{cast_section_props['dg']/cast_parent.d:.2f}×")
        
        st.markdown("---")
        
        # ==========================================
        # RUN DETAILED PROFESSIONAL CALCULATIONS
        # ==========================================
        st.markdown("### 📋 PROFESSIONAL DESIGN CALCULATIONS")
        st.markdown("*Complete step-by-step calculations per AISC Design Guide 31*")
        
        try:
            # Generate detailed professional report
            detailed_report = design_castellated_detailed(
                parent_name=cast_parent_name,
                d=cast_parent.d, bf=cast_parent.bf, tf=cast_parent.tf, tw=cast_parent.tw,
                A=cast_parent.A, Ix=cast_parent.Ix,
                beam_type=cast_beam_type,
                ho=cast_ho, e=cast_e, b=cast_b, S=cast_S, theta=cast_theta,
                Do=cast_Do if cast_beam_type == "Cellular" else 0,
                Fy=Fy, Fu=Fu, E=200000,
                w_dead=w_DL, w_live=w_LL, L=L*1000,
                Lb=L*1000/4,  # Quarter span unbraced
                method=method
            )
            
            # Store castellated results in session state for report generation
            st.session_state['castellated_results'] = {
                'opening_type': cast_beam_type,
                'ho': cast_ho,
                'e': cast_e,
                'b': cast_b,
                'S': cast_S,
                'theta': cast_theta,
                'Do': cast_Do if cast_beam_type == "Cellular" else 0,
                'dg': cast_section_props['dg'],
                'dt': cast_section_props['dt'],
                'Ix_gross': cast_section_props['Ix_gross'],
                'Ix_net': cast_section_props['Ix_net'],
                'expansion_ratio': cast_section_props['dg'] / cast_parent.d,
                'overall_status': detailed_report.overall_status,
                'summary': detailed_report.summary,
                'parent_section': cast_parent_name,
            }
            
            # Overall result banner
            if detailed_report.overall_status == "PASS":
                st.success("✅ **ALL DESIGN CHECKS PASS** - Beam is adequate per AISC DG31")
            else:
                st.error("❌ **DESIGN FAILS** - Review detailed calculations below")
            
            # Summary table
            st.markdown("#### DESIGN SUMMARY")
            st.code(detailed_report.summary, language=None)
            
            # ==========================================
            # DETAILED CALCULATIONS BY SECTION
            # ==========================================
            st.markdown("---")
            st.markdown("## 📖 DETAILED CALCULATION SHEETS")
            st.markdown("*Each section below contains complete hand-calculation style documentation*")
            
            for section in detailed_report.sections:
                # Section header
                section_status = "✅" if section.status == "PASS" else "❌" if section.status == "FAIL" else "⚠️"
                
                with st.expander(f"{section_status} **SECTION {section.section_number}: {section.title}** - {section.code_ref}", expanded=(section.status == "FAIL")):
                    
                    # Section description
                    st.markdown(f"**Purpose:** {section.description}")
                    st.markdown("---")
                    
                    # Each calculation step
                    for step in section.steps:
                        # Step header with status
                        if step.status == "PASS":
                            step_icon = "✅"
                        elif step.status == "FAIL":
                            step_icon = "❌"
                        elif step.status == "WARNING":
                            step_icon = "⚠️"
                        else:
                            step_icon = "📐"
                        
                        st.markdown(f"### Step {step.step_number}: {step.title} {step_icon}")
                        
                        # Description/Explanation
                        st.markdown(f"**Explanation:**")
                        st.markdown(f"> {step.description}")
                        
                        # Equation box
                        st.markdown(f"**Equation:**")
                        st.latex(step.equation.replace("×", r" \times ").replace("√", r"\sqrt").replace("≤", r" \leq ").replace("≥", r" \geq "))
                        
                        # Substitution
                        st.markdown(f"**Substitution:**")
                        st.code(step.substitution, language=None)
                        
                        # Result
                        col_res1, col_res2, col_res3 = st.columns([2, 1, 2])
                        with col_res1:
                            st.markdown(f"**Result:** `{step.result:.4g} {step.unit}`")
                        with col_res2:
                            if step.status and step.status != "INFO":
                                if step.status == "PASS":
                                    st.success(step.status)
                                elif step.status == "FAIL":
                                    st.error(step.status)
                                else:
                                    st.warning(step.status)
                        with col_res3:
                            st.markdown(f"**Reference:** `{step.code_ref}`")
                        
                        # Notes if any
                        if step.notes:
                            st.info(f"📝 **Note:** {step.notes}")
                        
                        st.markdown("---")
                    
                    # Section conclusion
                    st.markdown("### Section Conclusion")
                    st.code(section.conclusion, language=None)
            
            # ==========================================
            # PRINTABLE CALCULATION SHEET
            # ==========================================
            st.markdown("---")
            st.markdown("### 📄 Export Complete Calculation Report")
            
            # Generate full text report
            full_report_text = format_detailed_report(detailed_report)
            
            # Download button for calculations
            st.download_button(
                label="📥 Download Complete Calculations (TXT)",
                data=full_report_text,
                file_name=f"Castellated_Calcs_{cast_parent_name.replace(' ', '_')}.txt",
                mime="text/plain"
            )
            
            # Also show in collapsible text area
            with st.expander("📋 View Complete Calculation Text (Copy/Print)"):
                st.text_area("Complete Calculations", full_report_text, height=600)
            
        except Exception as e:
            st.error(f"Error in detailed calculations: {e}")
            import traceback
            st.code(traceback.format_exc())
        
        # ==========================================
        # CODE REFERENCES
        # ==========================================
        with st.expander("📚 Code References - AISC Design Guide 31"):
            st.markdown("""
            **Chapter 3 - Dimensional Limits:**
            - §3.2 - Opening Height Limits: 0.5 ≤ ho/dg ≤ 0.7
            - §3.3 - Expansion Ratio: 1.3 ≤ dg/d ≤ 1.6
            - §3.4 - Castellated: e/ho = 0.25-0.5, θ = 45°-70°
            - §3.5 - Cellular: S/Do ≥ 1.1, web post ≥ 0.1Do
            
            **Chapter 5 - Design Checks:**
            - §5.2 - Global Flexural Strength (modified for openings)
            - §5.3 - Vierendeel Bending (local bending in tees)
            - §5.4 - Web Post Buckling (compression in web post)
            - §5.5 - Horizontal Shear (moment gradient transfer)
            - §5.6 - Vertical Shear at Openings (tee shear)
            - §5.7 - Deflection (increased due to openings)
            
            **AISC 360-16 References:**
            - Chapter E - Compression Members (web post)
            - Chapter F - Flexural Members
            - Chapter G - Shear Design
            """)

# ============== REPORT TAB ==============
with tab10:
    st.subheader("📋 FULL CALCULATION REPORT")
    st.markdown("**Complete Design Documentation per AISC 360-16, AISI S100-16, ACI 318-19, SDI C-2017**")
    
    # Report generation options
    st.markdown("### 📑 Select Sections to Include in Report")
    
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    with col_opt1:
        st.markdown("**Core Design**")
        include_precomp = st.checkbox("Pre-Composite Design", value=True, key="rpt_precomp")
        # Only show composite options in composite mode
        if design_mode == "Composite":
            include_composite = st.checkbox("Composite Design", value=True, key="rpt_comp")
            include_studs = st.checkbox("Shear Stud Design", value=True, key="rpt_studs")
        else:
            include_composite = False
            include_studs = False
            include_noncomp = st.checkbox("Non-Composite Steel Beam", value=True, key="rpt_noncomp")
    with col_opt2:
        st.markdown("**Floor System**")
        include_deck = st.checkbox("Metal Deck Design", value=deck_enabled, key="rpt_deck")
        if design_mode == "Composite":
            include_slab = st.checkbox("Composite Slab Design", value=slab_enabled, key="rpt_slab")
            include_oneway = False
        else:
            include_slab = False
            include_oneway = st.checkbox("One-Way Slab Design", value=ow_slab_enabled, key="rpt_oneway")
        include_diaphragm = st.checkbox("Diaphragm Design", value=False, key="rpt_diaph")
    with col_opt3:
        st.markdown("**Special Checks**")
        include_vibration = st.checkbox("Vibration Analysis", value=vibration_enabled, key="rpt_vib")
        include_castellated = st.checkbox("Castellated/Cellular", value=(sec_type == "Castellated/Cellular"), key="rpt_cast")
        include_summary = st.checkbox("Design Summary Tables", value=True, key="rpt_summary")
    
    st.markdown("---")
    
    # Build comprehensive report content
    report_title = "COMPOSITE FLOOR SYSTEM" if design_mode == "Composite" else "NON-COMPOSITE FLOOR SYSTEM"
    report_content = f"""
# {report_title}
# COMPLETE DESIGN CALCULATIONS
# METRIC UNITS (SI)

**Project:** {'Composite' if design_mode == 'Composite' else 'Non-Composite'} Beam Design
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Design Method:** {method}
**Design Mode:** {design_mode}
**Software:** CompositeBeam Pro v3.0

---

# TABLE OF CONTENTS

PART A: STEEL BEAM DESIGN (AISC 360-16)
   1. Material Properties and Section Selection
   2. Construction Stage Design (Non-Composite)
   3. Composite Beam Flexural Strength
   4. Shear Strength
   5. Deflection Calculations

PART B: SHEAR STUD DESIGN (AISC 360-16 Section I8)
   6. Shear Stud Strength
   7. Number of Studs and Spacing
   8. Detailing Requirements

PART C: METAL DECK DESIGN (SDI C-2017, AISI S100-16)
   9. Deck Profile Geometry
   10. Construction Stage Checks
   11. Flexural, Shear, Web Crippling

PART D: COMPOSITE SLAB DESIGN (ACI 318-19)
   12. Slab Geometry and Materials
   13. Flexural and Shear Strength

PART E: VIBRATION ANALYSIS (AISC Design Guide 11)
   14. Natural Frequency
   15. Peak Acceleration Check

---

# PART A: STEEL BEAM DESIGN
**Per AISC 360-16 Specification for Structural Steel Buildings**

## 1. MATERIAL PROPERTIES AND SECTION SELECTION

### 1.1 Structural Steel Properties

| Property | Symbol | Value | Reference |
|----------|--------|-------|-----------|
| Grade | - | {grade} | ASTM A992 |
| Yield Strength | Fy | {Fy} MPa | AISC 360-16 Table A3.1 |
| Tensile Strength | Fu | {Fu} MPa | AISC 360-16 Table A3.1 |
| Modulus of Elasticity | E | 200,000 MPa | AISC 360-16 §E3 |

### 1.2 Steel Section Properties: {sec_name}

| Property | Symbol | Value | Units |
|----------|--------|-------|-------|
| Depth | d | {sec['d']:.1f} | mm |
| Flange Width | bf | {sec['bf']:.1f} | mm |
| Flange Thickness | tf | {sec['tf']:.2f} | mm |
| Web Thickness | tw | {sec['tw']:.2f} | mm |
| Area | A | {sec['A']:.0f} | mm² |
| Moment of Inertia (major) | Ix | {sec['Ix']:.2e} | mm⁴ |
| Section Modulus | Sx | {sec['Sx']:.0f} | mm³ |
| Plastic Section Modulus | Zx | {sec['Zx']:.0f} | mm³ |
| Weight | w | {sec.get('wt', sec['A']*7850/1e6):.1f} | kg/m |

### 1.3 Concrete Properties

| Property | Symbol | Value | Reference |
|----------|--------|-------|-----------|
| Compressive Strength | f'c | {fc} MPa | ACI 318-19 |
| Unit Weight | wc | 2400 | kg/m³ |
| Modulus of Elasticity | Ec | {int(4700*math.sqrt(fc))} MPa | Ec = 4700√f'c |
| Modular Ratio | n | {200000/(4700*math.sqrt(fc)):.1f} | n = Es/Ec |

### 1.4 Geometric Parameters

| Parameter | Symbol | Value | Reference |
|-----------|--------|-------|-----------|
| Beam Span | L | {L:.2f} m | Given |
| Beam Spacing | s | {spacing:.2f} m | Given |
| Slab Thickness | tc | {tc} mm | Given |
| Effective Width | beff | {beff:.0f} mm | AISC 360-16 §I3.1a |

**Effective Width Calculation (AISC 360-16 §I3.1a):**

For interior beams:
beff = min(L/4, s) = min({L*1000/4:.0f}, {spacing*1000:.0f}) = {beff:.0f} mm

---

## 2. LOAD ANALYSIS

### 2.1 Dead Loads

| Load Component | Calculation | Value (kN/m) |
|----------------|-------------|--------------|
| Slab weight | {tc/1000:.3f} m × 24 kN/m³ × {spacing:.2f} m | {w_slab:.2f} |
| Steel beam | {sec.get('wt', sec['A']*7850/1e6):.1f} kg/m × 9.81/1000 | {sec.get('wt', sec['A']*7850/1e6)*9.81/1000:.2f} |
| **Total DL** | | **{w_DL:.2f}** |

### 2.2 Construction Stage Loads

| Load Component | Value (kN/m) |
|----------------|--------------|
| Dead Load (DL) | {w_DL:.2f} |
| Construction Live Load | {w_const:.2f} |
| **Total Construction** | **{w_DL + w_const:.2f}** |

### 2.3 Composite Stage Loads

| Load Component | Value (kN/m) |
|----------------|--------------|
| Dead Load (DL) | {w_DL:.2f} |
| Superimposed Dead (SDL) | {w_SDL:.2f} |
| Live Load (LL) | {w_LL:.2f} |
| **Total Service** | **{w_DL + w_SDL + w_LL:.2f}** |

### 2.4 Factored Loads ({method})

"""

    if method == "LRFD":
        report_content += f"""
**LRFD Load Combinations (ASCE 7-22):**

Construction: wu = 1.4 × D = 1.4 × {w_DL + w_const:.2f} = {1.4*(w_DL + w_const):.2f} kN/m

Composite: wu = 1.2D + 1.6L = 1.2 × {w_DL + w_SDL:.2f} + 1.6 × {w_LL:.2f} = {1.2*(w_DL + w_SDL) + 1.6*w_LL:.2f} kN/m
"""
    else:
        report_content += f"""
**ASD Load Combinations (ASCE 7-22):**

Construction: wa = D = {w_DL + w_const:.2f} kN/m

Composite: wa = D + L = {w_DL + w_SDL + w_LL:.2f} kN/m
"""

    if include_precomp:
        report_content += f"""
---

## 3. CONSTRUCTION STAGE DESIGN (NON-COMPOSITE)
**Reference:** AISC 360-16 Chapters F & G

### 3.1 Classification Check

**Flange Slenderness (AISC 360-16 Table B4.1b):**

λf = bf/(2tf) = {sec['bf']:.1f}/(2×{sec['tf']:.2f}) = {sec['bf']/(2*sec['tf']):.2f}

λpf = 0.38√(E/Fy) = 0.38√(200000/{Fy}) = {0.38*math.sqrt(200000/Fy):.2f}

Status: {"Compact ✓" if sec['bf']/(2*sec['tf']) <= 0.38*math.sqrt(200000/Fy) else "Non-Compact"}

**Web Slenderness (AISC 360-16 Table B4.1b):**

λw = h/tw ≈ {(sec['d']-2*sec['tf'])/sec['tw']:.1f}

λpw = 3.76√(E/Fy) = 3.76√(200000/{Fy}) = {3.76*math.sqrt(200000/Fy):.2f}

Status: {"Compact ✓" if (sec['d']-2*sec['tf'])/sec['tw'] <= 3.76*math.sqrt(200000/Fy) else "Non-Compact"}

### 3.2 Flexural Strength (Section F2)

**Nominal Flexural Strength:**

Mn = Mp = Fy × Zx

Mn = {Fy} × {sec['Zx']:.0f} = {Fy * sec['Zx'] / 1e6:.2f} kN·m

**Design Flexural Strength:**

{"φbMn = 0.90 × " + f"{Fy * sec['Zx'] / 1e6:.2f} = {0.90 * Fy * sec['Zx'] / 1e6:.2f} kN·m" if method == "LRFD" else "Mn/Ωb = " + f"{Fy * sec['Zx'] / 1e6:.2f} / 1.67 = {Fy * sec['Zx'] / 1e6 / 1.67:.2f} kN·m"}

**Required Flexural Strength:**

Mu = wu × L² / 8 = {precomp['Mu_pre']:.2f} kN·m

**DCR = {precomp['Mu_pre']:.2f} / {precomp['phi_Mn_pre']:.2f} = {precomp['DCR_flex_pre']:.3f} {"✓ OK" if precomp['DCR_flex_pre'] <= 1.0 else "✗ NG"}**

### 3.3 Shear Strength (Section G2)

**Nominal Shear Strength:**

Vn = 0.6 × Fy × Aw × Cv1

Aw = d × tw = {sec['d']:.1f} × {sec['tw']:.2f} = {sec['d']*sec['tw']:.0f} mm²

Cv1 = 1.0 (for most rolled W-shapes)

Vn = 0.6 × {Fy} × {sec['d']*sec['tw']:.0f} × 1.0 / 1000 = {0.6 * Fy * sec['d'] * sec['tw'] / 1000:.2f} kN

**Design Shear Strength:**

{"φvVn = 1.0 × " + f"{0.6 * Fy * sec['d'] * sec['tw'] / 1000:.2f} = {0.6 * Fy * sec['d'] * sec['tw'] / 1000:.2f} kN" if method == "LRFD" else "Vn/Ωv = " + f"{0.6 * Fy * sec['d'] * sec['tw'] / 1000:.2f} / 1.50 = {0.6 * Fy * sec['d'] * sec['tw'] / 1000 / 1.50:.2f} kN"}

**Required Shear Strength:**

Vu = wu × L / 2 = {precomp['Vu_pre']:.2f} kN

**DCR = {precomp['Vu_pre']:.2f} / {precomp['phi_Vn_pre']:.2f} = {precomp['DCR_shear_pre']:.3f} {"✓ OK" if precomp['DCR_shear_pre'] <= 1.0 else "✗ NG"}**

### 3.4 Deflection Check

**Deflection Formula:**

δ = 5wL⁴ / (384EIx)

δ = 5 × {w_DL + w_const:.2f} × ({L*1000:.0f})⁴ / (384 × 200000 × {sec['Ix']:.2e})

δ = {precomp['delta_pre']:.2f} mm

**Limit:** L/360 = {L*1000/360:.2f} mm (or L/180 = {L*1000/180:.2f} mm for construction)

**DCR = {precomp['delta_pre']:.2f} / {precomp['delta_limit_pre']:.2f} = {precomp['DCR_defl_pre']:.3f} {"✓ OK" if precomp['DCR_defl_pre'] <= 1.0 else "✗ NG"}**

### 3.5 Construction Stage Summary

| Check | Demand | Capacity | DCR | Status |
|-------|--------|----------|-----|--------|
| Flexure | {precomp['Mu_pre']:.1f} kN·m | {precomp['phi_Mn_pre']:.1f} kN·m | {precomp['DCR_flex_pre']:.3f} | {"✓ OK" if precomp['flex_ok'] else "✗ NG"} |
| Shear | {precomp['Vu_pre']:.1f} kN | {precomp['phi_Vn_pre']:.1f} kN | {precomp['DCR_shear_pre']:.3f} | {"✓ OK" if precomp['shear_ok'] else "✗ NG"} |
| Deflection | {precomp['delta_pre']:.1f} mm | {precomp['delta_limit_pre']:.1f} mm | {precomp['DCR_defl_pre']:.3f} | {"✓ OK" if precomp['defl_ok'] else "✗ NG"} |

"""

    if include_composite and comp is not None:
        report_content += f"""
---

## 4. COMPOSITE BEAM FLEXURAL STRENGTH
**Reference:** AISC 360-16 Section I3.2

### 4.1 Force Components

**Concrete Compression Force (Maximum):**

Cc = 0.85 × f'c × beff × tc

Cc = 0.85 × {fc} × {beff:.0f} × {tc} / 1000 = {comp['Cc']:.1f} kN

**Steel Tension Force (Maximum):**

Ts = Fy × As

Ts = {Fy} × {sec['A']:.0f} / 1000 = {comp['Ts']:.1f} kN

**Shear Connection Capacity:**

ΣQn = n × Qn = {n_studs*2} × {stud_r['Qn']/1000:.2f} = {comp['Qn_total']:.1f} kN

### 4.2 Degree of Composite Action

**Governing Force:**

C = min(Cc, Ts, ΣQn) = min({comp['Cc']:.1f}, {comp['Ts']:.1f}, {comp['Qn_total']:.1f}) = {min(comp['Cc'], comp['Ts'], comp['Qn_total']):.1f} kN

**Composite Ratio:**

{comp['comp_type']}: {comp['comp_ratio']*100:.0f}%

### 4.3 Plastic Neutral Axis Location

**Compression Block Depth:**

a = C / (0.85 × f'c × beff)

a = {min(comp['Cc'], comp['Ts'], comp['Qn_total']):.1f} × 1000 / (0.85 × {fc} × {beff:.0f}) = {min(comp['Cc'], comp['Ts'], comp['Qn_total']) * 1000 / (0.85 * fc * beff):.2f} mm

### 4.4 Nominal Flexural Strength

**Moment Arm:**

d1 = d/2 + tc - a/2

**Nominal Strength:**

Mn = C × d1 = {comp['Mn']:.2f} kN·m

**Design Strength:**

{"φbMn = 0.90 × " + f"{comp['Mn']:.2f} = {comp['phi_Mn']:.2f} kN·m" if method == "LRFD" else "Mn/Ωb = " + f"{comp['Mn']:.2f} / 1.67 = {comp['phi_Mn']:.2f} kN·m"}

**Required Strength:**

Mu = {comp['Mu']:.2f} kN·m

**DCR = {comp['Mu']:.2f} / {comp['phi_Mn']:.2f} = {comp['DCR_flex']:.3f} {"✓ OK" if comp['DCR_flex'] <= 1.0 else "✗ NG"}**

### 4.5 Composite Section Properties

**Transformed Moment of Inertia:**

Itr = {comp['Itr']:.2e} mm⁴

**Effective Moment of Inertia:**

Ieff = Is + √(Qn'/Cf) × (Itr - Is)

Ieff = {comp['Ieff']:.2e} mm⁴

### 4.6 Deflection Checks

**Live Load Deflection:**

δLL = 5 × wLL × L⁴ / (384 × E × Ieff) = {comp['delta_LL']:.2f} mm

Limit: L/360 = {comp['delta_limit_LL']:.2f} mm

DCR = {comp['DCR_defl_LL']:.3f} {"✓ OK" if comp['DCR_defl_LL'] <= 1.0 else "✗ NG"}

**Total Deflection:**

δtotal = δDL + δLL = {comp['delta_total']:.2f} mm

Limit: L/240 = {comp['delta_limit_total']:.2f} mm

DCR = {comp['DCR_defl_total']:.3f} {"✓ OK" if comp['DCR_defl_total'] <= 1.0 else "✗ NG"}

### 4.7 Composite Stage Summary

| Check | Demand | Capacity | DCR | Status |
|-------|--------|----------|-----|--------|
| Flexure | {comp['Mu']:.1f} kN·m | {comp['phi_Mn']:.1f} kN·m | {comp['DCR_flex']:.3f} | {"✓ OK" if comp['DCR_flex']<=1 else "✗ NG"} |
| Shear | {comp['Vu']:.1f} kN | {comp['phi_Vn']:.1f} kN | {comp['DCR_shear']:.3f} | {"✓ OK" if comp['DCR_shear']<=1 else "✗ NG"} |
| δ_LL | {comp['delta_LL']:.1f} mm | {comp['delta_limit_LL']:.1f} mm | {comp['DCR_defl_LL']:.3f} | {"✓ OK" if comp['DCR_defl_LL']<=1 else "✗ NG"} |
| δ_Total | {comp['delta_total']:.1f} mm | {comp['delta_limit_total']:.1f} mm | {comp['DCR_defl_total']:.3f} | {"✓ OK" if comp['DCR_defl_total']<=1 else "✗ NG"} |

"""

    if include_studs and comp is not None:
        report_content += f"""
---

# PART B: SHEAR STUD DESIGN
**Per AISC 360-16 Section I8**

## 5. SHEAR STUD STRENGTH

### 5.1 Stud Properties

| Property | Value |
|----------|-------|
| Stud Diameter | ∅{stud_dia} mm |
| Stud Height | {stud_ht} mm |
| Tensile Strength | Fu = {stud_Fu} MPa |
| Stud Area | Asa = π×{stud_dia}²/4 = {math.pi*stud_dia**2/4:.0f} mm² |

### 5.2 Nominal Stud Strength (Section I8.2a)

**Basic Formula:**

Qn = 0.5 × Asa × √(f'c × Ec) ≤ Rg × Rp × Asa × Fu

**Concrete Term:**

0.5 × Asa × √(f'c × Ec) = 0.5 × {math.pi*stud_dia**2/4:.0f} × √({fc} × {int(4700*math.sqrt(fc))}) = {0.5 * math.pi*stud_dia**2/4 * math.sqrt(fc * 4700*math.sqrt(fc)) / 1000:.2f} kN

**Steel Limit:**

Rg × Rp × Asa × Fu = {Rg:.2f} × {Rp:.2f} × {math.pi*stud_dia**2/4:.0f} × {stud_Fu} / 1000 = {Rg * Rp * math.pi*stud_dia**2/4 * stud_Fu / 1000:.2f} kN

**Governing:**

**Qn = {stud_r['Qn']/1000:.2f} kN/stud**

### 5.3 Reduction Factors

| Factor | Value | Condition |
|--------|-------|-----------|
| Rg (Group) | {Rg:.2f} | {spr} stud(s)/rib |
| Rp (Position) | {Rp:.2f} | Deck ribs {deck} |

### 5.4 Number of Studs Required

**Required Shear Connection:**

V' = min(Cc, Ts) = min({comp['Cc']:.1f}, {comp['Ts']:.1f}) = {min(comp['Cc'], comp['Ts']):.1f} kN

**Number per Half Span:**

n = V' / Qn = {min(comp['Cc'], comp['Ts']):.1f} / {stud_r['Qn']/1000:.2f} = {min(comp['Cc'], comp['Ts']) / (stud_r['Qn']/1000):.1f}

Use: **{n_studs} studs per half span** (Total: {n_studs*2} studs)

### 5.5 Spacing Check

Average Spacing: {L*1000/2/n_studs:.0f} mm

Maximum Allowed: min(8×tc, 914mm) = min({8*tc:.0f}, 914) = {min(8*tc, 914):.0f} mm

Status: {"✓ OK" if L*1000/2/n_studs <= min(8*tc, 914) else "✗ NG"}

"""

    report_content += """
---

## REFERENCES

1. AISC 360-16: Specification for Structural Steel Buildings
2. AISC Design Guide 3: Serviceability Design Considerations  
3. AISC Design Guide 11: Vibrations of Steel-Framed Structural Systems
4. AISI S100-16: North American Specification for Cold-Formed Steel
5. SDI C-2017: Composite Steel Floor Deck-Slabs
6. ACI 318-19: Building Code Requirements for Structural Concrete
7. ASCE 7-22: Minimum Design Loads and Associated Criteria

---

**END OF REPORT**

"""

    # Display report in markdown
    st.markdown(report_content)
    
    # Download buttons
    st.markdown("---")
    st.markdown("### 📥 Export Options")
    
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    
    with col_dl1:
        st.download_button(
            "📄 Download Markdown",
            report_content,
            f"CompositeBeam_Report_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            key="md_download"
        )
    
    with col_dl2:
        # Generate PDF button - only generates when clicked
        if st.button("📕 Generate Academic PDF Report", key="gen_pdf_btn"):
            try:
                from core.comprehensive_report_generator import generate_comprehensive_report, ReportSections
                
                with st.spinner("Generating comprehensive academic-style PDF report..."):
                    # Create section configuration from checkboxes
                    report_sections = ReportSections(
                        include_precomp=include_precomp,
                        include_composite=include_composite,
                        include_studs=include_studs,
                        include_deck=include_deck,
                        include_slab=include_slab,
                        include_vibration=include_vibration,
                        include_diaphragm=include_diaphragm,
                        include_castellated=include_castellated,
                        include_summary=include_summary
                    )
                    
                    # Collect metal deck data if available
                    deck_data = None
                    if include_deck and deck_enabled:
                        deck_data = st.session_state.get('deck_results', None)
                        if deck_data is None:
                            # Provide basic deck info if results not calculated yet
                            deck_data = {
                                'type': 'Composite',
                                'hr': deck_hr,
                                'wr': deck_wr_top,
                                't': deck_t,
                                'Fy': deck_Fy,
                            }
                    
                    # Collect vibration data if available
                    vibration_data = None
                    if include_vibration and vibration_enabled:
                        vibration_data = st.session_state.get('vibration_results', None)
                    
                    # Collect slab data if available
                    slab_data = None
                    if include_slab and slab_enabled:
                        slab_data = {
                            'tc': tc,
                            'tc_above': tc - deck_hr if deck_enabled else tc,
                        }
                    
                    # Collect castellated data if available
                    castellated_data = None
                    if include_castellated and sec_type == "Castellated/Cellular":
                        castellated_data = st.session_state.get('castellated_results', None)
                    
                    # Generate the PDF using the comprehensive report generator
                    pdf_data = generate_comprehensive_report(
                        sec=sec,
                        sec_name=sec_name,
                        grade=grade,
                        Fy=Fy,
                        Fu=Fu,
                        fc=fc,
                        tc=tc,
                        L=L,
                        spacing=spacing,
                        beff=beff,
                        w_DL=w_DL,
                        w_SDL=w_SDL,
                        w_LL=w_LL,
                        w_slab=w_slab,
                        w_const=w_const,
                        precomp=precomp,
                        comp=comp,
                        stud_r=stud_r,
                        stud_dia=stud_dia,
                        stud_ht=stud_ht,
                        stud_Fu=stud_Fu,
                        n_studs=n_studs,
                        Rg=Rg,
                        Rp=Rp,
                        method=method,
                        phi_b=phi_b,
                        phi_v=phi_v,
                        sections=report_sections,
                        deck_data=deck_data,
                        slab_data=slab_data,
                        vibration_data=vibration_data,
                        diaphragm_data=None,
                        castellated_data=castellated_data,
                    )
                    
                    # Count included sections
                    section_count = sum([include_precomp, include_composite, include_studs, 
                                        include_deck, include_slab, include_vibration,
                                        include_diaphragm, include_castellated, include_summary])
                    
                    # Store in session state for download
                    st.session_state['pdf_data'] = pdf_data
                    st.session_state['pdf_ready'] = True
                    st.success(f"✅ Academic PDF Report generated successfully! ({section_count} sections included)")
                    
            except ImportError as e:
                st.error(f"PDF generation requires reportlab: pip install reportlab")
            except Exception as e:
                st.error(f"PDF generation error: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # Show download button only if PDF is ready
        if st.session_state.get('pdf_ready', False):
            st.download_button(
                "⬇️ Download Academic PDF",
                st.session_state['pdf_data'],
                f"CompositeBeam_AcademicReport_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="pdf_download"
            )
    with col_dl3:
        # Text file version
        st.download_button(
            "📝 Download TXT",
            report_content.replace('**', '').replace('#', ''),
            f"CompositeBeam_Report_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="txt_download"
        )


# Footer
st.sidebar.markdown("---")

# OPTIMIZATION SECTION
st.sidebar.markdown("### 🎯 Section Optimizer")
run_optimizer = st.sidebar.checkbox("Enable Auto-Optimization", value=False)

if run_optimizer:
    opt_target = st.sidebar.selectbox("Optimize for:", 
                                       ["Minimum Weight", "Minimum Depth", "Minimum Cost", "Minimum Deflection"])
    opt_max_depth = st.sidebar.number_input("Max Depth (mm, 0=none)", 0, 1000, 0, 50)
    opt_families = st.sidebar.multiselect("Section Families", list(SECTIONS.keys()), default=list(SECTIONS.keys()))
    
    if st.sidebar.button("🔍 Find Optimal Section"):
        with st.spinner("Optimizing..."):
            # Run optimization
            from dataclasses import dataclass
            
            @dataclass
            class OptConstraints:
                span: float
                spacing: float
                max_depth: float
                Fy: float
                fc: float
                tc: float
                DL: float
                SDL: float
                LL: float
                const_LL: float
                method: str
                max_DCR: float = 1.0
                deflection_limit_LL: float = 360
                deflection_limit_total: float = 240
                check_vibration: bool = True
                fn_min: float = 4.0
                ap_max: float = 0.005
                damping: float = 0.03
                min_comp_ratio: float = 0.25
                stud_dia: float = 19
                stud_Fu: float = 450
            
            constraints = OptConstraints(
                span=L,
                spacing=spacing,
                max_depth=opt_max_depth if opt_max_depth > 0 else None,
                Fy=Fy,
                fc=fc,
                tc=tc,
                DL=w_slab/spacing if spacing > 0 else 3.5,
                SDL=w_SDL/spacing if spacing > 0 else 1.0,
                LL=w_LL/spacing if spacing > 0 else 2.4,
                const_LL=w_const/spacing if spacing > 0 else 1.0,
                method=method
            )
            
            E_opt = 200000
            passing_sections = []
            
            for fam_name in opt_families:
                for sec_name, sec_props in SECTIONS[fam_name].items():
                    d = sec_props.get('d', 0)
                    A = sec_props.get('A', 0)
                    Ix = sec_props.get('Ix', 0)
                    Zx = sec_props.get('Zx', 0) or sec_props.get('Sx', 0) * 1.1
                    tw = sec_props.get('tw', 0)
                    wt = sec_props.get('wt', 0) or sec_props.get('weight', 0)
                    
                    if d == 0 or A == 0 or Ix == 0:
                        continue
                    if opt_max_depth > 0 and d > opt_max_depth:
                        continue
                    
                    # Quick check calculations
                    w_beam_opt = wt * 9.81 / 1000
                    w_DL_opt = w_slab + w_beam_opt
                    
                    if method == "LRFD":
                        phi_b_opt = 0.90
                        wu_pre_opt = 1.2 * w_DL_opt + 1.6 * w_const
                        wu_comp_opt = 1.2 * (w_DL_opt + w_SDL) + 1.6 * w_LL
                    else:
                        phi_b_opt = 1/1.67
                        wu_pre_opt = w_DL_opt + w_const
                        wu_comp_opt = w_DL_opt + w_SDL + w_LL
                    
                    L_mm_opt = L * 1000
                    Mu_pre_opt = wu_pre_opt * L**2 / 8
                    Mp_opt = Zx * Fy / 1e6
                    DCR_flex_pre_opt = Mu_pre_opt / (phi_b_opt * Mp_opt) if Mp_opt > 0 else 99
                    
                    delta_LL_opt = 5 * w_LL * L_mm_opt**4 / (384 * E_opt * Ix)
                    DCR_defl_opt = delta_LL_opt / (L_mm_opt / 360)
                    
                    # Vibration quick check
                    w_floor_opt = (w_slab/spacing + w_SDL/spacing) * spacing if spacing > 0 else 4.5
                    fn_opt = (math.pi / (2 * L_mm_opt**2)) * math.sqrt(E_opt * Ix * 9810 / w_floor_opt) if w_floor_opt > 0 else 0
                    
                    if DCR_flex_pre_opt <= 1.0 and DCR_defl_opt <= 1.0 and fn_opt >= 3.5:
                        cost_opt = wt * L  # Simple cost index
                        passing_sections.append({
                            'name': sec_name,
                            'family': fam_name,
                            'weight': wt,
                            'depth': d,
                            'DCR_flex': DCR_flex_pre_opt,
                            'DCR_defl': DCR_defl_opt,
                            'fn': fn_opt,
                            'cost': cost_opt
                        })
            
            # Sort by target
            if passing_sections:
                if "Weight" in opt_target:
                    passing_sections.sort(key=lambda x: x['weight'])
                elif "Depth" in opt_target:
                    passing_sections.sort(key=lambda x: x['depth'])
                elif "Cost" in opt_target:
                    passing_sections.sort(key=lambda x: x['cost'])
                elif "Deflection" in opt_target:
                    passing_sections.sort(key=lambda x: x['DCR_defl'])
                
                st.sidebar.success(f"✅ Found {len(passing_sections)} options")
                st.sidebar.markdown("**Top 5 Sections:**")
                for i, s in enumerate(passing_sections[:5], 1):
                    st.sidebar.write(f"{i}. **{s['name']}** ({s['weight']} kg/m, d={s['depth']}mm)")
                
                best = passing_sections[0]
                st.sidebar.info(f"**Optimal: {best['name']}**\n"
                               f"Weight: {best['weight']} kg/m\n"
                               f"DCR: {best['DCR_flex']:.2f}")
            else:
                st.sidebar.error("❌ No sections meet criteria. Relax constraints.")

st.sidebar.caption(f"v3.0 | {total_sections} sections | AISC 360-16 + DG31 + AISI S100-16 + ACI 318-19 + SDI DDM04")
