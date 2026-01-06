"""
Script to generate explanatory diagrams for the ESP project pipeline.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np

def create_pipeline_diagram():
    """Create a diagram showing the complete data pipeline."""
    fig, ax = plt.subplots(1, 1, figsize=(20, 10))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Define positions - corrected flow layout
    positions = {
        'raw': (2, 8),
        'load': (2, 6),
        'signals': (2, 4),
        'hybrid': (6, 6),      # Parallel reference branch
        'ranges': (6, 2),
        'envelope': (10, 4),
        'confirmation': (10, 2),
        'alarms': (14, 4),
        'pred_evento': (14, 2),
        'imputation': (18, 6), # Added missing step
        'evaluation': (18, 4),
        'output': (18, 2)
    }

    # Create boxes with adjusted sizes
    boxes = {}
    for key, pos in positions.items():
        # Adjust box width based on content
        width = 2.5 if key in ['signals', 'ranges', 'alarms', 'imputation'] else 2.0

        if key == 'raw':
            boxes[key] = FancyBboxPatch(pos, width, 0.8, boxstyle="round,pad=0.1",
                                      facecolor='lightblue', edgecolor='navy', linewidth=2)
        elif key in ['load', 'signals']:
            boxes[key] = FancyBboxPatch(pos, width, 0.8, boxstyle="round,pad=0.1",
                                      facecolor='lightgreen', edgecolor='darkgreen', linewidth=2)
        elif key in ['ranges', 'envelope', 'confirmation']:
            boxes[key] = FancyBboxPatch(pos, width, 0.8, boxstyle="round,pad=0.1",
                                      facecolor='lightyellow', edgecolor='orange', linewidth=2)
        elif key in ['alarms', 'pred_evento']:
            boxes[key] = FancyBboxPatch(pos, width, 0.8, boxstyle="round,pad=0.1",
                                      facecolor='lightcoral', edgecolor='red', linewidth=2)
        elif key == 'hybrid':
            boxes[key] = FancyBboxPatch(pos, width, 0.8, boxstyle="round,pad=0.1",
                                      facecolor='lightcyan', edgecolor='teal', linewidth=2)
        elif key == 'imputation':
            boxes[key] = FancyBboxPatch(pos, width, 0.8, boxstyle="round,pad=0.1",
                                      facecolor='plum', edgecolor='purple', linewidth=2)
        elif key == 'evaluation':
            boxes[key] = FancyBboxPatch(pos, width, 0.8, boxstyle="round,pad=0.1",
                                      facecolor='plum', edgecolor='purple', linewidth=2)
        else:
            boxes[key] = FancyBboxPatch(pos, width, 0.8, boxstyle="round,pad=0.1",
                                      facecolor='lightgray', edgecolor='black', linewidth=2)

        ax.add_patch(boxes[key])

    # Add text
    labels = {
        'raw': 'RAW DATA\n(DATOS_ESP.xlsx)',
        'load': 'LOAD & CLEAN\n(dates, types,\nregimen creation)',
        'signals': 'PRODUCTION SIGNALS\n(slope_7, delta_1,\nratio14)',
        'hybrid': 'HYBRID EVENTS\n(evento_hibrido)\nReference classification',
        'ranges': 'OPERATIONAL RANGES\n(percentiles by regimen)',
        'envelope': 'ENVELOPE SIGNALS\n(env_q, env_gate)',
        'confirmation': 'CONFIRMATION\n(statistical thresholds)',
        'alarms': 'ALARMS\n(persistence + refractory)',
        'pred_evento': 'PRED_EVENTO\n(robust classification)',
        'imputation': 'MISSING DATA\nIMPUTATION\n(by regimen)',
        'evaluation': 'EVALUATION\n(metrics & correlations)',
        'output': 'FINAL DATASET\n+ REPORTS'
    }

    for key, label in labels.items():
        # Adjust text position based on box width
        width = 2.5 if key in ['signals', 'ranges', 'alarms', 'imputation'] else 2.0
        ax.text(positions[key][0] + width/2, positions[key][1] + 0.4, label,
               ha='center', va='center', fontsize=8, fontweight='bold')

    # Add arrows - corrected flow based on actual pipeline
    arrows = [
        ('raw', 'load'),
        ('load', 'signals'),
        ('signals', 'hybrid'),      # Reference branch
        ('signals', 'ranges'),      # Main branch
        ('ranges', 'envelope'),
        ('envelope', 'confirmation'),
        ('confirmation', 'alarms'),
        ('alarms', 'pred_evento'),
        ('pred_evento', 'imputation'),  # Added imputation step
        ('imputation', 'evaluation'),
        ('evaluation', 'output')
    ]

    # Add reference arrow from hybrid to evaluation
    reference_arrows = [
        ('hybrid', 'evaluation')  # Reference for comparison
    ]

    for start, end in arrows:
        # Adjust start position based on box width
        start_width = 2.5 if start in ['signals', 'ranges', 'alarms', 'imputation'] else 2.0
        start_pos = (positions[start][0] + start_width, positions[start][1] + 0.4)

        # Adjust end position
        end_width = 2.5 if end in ['signals', 'ranges', 'alarms', 'imputation'] else 2.0
        end_pos = (positions[end][0], positions[end][1] + 0.4)

        # Special adjustments for connections
        if start == 'signals' and end == 'hybrid':
            start_pos = (positions[start][0] + start_width/2, positions[start][1] + 0.8)
            end_pos = (positions[end][0], positions[end][1] + 0.4)
        elif start == 'signals' and end == 'ranges':
            start_pos = (positions[start][0] + start_width/2, positions[start][1])
            end_pos = (positions[end][0] + end_width/2, positions[end][1] + 0.8)
        elif start == 'pred_evento' and end == 'imputation':
            start_pos = (positions[start][0] + start_width/2, positions[start][1] + 0.8)
            end_pos = (positions[end][0], positions[end][1] + 0.4)
        elif start == 'imputation' and end == 'evaluation':
            start_pos = (positions[start][0] + start_width, positions[start][1] + 0.4)
            end_pos = (positions[end][0], positions[end][1] + 0.4)

        arrow = ConnectionPatch(start_pos, end_pos, "data", "data",
                              arrowstyle="->", shrinkA=5, shrinkB=5,
                              mutation_scale=15, fc="k", color="k")
        ax.add_artist(arrow)

    # Add reference arrows (dashed lines)
    for start, end in reference_arrows:
        start_width = 2.5 if start in ['signals', 'ranges', 'alarms', 'imputation'] else 2.0
        end_width = 2.5 if end in ['signals', 'ranges', 'alarms', 'imputation'] else 2.0
        start_pos = (positions[start][0] + start_width/2, positions[start][1])
        end_pos = (positions[end][0] + end_width/2, positions[end][1] + 0.8)

        ref_arrow = ConnectionPatch(start_pos, end_pos, "data", "data",
                                  arrowstyle="->", shrinkA=5, shrinkB=5,
                                  mutation_scale=15, fc="gray", color="gray",
                                  linestyle="--", linewidth=1.5)
        ax.add_artist(ref_arrow)

        # Add reference label
        mid_x = (start_pos[0] + end_pos[0]) / 2
        mid_y = (start_pos[1] + end_pos[1]) / 2
        ax.text(mid_x, mid_y + 0.1, 'reference', ha='center', va='center',
               fontsize=7, color='gray', style='italic')

    # Add title
    ax.text(8, 9.5, 'ESP PROJECT DATA PIPELINE', ha='center', va='center',
           fontsize=16, fontweight='bold')

    plt.tight_layout()
    plt.savefig('pipeline_diagram.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_signals_diagram():
    """Create a diagram explaining signal calculations."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')

    # Production time series
    x = np.linspace(0, 10, 100)
    y = 100 + 10*np.sin(x) - 0.1*x**2 + np.random.normal(0, 2, 100)

    ax.plot(x, y, 'b-', linewidth=2, label='Production Q(t)')
    ax.set_xlabel('Time (days)')
    ax.set_ylabel('Production (bbl/d)')
    ax.set_title('Signal Calculations from Production Time Series', fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Highlight windows
    ax.axvspan(3, 3+7/10, alpha=0.2, color='red', label='7-day window')
    ax.axvspan(6, 6+14/10, alpha=0.2, color='green', label='14-day window')

    # Slope annotations
    ax.annotate('slope_7\n(7-day trend)', xy=(4, 95), xytext=(5, 85),
               arrowprops=dict(arrowstyle='->'), fontsize=10, color='red')

    ax.annotate('slope_14\n(14-day trend)', xy=(7, 90), xytext=(8, 80),
               arrowprops=dict(arrowstyle='->'), fontsize=10, color='green')

    # Delta annotations
    ax.annotate('delta_1\n(day-to-day change)', xy=(2, 105), xytext=(0, 110),
               arrowprops=dict(arrowstyle='->'), fontsize=10, color='purple')

    ax.legend()
    plt.tight_layout()
    plt.savefig('signals_diagram.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_classification_diagram():
    """Create a diagram explaining event classification."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    # Create a simple decision tree
    ax.axis('off')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)

    # Root
    ax.text(5, 5.5, 'Production Anomaly Detection', ha='center', fontsize=12, fontweight='bold',
           bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))

    # Level 1
    ax.text(2.5, 4, 'Envelope Check\n(env_q + env_gate)', ha='center', fontsize=10,
           bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow"))
    ax.text(7.5, 4, 'Statistical Confirmation\n(slope_7 + delta_1 + ratio14)', ha='center', fontsize=10,
           bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow"))

    # Arrows
    ax.arrow(5, 5.2, -1.5, -0.8, head_width=0.1, head_length=0.1, fc='k', ec='k')
    ax.arrow(5, 5.2, 1.5, -0.8, head_width=0.1, head_length=0.1, fc='k', ec='k')

    # Level 2
    ax.text(1.25, 2.5, 'Outside\nOperational\nRange', ha='center', fontsize=9,
           bbox=dict(boxstyle="round,pad=0.2", facecolor="lightcoral"))
    ax.text(3.75, 2.5, 'Gas Gate\nTriggered', ha='center', fontsize=9,
           bbox=dict(boxstyle="round,pad=0.2", facecolor="lightcoral"))

    ax.text(6.25, 2.5, 'Drop Confirmed\n(slope_7 < μ-σ\nOR delta_1 < p10)', ha='center', fontsize=9,
           bbox=dict(boxstyle="round,pad=0.2", facecolor="orange"))
    ax.text(8.75, 2.5, 'Rise Confirmed\n(slope_7 > μ+σ\nOR delta_1 > p90\nOR ratio14 > 0.2)', ha='center', fontsize=9,
           bbox=dict(boxstyle="round,pad=0.2", facecolor="lightgreen"))

    # Arrows level 2
    ax.arrow(2.5, 3.7, -0.75, -0.7, head_width=0.05, head_length=0.05, fc='k', ec='k')
    ax.arrow(2.5, 3.7, 0.75, -0.7, head_width=0.05, head_length=0.05, fc='k', ec='k')
    ax.arrow(7.5, 3.7, -0.75, -0.7, head_width=0.05, head_length=0.05, fc='k', ec='k')
    ax.arrow(7.5, 3.7, 0.75, -0.7, head_width=0.05, head_length=0.05, fc='k', ec='k')

    # Final classification
    ax.text(5, 1, 'pred_evento:\n0=Normal, 1=Drop, 2=Rise', ha='center', fontsize=10, fontweight='bold',
           bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen"))

    # Final arrows
    ax.arrow(1.25, 2.2, 1.25, -0.7, head_width=0.05, head_length=0.05, fc='k', ec='k')
    ax.arrow(3.75, 2.2, 0.25, -0.7, head_width=0.05, head_length=0.05, fc='k', ec='k')
    ax.arrow(6.25, 2.2, -0.25, -0.7, head_width=0.05, head_length=0.05, fc='k', ec='k')
    ax.arrow(8.75, 2.2, -1.25, -0.7, head_width=0.05, head_length=0.05, fc='k', ec='k')

    plt.tight_layout()
    plt.savefig('classification_diagram.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    create_pipeline_diagram()
    create_signals_diagram()
    create_classification_diagram()
    print("Diagrams saved as PNG files")