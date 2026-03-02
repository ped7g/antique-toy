#!/usr/bin/env python3
"""
ch16_sprite_masking.py -- AND/OR sprite masking diagram.

Shows the three stages of masked sprite rendering:
1. Background (checkered pattern)
2. AND mask clears pixels (mask applied)
3. OR stamps the graphic (final result)

Before/after comparison on a checkered background.

Output: illustrations/output/ch16_sprite_masking.png
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

# Grid size (8x8 pixel sprite)
GRID = 8
CELL = 0.35

# --- Pixel data ---
# Checkered background pattern
bg = np.zeros((GRID, GRID), dtype=int)
for r in range(GRID):
    for c in range(GRID):
        bg[r, c] = (r + c) % 2  # 1 = filled, 0 = empty

# Sprite graphic: simple arrow shape
sprite = np.array([
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
])

# Mask: 0 where sprite exists (AND clears those bits), 1 elsewhere
mask = 1 - sprite

# Step 1: bg AND mask → clears sprite area
after_and = bg & mask

# Step 2: (bg AND mask) OR sprite → stamps sprite
result = after_and | sprite

# --- Colour maps ---
def get_color_bg(val):
    return '#4488CC' if val else '#BBDDEE'

def get_color_mask(val):
    return '#222222' if val == 0 else '#EEEEEE'

def get_color_sprite(val):
    return ZX_RED if val else '#FFFFFF'

def get_color_result(val, is_sprite):
    if is_sprite:
        return ZX_RED
    return '#4488CC' if val else '#BBDDEE'

# --- Figure ---
fig, axes = plt.subplots(1, 5, figsize=(7, 2.8))
fig.patch.set_facecolor('white')

panels = [
    ('Background', bg, lambda r, c: get_color_bg(bg[r, c])),
    ('AND Mask', mask, lambda r, c: get_color_mask(mask[r, c])),
    ('After AND', after_and, lambda r, c: get_color_bg(after_and[r, c]) if mask[r, c] else '#FFFFFF'),
    ('Sprite', sprite, lambda r, c: get_color_sprite(sprite[r, c])),
    ('After OR', result, lambda r, c: get_color_result(result[r, c], sprite[r, c])),
]

for idx, (title, data, color_fn) in enumerate(panels):
    ax = axes[idx]
    ax.set_facecolor('white')
    ax.axis('off')

    x_off = 0.1
    y_off = 0.1

    for r in range(GRID):
        for c in range(GRID):
            x = x_off + c * CELL
            y = y_off + (GRID - 1 - r) * CELL  # flip y

            fc = color_fn(r, c)
            rect = plt.Rectangle((x, y), CELL - 0.02, CELL - 0.02,
                                  facecolor=fc, edgecolor='#AAAAAA',
                                  linewidth=0.4)
            ax.add_patch(rect)

    ax.set_xlim(-0.05, x_off + GRID * CELL + 0.1)
    ax.set_ylim(-0.3, y_off + GRID * CELL + 0.3)
    ax.set_aspect('equal')

    ax.text(x_off + GRID * CELL / 2, y_off + GRID * CELL + 0.15, title,
            ha='center', va='bottom', fontsize=9, fontweight='bold',
            fontfamily='sans-serif', color='#333333')

# Draw operation labels between panels
for idx, label in enumerate(['AND', '=', 'OR', '=']):
    x_mid = (axes[idx].get_position().x1 + axes[idx + 1].get_position().x0) / 2
    fig.text(x_mid, 0.45, label,
             ha='center', va='center', fontsize=11, fontweight='bold',
             fontfamily='monospace', color='#666666')

# Title
fig.text(0.5, 0.97, 'Masked Sprite Rendering: AND Clears, OR Stamps',
         ha='center', va='top', fontsize=13, fontweight='bold',
         fontfamily='sans-serif', color='#1a1a1a')

# Caption
fig.text(0.5, 0.02, 'Mask has 0s where sprite pixels go (AND clears them), '
         '1s elsewhere (AND preserves background)',
         ha='center', va='bottom', fontsize=7.5, fontfamily='sans-serif',
         color='#888888', style='italic')

plt.tight_layout(rect=[0, 0.06, 1, 0.93])
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch16_sprite_masking.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch16_sprite_masking.png')
