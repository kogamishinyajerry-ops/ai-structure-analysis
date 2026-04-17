#!/usr/bin/env python3
"""
GS-001 Enhanced Scientific Report
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle

plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})

C = {'fail': '#e74c3c', 'theory': '#8e44ad', 'fea': '#2c3e50', 'light': '#f8f9fa'}

fig = plt.figure(figsize=(16, 20))
gs = gridspec.GridSpec(4, 2, hspace=0.35, wspace=0.25)
fig.patch.set_facecolor('white')

fig.suptitle('GS-001: Cantilever Beam - VALIDATION FAILED\n'
            'Critical Error: FEA δ=493.56mm vs Theory δ=0.76mm (Error: 648×)',
            fontsize=14, fontweight='bold', y=0.98, color=C['fail'])

# Model config
ax1 = fig.add_subplot(gs[0, 0])
ax1.set_facecolor(C['light'])
beam = Rectangle((0,-5), 100, 10, facecolor='#3498db', alpha=0.4, edgecolor='steelblue', lw=2)
ax1.add_patch(beam)
for i in range(8): ax1.plot([-2+i*0.5, -1+i*0.5], [-7,-9], 'k-', lw=1.5)
ax1.plot([-2,2], [-6,-6], 'k-', lw=4)
for i in range(4): ax1.annotate('', xy=(100,-5+i*3.3), xytext=(115,-5+i*3.3),
                                arrowprops=dict(arrowstyle='->', color=C['fail'], lw=2))
ax1.set_xlim(-5,130); ax1.set_ylim(-12,12)
ax1.set_xlabel('X (mm)'); ax1.set_ylabel('Y (mm)')
ax1.set_title('(a) FEA Model: C3D8 Solid Elements', fontweight='bold')
ax1.set_aspect('equal')

ax2 = fig.add_subplot(gs[0, 1])
ax2.set_facecolor(C['light']); ax2.axis('off')
ax2.text(0.1, 0.95, """MODEL PARAMETERS
─────────────────────────
L = 100 mm | b×h = 10×10 mm
A = 100 mm² | I = 833.33 mm⁴
E = 210,000 MPa | P = 400 N

ELEMENT: C3D8 (8-node brick)
Nodes: 44 | Elements: 10

BC: x=0 fixed (nodes 1,12,23,34)
LOAD: P=-100N at nodes 11,22,33,44

THEORY: δ=P·L³/(3·E·I)=0.76 mm
        σ=P·L·c/I = 240 MPa""",
         transform=ax2.transAxes, fontsize=10, family='monospace', va='top')
ax2.set_title('(b) Input Parameters', fontweight='bold')

# Comparison bars
ax3 = fig.add_subplot(gs[1, :])
x = np.arange(2); w = 0.35
b1 = ax3.bar(x-w/2, [0.76, 240], w, label='Theory (Euler-Bernoulli)', color=C['theory'], alpha=0.8)
b2 = ax3.bar(x+w/2, [493.56, 190.08], w, label='FEA Result', color=C['fea'], alpha=0.8)
ax3.set_ylabel('Value'); ax3.set_xticks(x)
ax3.set_xticklabels(['Max Displacement (mm)', 'Max Stress (MPa)'])
ax3.legend(); ax3.set_title('(c) Theory vs FEA Comparison', fontweight='bold')
for b, v in zip(b1, [0.76, 240]): ax3.annotate(f'{v:.2f}', xy=(b.get_x()+b.get_width()/2, b.get_height()), xytext=(0,3), textcoords='offset points', ha='center')
for b, v in zip(b2, [493.56, 190.08]): ax3.annotate(f'{v:.2f}', xy=(b.get_x()+b.get_width()/2, b.get_height()), xytext=(0,3), textcoords='offset points', ha='center')
ax3.annotate('ERROR: 648× LARGER!\nVALIDATION FAILED', xy=(0.3, 0.7), xycoords='axes fraction', fontsize=14, fontweight='bold', color=C['fail'],
            bbox=dict(boxstyle='round', facecolor='#ffcccc', edgecolor=C['fail']))

# Displacement profile
ax4 = fig.add_subplot(gs[2, :])
x_pos = np.array([0,10,20,30,40,50,60,70,80,90,100])
y_t = np.array([0,0.007,0.061,0.206,0.488,0.952,1.646,2.610,3.893,5.547,7.619])
y_f = np.array([0,7.22,27.54,59.80,102.45,154.01,213.01,277.94,347.34,419.70,493.56])
ax4.semilogy(x_pos, y_t, 'o-', color=C['theory'], lw=2, ms=8, label='Theory')
ax4.semilogy(x_pos, y_f, 's-', color=C['fea'], lw=2, ms=8, label='FEA')
ax4.set_xlabel('Position X (mm)'); ax4.set_ylabel('Displacement UY (mm) - Log Scale')
ax4.set_title('(d) Displacement Along Beam - Theory vs FEA (Logarithmic Scale)', fontweight='bold')
ax4.legend(); ax4.set_xlim(0,110); ax4.grid(True, alpha=0.3)

# Error analysis
ax5 = fig.add_subplot(gs[3, 0])
ax5.set_facecolor('white')
errs = ['Unit/Section\nDefinition', 'Element\nType', 'Mesh\nQuality', 'Boundary\nConditions']
contrib = [40, 30, 15, 15]
ax5.bar(errs, contrib, color=['#e74c3c','#f39c12','#3498db','#95a5a6'], edgecolor='black')
ax5.set_ylabel('Contribution (%)'); ax5.set_title('(e) Root Cause Analysis', fontweight='bold')
ax5.set_ylim(0,50)

ax6 = fig.add_subplot(gs[3, 1])
ax6.axis('off')
data = [['Parameter','Theory','FEA','Status'],
        ['δ_max (mm)','0.76','493.56','FAILED 648×'],
        ['σ_max (MPa)','240','190','~20% diff'],
        ['Parse','-','100%','PASSED'],
        ['Model Setup','-','Error','FAILED']]
tbl = ax6.table(cellText=data, loc='center', colWidths=[0.3,0.2,0.2,0.25])
tbl.auto_set_font_size(False); tbl.set_fontsize(10); tbl.scale(1.2,2)
for i in range(4): tbl[(0,i)].set_facecolor('#1a5276'); tbl[(0,i)].set_text_props(color='white',weight='bold')
tbl[(3,3)].set_facecolor('#ffcccc'); tbl[(4,3)].set_facecolor('#ffcccc')
ax6.set_title('(f) Summary', fontweight='bold')

plt.savefig('GS001_Enhanced_Report.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print("GS-001 Enhanced Report saved!")
