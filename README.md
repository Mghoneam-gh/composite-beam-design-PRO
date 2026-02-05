# CompositeBeam Pro v2.1

Professional Composite Floor Beam Design per AISC 360-16 / AISI S100-16

## What's New in v2.1 (Phase 2 Complete)

### Metal Deck Module
- **DXF Parser**: Import custom deck profiles from DXF files (1m strip)
- **Effective Width**: AISI S100-16 effective width method for cold-formed steel
- **Deck Design Checks**: Comprehensive design per AISI S100-16 and SDI C-2017
  - Flexural strength (positive and negative moment)
  - Shear strength
  - Web crippling (EOF, IOF, ETF, ITF)
  - Combined bending and web crippling
  - Deflection limits

### Phase 3 Features (from v2.0)
- **Section Optimizer**: Auto-select optimal sections by weight, depth, cost, or deflection
- **Enhanced Reports**: Professional calculation reports with equations
- **Vibration Check**: Complete AISC DG11 walking excitation analysis
- **202 Section Database**: AISC W-shapes, HEA, HEB, IPE, British UB/UC

## Design Standards

| Module | Standards |
|--------|-----------|
| Composite Beam | AISC 360-16 Chapter I |
| Steel Beam | AISC 360-16 Chapters B, E, F, G |
| Metal Deck | AISI S100-16, SDI C-2017 |
| Shear Studs | AISC 360-16 Section I8 |
| Vibration | AISC Design Guide 11 |
| Deflection | AISC Design Guide 3 |

## Installation

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## Project Structure

```
CompositeBeamPro_v2/
├── app/
│   └── streamlit_app.py     # Main application
├── core/
│   ├── utils/               # Phase 2
│   │   ├── dxf_parser.py    # DXF profile import
│   │   └── effective_width.py # AISI S100-16
│   ├── design/              # Phase 2
│   │   └── metal_deck.py    # Deck design checks
│   ├── optimizer.py         # Phase 3
│   └── report_generator_v2.py # Phase 3
└── requirements.txt
```

## Phase 2 Module Usage

### DXF Parser
```python
from core.utils.dxf_parser import parse_deck_dxf, calculate_gross_properties

# Parse DXF file
result = parse_deck_dxf("deck_profile.dxf")
if result.is_valid:
    print(f"Rib height: {result.hr} mm")
    print(f"Strip width: {result.strip_width} mm")

# Calculate gross properties
props = calculate_gross_properties(result, thickness=0.9)
print(f"Ag = {props.Ag} mm²/m")
print(f"Ig = {props.Ig} mm⁴/m")
```

### Effective Width (AISI S100-16)
```python
from core.utils.effective_width import (
    effective_width_stiffened,
    effective_width_web_stress_gradient
)

# Stiffened compression element
result = effective_width_stiffened(w=100, t=1.0, f=345, E=200000)
print(f"be = {result.be} mm (ρ = {result.rho})")

# Web with stress gradient
web = effective_width_web_stress_gradient(h=150, t=1.0, f1=345, f2=-200)
print(f"be1 = {web.be1} mm, be2 = {web.be2} mm")
```

### Metal Deck Design Checks
```python
from core.design.metal_deck import (
    DeckGeometry, DeckMaterial, DeckSectionProperties,
    design_metal_deck, DesignMethod, generate_design_summary
)

# Define geometry
geometry = DeckGeometry(
    hr=50.8,      # Rib height (mm)
    wr_top=114,   # Top opening (mm)
    wr_bot=38,    # Bottom width (mm)
    pitch=152.4,  # Rib pitch (mm)
    t=0.9,        # Thickness (mm)
    theta=80      # Web angle (degrees)
)

# Run all design checks
results = design_metal_deck(
    geometry=geometry,
    properties=properties,
    material=DeckMaterial(Fy=230),
    span=2400,
    w_construction=2.5,
    method=DesignMethod.LRFD
)

# Print summary
print(generate_design_summary(results))
```

## Key Equations Reference

### AISI S100-16 Effective Width
```
λ = (1.052/√k) × (w/t) × √(f/E)     [Eq. 1.1-2]
ρ = (1 - 0.22/λ) / λ  for λ > 0.673  [Eq. 1.1-1]
be = ρ × w                           [Eq. 1.1-3]
```

### AISI S100-16 Flexural Strength
```
Mn = Se × Fy                         [Eq. F3.1-1]
φb = 0.90 (LRFD)
Ωb = 1.67 (ASD)
```

### AISI S100-16 Web Crippling
```
Pn = C×t²×Fy×sin(θ)×[1-CR√(R/t)]×[1+CN√(N/t)]×[1-Ch√(h/t)]  [Eq. G5-1]
```

## Development Roadmap

- [x] Phase 1: Foundation (Pydantic models, section database)
- [x] Phase 2: Metal Deck Module (DXF, effective width, design checks)
- [x] Phase 3: Optimization + Reports
- [ ] Phase 4: Composite Slab (ACI 318-19)
- [ ] Phase 5: Diaphragm Design (SDI DDM04)

## Authors

CompositeBeam Pro - Structural Engineering Software

## License

For internal company use.
