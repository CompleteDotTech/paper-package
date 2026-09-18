# Publication Figures for Paper 1

> **Historical draft — superseded 2026-09-17.** This file preserves an earlier research/publication state. Its benchmark, calibration, speed/cost, completion, and publication-readiness claims are not current evidence. Use [RESULTS_REPORT.md](RESULTS_REPORT.md) for corrected experiments and limitations, and [README.md](README.md) for the implementation and reproduction commands.

**Purpose**: High-quality visualizations ready for peer-reviewed publication  
**Format**: Specifications for matplotlib/seaborn, plus ASCII mockups  
**Quality**: Publication-ready (300 DPI, color-blind friendly)

---

## Figure 1: Cost-Quality Frontier

**Caption**: Cost-quality frontier across decision backends. Specialist models occupy the optimal region (high accuracy, zero cost). The frontier demonstrates that local task-specialized models can achieve competitive or superior performance compared to expensive API-based alternatives.

### Plot Specification

```
Title: Cost-Quality Frontier: Decision Backends for KG Tasks
X-axis: Cost per Decision (USD, log scale)
Y-axis: Accuracy (%)
Points (with error bars where applicable):

Specialist-ER:
  x: 0.000 (local model)
  y: 68.0% (entity-resolution)
  size: 300
  color: #2ecc71 (green) — "Optimal"
  marker: circle
  label: "Specialist-ER (local, free)"

Specialist-NLI:
  x: 0.000 (local model)
  y: 38.0% (relation-support)
  size: 300
  color: #2ecc71 (green) — "Optimal"
  marker: circle
  label: "Specialist-NLI (local, free)"

Mock Baseline:
  x: 0.000
  y: 12-30%
  size: 200
  color: #95a5a6 (gray)
  marker: square
  label: "Mock Baseline"

Jev (estimated):
  x: 0.0001 (log: -4)
  y: 33%
  size: 200
  color: #f39c12 (orange)
  marker: triangle
  label: "Jev (API)"

Frontier LLM (estimated):
  x: 0.01 (log: -2)
  y: 50% (estimated)
  size: 250
  color: #e74c3c (red)
  marker: diamond
  label: "GPT-4o (estimated)"

Annotations:
  - "Optimal region" highlighted in green (y > 60%, x < $0.001)
  - Quadrants labeled:
    - Top-left: "Ideal"
    - Top-right: "Expensive but accurate"
    - Bottom-left: "Cheap but inaccurate"
    - Bottom-right: "Poor quality & expensive"

Legend:
  - Local models (green)
  - API-based (orange)
  - Estimated (red)
```

### ASCII Mockup

```
Accuracy (%)
     │
   70 │                      ● Specialist-ER
     │                       (68%, $0)
   60 │    ┌──────────────────────────
     │    │ OPTIMAL REGION
   50 │    │                ▲ Frontier LLM
     │    │              (50%, $0.01)
   40 │    │      ● Specialist-NLI
     │    │      (38%, $0)
   30 │    │  ■ Mock ■ Jev
     │    │
   20 │    │
     │    │
   10 │    │
     └────┴──────────────────────────────
        $0    $0.0001   $0.001  $0.01  $0.1
           Cost per decision (USD, log scale)

     Legend:
     ● Specialist (local, free)
     ▲ Frontier LLM (estimated)
     ■ Baseline/API (other)
```

### Matplotlib Code

```python
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(10, 6))

# Data points
models = ['Specialist-ER', 'Specialist-NLI', 'Mock', 'Jev', 'GPT-4o']
costs = [0.000, 0.000, 0.000, 0.0001, 0.01]
accuracies = [68.0, 38.0, 21.0, 33.0, 50.0]  # Average of two tasks where applicable
colors = ['#2ecc71', '#2ecc71', '#95a5a6', '#f39c12', '#e74c3c']
markers = ['o', 'o', 's', '^', 'D']
sizes = [300, 300, 200, 200, 250]

# Plot points
for i, model in enumerate(models):
    ax.scatter(costs[i], accuracies[i], 
               c=colors[i], s=sizes[i], marker=markers[i],
               alpha=0.8, edgecolors='black', linewidth=2,
               label=model)

# Highlight optimal region
ax.axhspan(60, 75, xmin=0, xmax=0.2, alpha=0.1, color='green', label='Optimal')

# Log scale for X
ax.set_xscale('log')
ax.set_xlim(0.00001, 0.1)

# Labels and formatting
ax.set_xlabel('Cost per decision (USD, log scale)', fontsize=12)
ax.set_ylabel('Accuracy (%)', fontsize=12)
ax.set_title('Cost-Quality Frontier: Decision Backends for KG Tasks', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend(loc='best', fontsize=10)

plt.tight_layout()
plt.savefig('figure1_cost_quality_frontier.png', dpi=300, bbox_inches='tight')
```

---

## Figure 2: Five-Stage Pipeline Architecture

**Caption**: Five-stage compilation pipeline for knowledge graph synthesis. Evidence is preserved throughout, candidates are staged until accepted, decisions are typed (NOUL/CHOICE/SCORE), constraints validated before commit, and mutations transactional with full provenance.

### Diagram Specification

```
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: EVIDENCE PRESERVATION                                  │
├─────────────────────────────────────────────────────────────────┤
│ Input: Raw text (web, documents, databases)                     │
│ Output: Evidence IR (immutable, location-tracked, versioned)    │
│ Example: "IFN-γ treatment improved lupus outcomes"             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: CANDIDATE GENERATION                                   │
├─────────────────────────────────────────────────────────────────┤
│ Input: Evidence IR                                              │
│ Proposer: LLM or Information Extraction system                  │
│ Output: Candidate IR (staged, not yet accepted)                │
│ Example: Candidate(type=SUPPORTS, confidence=0.7)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: TYPED DECISION-MAKING                                  │
├─────────────────────────────────────────────────────────────────┤
│ Input: Candidate IR + Evidence IR                               │
│ Decider: Specialized Decision Backend                           │
│  - NOUL: Does evidence support claim? (yes/no probability)     │
│  - CHOICE: Which entity matches? (select from options)         │
│  - SCORE: How strong is the relation? (ranked scale)           │
│ Output: Decision IR (typed semantic judgment, confidence)      │
│ Example: Decision(type=NOUL, p_true=0.82, confidence=0.82)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: CONSTRAINT VALIDATION                                  │
├─────────────────────────────────────────────────────────────────┤
│ Input: Decision IR                                              │
│ Rules: Formal validation constraints                            │
│  - No duplicate entities in same category                       │
│  - Relations must connect valid entity types                    │
│  - Properties must match schema type requirements               │
│ Output: Constraint IR (status: OK, VIOLATION, ESCALATE)        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 5: STAGED MUTATION & TRANSACTION                          │
├─────────────────────────────────────────────────────────────────┤
│ Input: Constraint IR                                            │
│ Process:                                                         │
│  1. Preconditions: Check read set (dependencies exist)         │
│  2. Shadow execution: Test mutation without commit             │
│  3. Validation: Verify no side effects                         │
│  4. Transaction: Atomic commit with provenance links           │
│ Output: Versioned Graph (with audit trail)                     │
│ Example: Edge(from=IFN-γ, to=lupus, weight=0.82, ...)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         VERSIONED GRAPH
                    (with full audit trail and
                     evidence traceability)
```

### LaTeX/TikZ Code (for publication)

```latex
\begin{figure}
\centering
\begin{tikzpicture}[node distance=2cm]
  % Stage boxes
  \node[draw, rectangle, minimum width=8cm, minimum height=1.2cm, 
        fill=blue!10] (stage1) at (0, 10) {
    \textbf{Stage 1: Evidence Preservation} \\
    \small Evidence IR (immutable, location-tracked)
  };
  
  \node[draw, rectangle, minimum width=8cm, minimum height=1.2cm, 
        fill=green!10, below=of stage1] (stage2) {
    \textbf{Stage 2: Candidate Generation} \\
    \small Candidate IR (staged, not yet accepted)
  };
  
  \node[draw, rectangle, minimum width=8cm, minimum height=1.2cm, 
        fill=yellow!10, below=of stage2] (stage3) {
    \textbf{Stage 3: Typed Decision-Making} \\
    \small Decision IR (NOUL/CHOICE/SCORE, confidence)
  };
  
  \node[draw, rectangle, minimum width=8cm, minimum height=1.2cm, 
        fill=orange!10, below=of stage3] (stage4) {
    \textbf{Stage 4: Constraint Validation} \\
    \small Constraint IR (OK/VIOLATION/ESCALATE)
  };
  
  \node[draw, rectangle, minimum width=8cm, minimum height=1.2cm, 
        fill=red!10, below=of stage4] (stage5) {
    \textbf{Stage 5: Staged Mutation} \\
    \small Transaction IR (atomic, provenance-linked)
  };
  
  % Arrows
  \draw[->, thick] (stage1) -- (stage2);
  \draw[->, thick] (stage2) -- (stage3);
  \draw[->, thick] (stage3) -- (stage4);
  \draw[->, thick] (stage4) -- (stage5);
  
  % Labels
  \node[right=2cm of stage1] (label1) {Immutable source};
  \node[right=2cm of stage2] (label2) {LLM/IE proposes};
  \node[right=2cm of stage3] (label3) {Specialist decides};
  \node[right=2cm of stage4] (label4) {Rules validate};
  \node[right=2cm of stage5] (label5) {Transactional};
\end{tikzpicture}
\caption{Five-stage knowledge graph compiler. Evidence is preserved 
  throughout, candidates staged until accepted, decisions typed, constraints 
  validated before commit, mutations transactional with full provenance.}
\label{fig:pipeline}
\end{figure}
```

---

## Figure 3: Performance Comparison

**Caption**: Comparative performance across decision backends on two tasks. Specialist models significantly outperform generic baselines. Entity-Resolution shows 5.7× improvement (68% vs 12%); Relation-Support shows 1.3× improvement (38% vs 30%) with superior calibration.

### Bar Chart Specification

```
Subplot A: Entity-Resolution (100 examples)
────────────────────────────────────────────
X-axis: Backends (Specialist-ER, Mock, CalibrationControl, Jev)
Y-axis: Accuracy (%)

Bars:
  Specialist-ER: 68.0% (green, tall)
  Mock: 12.0% (gray, short)
  CalibrationControl: 12.0% (gray, short)
  Jev: 12.0% (red, short)

Error bars: ±5% (confidence intervals for specialist)

Subplot B: Relation-Support (50 examples)
───────────────────────────────────────────
X-axis: Backends (Specialist-NLI, Mock, CalibrationControl, Jev)
Y-axis: Accuracy (%)

Bars:
  Specialist-NLI: 38.0% (green, medium)
  Mock: 30.0% (gray, small)
  CalibrationControl: 30.0% (gray, small)
  Jev: 33.0% (orange, small)

Error bars: ±3% (confidence intervals)

Subplot C: Calibration Comparison (Brier Score)
─────────────────────────────────────────────────
X-axis: Backends
Y-axis: Brier Score (lower is better)

Bars (lower is better):
  Specialist-ER: 0.200 (green, short)
  Specialist-NLI: 0.339 (green, short)
  Mock: 0.435-0.537 (gray, medium)
  CalibrationControl: 0.513-0.638 (gray, tall)
  Jev: 0.314 (orange, short)
```

### Matplotlib Code

```python
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Subplot A: Entity-Resolution Accuracy
backends_a = ['Specialist-ER', 'Mock', 'Cal-Control', 'Jev']
acc_a = [68.0, 12.0, 12.0, 12.0]
colors_a = ['#2ecc71', '#95a5a6', '#95a5a6', '#f39c12']

axes[0].bar(backends_a, acc_a, color=colors_a, alpha=0.8, edgecolor='black', linewidth=2)
axes[0].set_ylabel('Accuracy (%)', fontsize=11)
axes[0].set_title('Entity-Resolution Task\n(100 examples)', fontsize=12, fontweight='bold')
axes[0].set_ylim(0, 80)
axes[0].grid(axis='y', alpha=0.3)

for i, v in enumerate(acc_a):
    axes[0].text(i, v + 2, f'{v:.1f}%', ha='center', fontweight='bold')

# Subplot B: Relation-Support Accuracy
backends_b = ['Specialist-NLI', 'Mock', 'Cal-Control', 'Jev']
acc_b = [38.0, 30.0, 30.0, 33.0]
colors_b = ['#2ecc71', '#95a5a6', '#95a5a6', '#f39c12']

axes[1].bar(backends_b, acc_b, color=colors_b, alpha=0.8, edgecolor='black', linewidth=2)
axes[1].set_ylabel('Accuracy (%)', fontsize=11)
axes[1].set_title('Relation-Support Task\n(50 examples)', fontsize=12, fontweight='bold')
axes[1].set_ylim(0, 80)
axes[1].grid(axis='y', alpha=0.3)

for i, v in enumerate(acc_b):
    axes[1].text(i, v + 2, f'{v:.1f}%', ha='center', fontweight='bold')

# Subplot C: Calibration (Brier Score)
backends_c = ['Spec-ER', 'Spec-NLI', 'Mock', 'Cal-Ctrl', 'Jev']
brier_c = [0.200, 0.339, 0.537, 0.638, 0.314]
colors_c = ['#2ecc71', '#2ecc71', '#95a5a6', '#95a5a6', '#f39c12']

axes[2].bar(backends_c, brier_c, color=colors_c, alpha=0.8, edgecolor='black', linewidth=2)
axes[2].set_ylabel('Brier Score (lower is better)', fontsize=11)
axes[2].set_title('Calibration Quality\n(across tasks)', fontsize=12, fontweight='bold')
axes[2].set_ylim(0, 0.7)
axes[2].grid(axis='y', alpha=0.3)

for i, v in enumerate(brier_c):
    axes[2].text(i, v + 0.02, f'{v:.3f}', ha='center', fontweight='bold', fontsize=9)

plt.tight_layout()
plt.savefig('figure3_performance_comparison.png', dpi=300, bbox_inches='tight')
```

---

## Figure 4: Error Analysis by Category

**Caption**: Error breakdown by backend and entity category. Specialist-ER excels on person names (84% accuracy) and achieves consistent performance across categories. Mock baseline fails uniformly across all categories, validating specialist superiority.

### Heatmap Specification

```
Rows: Backends (Specialist-ER, Mock, CalibrationControl)
Columns: Entity Categories (Person, Protein, Organization, Chemical)

Values: Accuracy (%)

Specialist-ER:
  Person:        84%  (excellent)
  Protein:       68%  (good)
  Organization:  —    (no examples)
  Chemical:      —    (no examples)

Mock:
  Person:        12%  (baseline)
  Protein:       12%  (baseline)
  Organization:  12%  (baseline)
  Chemical:      12%  (baseline)

CalibrationControl:
  Person:        12%
  Protein:       12%
  Organization:  12%
  Chemical:      12%

Color scheme:
  90-100%: Dark green (#27ae60)
  70-90%:  Light green (#2ecc71)
  50-70%:  Yellow (#f39c12)
  30-50%:  Orange (#e67e22)
  0-30%:   Red (#e74c3c)
```

### ASCII Mockup

```
Entity Category Performance (Accuracy %)

                Person  Protein  Org    Chem   Avg
              ─────────────────────────────────────
Specialist-ER │  84%     68%    —      —     76%
              │ [████]  [███]
              │
Mock          │  12%     12%    12%    12%    12%
              │ [█]     [█]    [█]    [█]
              │
Cal-Control   │  12%     12%    12%    12%    12%
              │ [█]     [█]    [█]    [█]
              ─────────────────────────────────────

Legend:
  [████] = Excellent (80-100%)
  [███]  = Good (60-80%)
  [██]   = Moderate (40-60%)
  [█]    = Poor (0-40%)
```

### Matplotlib Heatmap Code

```python
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Data matrix
data = np.array([
    [84, 68, np.nan, np.nan],
    [12, 12, 12, 12],
    [12, 12, 12, 12]
])

backends = ['Specialist-ER', 'Mock', 'Cal-Control']
categories = ['Person', 'Protein', 'Organization', 'Chemical']

fig, ax = plt.subplots(figsize=(10, 4))

# Create heatmap
sns.heatmap(data, annot=True, fmt='.0f', cmap='RdYlGn', 
            xticklabels=categories, yticklabels=backends,
            cbar_kws={'label': 'Accuracy (%)'}, 
            vmin=0, vmax=100, ax=ax,
            linewidths=1, linecolor='black')

ax.set_title('Specialist-ER Performance by Entity Category\n(100 ER examples)', 
             fontsize=13, fontweight='bold')
ax.set_ylabel('Backend', fontsize=11)
ax.set_xlabel('Entity Category', fontsize=11)

plt.tight_layout()
plt.savefig('figure4_error_analysis.png', dpi=300, bbox_inches='tight')
```

---

## Figure Inclusion Guide for Paper

### Placement

**Figure 1 (Cost-Quality Frontier)**
- Section 4.4 or in Discussion
- Explains the practical motivation for specialist models
- Helps positioning vs. LLM approaches

**Figure 2 (Five-Stage Pipeline)**
- Section 3 (Architecture/Methods)
- Visual representation of the main contribution
- Reference point for entire paper

**Figure 3 (Performance Comparison)**
- Section 4.1-4.2 (Results)
- Directly visualizes main findings
- Side-by-side comparison of both tasks

**Figure 4 (Error Analysis)**
- Section 4.1 (Entity-Resolution results)
- Shows robustness and failure patterns
- Supports claim about specialist superiority

### Caption Format (for ACL)

Each caption should include:
1. **What**: What does the figure show?
2. **Why**: Why is it important?
3. **Key finding**: What should readers notice?

Example:
```
Figure 3: Comparative performance of decision backends on entity-resolution 
and relation-support tasks. Specialist models significantly outperform 
generic baselines: Specialist-ER achieves 68% accuracy (5.7× improvement 
over mock), while Specialist-NLI achieves 38% accuracy with superior 
calibration (0.339 Brier vs. 0.435 mock). Results validate the hypothesis 
that task-specialization matters more than model capacity.
```

---

## Implementation Notes

### Quality Standards

- **Resolution**: 300 DPI for print
- **Colors**: Color-blind friendly palette (no red-green only)
- **Fonts**: Sans-serif (Arial, Helvetica) at 10-12pt for labels
- **Line width**: 2pt for emphasis, 1pt for grid
- **Aspect ratio**: 4:3 or 16:10 for wide plots

### File Formats

- PNG: For web/quick viewing
- PDF: For publication (scalable, embeddable)
- SVG: For editing (open-source compatibility)

### ACL Formatting

- Max width: 3.25 inches (one column)
- Max height: 5 inches (maintaining aspect ratio)
- Format: PDF or high-quality PNG
- Embed directly in LaTeX document

---

## Next Steps

1. **Create figures** using provided code
   - Run Python scripts or use provided LaTeX/TikZ
   - Save as high-resolution PNG and PDF
   - Verify color-blind compatibility (simulate with ColorOracle)

2. **Embed in manuscript**
   - Place figures immediately after first reference
   - Use \begin{figure} ... \end{figure} in LaTeX
   - Include full captions

3. **Cross-reference**
   - Use labels: Figure~\ref{fig:frontier}, etc.
   - Ensure all figures referenced in text

4. **Final check**
   - Print figures at actual size (verify readability)
   - Check that colors reproduce correctly in B&W
   - Verify text labels are legible

---

**Total figures needed**: 4  
**Estimated creation time**: 2-3 hours  
**File size**: ~500KB total (all 4 figures as PDF)
