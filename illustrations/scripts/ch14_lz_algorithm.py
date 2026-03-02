#!/usr/bin/env python3
"""
ch14_lz_algorithm.py -- LZ compression back-reference diagram.

Shows a byte stream with literals and back-references highlighted.
Demonstrates how (offset, length) replaces repeated sequences.

Output: illustrations/output/ch14_lz_algorithm.png
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

# --- Data: original byte stream ---
# Simulates a typical Spectrum tile pattern with repeats
original = ['A0', 'B1', 'C2', 'D3',  'A0', 'B1', 'C2', 'D3',
            'E4', 'F5',  'A0', 'B1', 'C2', 'D3',  '00', '00']

# Match regions: (start_in_original, offset_back, length)
# Match 1: bytes 4-7 copy from bytes 0-3 (offset=4, length=4)
# Match 2: bytes 10-13 copy from bytes 0-3 (offset=10, length=4)
# Match 3: bytes 15 copies from byte 14 (offset=1, length=1)
matches = [
    {'dst_start': 4,  'src_start': 0, 'length': 4, 'offset': 4},
    {'dst_start': 10, 'src_start': 0, 'length': 4, 'offset': 10},
    {'dst_start': 15, 'src_start': 14, 'length': 1, 'offset': 1},
]

# --- Figure ---
fig, axes = plt.subplots(2, 1, figsize=(7, 4.5), gridspec_kw={'height_ratios': [1, 1.2]})
fig.patch.set_facecolor('white')

# ---- Top: Original byte stream ----
ax1 = axes[0]
ax1.set_facecolor('white')
ax1.axis('off')

n = len(original)
box_w = 0.38
box_h = 0.5
y_row = 0.5
x_start = 0.2

# Determine which bytes are match destinations
match_dst = set()
match_src = set()
for m in matches:
    for i in range(m['length']):
        match_dst.add(m['dst_start'] + i)
        match_src.add(m['src_start'] + i)

for i, byte_val in enumerate(original):
    x = x_start + i * box_w
    if i in match_dst:
        fc = '#FFE0E0'
        ec = ZX_RED
        alpha = 0.7
    elif i in match_src:
        fc = '#E0F0FF'
        ec = ZX_BLUE
        alpha = 0.7
    else:
        fc = '#F0F0F0'
        ec = '#999999'
        alpha = 0.6

    rect = mpatches.FancyBboxPatch(
        (x, y_row - box_h / 2), box_w - 0.03, box_h,
        boxstyle='round,pad=0.03',
        facecolor=fc, edgecolor=ec, linewidth=1.2, alpha=alpha
    )
    ax1.add_patch(rect)
    ax1.text(x + (box_w - 0.03) / 2, y_row, byte_val,
             ha='center', va='center', fontsize=8, fontfamily='monospace',
             fontweight='bold', color='#333333')
    # Index below
    ax1.text(x + (box_w - 0.03) / 2, y_row - box_h / 2 - 0.12, str(i),
             ha='center', va='top', fontsize=6, fontfamily='monospace',
             color='#999999')

ax1.set_xlim(-0.1, x_start + n * box_w + 0.1)
ax1.set_ylim(-0.3, 1.2)

ax1.text(x_start + n * box_w / 2, 1.05, 'Original Byte Stream (16 bytes)',
         ha='center', va='center', fontsize=12, fontweight='bold',
         fontfamily='sans-serif', color='#1a1a1a')

# Draw back-reference arcs
for m in matches:
    src_x = x_start + m['src_start'] * box_w + (box_w - 0.03) / 2
    dst_x = x_start + m['dst_start'] * box_w + (box_w - 0.03) / 2
    mid_x = (src_x + dst_x) / 2
    arc_height = 0.15 + 0.08 * m['offset']  # taller arcs for longer references

    ax1.annotate('', xy=(dst_x, y_row + box_h / 2 + 0.02),
                 xytext=(src_x, y_row + box_h / 2 + 0.02),
                 arrowprops=dict(arrowstyle='->', color=ZX_RED, lw=1.5,
                                 connectionstyle=f'arc3,rad=-0.4'))

# ---- Bottom: Compressed stream ----
ax2 = axes[1]
ax2.set_facecolor('white')
ax2.axis('off')

# Compressed representation: literals + match tokens
compressed = [
    {'type': 'lit', 'val': 'A0'},
    {'type': 'lit', 'val': 'B1'},
    {'type': 'lit', 'val': 'C2'},
    {'type': 'lit', 'val': 'D3'},
    {'type': 'match', 'val': '(-4, 4)', 'desc': 'copy 4\nfrom -4'},
    {'type': 'lit', 'val': 'E4'},
    {'type': 'lit', 'val': 'F5'},
    {'type': 'match', 'val': '(-10, 4)', 'desc': 'copy 4\nfrom -10'},
    {'type': 'lit', 'val': '00'},
    {'type': 'match', 'val': '(-1, 1)', 'desc': 'copy 1\nfrom -1'},
]

y_row2 = 0.55
match_w = 0.72  # wider box for match tokens
x = x_start

for item in compressed:
    if item['type'] == 'lit':
        w = box_w - 0.03
        rect = mpatches.FancyBboxPatch(
            (x, y_row2 - box_h / 2), w, box_h,
            boxstyle='round,pad=0.03',
            facecolor='#E8F5E8', edgecolor=ZX_GREEN, linewidth=1.2, alpha=0.7
        )
        ax2.add_patch(rect)
        ax2.text(x + w / 2, y_row2, item['val'],
                 ha='center', va='center', fontsize=8, fontfamily='monospace',
                 fontweight='bold', color='#333333')
        x += w + 0.03
    else:
        w = match_w
        rect = mpatches.FancyBboxPatch(
            (x, y_row2 - box_h / 2), w, box_h,
            boxstyle='round,pad=0.03',
            facecolor='#FFE8D0', edgecolor='#DD6622', linewidth=1.5, alpha=0.8
        )
        ax2.add_patch(rect)
        ax2.text(x + w / 2, y_row2 + 0.05, item['val'],
                 ha='center', va='center', fontsize=7.5, fontfamily='monospace',
                 fontweight='bold', color='#AA4400')
        ax2.text(x + w / 2, y_row2 - 0.18, item['desc'],
                 ha='center', va='center', fontsize=5.5, fontfamily='sans-serif',
                 color='#886644', linespacing=1.1)
        x += w + 0.03

ax2.set_xlim(-0.1, x_start + n * box_w + 0.1)
ax2.set_ylim(-0.35, 1.3)

ax2.text(x_start + n * box_w / 2, 1.15, 'Compressed Stream (10 tokens = fewer bytes)',
         ha='center', va='center', fontsize=12, fontweight='bold',
         fontfamily='sans-serif', color='#1a1a1a')

# Legend
legend_y = -0.15
legend_items = [
    ('#E8F5E8', ZX_GREEN, 'Literal byte'),
    ('#FFE8D0', '#DD6622', 'Match (offset, length)'),
    ('#E0F0FF', ZX_BLUE, 'Source (referenced)'),
    ('#FFE0E0', ZX_RED, 'Replaced by match'),
]
legend_x = x_start
for fc, ec, label in legend_items:
    rect = mpatches.FancyBboxPatch(
        (legend_x, legend_y - 0.08), 0.2, 0.16,
        boxstyle='round,pad=0.02', facecolor=fc, edgecolor=ec, linewidth=1.0
    )
    ax2.add_patch(rect)
    ax2.text(legend_x + 0.28, legend_y, label,
             ha='left', va='center', fontsize=7, fontfamily='sans-serif',
             color='#555555')
    legend_x += 1.5

plt.tight_layout()
plt.savefig('/Users/alice/dev/antique-toy/illustrations/output/ch14_lz_algorithm.png',
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved ch14_lz_algorithm.png')
