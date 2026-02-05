"""
Professional Tab Implementations for CompositeBeam Pro v2.9
Uses matplotlib for diagrams and st.latex() for equations
"""

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math


def draw_beam_diagram(ax, L, w, P_locations=None, title="Loading Diagram"):
    """Draw a professional beam loading diagram"""
    ax.clear()
    
    # Draw beam
    ax.plot([0, L], [0, 0], 'k-', linewidth=4)
    
    # Draw supports (triangles)
    support_size = L * 0.03
    triangle_left = plt.Polygon([[0, 0], [-support_size, -support_size*1.5], 
                                  [support_size, -support_size*1.5]], color='gray')
    triangle_right = plt.Polygon([[L, 0], [L-support_size, -support_size*1.5], 
                                   [L+support_size, -support_size*1.5]], color='gray')
    ax.add_patch(triangle_left)
    ax.add_patch(triangle_right)
    
    # Draw distributed load arrows
    n_arrows = 15
    arrow_spacing = L / n_arrows
    arrow_height = L * 0.08
    for i in range(n_arrows + 1):
        x = i * arrow_spacing
        ax.annotate('', xy=(x, 0), xytext=(x, arrow_height),
                   arrowprops=dict(arrowstyle='->', color='blue', lw=1))
    
    # Draw load line
    ax.plot([0, L], [arrow_height, arrow_height], 'b-', linewidth=2)
    ax.text(L/2, arrow_height * 1.3, f'w = {w:.2f} kN/m', ha='center', fontsize=11, color='blue')
    
    # Draw concentrated loads if provided
    if P_locations:
        for x, P in P_locations:
            ax.annotate('', xy=(x, 0), xytext=(x, arrow_height * 1.8),
                       arrowprops=dict(arrowstyle='->', color='red', lw=2))
            ax.text(x, arrow_height * 2, f'P={P:.1f}kN', ha='center', fontsize=10, color='red')
    
    # Span dimension
    ax.annotate('', xy=(L, -L*0.08), xytext=(0, -L*0.08),
               arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax.text(L/2, -L*0.12, f'L = {L:.0f} mm', ha='center', fontsize=11, color='green')
    
    ax.set_xlim(-L*0.1, L*1.1)
    ax.set_ylim(-L*0.15, arrow_height * 2.5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=12, fontweight='bold')
    
    return ax


def draw_stress_distribution(ax, d, a, Fy, fc, pna_in_concrete=True, title="Stress Distribution"):
    """Draw plastic stress distribution diagram"""
    ax.clear()
    
    width = d * 0.8
    
    if pna_in_concrete:
        # Compression in concrete (top)
        rect_comp = patches.Rectangle((0, d-a), width, a, 
                                       facecolor='lightcoral', edgecolor='red', linewidth=2)
        ax.add_patch(rect_comp)
        ax.text(width/2, d-a/2, f'0.85f\'c\n={0.85*fc:.1f} MPa', ha='center', va='center', fontsize=9)
        
        # Tension in steel (below)
        rect_tens = patches.Rectangle((width*0.3, 0), width*0.4, d-a,
                                       facecolor='lightblue', edgecolor='blue', linewidth=2)
        ax.add_patch(rect_tens)
        ax.text(width/2, (d-a)/2, f'Fy\n={Fy:.0f} MPa', ha='center', va='center', fontsize=9)
        
        # PNA line
        ax.plot([0, width], [d-a, d-a], 'k--', linewidth=2)
        ax.text(width*1.05, d-a, 'PNA', fontsize=10, va='center')
    else:
        # PNA in steel
        # Full slab compression
        rect_slab = patches.Rectangle((0, d*0.8), width, d*0.2,
                                       facecolor='lightcoral', edgecolor='red', linewidth=2)
        ax.add_patch(rect_slab)
        
        # Steel compression
        rect_steel_comp = patches.Rectangle((width*0.3, d*0.5), width*0.4, d*0.3,
                                            facecolor='lightyellow', edgecolor='orange', linewidth=2)
        ax.add_patch(rect_steel_comp)
        
        # Steel tension
        rect_steel_tens = patches.Rectangle((width*0.3, 0), width*0.4, d*0.5,
                                            facecolor='lightblue', edgecolor='blue', linewidth=2)
        ax.add_patch(rect_steel_tens)
        
        # PNA line
        ax.plot([0, width], [d*0.5, d*0.5], 'k--', linewidth=2)
        ax.text(width*1.05, d*0.5, 'PNA', fontsize=10, va='center')
    
    # Dimension
    ax.annotate('', xy=(width*1.15, d), xytext=(width*1.15, 0),
               arrowprops=dict(arrowstyle='<->', color='black', lw=1))
    ax.text(width*1.25, d/2, f'd={d:.0f}', fontsize=10, va='center')
    
    ax.set_xlim(-width*0.1, width*1.4)
    ax.set_ylim(-d*0.1, d*1.1)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=12, fontweight='bold')
    
    return ax


def draw_deflection_curve(ax, L, delta_max, title="Deflected Shape"):
    """Draw deflection curve"""
    ax.clear()
    
    x = np.linspace(0, L, 100)
    # Parabolic deflection shape for uniform load
    y = -delta_max * 16 * x * (L - x) / L**2 * (1 - 4*(x/L - 0.5)**2)
    
    # Original position
    ax.plot([0, L], [0, 0], 'k--', alpha=0.5, linewidth=1, label='Original')
    
    # Deflected shape (exaggerated)
    scale = max(L / (delta_max * 20), 1) if delta_max > 0 else 1
    ax.plot(x, y * scale, 'b-', linewidth=2, label='Deflected')
    ax.fill_between(x, 0, y * scale, alpha=0.2, color='blue')
    
    # Supports
    ax.plot([0], [0], 'k^', markersize=12)
    ax.plot([L], [0], 'k^', markersize=12)
    
    # Max deflection annotation
    ax.annotate(f'δmax = {delta_max:.2f} mm', 
               xy=(L/2, min(y) * scale),
               xytext=(L/2, min(y) * scale * 1.5),
               ha='center', fontsize=10,
               arrowprops=dict(arrowstyle='->', color='red'))
    
    ax.set_xlim(-L*0.05, L*1.05)
    ax.set_xlabel('Span (mm)', fontsize=10)
    ax.set_ylabel('Deflection (scaled)', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    return ax


def draw_w_section(ax, d, bf, tf, tw, title="W-Section"):
    """Draw W-section cross-section"""
    ax.clear()
    
    # Draw flanges and web
    # Top flange
    ax.fill([0, bf, bf, 0, 0], [d, d, d-tf, d-tf, d], 
            color='steelblue', edgecolor='black', linewidth=2)
    
    # Bottom flange
    ax.fill([0, bf, bf, 0, 0], [0, 0, tf, tf, 0], 
            color='steelblue', edgecolor='black', linewidth=2)
    
    # Web
    ax.fill([(bf-tw)/2, (bf+tw)/2, (bf+tw)/2, (bf-tw)/2, (bf-tw)/2],
            [tf, tf, d-tf, d-tf, tf],
            color='steelblue', edgecolor='black', linewidth=2)
    
    # Dimensions
    # d
    ax.annotate('', xy=(bf*1.1, d), xytext=(bf*1.1, 0),
               arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax.text(bf*1.15, d/2, f'd={d:.0f}', fontsize=9, color='red', va='center')
    
    # bf
    ax.annotate('', xy=(bf, -d*0.08), xytext=(0, -d*0.08),
               arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax.text(bf/2, -d*0.15, f'bf={bf:.0f}', fontsize=9, color='green', ha='center')
    
    # tf
    ax.annotate('', xy=(-bf*0.05, d), xytext=(-bf*0.05, d-tf),
               arrowprops=dict(arrowstyle='<->', color='blue', lw=1))
    ax.text(-bf*0.15, d-tf/2, f'tf={tf:.1f}', fontsize=8, color='blue', va='center')
    
    # tw
    ax.annotate('', xy=((bf+tw)/2, d/2), xytext=((bf-tw)/2, d/2),
               arrowprops=dict(arrowstyle='<->', color='purple', lw=1))
    ax.text(bf/2, d/2+d*0.05, f'tw={tw:.1f}', fontsize=8, color='purple', ha='center')
    
    ax.set_xlim(-bf*0.3, bf*1.3)
    ax.set_ylim(-d*0.2, d*1.1)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=12, fontweight='bold')
    
    return ax


def draw_composite_section(ax, d, bf, tf, tc, hr, beff, title="Composite Section"):
    """Draw composite beam section"""
    ax.clear()
    
    # Scale for display
    total_height = d + tc
    
    # Draw slab
    slab_left = (bf - beff) / 2
    ax.fill([slab_left, slab_left + beff, slab_left + beff, slab_left, slab_left],
            [d, d, d + tc, d + tc, d],
            color='lightgray', edgecolor='black', linewidth=2, hatch='///')
    
    # Draw deck ribs (simplified)
    n_ribs = 3
    rib_width = beff / (n_ribs * 2)
    for i in range(n_ribs):
        rib_x = slab_left + rib_width + i * 2 * rib_width
        ax.fill([rib_x, rib_x + rib_width, rib_x + rib_width, rib_x, rib_x],
                [d, d, d - hr, d - hr, d],
                color='lightgray', edgecolor='gray', linewidth=1)
    
    # Draw steel section
    # Top flange
    ax.fill([0, bf, bf, 0, 0], 
            [d-tf, d-tf, d, d, d-tf],
            color='steelblue', edgecolor='black', linewidth=2)
    
    # Bottom flange
    ax.fill([0, bf, bf, 0, 0], 
            [0, 0, tf, tf, 0],
            color='steelblue', edgecolor='black', linewidth=2)
    
    # Web
    tw = bf * 0.1  # Approximate
    ax.fill([(bf-tw)/2, (bf+tw)/2, (bf+tw)/2, (bf-tw)/2, (bf-tw)/2],
            [tf, tf, d-tf, d-tf, tf],
            color='steelblue', edgecolor='black', linewidth=2)
    
    # Dimensions
    # Total height
    ax.annotate('', xy=(slab_left + beff + 20, d + tc), xytext=(slab_left + beff + 20, 0),
               arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax.text(slab_left + beff + 30, (d + tc)/2, f'Total\n{d+tc:.0f}', fontsize=8, color='red', va='center')
    
    # beff
    ax.annotate('', xy=(slab_left + beff, d + tc + 10), xytext=(slab_left, d + tc + 10),
               arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax.text(bf/2, d + tc + 20, f'beff={beff:.0f}', fontsize=9, color='green', ha='center')
    
    ax.set_xlim(slab_left - 50, slab_left + beff + 80)
    ax.set_ylim(-20, d + tc + 40)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=12, fontweight='bold')
    
    return ax


def draw_deck_profile(ax, hr, wr_top, wr_bot, pitch, t, title="Deck Profile"):
    """Draw metal deck cross-section profile"""
    ax.clear()
    
    # Draw 2 complete ribs
    for n in range(2):
        x_offset = n * pitch
        
        # Draw deck profile
        x_coords = [
            x_offset,                          # Start at flat
            x_offset + (pitch - wr_top) / 2,   # Start of rib slope
            x_offset + (pitch - wr_bot) / 2,   # Bottom of rib
            x_offset + (pitch + wr_bot) / 2,   # Other side of rib bottom
            x_offset + (pitch + wr_top) / 2,   # End of rib slope
            x_offset + pitch                   # End at flat
        ]
        y_coords = [hr, hr, 0, 0, hr, hr]
        
        ax.fill(x_coords, y_coords, color='steelblue', alpha=0.4, edgecolor='steelblue', linewidth=2)
        ax.plot(x_coords, y_coords, 'steelblue', linewidth=2)
    
    # Dimensions
    # Pitch
    ax.annotate('', xy=(pitch, hr + 5), xytext=(0, hr + 5),
               arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax.text(pitch/2, hr + 12, f'pitch = {pitch:.0f} mm', ha='center', fontsize=10, color='red')
    
    # hr
    ax.annotate('', xy=(2*pitch + 10, hr), xytext=(2*pitch + 10, 0),
               arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
    ax.text(2*pitch + 20, hr/2, f'hr = {hr:.0f} mm', fontsize=10, color='green', va='center')
    
    # wr_top
    x_mid = pitch / 2
    ax.annotate('', xy=(x_mid + wr_top/2, hr), xytext=(x_mid - wr_top/2, hr),
               arrowprops=dict(arrowstyle='<->', color='purple', lw=1))
    ax.text(x_mid, hr - 5, f'wr_top={wr_top:.0f}', fontsize=8, color='purple', ha='center', va='top')
    
    ax.set_xlim(-20, 2*pitch + 60)
    ax.set_ylim(-15, hr + 25)
    ax.set_aspect('equal')
    ax.set_xlabel('Width (mm)', fontsize=10)
    ax.set_ylabel('Height (mm)', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    return ax


def create_summary_table(checks_dict):
    """Create a summary table from check results"""
    return {
        "Check": list(checks_dict.keys()),
        "Demand": [f"{v['demand']:.3f} {v.get('unit', '')}" for v in checks_dict.values()],
        "Capacity": [f"{v['capacity']:.3f} {v.get('unit', '')}" for v in checks_dict.values()],
        "DCR": [f"{v['dcr']:.3f}" for v in checks_dict.values()],
        "Status": ["✅ PASS" if v['dcr'] <= 1.0 else "❌ FAIL" for v in checks_dict.values()]
    }
