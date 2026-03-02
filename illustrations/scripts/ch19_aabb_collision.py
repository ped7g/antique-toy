#!/usr/bin/env python3
"""
ch19_aabb_collision.py -- AABB collision detection diagram.

Two panels side by side:
  Left:  Overlapping bounding boxes (collision detected)
  Right: Separated bounding boxes (no collision)
Axis projections labeled to show overlap test.

Output: illustrations/output/ch19_aabb_collision.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# --- ZX Spectrum palette ---
ZX_BLUE    = '#0000D7'
ZX_RED     = '#D70000'
ZX_GREEN   = '#00D700'
ZX_CYAN    = '#00D7D7'
ZX_MAGENTA = '#D700D7'

# --- Figure ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 3.8))
fig.patch.set_facecolor('white')

def draw_aabb_scene(ax, box_a, box_b, title, colliding):
    """Draw two AABB boxes with axis projections.

    box = (left, bottom, width, height)
    """
    ax.set_facecolor('white')

    a_l, a_b, a_w, a_h = box_a
    b_l, b_b, b_w, b_h = box_b

    a_r = a_l + a_w
    a_t = a_b + a_h
    b_r = b_l + b_w
    b_t = b_b + b_h

    # Draw boxes
    rect_a = mpatches.FancyBboxPatch(
        (a_l, a_b), a_w, a_h,
        boxstyle='round,pad=0.02',
        facecolor=ZX_BLUE, alpha=0.20,
        edgecolor=ZX_BLUE, linewidth=2.0
    )
    ax.add_patch(rect_a)

    rect_b = mpatches.FancyBboxPatch(
        (b_l, b_b), b_w, b_h,
        boxstyle='round,pad=0.02',
        facecolor=ZX_RED, alpha=0.20,
        edgecolor=ZX_RED, linewidth=2.0
    )
    ax.add_patch(rect_b)

    # Labels
    ax.text(a_l + a_w / 2, a_b + a_h / 2, 'A',
            ha='center', va='center', fontsize=16, fontweight='bold',
            fontfamily='sans-serif', color=ZX_BLUE, alpha=0.6)
    ax.text(b_l + b_w / 2, b_b + b_h / 2, 'B',
            ha='center', va='center', fontsize=16, fontweight='bold',
            fontfamily='sans-serif', color=ZX_RED, alpha=0.6)

    # X-axis projections (below boxes)
    proj_y = -0.3
    bar_h = 0.12

    # A's X projection
    ax.add_patch(plt.Rectangle((a_l, proj_y), a_w, bar_h,
                                facecolor=ZX_BLUE, alpha=0.35, edgecolor='none'))
    # B's X projection
    ax.add_patch(plt.Rectangle((b_l, proj_y - bar_h - 0.04), b_w, bar_h,
                                facecolor=ZX_RED, alpha=0.35, edgecolor='none'))

    # Y-axis projections (left of boxes)
    proj_x = -0.3
    bar_w = 0.12

    # A's Y projection
    ax.add_patch(plt.Rectangle((proj_x, a_b), bar_w, a_h,
                                facecolor=ZX_BLUE, alpha=0.35, edgecolor='none'))
    # B's Y projection
    ax.add_patch(plt.Rectangle((proj_x - bar_w - 0.04, b_b), bar_w, b_h,
                                facecolor=ZX_RED, alpha=0.35, edgecolor='none'))

    # Overlap region highlight
    if colliding:
        ol = max(a_l, b_l)
        or_ = min(a_r, b_r)
        ob = max(a_b, b_b)
        ot = min(a_t, b_t)
        if ol < or_ and ob < ot:
            overlap = plt.Rectangle((ol, ob), or_ - ol, ot - ob,
                                     facecolor=ZX_MAGENTA, alpha=0.25,
                                     edgecolor=ZX_MAGENTA, linewidth=1.5,
                                     linestyle='--')
            ax.add_patch(overlap)

        # X overlap bracket
        ax.annotate('', xy=(or_, proj_y + bar_h + 0.06),
                    xytext=(ol, proj_y + bar_h + 0.06),
                    arrowprops=dict(arrowstyle='<->', color=ZX_MAGENTA, lw=1.5))
        ax.text((ol + or_) / 2, proj_y + bar_h + 0.15, 'X overlap',
                ha='center', va='bottom', fontsize=6.5, fontfamily='sans-serif',
                color=ZX_MAGENTA, fontweight='bold')

    # Result label
    if colliding:
        result_text = 'COLLISION'
        result_color = ZX_RED
    else:
        result_text = 'NO COLLISION'
        result_color = ZX_GREEN

    ax.text(0.5, 1.05, title, transform=ax.transAxes,
            ha='center', va='bottom', fontsize=11, fontweight='bold',
            fontfamily='sans-serif', color='#333333')

    ax.text(0.5, -0.18, result_text, transform=ax.transAxes,
            ha='center', va='top', fontsize=10, fontweight='bold',
            fontfamily='monospace', color=result_color,
            bbox=dict(boxstyle='round,pad=0.2', facecolor=result_color,
                      alpha=0.12, edgecolor=result_color, linewidth=1.0))

    # Axis labels
    ax.text(0.5, -0.08, 'X axis →', transform=ax.transAxes,
            ha='center', va='top', fontsize=7, fontfamily='sans-serif',
            color='#AAAAAA')
    ax.text(-0.08, 0.5, 'Y axis →', transform=ax.transAxes,
            ha='center', va='center', fontsize=7, fontfamily='sans-serif',
            color='#AAAAAA', rotation=90)

    ax.set_xlim(-0.8, 5.0)
    ax.set_ylim(-0.9, 4.5)
    ax.set_aspect('equal')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])


# Panel 1: Overlapping boxes
draw_aabb_scene(ax1,
    box_a=(0.5, 1.0, 2.5, 2.0),
    box_b=(2.0, 1.5, 2.0, 2.5),
    title='Overlapping',
    colliding=True)

# Panel 2: Separated boxes
draw_aabb_scene(ax2,
    box_a=(0.3, 1.5, 1.8, 1.5),
    box_b=(3.0, 1.0, 1.5, 2.0),
    title='Separated',
    colliding=False)

# Overall title
fig.text(0.5, 0.98, 'AABB Collision Detection — Axis Projections',
         ha='center', va='top', fontsize=13, fontweight='bold',
         fontfamily='sans-serif', color='#1a1a1a')

# Explanation
fig.text(0.5, 0.01,
         'Two boxes collide iff their projections overlap on BOTH axes. '
         'One axis with no overlap → early exit.',
         ha='center', va='bottom', fontsize=7.5, fontfamily='sans-serif',
         color='#888888', style='italic')

plt.tight_layout(rect=[0, 0.04, 1, 0.94])
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch19_aabb_collision.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch19_aabb_collision.png')
