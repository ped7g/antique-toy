#!/usr/bin/env python3
"""
ch18_state_machine.py -- Game state machine diagram.

State diagram: Title -> Menu -> Game <-> Pause -> GameOver -> Title.
Transition labels on arrows. Boxes coloured by state type.

Output: illustrations/output/ch18_state_machine.png
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
ZX_YELLOW  = '#D7D700'

# --- State definitions ---
# (name, x, y, colour, description)
states = [
    ('Title',     1.0, 3.0, '#666666',  'animate logo\nwait for key'),
    ('Menu',      3.0, 3.0, ZX_CYAN,    'highlight options\nread input'),
    ('Game',      5.0, 3.0, ZX_GREEN,   'main game loop\n50 Hz update'),
    ('Pause',     5.0, 1.2, ZX_YELLOW,  'freeze state\nwait for key'),
    ('Game Over', 3.0, 1.2, ZX_RED,     'show score\nwait for key'),
]

# Transitions: (from_idx, to_idx, label, curvature)
transitions = [
    (0, 1, 'START',      0.0),     # Title -> Menu
    (1, 2, 'PLAY',       0.0),     # Menu -> Game
    (2, 3, 'PAUSE',      0.0),     # Game -> Pause
    (3, 2, 'RESUME',     0.0),     # Pause -> Game (return)
    (2, 4, 'DEATH',     -0.3),     # Game -> GameOver
    (4, 0, 'RESTART',   -0.2),     # GameOver -> Title
    (4, 1, 'MENU',       0.0),     # GameOver -> Menu
]

# --- Figure ---
fig, ax = plt.subplots(figsize=(7, 4.5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
ax.axis('off')

box_w = 1.4
box_h = 0.9

# Draw states
for name, x, y, col, desc in states:
    rect = mpatches.FancyBboxPatch(
        (x - box_w / 2, y - box_h / 2), box_w, box_h,
        boxstyle='round,pad=0.10',
        facecolor=col, alpha=0.15,
        edgecolor=col, linewidth=2.5
    )
    ax.add_patch(rect)

    ax.text(x, y + 0.15, name,
            ha='center', va='center', fontsize=12, fontweight='bold',
            fontfamily='sans-serif',
            color=col if col != '#666666' else '#333333')

    ax.text(x, y - 0.18, desc,
            ha='center', va='center', fontsize=6.5, fontfamily='sans-serif',
            color='#666666', linespacing=1.2)

# Draw transitions
for from_idx, to_idx, label, curve in transitions:
    x1, y1 = states[from_idx][1], states[from_idx][2]
    x2, y2 = states[to_idx][1], states[to_idx][2]

    dx = x2 - x1
    dy = y2 - y1
    length = np.sqrt(dx**2 + dy**2)
    nx, ny = dx / length, dy / length

    # Shrink to box edges
    shrink_start = 0.75
    shrink_end = 0.75

    ax1_x = x1 + nx * shrink_start
    ax1_y = y1 + ny * shrink_start
    ax2_x = x2 - nx * shrink_end
    ax2_y = y2 - ny * shrink_end

    # Special handling for Game<->Pause (vertical, side by side)
    if from_idx == 2 and to_idx == 3:  # Game -> Pause (right side)
        ax1_x = x1 + 0.25
        ax1_y = y1 - box_h / 2
        ax2_x = x2 + 0.25
        ax2_y = y2 + box_h / 2
        rad = 0.3
    elif from_idx == 3 and to_idx == 2:  # Pause -> Game (left side)
        ax1_x = x1 - 0.25
        ax1_y = y1 + box_h / 2
        ax2_x = x2 - 0.25
        ax2_y = y2 - box_h / 2
        rad = 0.3
    else:
        rad = curve

    conn_style = f'arc3,rad={rad}' if rad != 0 else 'arc3,rad=0'

    ax.annotate('', xy=(ax2_x, ax2_y), xytext=(ax1_x, ax1_y),
                arrowprops=dict(
                    arrowstyle='->', color='#555555', lw=1.8,
                    connectionstyle=conn_style,
                    shrinkA=3, shrinkB=3
                ))

    # Label placement
    mid_x = (ax1_x + ax2_x) / 2
    mid_y = (ax1_y + ax2_y) / 2

    # Offset label perpendicular to arrow direction
    perp_x, perp_y = -ny, nx
    offset = 0.18
    if rad < 0:
        offset = -0.22
    elif from_idx == 2 and to_idx == 3:
        mid_x = x1 + 0.55
        mid_y = (y1 + y2) / 2
        offset = 0
    elif from_idx == 3 and to_idx == 2:
        mid_x = x1 - 0.55
        mid_y = (y1 + y2) / 2
        offset = 0

    lbl_x = mid_x + perp_x * offset
    lbl_y = mid_y + perp_y * offset

    ax.text(lbl_x, lbl_y, label,
            ha='center', va='center', fontsize=7, fontfamily='monospace',
            fontweight='bold', color='#888888',
            bbox=dict(boxstyle='round,pad=0.12', facecolor='white',
                      edgecolor='#DDDDDD', linewidth=0.5, alpha=0.9))

# Title
ax.text(3.0, 4.1, 'Game State Machine',
        ha='center', va='center', fontsize=14, fontweight='bold',
        fontfamily='sans-serif', color='#1a1a1a')

ax.text(3.0, 3.8, 'Each state runs its own loop — transitions via jump table',
        ha='center', va='center', fontsize=8, fontfamily='sans-serif',
        color='#888888', style='italic')

ax.set_xlim(-0.2, 6.5)
ax.set_ylim(0.3, 4.4)

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch18_state_machine.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch18_state_machine.png')
