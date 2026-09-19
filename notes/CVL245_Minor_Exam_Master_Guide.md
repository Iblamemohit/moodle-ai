---
title: "CVL245: Construction Management — Minor Examination Master Study Guide"
course: "CVL245A"
institution: "IIT Delhi"
semester: "Semester 1, 2026-2027 (2601)"
exam_date: "September 18, 2026 (Slot H, 6:00 PM – 8:00 PM)"
tags: [civil-engineering, construction-management, cpm, pert, floats, crashing, eva, lob, wbs, project-life-cycle]
last_updated: "2026-09-18"
---

# CVL245: Construction Management — Minor Exam Master Guide (0 to 100)

> **Exam Target**: Complete mastery of all slides, concepts, diagrams, node conventions, formulas, and solved numerical templates across Lectures 1 through 8 and the Denver Airport Scope Creep Case Study.

---

## Table of Contents
1. [Master Formula & Quick-Reference Matrix](#1-master-formula--quick-reference-matrix)
2. [Visual Diagram Deconstructions (Slide-by-Slide Image Guide)](#2-visual-diagram-deconstructions)
3. [Module 1: Introduction, Project Life Cycle & Scope Creep](#3-module-1-introduction-project-life-cycle--scope-creep)
4. [Module 2: Construction Planning, WBS & CPM Networks](#4-module-2-construction-planning-wbs--cpm-networks)
5. [Module 3: Float Analysis & Critical Path Method (CPM)](#5-module-3-float-analysis--critical-path-method-cpm)
6. [Module 4: Resource Levelling & Resource Allocation](#6-module-4-resource-levelling--resource-allocation)
7. [Module 5: Earned Value Analysis (EVA / EVM) & Project Monitoring](#7-module-5-earned-value-analysis-eva--evm--project-monitoring)
8. [Module 6: Project Crashing & Time-Cost Optimization](#8-module-6-project-crashing--time-cost-optimization)
9. [Module 7: Line of Balance (LOB) / Linear Scheduling Method (LSM)](#9-module-7-line-of-balance-lob--linear-scheduling-method-lsm)
10. [Module 8: Program Evaluation and Review Technique (PERT)](#10-module-8-program-evaluation-and-review-technique-pert)
11. [Module 9: Construction Contracts, Bidding & PPP Models (Lecture 8)](#11-module-9-construction-contracts-bidding--ppp-models)
12. [High-Yield Solved Problem Repository](#12-high-yield-solved-problem-repository)
13. [Common Exam Traps & Examiner Checkpoints](#13-common-exam-traps--examiner-checkpoints)

---

## 1. Master Formula & Quick-Reference Matrix

| Category | Parameter | Formula / Governing Equation | Crucial Exam Checkpoint |
| :--- | :--- | :--- | :--- |
| **CPM Forward Pass** | Early Start ($ES$) | $ES_j = \max_i(EF_i)$ for all predecessors $i$ | Initial activity starts at $ES = 0$. |
| | Early Finish ($EF$) | $EF_j = ES_j + D_j$ | Duration $D_j$ is added. |
| **CPM Backward Pass** | Late Finish ($LF$) | $LF_i = \min_j(LS_j)$ for all successors $j$ | Final activity ends at $LF = \text{Project Duration}$. |
| | Late Start ($LS$) | $LS_i = LF_i - D_i$ | Duration is subtracted. |
| **Float Calculations** | Total Float ($TF$) | $TF = LS - ES = LF - EF$ | Time an activity can delay without delaying project completion. |
| | Free Float ($FF$) | $FF_i = \min_j(ES_j) - EF_i$ | Delay without affecting early start of any successor. |
| | Interfering Float ($INTF$) | $INTF = TF - FF = LF_i - \min_j(ES_j)$ | Head event slack ($L_j - E_j$). |
| | Independent Float ($INDF$) | $INDF_j = \max\Big(0, \; \min_k(ES_k) - \max_i(LF_i) - D_j\Big)$ | Most conservative; affects neither predecessors nor successors. |
| **Earned Value (EVA)** | Planned Value ($PV$) | $PV = \% \text{Planned Work} \times BAC$ | Baseline budget for scheduled work ($BCWS$). |
| | Actual Cost ($AC$) | Cash recorded from accounting books | Actual expense incurred ($ACWP$). |
| | Earned Value ($EV$) | $EV = \% \text{Completed Work} \times BAC$ | Budgeted value of work done ($BCWP$). |
| | Cost Variance ($CV$) | $CV = EV - AC$ | Positive = Under budget; Negative = Over budget. |
| | Schedule Variance ($SV$) | $SV = EV - PV$ | Positive = Ahead; Negative = Behind (in money terms). |
| | Cost Performance Index ($CPI$) | $CPI = EV / AC$ | $> 1.0$ = efficient; $< 1.0$ = cost overrun. |
| | Schedule Performance Index ($SPI$) | $SPI = EV / PV$ | $> 1.0$ = ahead; $< 1.0$ = delayed. |
| | Estimate at Completion ($EAC$) | $EAC = BAC / CPI$ | Forecasted total final cost. |
| | Estimate to Complete ($ETC$) | $ETC = EAC - AC$ | Extra cash needed to finish. |
| | Variance at Completion ($VAC$) | $VAC = BAC - EAC$ | Anticipated cost variance at project end. |
| **Crashing** | Cost Slope ($S$) | $S = \frac{CC - NC}{NT - CT} = \frac{\Delta \text{Cost}}{\Delta \text{Time}}$ | Extra direct cost per day saved. |
| | Optimum Duration | Minimum of $\text{Total Cost} = \text{Direct Cost} + \text{Indirect Cost}$ | Crash critical activities with lowest slope. |
| **Line of Balance (LOB)** | Production Rate ($R$) | $R = \text{Slope} = \frac{\Delta \text{Units}}{\Delta \text{Time}}$ | Steeper line = faster gang. |
| | Slower Successor | $R_{\text{succ}} < R_{\text{pred}} \implies$ Diverging lines | Governed at **Unit 1** $\rightarrow \text{Start}_{\text{succ}} = \text{Start}_{\text{pred}} + \text{Duration}_1 + \text{Lag}$. |
| | Faster Successor | $R_{\text{succ}} > R_{\text{pred}} \implies$ Converging lines | Governed at **Final Unit** $\rightarrow \text{Finish}_{\text{succ}} = \text{Finish}_{\text{pred}} + \text{Lag}$. |
| **PERT** | Expected Duration ($t_e$) | $t_e = \frac{t_o + 4t_m + t_p}{6}$ | Weighted mean of Beta ($\beta$) distribution. |
| | Standard Deviation ($\sigma$) | $\sigma = \frac{t_p - t_o}{6}, \quad \text{Variance } V = \sigma^2$ | Tail probability = 1% for $t_o$ and $t_p$. |
| | Project Variance ($\sigma_{\text{proj}}^2$) | $\sigma_{\text{proj}}^2 = \sum_{\text{critical}} \sigma_i^2$ | Variances add along path; std deviations do NOT! |
| | Standard Normal Variate ($Z$) | $Z = \frac{T_s - T_e}{\sigma_{\text{proj}}}$ | Maps to Normal distribution (Central Limit Theorem). |

---

## 2. Visual Diagram Deconstructions

### Diagram 1: Paulson’s Influence vs. Cost Curve (Lecture 1, Slide 23)
```
Level of Cost /
Influence (%)
100% | \                                          --- - - - - Final Cost
     |  \  Ability to Influence Costs (Decreases)   /
     |   \                                       /  Cumulative Construction
     |    \                                     /   Cost (Increases rapidly)
     |     \                                   /
     |      \                                 /
     |       \                               /
  0% +--------\-----------------------------/--------------------> Project Time
      Concept    Engineering    Procurement    Startup   O&M
      Planning     Design       Construction
```
- **Solid Curve (Ability to Influence Costs)**: Starts at 100% during Concept/Feasibility and plummets towards 0%. A design change at day 1 costs almost nothing; a design change during concrete pouring costs millions.
- **Dashed S-Curve (Expenditure / Cost of Changes)**: Starts near 0% and climbs exponentially during Procurement and Construction, plateauing at 100% at startup.

---

### Diagram 2: PMBOK Life Cycle Level of Effort (Lecture 1, Slide 21)
```
Effort /
Staffing
  ^
  |                  EXECUTING (Highest peak, bulk of man-hours)
  |                      /\
  |       PLANNING      /  \
  |         /\         /    \
  | INITIATE/ \       /      \        CLOSING
  |   /\   /   \     /        \         /\
  |  /  \ /     \   /          \       /  \
--+----------------------------------------------------> Time
  | <----------------- MONITORING & CONTROLLING ----------------->
  |       (Spans across all phases from day 1 to project end)
```
- **Takeaway**: Monitoring & Controlling is **continuous** across the entire project lifecycle, not a sequential phase at the end.

---

### Diagram 3: CPM Node Representation Standards

#### Format A: Professor's Resource Scheduling Node (Lecture 4, Slide 6)
```
+---------------+---------------+---------------+
| Early Start   |   Duration    | Early Finish  |
|     (ES)      |      (D)      |     (EF)      |
+---------------+---------------+---------------+
|                   ACTIVITY                    |
+---------------+---------------+---------------+
|  Late Start   |   Resources   |  Late Finish  |
|     (LS)      |      (R)      |     (LF)      |
+---------------+---------------+---------------+
```

#### Format B: Standard Float / Koll Center Node (Lecture 2, Slide 40 & Lecture 3, Slide 15)
```
+---------------+---------------+---------------+
| Early Start   |  Activity ID  | Early Finish  |
|     (ES)      |     (ID)      |     (EF)      |
+---------------+---------------+---------------+
| Slack / Float |  Description  |               |
|     (TF)      |               |               |
+---------------+---------------+---------------+
|  Late Start   |   Duration    |  Late Finish  |
|     (LS)      |     (DUR)     |     (LF)      |
+---------------+---------------+---------------+
```

---

### Diagram 4: Earned Value S-Curves & Callout Identification (Lecture 5, Slides 14–15)
```
Cumulative
Cost ($)
  ^
  |                                        . - - - - Planned Value (PV)
  |                                 . - ' /
  |                          . - '       /  <--- Vertical distance = SV ($)
  |                   . - '             /
  |            . - ' . - - - - - - - - x [Target Date Review]
  |     . - '       /  Actual Cost (AC) |
  |  . '           /                   |  <--- Vertical distance = CV ($)
  | /             x - - - - - - - - - -+
  |/             /   Earned Value (EV) |
  +-------------x----------------------+------------------------> Time
                |                      |
                |<-- Horizontal ------>|
                     Delay (Time SV)
```
- **Top curve**: Planned Value ($PV$) $\implies$ scheduled spending.
- **Middle curve**: Actual Cost ($AC$) $\implies$ actual cash paid out.
- **Bottom curve**: Earned Value ($EV$) $\implies$ value of actual work delivered.
- **Exam Interpretation**:
  - Distance between $EV$ and $AC$: $\mathbf{CV = EV - AC}$ (Since $EV < AC$, project is **Over Budget**).
  - Distance between $EV$ and $PV$: $\mathbf{SV = EV - PV}$ (Since $EV < PV$, project is **Behind Schedule**).
  - Horizontal distance between $EV$ curve and $PV$ curve: **Time Schedule Variance** in weeks/months.

---

### Diagram 5: Line of Balance Crew Clashes (Lecture 7, Slides 6–7)
```
Units /
Location
  ^                                             ^
  |          Activity B                         |                     Activity B
  |         /          /                        |                   /       /
  |        /          /                         |                  /       /
  |       /          /  Time Buffer             |                 /       /
  |      /          /<------------>             |                /   COLLISION!
  |     /          /                            |               /     ( * )
  |    /          /                             |              /     /
  |   / Activity A                              |   Activity A/     /
  |  /          /                               |           /      /
  | /          /                                |          /      /
--+----------------------------> Time         --+----------------------------> Time
     Case 1: Parallel / Diverging                     Case 2: Successor is FASTER
       (Successor slower or equal)                      (Must delay successor start!)
```
- **Time Buffer**: Horizontal distance between activity lines.
- **Distance Buffer**: Vertical distance between operations at any point in time.
- **Star Marker (Collision)**: Occurs when a faster crew starts too early and overtakes the preceding crew on upper floors.

---

## 3. Module 1: Introduction, Project Life Cycle & Scope Creep
**Source**: [1. Introduction-PROJECT LIFE CYCLE.pdf](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/1.%20Introduction-PROJECT%20LIFE%20CYCLE.pdf) & [scope creep case study.pdf](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/scope%20creep%20case%20study.pdf)

### 1. Project vs. Operations Management
- **Project**: Temporary endeavor with a distinct beginning and end, undertaken to create a unique product, service, or result. Cross-functional, non-routine, and operates under risk and uncertainty.
- **Operations**: Ongoing, continuous, repetitive activities designed to sustain the business (e.g., routine building maintenance, manufacturing assembly line).

### 2. The Project Management Iron Triangle
- **Traditional Triangle**: Time, Cost, Scope/Quality.
- **Modern Extension (Prof. K.N. Jha Framework)**:
  - Central Core: Planning, Executing, Controlling.
  - Inputs: Funds, Time, Human Resources, Technical Resources.
  - Constraints/Outcomes: Quality, Safety, Environmental Sustainability, Client Satisfaction.

### 3. NBC Classification of Buildings (National Building Code of India)
- **Group A**: Residential
- **Group B**: Educational
- **Group C**: Institutional (Medical, Custodial)
- **Group D**: Assembly (Theaters, Halls, Sports complexes)
- **Group E**: Business (Offices, Banks)
- **Group F**: Mercantile (Shops, Malls, Supermarkets)
- **Group G**: Industrial
- **Group H**: Storage
- **Group I**: Hazardous

### 4. Scope Creep & Denver Airport Baggage Handling Case Study
- **Definition**: The uncontrolled expansion of project scope without adjustments to time, cost, and resources.
- **Denver International Airport (DIA) Baggage Handling Disaster**:
  - **Goal**: World's largest automated baggage system across 3 concourses; target aircraft turnaround time $= 30\text{ minutes}$.
  - **Core Causes of Failure**:
    1. Extreme complexity grossly underestimated (17 miles of track, 3,100 carts, 55 PCs).
    2. Scope Creep: Late changes by United and Continental Airlines (demanding ski equipment handling facilities and oversized bag handling midway through construction).
    3. Failure to listen to feasibility reports (Breier Neidle Patrone report in 1990 advised that automated system across all concourses was unfeasible in the given timeframe).
    4. Compressed schedule: Bidding failed; direct single-source contract given to BAE Systems with unrealistically short deadline.
  - **Outcome**: 16-month delay to airport opening; interest and maintenance cost the City of Denver **$1.1 Million per day** ($360M+ total overrun); system was eventually abandoned for manual tugs and trolleys.

---

## 4. Module 2: Construction Planning, WBS & CPM Networks
**Source**: [2. CONSTRUCTION PLANNING-WBS CPM.pdf](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/2.%20CONSTRUCTION%20PLANNING-WBS%20CPM.pdf)

### 1. Work Breakdown Structure (WBS)
- Hierarchical decomposition of project scope into progressively smaller work elements.
- **100% Rule**: The WBS encompasses 100% of the project scope—nothing more, nothing less. The child elements must sum to exactly 100% of their parent.
- **Work Package**: The lowest level of the WBS. Must be:
  - Uniquely assignable to a specific person/crew.
  - Clear in terms of start/finish dates, budget, and deliverables.
  - Typically 1 to 10 days duration for construction control.

### 2. Precedence Relationships (The 4 Fundamental Types)
1. **Finish-to-Start (FS)**: Successor cannot start until predecessor finishes. *(Masonry $\rightarrow$ Plastering)*.
2. **Start-to-Start (SS)**: Successor cannot start until predecessor starts. *(Excavation $\rightarrow$ Trench Dewatering)*.
3. **Finish-to-Finish (FF)**: Successor cannot finish until predecessor finishes. *(Painting $\rightarrow$ Quality Inspection)*.
4. **Start-to-Finish (SF)**: Successor cannot finish until predecessor starts. *(Temporary power generator running until permanent sub-station is energized)*.
- *Lags and Leads*: Lead $=$ negative lag (advance start); Lag $=$ positive waiting time.

### 3. Network Conventions: AOA vs. AON
- **Activity-on-Arrow (AOA)**:
  - Arrows represent activities; Nodes represent events (instantaneous moments in time).
  - **Requires Dummy Activities** (dashed arrows, duration = 0, cost = 0) for:
    1. Grammatical Rule: Maintaining unique node identification (two activities sharing both start and end nodes cannot exist).
    2. Logical Rule: Distinguishing shared dependencies (e.g., Activity C depends on A and B, while Activity D depends only on B).
- **Activity-on-Node (AON / PDM)**:
  - Nodes represent activities; Arrows represent dependencies.
  - **No dummy activities are ever required**; easily accommodates SS, FF, and SF with lags.

---

## 5. Module 3: Float Analysis & Critical Path Method (CPM)
**Source**: [3. CONSTRUCTION PLANNING-FLOATS.pdf](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/3.%20CONSTRUCTION%20PLANNING-FLOATS.pdf)

### 1. Definitions & Exact Formulas

```
+---------------------------------------------------------------------------------+
| 1. Total Float (TF)         | TF = LS - ES = LF - EF                            |
| 2. Free Float (FF)          | FF_i = min_j(ES_j) - EF_i                         |
| 3. Interfering Float (INTF) | INTF = TF - FF = LF_i - min_j(ES_j)               |
| 4. Independent Float (INDF) | INDF_j = max(0, min_k(ES_k) - max_i(LF_i) - D_j)  |
+---------------------------------------------------------------------------------+
```

- **Total Float ($TF$)**: Time an activity can be delayed without delaying the **overall project finish date**.
- **Free Float ($FF$)**: Time an activity can be delayed without delaying the **earliest start ($ES$) of any following activity**.
- **Interfering Float ($INTF$)**: The portion of total float that, if consumed, **delays subsequent non-critical activities** (consumes successor float) without delaying project completion. Mathematically equal to Head Event Slack ($L_j - E_j$).
- **Independent Float ($INDF$)**: The float available when predecessor activities finish as late as possible ($LF$) and successor activities start as early as possible ($ES$). It is **completely autonomous**—consuming it affects neither predecessors nor successors.

### 2. Complete Solved Slide Example (Lecture 3, Slides 14–16)
Given Network:
- $Start \rightarrow A(4) \rightarrow B(8), C(3), D(2)$
- $B(8) \rightarrow E(7)$
- $C(3) \rightarrow E(7), F(5)$
- $D(2) \rightarrow E(7), F(5)$
- $E(7) \rightarrow G(1) \rightarrow Finish$
- $F(5) \rightarrow G(1) \rightarrow Finish$

**Step 1: Forward Pass ($ES, EF$)**:
- $A$: $ES = 0, EF = 0 + 4 = 4$.
- $B$: $ES = 4, EF = 4 + 8 = 12$.
- $C$: $ES = 4, EF = 4 + 3 = 7$.
- $D$: $ES = 4, EF = 4 + 2 = 6$.
- $E$: Predecessors are $B(12), C(7), D(6) \implies ES = \max(12, 7, 6) = 12$. $EF = 12 + 7 = 19$.
- $F$: Predecessors are $C(7), D(6) \implies ES = \max(7, 6) = 7$. $EF = 7 + 5 = 12$.
- $G$: Predecessors are $E(19), F(12) \implies ES = \max(19, 12) = 19$. $EF = 19 + 1 = 20$.
- **Project Duration = 20 days**.

**Step 2: Backward Pass ($LF, LS$)**:
- $G$: $LF = 20, LS = 20 - 1 = 19$.
- $E$: Successor is $G(19) \implies LF = 19, LS = 19 - 7 = 12$.
- $F$: Successor is $G(19) \implies LF = 19, LS = 19 - 5 = 14$.
- $B$: Successor is $E(12) \implies LF = 12, LS = 12 - 8 = 4$.
- $C$: Successors are $E(12), F(14) \implies LF = \min(12, 14) = 12, LS = 12 - 3 = 9$.
- $D$: Successors are $E(12), F(14) \implies LF = \min(12, 14) = 12, LS = 12 - 2 = 10$.
- $A$: Successors are $B(4), C(9), D(10) \implies LF = \min(4, 9, 10) = 4, LS = 4 - 4 = 0$.

**Step 3: Master Float Table (Identical to Slide 16)**:

| Activity | Dur ($D$) | ES | EF | LS | LF | Total Float ($TF$) | Free Float ($FF$) | Interfering ($INTF$) | Independent ($INDF$) | Critical? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** | 4 | 0 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | **YES** |
| **B** | 8 | 4 | 12 | 4 | 12 | 0 | 0 | 0 | 0 | **YES** |
| **C** | 3 | 4 | 7 | 9 | 12 | **5** | $\min(12, 7) - 7 = \mathbf{0}$ | $5 - 0 = \mathbf{5}$ | $\max(0, 7 - 4 - 3) = \mathbf{0}$ | NO |
| **D** | 2 | 4 | 6 | 10 | 12 | **6** | $\min(12, 7) - 6 = \mathbf{1}$ | $6 - 1 = \mathbf{5}$ | $\max(0, 7 - 4 - 2) = \mathbf{1}$ | NO |
| **E** | 7 | 12 | 19 | 12 | 19 | 0 | 0 | 0 | 0 | **YES** |
| **F** | 5 | 7 | 12 | 14 | 19 | **7** | $19 - 12 = \mathbf{7}$ | $7 - 7 = \mathbf{0}$ | $\max(0, 19 - 12 - 5) = \mathbf{2}$ | NO |
| **G** | 1 | 19 | 20 | 19 | 20 | 0 | 0 | 0 | 0 | **YES** |

- **Critical Path**: $\mathbf{Start \rightarrow A \rightarrow B \rightarrow E \rightarrow G \rightarrow Finish}$ (Duration = 20 days).

---

## 6. Module 4: Resource Levelling & Resource Allocation
**Source**: [4. Resources.pdf](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/4.%20Resources.pdf)

### 1. Classification of Scheduling Problem
- **Time-Constrained (Resource Levelling)**:
  - Imposed project end date is **fixed**. Resources are flexible.
  - Goal: Minimize fluctuations/peaks in resource demand.
  - Method: Shift non-critical activities within their float ($TF, FF$).
  - **Project duration does NOT increase**.
- **Resource-Constrained (Resource Allocation)**:
  - Resource ceiling is **fixed/capped**. Project duration is flexible.
  - Goal: Schedule activities so resource limits are never exceeded.
  - Method: When demand exceeds supply, delay activities based on priority heuristics (e.g., lowest float, shortest duration, lowest activity ID).
  - **Project duration usually increases**.

### 2. Resource Profiles from Lecture 4 (Slides 8, 10, 12)
- **Early Start Priority Profile**: Extreme peak of **11 units** on Days 4–6 (violates resource ceiling of 10).
- **Late Start Priority Profile**: Peak shifts to Days 8–11 at **10 units**.
- **Levelled Profile**: By shifting Activity D by 4 days, peak demand drops to **7 units** across Days 4–6 and 8–11, remaining strictly within the 16-day deadline.

---

## 7. Module 5: Earned Value Analysis (EVA / EVM) & Project Monitoring
**Source**: [5. EVA.pdf](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/5.%20EVA.pdf)

### 1. The Core Metrics
- **Planned Value ($PV$ / $BCWS$)**: Budgeted cost of work scheduled up to evaluation time.
- **Actual Cost ($AC$ / $ACWP$)**: Actual cash disbursed for work accomplished to date.
- **Earned Value ($EV$ / $BCWP$)**: Budgeted value of work *actually completed* ($EV = \% \text{Completed} \times BAC$).

### 2. Status Analysis
- **$CV = EV - AC$**: Negative = Over Budget; Positive = Under Budget.
- **$SV = EV - PV$**: Negative = Behind Schedule; Positive = Ahead of Schedule.
- **$CPI = EV / AC$**: Cost efficiency ($>1$ favorable, $<1$ unfavorable).
- **$SPI = EV / PV$**: Schedule efficiency ($>1$ favorable, $<1$ unfavorable).

### 3. Forecasting Equations
- **$EAC = BAC / CPI$**: Expected total project cost (assuming ongoing cost performance).
- **$ETC = EAC - AC$**: Expected remaining cost to finish.
- **$VAC = BAC - EAC$**: Projected cost overrun/underrun at completion.

### 4. Solved Slide Problems
1. **5 km Road Project (Slide 17)**:
   - $BAC = ₹500\text{ Lakh}$, 5 months (₹100 Lakh/month).
   - Month 2: 1.5 km complete, $AC = ₹180\text{ Lakh}$.
   - $PV = 2 \times 100 = ₹200\text{ Lakh}$; $EV = 1.5 \times 100 = ₹150\text{ Lakh}$.
   - $CV = 150 - 180 = -₹30\text{ Lakh}$ (Over budget).
   - $SV = 150 - 200 = -₹50\text{ Lakh}$ (Behind schedule).
   - $CPI = 150/180 = 0.833$; $SPI = 150/200 = 0.750$.
2. **Wind Power Plant (Slide 18)**:
   - $BAC = \$500,000$, 10 months. Month 5: $AC = \$220,000, EV = \$255,000, PV = \$250,000$.
   - $CPI = 255/220 = \mathbf{1.16}$ (Under budget); $SPI = 255/250 = \mathbf{1.02}$ (Ahead of schedule).

---

## 8. Module 6: Project Crashing & Time-Cost Optimization
**Source**: [6. Project Crashing.pdf](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/6.%20Project%20Crashing.pdf)

### 1. Time-Cost Relationship
- **Direct Costs**: Increase with shorter duration (labor overtime, multiple shifts, premium shipping, larger machinery).
- **Indirect Costs**: Decrease with shorter duration (site overheads, office rent, project manager salaries, liquidated damages).
- **Total Project Cost**: Direct Cost $+$ Indirect Cost (U-shaped curve; minimum point $=$ **Optimum Duration**).

### 2. Cost Slope Formula
$$S = \frac{\text{Crash Cost} - \text{Normal Cost}}{\text{Normal Duration} - \text{Crash Duration}} = \frac{CC - NC}{NT - CT}$$

### 3. Crashing Rules & Parallel Paths
1. Never crash a non-critical activity.
2. Crash the critical activity with the **least cost slope**.
3. When multiple paths become critical, crash either:
   - A single activity common to all critical paths, OR
   - A combination of activities (one per path) that yields the minimum combined slope.

### 4. Complete Lecture Crashing Walkthrough (Slides 5–9)
- Paths: Path 1: $A(120)$; Path 2: $B-C-D-E(140)$; Path 3: $B-F-E(130)$.
- Cost Slopes: $S_A = 100, S_B = 200, S_C = 600, S_D = 60, S_E = 120, S_F = 300$.
- Normal Cost $= \$48,300$, Normal Time $= 140\text{ days}$. Target $= 110\text{ days}$.
- **Stage 1 (140 $\rightarrow$ 130 days)**: Crash $D$ by 10 days ($S_D = \$60/\text{day}$). Cost $+ \$600 \implies \$48,900$. Critical paths: $B-C-D-E$ (130) and $B-F-E$ (130).
- **Stage 2 (130 $\rightarrow$ 120 days)**: Crash common activity $E$ by 10 days ($S_E = \$120/\text{day}$). Cost $+ \$1,200 \implies \$50,100$. All 3 paths are now critical ($A=120, B-C-D-E=120, B-F-E=120$).
- **Stage 3 (120 $\rightarrow$ 115 days)**: Crash $A$ ($100$) $+$ common activity $B$ ($200$) $\implies$ Combined slope $= \$300/\text{day}$. Crash by 5 days (B limit). Cost $+ \$1,500 \implies \$51,600$.
- **Stage 4 (115 $\rightarrow$ 110 days)**: Crash $A$ ($100$) $+ C$ ($600$) $+ F$ ($300$) $\implies$ Combined slope $= \$1,000/\text{day}$. Crash by 5 days. Cost $+ \$5,000 \implies \mathbf{\$56,600}$.

---

## 9. Module 7: Line of Balance (LOB) / Linear Scheduling Method (LSM)
**Source**: [7. CONSTRUCTION PLANNING- PERT.pdf (Pages 2–9)](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/7.%20CONSTRUCTION%20PLANNING-%20PERT.pdf)

### 1. Features & Principles
- Designed for **repetitive, linear projects** (highways, pipelines, multi-story building floors).
- Developed by Goodyear (1940s), formalized by U.S. Navy.
- **Plot**: Y-axis = Repetitive Units/Stations; X-axis = Time.
- **Slope ($R$)**: Production rate ($R = \frac{\Delta \text{Units}}{\Delta \text{Time}}$).

### 2. Crew Clash Rules & Buffers
- **Time Buffer**: Horizontal distance between lines (time float).
- **Distance Buffer**: Vertical distance between lines (physical work buffer).
- **Direction of Divergence/Convergence**:
  - **Successor Slower than Predecessor ($R_2 < R_1$)**: Lines diverge. Governed at **Unit 1**. Start successor immediately after Unit 1 finishes (+ lag).
  - **Successor Faster than Predecessor ($R_2 > R_1$)**: Lines converge. Governed at **Final Unit**. Must delay the start of the successor so that crews do not collide at the end!

### 3. Complete Solved Pipeline Example (Slide 8)
- 1000 m pipeline, 1-day minimum lag:
  1. Excavation ($100\text{ m/day}$): Days 0 to 10 (Duration = 10 days).
  2. Subbase ($125\text{ m/day}$): Faster! Finishes at Day $10 + 1 = 11$. Duration = 8 days $\implies$ Starts at Day $11 - 8 = \mathbf{\text{Day } 3}$.
  3. Pipe Laying ($75\text{ m/day}$): Slower! Starts at Day $3 + 1 = \mathbf{\text{Day } 4}$. Duration = 13.33 days $\rightarrow$ Finishes at **Day 18** (or Day 19).
  4. Backfilling ($200\text{ m/day}$): Faster! Finishes at Day $18 + 1 = 19$. Duration = 5 days $\implies$ Starts at Day $19 - 5 = \mathbf{\text{Day } 14}$.
  5. Compaction ($150\text{ m/day}$): Slower! Starts at Day $14 + 1 = \mathbf{\text{Day } 15}$. Duration = 6.67 days $\rightarrow$ Finishes on **Day 22**.
- Total Project Duration $= \mathbf{22\text{ days}}$.

---

## 10. Module 8: Program Evaluation and Review Technique (PERT)
**Source**: [7. CONSTRUCTION PLANNING- PERT.pdf (Pages 10–31)](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/7.%20CONSTRUCTION%20PLANNING-%20PERT.pdf)

### 1. Probabilistic Modeling
- Developed by U.S. Navy (1958) for Polaris Missile Program.
- Suited for non-repetitive R&D projects with high duration uncertainty.
- **3 Time Estimates**:
  - $t_o$ (Optimistic): Minimum duration, 1% tail probability.
  - $t_m$ (Most Likely): Modal duration.
  - $t_p$ (Pessimistic): Maximum duration, 1% tail probability.
- **Expected Duration & Variance**:
  $$t_e = \frac{t_o + 4t_m + t_p}{6}, \quad \sigma = \frac{t_p - t_o}{6}, \quad \sigma^2 = \left(\frac{t_p - t_o}{6}\right)^2$$

### 2. Central Limit Theorem & Project Variance
- Individual activities follow **Beta ($\beta$) distributions**.
- By the **Central Limit Theorem**, the sum of independent activity durations along the critical path converges to a **Normal Distribution**:
  $$T_e = \sum_{\text{critical}} t_e, \quad \sigma_{\text{proj}}^2 = \sum_{\text{critical}} \sigma_i^2 \implies \sigma_{\text{proj}} = \sqrt{\sum \sigma_i^2}$$
- **Standard Normal Variate**:
  $$Z = \frac{T_s - T_e}{\sigma_{\text{proj}}}$$
  - $P(T \le T_e) = 50\%$.
  - For positively skewed projects: $P(T \le T_m) < 50\%$ (typically 30–45%).

### 3. Parallel Critical Paths in PERT
- When two paths have the same expected duration $T_e$:
  - **Rule of Greater Variance**: Select the path with the **larger variance ($\sigma^2$)** as governing. It gives a lower $Z$-value and conservative completion probability.
  - **Common Activities**: If paths share common activities, they are positively correlated; do NOT multiply probabilities ($P_1 \times P_2$). The governing probability is:
    $$\mathbf{P(\text{Project}) = \min(P_1, P_2)}$$

---

---

## 11. Module 9: Construction Contracts, Bidding & PPP Models (Lecture 8 Complete)
**Source**: [8. CONTRACTS.pdf](file:///Users/mohit/moodle-ai/output/Semester_2601/2601-CVL245A/8.%20CONTRACTS.pdf) ([Markdown](file:///Users/mohit/moodle-ai/data/parsed/Semester_2601/2601-CVL245A/8.%20CONTRACTS.md))

### 1. The Bidding Process & Types of Tendering
- **Definition**: Process starting with owner inviting parties to bid and culminating in a signed contract with the selected party.
- **Three Core Types of Tendering**:
  1. **Open Tendering**: Broadly advertised publicly; open to all qualified contractors. Promotes maximum transparency and healthy competition, but high administrative overhead evaluating numerous bids.
  2. **Selective / Prequalified Tendering**: Only shortlisted, pre-qualified contractors with proven technical capabilities are invited. Ensures quality and efficiency, but reduces price competition.
  3. **Negotiated Tendering**: Direct bilateral negotiation with one or two chosen contractors. Provides rapid start and high flexibility (e.g. specialized or emergency works), but risks higher costs due to absence of open market competition.

### 2. Basis of Bid Evaluation
1. **Quality and Cost-Based Selection (QCBS)**:
   - Evaluates both technical score (qualification, experience) and financial quote (cost).
   - **Default for transport infrastructure projects** (roads, highways, urban metro).
2. **Quality-Based Selection (QBS)**:
   - Evaluates purely technical qualification and expertise.
   - Used when technical requirements are highly specialized/complex and technical excellence completely dominates cost (e.g., specialized architectural design, seismic retrofitting consultancy).
3. **Least Cost Method (LCM / L1)**:
   - Bids meeting minimum technical threshold are ranked solely on price (lowest bidder wins).
   - Used for standardized, commodity-type construction where work is routine and non-differentiable.

### 3. Legal Definition & Essentials of a Valid Contract
Under the Indian Contract Act:
> **"An agreement enforceable by law is a contract."** (Contract = Agreement + Enforceability).
> Invariably requires: **Offer + Acceptance (Meeting of the Minds) + Consideration**.

#### The 5 Non-Negotiable Essentials of a Valid Contract:
1. **Competence of Parties**: Must be of age of majority (18+), sound mind (rational judgment), and not disqualified by law.
2. **Free Consent**: Both parties agree on the same thing in the same sense (*consensus ad idem*). Consent is NOT free if caused by:
   - Coercion / Threat
   - Undue Influence
   - Fraud / Misrepresentation
   - Mistake of fact
3. **Definite Proposal & Acceptance**: Terms must be clear, precise, and unambiguous.
4. **Lawful Object & Consideration**: Purpose must not be illegal, immoral, or opposed to public policy.
5. **Enforceability by Law**: Must create legal obligations.

### 4. Contract Documents & Hierarchy
Typical construction contract package consists of:
1. **Contract Agreement Form**: Legal binding deed signed by authorized representatives.
2. **Letter of Acceptance (LoA) & Notice to Proceed (NTP)**.
3. **Contract Drawings**: Site drawings, Architectural, Structural, MEP (HVAC, Electrical, Plumbing), Special detail drawings.
4. **Specifications**:
   - Material quality (e.g. M25 concrete as per IS 456, Fe 500 steel as per IS 1786).
   - Workmanship standards (e.g. 10 mm mortar joints, 7-day curing).
   - Frequency of testing (e.g. concrete cube tests at 7 & 28 days; 3 cubes per $100\text{ m}^3$).
   - Approved manufacturers (e.g. Ultratech/ACC for cement, Fenesta for windows).
5. **General Conditions of Contract (GCC)**: Standard corporate/government legal framework (spells out rights, obligations, payments, dispute clauses). Standard forms: **CPWD GCC** (India) and **FIDIC Red Book** (International, World Bank/ADB).
6. **Special Conditions of Contract (SCC)**: Project-specific amendments/overrides to GCC (defines mobilization advance, specific defects liability period, owner-supplied materials).
7. **Bill of Quantities (BOQ)**: Item-wise net quantities and descriptions.

### 5. Financial Securities, Advances & Deposits Matrix
| Security / Deposit | Amount / Percentage | Timing & Source | Purpose & Refund Mechanism |
| :--- | :--- | :--- | :--- |
| **Earnest Money Deposit (EMD)** | $1\% - 2\%$ of estimated cost | Submitted **with tender bid** | Bid security; proves seriousness; refunded to unsuccessful bidders; forfeited if selected bidder backs out. |
| **Performance Guarantee (PBG)** | Typically $5\%$ of contract value | Submitted **within 14 days of LoA** | Financial assurance of proper contract execution; valid until end of **Defects Liability Period (DLP)**. |
| **Security Deposit (SD)** | Typically $5\%$ of contract value | Deducted from **running progress bills** | Protects owner against latent defects/damages; refunded after DLP completion. |
| **Retention Money** | $5\% - 10\%$ withheld | Withheld from **each monthly bill** | Provides cash leverage to force defect rectification; released in stages (50% on practical completion, 50% after DLP). |
| **Mobilization Advance** | Typically $5\% - 10\%$ | Paid at **project startup** | Interest-bearing or interest-free cash advance for setup/plant; recovered at e.g. $10\%$ per running bill. |

### 6. Critical "Red Flag Clauses" (High Exam Importance)
1. **3-Tier Dispute Resolution Process**:
   - **Tier 1 (Amicable Negotiation)**: Parties meet within **14 days** of written notice.
   - **Tier 2 (Adjudication / DRB)**: If unresolved after **30 days**, referred to an Adjudicator/Dispute Review Board whose interim decision is binding.
   - **Tier 3 (Arbitration)**: If dissatisfied with adjudication, formal arbitration tribunal (ICC, AAA, Indian Arbitration Act) makes final award.
2. **Differing Site Conditions (FIDIC Clause 4.12 - Unforeseeable Physical Conditions)**:
   - Applies when actual subsurface/physical conditions (e.g., hidden groundwater table, hard rock strata) differ materially from tender geotechnical reports.
   - Contractor must notify the Engineer immediately to be entitled to **Time Extension (EoT)** and **Cost Compensation**.
3. **Delays, Suspensions & Force Majeure**:
   - Excusable Delays: Acts of God, war, unexpected government bans $\rightarrow$ Time extension granted.
   - Compensable Delays: Caused directly by owner/engineer (delayed site handover, drawings late) $\rightarrow$ Time + Cost damages.
   - "No-damages-for-delay" clause: Contracts that limit remedy to time extension only, barring monetary claims.
4. **Liquidated Damages (LD) for Delay**:
   - Pre-agreed, genuine pre-estimate of loss for late handover (e.g. ₹50,000/day).
   - **Statutory Cap**: Liquidated damages **CANNOT exceed 10% of total Contract Sum**. (Exceeding 10% requires contract termination or separate litigation).
5. **Quantity Variation Clause (Item Rate Contracts)**:
   - Tender bid rate strictly applies if actual quantity executed is within **$\pm 15\%$** (or $\pm 25\%$).
   - For quantities exceeding $\pm 15\%$, the unit rate is **renegotiated / recalculated** based on current direct costs plus reasonable overheads.
6. **Price Escalation Clause**:
   - Induces lower initial bid price in long-term contracts by owner agreeing to absorb inflation risk in cement, steel, fuel, and minimum statutory labor wages.

### 7. Types of Construction Contracts
| Contract Type | Payment Basis | Risk Allocation | Best Suited Scenario |
| :--- | :--- | :--- | :--- |
| **Lump Sum** | Single fixed price for entire scope | **Contractor takes cost risk**; Owner has budget certainty | Well-defined scope, complete architectural & structural drawings ready before tender. |
| **Item Rate (Unit Price / BOQ)** | Actual measured units in field $\times$ Quoted unit rates | **Shared risk**; Owner absorbs quantity risk, Contractor absorbs unit rate risk | Civil engineering projects where underground quantities cannot be precisely known upfront. |
| **Cost Plus Percentage** | Actual direct cost $+ X\%$ profit | **Owner bears 100% cost risk**; Zero incentive for contractor to save money | Extreme emergencies, disaster recovery, military works. |
| **Cost Plus Fixed Fee** | Actual direct cost $+$ Fixed lump sum fee | Owner bears direct cost risk, but contractor incentivized to finish fast to protect fee margin | Urgent projects where design is evolving concurrently. |
| **Cost Plus Incentive / Target Cost** | Actual cost $+$ Target fee $\pm$ Share of savings/overrun | Shared risk with financial reward for cost savings and penalty for overruns | Large, complex industrial/infrastructure works. |
| **EPC (Turnkey Model)** | Fixed lump sum staged payments | **Contractor bears single-point responsibility** for Engineering, Procurement & Construction | Process plants, power projects, highways where client desires "turn of key" operational asset. |

### 8. Public-Private Partnership (PPP) Delivery Models
- **Core Paradigm**: The public sector purchases **infrastructure services**, NOT physical assets.
- **Why Governments Use PPPs**: Easing state budget deficits, accessing private capital, life-cycle efficiency, optimal risk transfer.
- **The Spectrum of PPP Concession Models**:
  1. **BOT (Build-Operate-Transfer)**:
     - Private sector finances, designs, builds, and operates the facility for a concession period (e.g. 20–30 years), collecting user toll/tariffs to recover debt, equity, and profit, then transfers it back to the government.
  2. **BOOT (Build-Own-Operate-Transfer)**:
     - Differs from BOT in that the private concessionaire **actually holds legal title/ownership** during the concession period. Title significantly improves creditworthiness when borrowing large bank loans.
     - *Indian Examples*: **Delhi-Gurgaon Expressway** (GMR consortium), **Bangalore International Airport (BIAL)**.
  3. **BOO (Build-Own-Operate)**:
     - Private developer builds, owns, and operates the asset permanently (no transfer to government).
     - *Examples*: Independent Power Plants (IPPs) selling electricity to the grid; industrial water treatment plants.
  4. **DBFOT (Design-Build-Finance-Operate-Transfer)**:
     - Comprehensive concession where private entity assumes complete lifecycle responsibility from architectural design to financing and toll collection.
     - *Indian Example*: **Hyderabad Metro Rail Project** (L&T).

---

## 12. High-Yield Solved Problem Repository

### Problem 1: Critical Path & Float Numerical
Consider a 6-activity project:
- Activity A (4 days, pre: none)
- Activity B (6 days, pre: A)
- Activity C (5 days, pre: A)
- Activity D (7 days, pre: B)
- Activity E (8 days, pre: C)
- Activity F (3 days, pre: D, E)

1. Find critical path and project duration.
2. Compute $TF, FF, INTF, INDF$ for Activity C.

**Solution**:
- Paths:
  - Path 1: $A - B - D - F = 4 + 6 + 7 + 3 = \mathbf{20\text{ days}}$.
  - Path 2: $A - C - E - F = 4 + 5 + 8 + 3 = \mathbf{20\text{ days}}$.
  - **Both paths are Critical Paths** (Duration = 20 days).
- For Activity C ($D_C = 5$):
  - Predecessor: A ($EF_A = 4, LF_A = 4$).
  - Successor: E ($ES_E = 9, LS_E = 9$).
  - $ES_C = 4, EF_C = 9$.
  - $LF_C = LS_E = 9 \implies LS_C = 9 - 5 = 4$.
  - $TF = LS - ES = 4 - 4 = \mathbf{0}$.
  - $FF = ES_E - EF_C = 9 - 9 = \mathbf{0}$.
  - $INTF = TF - FF = \mathbf{0}$.
  - $INDF = \mathbf{0}$.
  *(Since C is on a critical path, all its floats are strictly zero!)*

---

### Problem 2: PERT Project Probability
A critical path consists of activities X, Y, Z:
- X: $t_o = 3, t_m = 6, t_p = 9$
- Y: $t_o = 2, t_m = 5, t_p = 14$
- Z: $t_o = 4, t_m = 7, t_p = 10$

Find:
1. $T_e$ and $\sigma_{\text{proj}}$.
2. Probability of finishing in 19 days or earlier.
3. Due date $T_s$ for 95% completion probability ($Z = 1.645$).

**Solution**:
1. Calculations:
   - X: $t_e = \frac{3 + 24 + 9}{6} = 6$; $\sigma^2 = (\frac{9-3}{6})^2 = 1.0$.
   - Y: $t_e = \frac{2 + 20 + 14}{6} = 6$; $\sigma^2 = (\frac{14-2}{6})^2 = 4.0$.
   - Z: $t_e = \frac{4 + 28 + 10}{6} = 7$; $\sigma^2 = (\frac{10-4}{6})^2 = 1.0$.
   - $T_e = 6 + 6 + 7 = \mathbf{19\text{ days}}$.
   - $\sigma_{\text{proj}}^2 = 1.0 + 4.0 + 1.0 = 6.0 \implies \sigma_{\text{proj}} = \sqrt{6} = \mathbf{2.449\text{ days}}$.
2. Probability for $T_s = 19$:
   - $Z = \frac{19 - 19}{2.449} = 0 \implies \mathbf{P = 50\%}$.
3. For 95% Probability:
   - $1.645 = \frac{T_s - 19}{2.449} \implies T_s = 19 + (1.645 \times 2.449) = \mathbf{23.03\text{ days}}$.

---

### Problem 3: Liquidated Damages & Quantity Variation
A contractor is awarded an item rate highway contract with:
- Contract Sum = ₹50 Crore
- Scheduled Completion: 18 months.
- Liquidated Damages clause: ₹2,00,000 per day of delay, capped at 10% of Contract Sum.
- Earthwork quantity in BOQ: $100,000\text{ m}^3$ at quoted rate of ₹300/$\text{m}^3$.
- Variation clause: Unit rate valid for variation up to $\pm 15\%$. Beyond $115\%$, excess is paid at revised rate of ₹260/$\text{m}^3$.

**(a)** If the project is delayed by 60 days without approved extension, what is the Liquidated Damages liability?  
**(b)** If the project is delayed by 300 days, what is the Liquidated Damages liability?  
**(c)** If actual earthwork executed is $130,000\text{ m}^3$, calculate the total payment for earthwork.

**Solution**:
- **(a) For 60 days delay**:
  $$\text{Calculated LD} = 60 \times ₹2,00,000 = ₹1,20,00,000\text{ (₹1.20 Crore)}$$
  $$\text{Cap on LD} = 10\% \times 50\text{ Crore} = ₹5.0\text{ Crore}$$
  Since ₹1.20 Crore < ₹5.0 Crore, **LD payable = ₹1.20 Crore**.
- **(b) For 300 days delay**:
  $$\text{Calculated LD} = 300 \times ₹2,00,000 = ₹6,00,00,000\text{ (₹6.0 Crore)}$$
  Since ₹6.0 Crore exceeds the 10% cap (₹5.0 Crore), **LD is strictly capped at ₹5.0 Crore**.
- **(c) For Earthwork Quantity Variation**:
  - Threshold quantity ($115\%$): $100,000 \times 1.15 = 115,000\text{ m}^3$.
  - Quantity paid at original rate (₹300): $115,000\text{ m}^3 \implies 115,000 \times 300 = ₹3,45,00,000$.
  - Excess quantity above $115\%$: $130,000 - 115,000 = 15,000\text{ m}^3$.
  - Quantity paid at revised rate (₹260): $15,000 \times 260 = ₹39,00,000$.
  - **Total Payment**: $₹3,45,00,000 + ₹39,00,000 = \mathbf{₹3,84,00,000\text{ (₹3.84 Crore)}}$.

---

## 13. Common Exam Traps & Examiner Checkpoints

1. **Adding Standard Deviations Directly**:
   - ❌ WRONG: $\sigma_{\text{proj}} = \sigma_1 + \sigma_2 + \sigma_3$.
   - ✅ RIGHT: Add variances first: $\sigma_{\text{proj}} = \sqrt{\sigma_1^2 + \sigma_2^2 + \sigma_3^2}$.
2. **Crashing Non-Critical Activities**:
   - Never crash an activity just because its cost slope is cheap if it is not on the critical path! Crashing non-critical activities increases direct cost while saving **0 days**.
3. **Independent Float Negative Sign**:
   - If formula $\min(ES_{\text{succ}}) - \max(LF_{\text{pred}}) - D$ gives a negative value, write $\mathbf{INDF = 0}$. Float cannot be negative in standard CPM forward/backward scheduling.
4. **Faster Successor in Line of Balance**:
   - If Activity 2 is faster than Activity 1, its line must NOT start right after Activity 1 on unit 1. It must be anchored at the **last unit** and back-calculated, otherwise a site collision occurs!
5. **Schedule Variance Unit Trap**:
   - $SV = EV - PV$ is expressed in **monetary currency (Rupees/Dollars)**, NOT in days/months!
6. **Central Limit Theorem Prerequisite**:
   - Variances are summable only under the condition that activity durations are **statistically independent** ($\text{Cov} = 0$).
7. **Liquidated Damages Cap**:
   - Liquidated damages cannot be assessed infinitely; they are strictly capped at **10% of the Contract Sum**.
8. **BOOT vs BOT Distinction**:
   - Under BOOT, the concessionaire **owns** the asset during the concession period, which provides collateral to secure bank debt. Under BOT, the concessionaire only holds the right to operate and collect tolls.
9. **Quantity Variation Rate Adjustment**:
   - In item rate contracts with $\pm 15\%$ variation, the revised unit rate applies **ONLY to the excess quantity above 115%**, NOT retroactively to the first 115%!

---
*Good luck on your CVL245 Minor Exam! You have complete command over the material.*
