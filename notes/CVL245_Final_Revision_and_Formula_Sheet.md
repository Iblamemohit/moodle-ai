# CVL245: Construction Management — Final Revision & Master Formula Sheet
**Designed for Last-Minute Rapid Review (Slot H Minor Exam)**  
*Covers all 8 Lectures with Deep Focus on Lecture 8 (Contracts & Bidding) + Complete Formula Bank.*

---

## 📑 TABLE OF CONTENTS
1. [Master Formula Bank (All Formulas in One Place)](#1-master-formula-bank)
2. [Special Focus: Lecture 8 — Contracts, Bidding & PPPs](#2-special-focus-lecture-8--contracts-bidding--ppps)
3. [Rapid Concept Summaries (Lectures 1 to 7)](#3-rapid-concept-summaries-lectures-1-to-7)
4. [Master Diagram & Curve Cheat Sheet](#4-master-diagram--curve-cheat-sheet)
5. [Top 12 Exam Traps & Examiner Checkpoints](#5-top-12-exam-traps--examiner-checkpoints)

---

# 1. Master Formula Bank

### A. CPM & PDM Forward / Backward Pass
* **Forward Pass**:
  * For $FS + \text{Lag}$: $ES_j \ge EF_i + \text{Lag}$
  * For $SS + \text{Lag}$: $ES_j \ge ES_i + \text{Lag}$
  * For $FF + \text{Lag}$: $ES_j \ge EF_i + \text{Lag} - D_j \quad (EF_j \ge EF_i + \text{Lag})$
  * For $SF + \text{Lag}$: $ES_j \ge ES_i + \text{Lag} - D_j \quad (EF_j \ge ES_i + \text{Lag})$
  * **Master $ES$**: $ES_j = \max(\text{all incoming converted constraints})$, and $EF_j = ES_j + D_j$
* **Backward Pass**:
  * For $FS + \text{Lag}$: $LF_i \le LS_j - \text{Lag}$
  * For $FF + \text{Lag}$: $LF_i \le LF_j - \text{Lag}$
  * For $SS + \text{Lag}$: $LF_i \le (LS_j - \text{Lag}) + D_i \quad (LS_i \le LS_j - \text{Lag})$
  * For $SF + \text{Lag}$: $LF_i \le (LF_j - \text{Lag}) + D_i \quad (LS_i \le LF_j - \text{Lag})$
  * **Master $LF$**: $LF_i = \min(\text{all outgoing converted constraints})$, and $LS_i = LF_i - D_i$
* **Negative Lag (Lead)**: Plug in directly with its negative sign: $EF + (-2) = EF - 2$, $LS - (-2) = LS + 2$.

---

### B. Floats & Slacks
| Float Type | Formula | Property / Key Check |
| :--- | :--- | :--- |
| **Total Float ($TF$)** | $TF = LS - ES = LF - EF$ | Shared along path. Delay without hurting project end. |
| **Free Float ($FF$)** | $FF_i = \min_j(ES_j) - EF_i$ | Exclusively owned. Delay without delaying any successor's $ES$. |
| **Interfering Float ($INTF$)** | $INTF = TF - FF = LF_i - \min_j(ES_j)$ | Head Event Slack ($L_j - E_j$). Pushes non-critical successors. |
| **Independent Float ($INDF$)** | $INDF = \max(0, \; \min(ES_{\text{succ}}) - \max(LF_{\text{pred}}) - D)$ | Autonomous under worst-case. If negative, set to **0**. |
| **Start Float ($SF$)** | $SF_i = LS_i - ES_i$ | Used in PDM when start and finish floats diverge. |
| **Finish Float ($FNF$)** | $FNF_i = LF_i - EF_i$ | Used in PDM when finish is driven by $FF$ link. |

* **Hierarchy Rule**: $\mathbf{TF \ge FF \ge INDF \ge 0}$
* **Additive Rule**: $\mathbf{TF = FF + INTF}$
* **Critical Path**: $\mathbf{TF = FF = INTF = INDF = 0}$

---

### C. Earned Value Analysis (EVA)
* **Planned Value ($PV$)**: $PV = \% \text{Planned Work} \times BAC$ (Baseline Budget)
* **Actual Cost ($AC$)**: Actual recorded spending from invoices
* **Earned Value ($EV$)**: $EV = \% \text{Actual Completed Work} \times BAC$ (Budgeted cost of work done)
* **Cost Variance ($CV$)**: $CV = EV - AC$ ($>0$ Under budget; $<0$ Over budget)
* **Schedule Variance ($SV$)**: $SV = EV - PV$ ($>0$ Ahead; $<0$ Delayed; **measured in monetary currency!**)
* **Cost Performance Index ($CPI$)**: $CPI = EV / AC$ ($>1.0$ efficient; $<1.0$ cost overrun)
* **Schedule Performance Index ($SPI$)**: $SPI = EV / PV$ ($>1.0$ ahead; $<1.0$ delayed)
* **Estimate at Completion ($EAC$)**: $EAC = BAC / CPI$
* **Estimate to Complete ($ETC$)**: $ETC = EAC - AC$
* **Variance at Completion ($VAC$)**: $VAC = BAC - EAC$

---

### D. Project Crashing & Time-Cost Optimization
* **Cost Slope ($S$)**:
  $$S = \frac{\text{Crash Cost} - \text{Normal Cost}}{\text{Normal Time} - \text{Crash Time}} = \frac{CC - NC}{NT - CT} = \frac{\Delta C}{\Delta T}$$
* **Crashing Priority**: Always crash the activity on the **Critical Path** that has the **lowest Cost Slope ($S$)**.
* **Total Cost**: $\text{Total Cost} = \text{Direct Cost} + \text{Indirect Cost}$.
* **Optimum Duration**: The point where Total Cost is at its minimum (slope of direct cost curve equals negative slope of indirect cost line).

---

### E. Line of Balance (LOB / LSM)
* **Production Rate ($R$)**: $R = \text{Slope} = \frac{\Delta \text{Units}}{\Delta \text{Time}}$
* **Slower Successor ($R_2 < R_1$)**: Diverging lines. Anchor buffer at **Unit 1**:
  $$\text{Start}_2(\text{Unit 1}) = \text{Finish}_1(\text{Unit 1}) + \text{Buffer}$$
* **Faster Successor ($R_2 > R_1$)**: Converging lines. Anchor buffer at **Final Unit ($N$)**:
  $$\text{Finish}_2(\text{Unit } N) = \text{Finish}_1(\text{Unit } N) + \text{Buffer}$$
  *(Back-calculate start of Unit 1 to prevent crew collisions!)*

---

### F. PERT (Probabilistic Network)
* **Expected Activity Duration ($t_e$)**: $t_e = \frac{t_o + 4t_m + t_p}{6}$
* **Activity Standard Deviation ($\sigma$)**: $\sigma = \frac{t_p - t_o}{6} \implies \text{Variance } \sigma^2 = \left(\frac{t_p - t_o}{6}\right)^2$
* **Project Expected Duration ($T_e$)**: $T_e = \sum t_e \text{ (along critical path)}$
* **Project Standard Deviation ($\sigma_{\text{proj}}$)**:
  $$\sigma_{\text{proj}} = \sqrt{\sum \sigma_{\text{critical}}^2} = \sqrt{\sigma_1^2 + \sigma_2^2 + \dots + \sigma_k^2}$$
* **Standard Normal Deviate ($Z$)**:
  $$Z = \frac{T_s - T_e}{\sigma_{\text{proj}}} \iff T_s = T_e + (Z \times \sigma_{\text{proj}})$$
* **Core $Z$-Values to Remember**:
  * $Z = 0.00 \implies P = \mathbf{50.0\%}$
  * $Z = +1.00 \implies P = \mathbf{84.13\%}$
  * $Z = +1.28 \implies P = \mathbf{90.0\%}$
  * $Z = +1.645 \implies P = \mathbf{95.0\%}$ *(Exam Classic!)*
  * $Z = +2.00 \implies P = \mathbf{97.72\%}$
  * $Z = +2.33 \implies P = \mathbf{99.0\%}$

---

### G. Contract & Financial Formulas
* **Quantity Variation ($\pm 15\%$)**:
  * Threshold quantity $= 1.15 \times \text{BOQ Quantity}$.
  * Units up to $1.15 \times \text{BOQ}$ are paid at **Quoted Unit Rate**.
  * Units beyond $1.15 \times \text{BOQ}$ are paid at **Revised Unit Rate**.
* **Liquidated Damages ($LD$)**:
  $$\text{Calculated LD} = \text{Delay in Days} \times \text{Daily LD Rate}$$
  $$\text{Maximum LD Payable} = \min(\text{Calculated LD}, \; \mathbf{10\% \times \text{Contract Sum}})$$
* **Cost Plus Incentive Fee (Target Cost)**:
  $$\text{Total Payout} = \text{Actual Cost} + \text{Target Fee} \pm (\text{Contractor Share \%} \times |\text{Target Cost} - \text{Actual Cost}|)$$

---

# 2. Special Focus: Lecture 8 — Contracts, Bidding & PPPs

### A. Bidding Systems & Bid Evaluation
1. **Bidding Methods**:
   * **Open Bidding**: Advertised publicly in press/gazette; open to all qualified contractors; high competition, but high administrative overhead.
   * **Selective / Restricted Bidding**: Limited to pre-qualified shortlists; ensures contractor competence and reduces evaluation time.
   * **Negotiated Bidding**: Direct single-source negotiation; used in emergencies, specialized proprietary technologies, or confidential works.
2. **Bid Evaluation Criteria**:
   * **QCBS (Quality- and Cost-Based Selection)**: Evaluates combined technical score ($e.g., 70\%$) and financial quote ($30\%$). **Default standard for transport, highway, and metro projects**.
   * **QBS (Quality-Based Selection)**: Technical score alone determines winner (100%); used for complex architectural, structural, or seismic retrofitting consultancy.
   * **Least Cost Method (LCM / L1)**: Evaluates lowest price among technically qualified bidders; used for routine, commodity civil construction.

---

### B. Indian Contract Act Essentials
* **Legal Definition**: *"An agreement enforceable by law is a contract."* ($\text{Contract} = \text{Agreement} + \text{Legal Enforceability}$).
* **Fundamental Requirement**: **Offer + Acceptance (Consensus ad idem / Meeting of minds) + Consideration**.
* **The 5 Non-Negotiable Essentials of a Valid Contract**:
  1. **Competence of Parties**: Age of majority ($18+$), sound mind (rational judgment), not disqualified by law (e.g. not an undischarged insolvent or alien enemy).
  2. **Free Consent**: Must be devoid of:
     * *Coercion* (physical threat / unlawful detaining)
     * *Undue Influence* (moral/positional dominance)
     * *Fraud* (intentional deception)
     * *Misrepresentation* (innocent false statement)
     * *Bilateral Mistake of Fact*
  3. **Definite Proposal & Acceptance**: Terms must be clear, precise, and unambiguous.
  4. **Lawful Object & Consideration**: Purpose must not be illegal, immoral, or opposed to public policy.
  5. **Enforceability by Law**: Clear intention to create legal relations.

---

### C. Hierarchy of Contract Documents
If an ambiguity or discrepancy arises during construction, the legally binding priority order is:
1. **Contract Agreement Form** (The signed deed)
2. **Letter of Acceptance (LoA) & Notice to Proceed (NTP)**
3. **Special Conditions of Contract (SCC)** (Overrides GCC)
4. **General Conditions of Contract (GCC)** (Standard CPWD / FIDIC framework)
5. **Technical Specifications** (Material standards IS 456, IS 1786, testing frequency)
6. **Bill of Quantities (BOQ)** (Item rates and descriptions)
7. **Contract Drawings** (Detailed architectural, structural, MEP drawings)
*(Rule: Specific conditions override General conditions; Written numbers override Scaled drawings!)*

---

### D. Securities, Deposits & Advances Matrix

| Financial Instrument | Typical % / Amount | Submitted When / Source | Core Purpose & Refund Stage |
| :--- | :--- | :--- | :--- |
| **Earnest Money Deposit (EMD)** | $1\% - 2\%$ of estimate | With Tender Submission | Ensures bidder seriousness; forfeited if selected bidder refuses to execute contract. Refunded to losers. |
| **Performance Bank Guarantee (PBG)** | Typically $5\%$ of contract value | Within 14 days of LoA | Guarantees proper project execution; valid until end of **Defects Liability Period (DLP)**. |
| **Security Deposit (SD)** | Typically $5\%$ of contract value | Deducted from running progress bills | Protects owner against latent construction defects; refunded upon DLP expiry. |
| **Retention Money** | $5\% - 10\%$ per bill | Withheld from each monthly invoice | Immediate financial leverage over contractor to fix defects (50% released at substantial completion, 50% post-DLP). |
| **Mobilization Advance** | $5\% - 10\%$ of contract sum | Paid at startup upon request | Cash advance to mobilize heavy equipment/camp setup; recovered proportionally (~10% deduction per running bill). |

---

### E. Critical "Red Flag Clauses"
1. **3-Tier Dispute Resolution Hierarchy**:
   $$\text{Amicable Negotiation (14 days)} \longrightarrow \text{Adjudication / DRB (30 days)} \longrightarrow \text{Arbitration (Final & Binding Award)}$$
   *Standard Indian Arbitration Act 1996 / FIDIC framework.*
2. **Differing Site Conditions (FIDIC Clause 4.12)**:
   * Covers *unforeseeable physical conditions* (underground hard rock, unexpectedly high water table).
   * Contractor must notify Engineer immediately $\implies$ Entitled to **Extension of Time (EoT)** AND **Cost Compensation**.
3. **Delay Classification**:
   * **Excusable Delay** (Force Majeure, extreme acts of God): Contractor gets **Time Extension only** (no money).
   * **Compensable Delay** (Owner defaults, drawings late, site handover delayed): Contractor gets **Time Extension + Delay Damages (Overhead costs)**.
   * **Non-Excusable Delay** (Contractor inefficiency, subcontractor default): Contractor pays **Liquidated Damages (LD)**.
4. **Liquidated Damages (LD)**:
   * Genuine pre-estimate of loss agreed before signing.
   * **Strict Statutory Cap: Max 10% of total Contract Sum**. (Exceeding 10% requires contract termination).
5. **Quantity Variation Clause ($\pm 15\%$)**:
   * Quoted unit rates apply strictly within $\pm 15\%$ variation.
   * Beyond $115\%$, revised rate applies **only to the excess portion**.

---

### F. Contract Types & Risk Allocation
* **Lump Sum**: Single fixed price. **Contractor absorbs 100% cost risk**. Requires 100% complete, frozen drawings before tender.
* **Item Rate (BOQ)**: **Shared Risk**:
  * **Owner absorbs Quantity Risk** (pays for actual units measured in field via Measurement Book).
  * **Contractor absorbs Unit Rate Risk** (locked to quoted ₹/unit rate).
  * Ideal for underground civil works, foundations, and highways.
* **Cost Plus Percentage**: Actual Cost $+ X\%$. **Owner absorbs 100% cost risk**. Contractor has zero incentive to economize. Used only in extreme disasters/emergencies.
* **Cost Plus Fixed Fee**: Actual Cost $+$ Flat ₹ fee. Owner takes direct cost risk, but contractor is incentivized to finish fast to protect fee margin.
* **Cost Plus Incentive / Target Cost**: Shared savings / overrun formula.
* **EPC Turnkey**: Single-point responsibility for Engineering, Procurement, and Construction. Contractor delivers a fully operational asset for a fixed sum.

---

### G. Public-Private Partnership (PPP) Models
* **Core Principle**: Governments buy **infrastructure services**, not concrete assets.
* **Concession Models**:
  * **BOT (Build-Operate-Transfer)**: Private consortium finances, builds, and operates (collects user toll for 20–30 years), then transfers facility to government.
  * **BOOT (Build-Own-Operate-Transfer)**: Concessionaire **holds legal title/ownership** during concession, which provides asset collateral to secure large bank loans (*Delhi-Gurgaon Expressway, Bangalore International Airport / BIAL*).
  * **BOO (Build-Own-Operate)**: Permanent private ownership; no transfer to state (*Independent Power Plants / IPPs*).
  * **DBFOT (Design-Build-Finance-Operate-Transfer)**: Complete lifecycle integration (*Hyderabad Metro Rail*).

---

# 3. Rapid Concept Summaries (Lectures 1 to 7)

* **Module 1 (Project Life Cycle)**: Conception $\rightarrow$ Definition $\rightarrow$ Execution $\rightarrow$ Handover. Stakeholder influence drops rapidly as project progresses, while cost of changes increases exponentially!
* **Module 2 (WBS & CPM Basics)**:
  * WBS is deliverables-oriented; adheres to **100% Rule** (sum of children = parent). Work packages are $1\text{ to }10$ days.
  * Precedence relationships: $FS, SS, FF, SF$. Lags ($+$) and Leads ($-$).
  * AOA networks need dummy activities for: (1) Grammatical rule (unique node IDs), (2) Logical rule (distinct dependencies).
* **Module 3 (Float Analysis)**:
  * $TF$: Shared by path ($LS - ES$).
  * $FF$: Delay without moving successor $ES$ ($\min ES_{\text{succ}} - EF$).
  * $INTF$: Head event slack ($TF - FF$).
  * $INDF$: Autonomous cushion ($\min ES_{\text{succ}} - \max LF_{\text{pred}} - D$).
* **Module 4 (Resource Levelling vs Allocation)**:
  * **Levelling (Time-constrained)**: Deadline fixed, resources elastic. Shift non-critical activities within float. Project duration **does not change**.
  * **Allocation (Resource-constrained)**: Resources capped, deadline elastic. Delay activities when demand exceeds limit. Project duration **increases**.
  * *If all activities are critical*: Float is 0. Levelling by shifting is impossible; you must add external resources (overtime/shifts) or project will delay.
* **Module 5 (Earned Value Analysis)**:
  * $PV$ (Budgeted cost of scheduled work), $AC$ (Actual cost of work performed), $EV$ (Budgeted cost of work performed).
  * $CV = EV - AC$ ($>0$ good), $SV = EV - PV$ ($>0$ good).
* **Module 6 (Crashing)**:
  * Direct costs rise; indirect costs drop.
  * Crash critical activities with the **lowest cost slope $S$**.
  * Keep checking for newly emerging parallel critical paths!
* **Module 7 (Line of Balance - LOB / LSM)**:
  * Slope represents production rate $R$ (units/day).
  * Slower successor $\rightarrow$ diverging lines $\implies$ anchor buffer at **Unit 1**.
  * Faster successor $\rightarrow$ converging lines $\implies$ anchor buffer at **Final Unit ($N$)** to avoid site collisions!

---

# 4. Master Diagram & Curve Cheat Sheet

### 1. Earned Value S-Curves & Callouts
```
Cumulative Cost ($)
  ^                                 Planned Value (PV)
  |                              . - '
  |                       . - ' /  <-- Vertical gap between PV and EV = SV ($)
  |                . - '       /
  |         . - ' . - - - - - X (Target Review Date)
  |  . - '       /  Actual Cost (AC)
  | /           / 
  |/           X - - - - - - - - - -+ <-- Vertical gap between AC and EV = CV ($)
  +-----------/   Earned Value (EV) |
  |          /                      |
  +---------X-----------------------+------------------> Time
            |<-- Horizontal Gap --->|
                   Time Delay
```
* If $EV < AC \implies$ **Cost Overrun (Over Budget)**.
* If $EV < PV \implies$ **Behind Schedule**.

---

### 2. Time-Cost Optimization (Crashing) Curve
```
Cost ($)
  ^
  |      \                     /  Total Cost Curve = Direct + Indirect
  |       \   Direct Cost     /
  |        \    Curve        /
  |         \      _.._     /
  |          \  .-'    '-. /
  |           X           X   <--- MINIMUM TOTAL COST POINT = Optimum Duration
  |          /             \
  |         /               \  Indirect Cost Line (Linear downward)
  |        /                 \
  +-------+-------------------+------------------------> Duration (Time)
      Crash Duration      Normal Duration
```

---

### 3. Line of Balance (LOB) Collision Trap
```
Units (Location)
  ^                    Activity B (Faster Gang: R_B > R_A)
  |                   /       /
  |                  /       /  <--- Converging Lines!
  |                 /       /
  |                /   COLLISION! (Activity B crashes into Activity A)
  |               /     ( * )
  |   Activity A /       /
  |      /      /       /
  +-----+------+-------+-------------------------------> Time
      Unit 1
```
* **Remedy**: Shift Activity B's start to the right by anchoring the buffer at the **highest unit**, back-calculating Unit 1.

---

# 5. Top 12 Exam Traps & Examiner Checkpoints

1. **PERT Variance Trap**:
   * ❌ WRONG: $\sigma_{\text{proj}} = \sigma_1 + \sigma_2 + \sigma_3$.
   * ✅ RIGHT: Add variances first! $\sigma_{\text{proj}} = \sqrt{\sigma_1^2 + \sigma_2^2 + \sigma_3^2}$.
2. **Schedule Variance ($SV$) Units**:
   * $SV = EV - PV$ is expressed in **Rupees / Dollars**, NOT in days or months!
3. **Negative Independent Float**:
   * If $\min(ES_{\text{succ}}) - \max(LF_{\text{pred}}) - D < 0$, write $\mathbf{INDF = 0}$. Float cannot be negative in standard scheduling.
4. **Crashing Non-Critical Tasks**:
   * Never crash a non-critical activity even if its cost slope is ₹1/day! Crashing non-critical activities spends money while saving **zero days**.
5. **Parallel Critical Paths During Crashing**:
   * When two paths become critical, you must crash **both simultaneously** (or crash an activity shared by both).
6. **Negative Lag (Lead) in PDM Backward Pass**:
   * For $FS - 2$, the late finish equation is $LF_i \le LS_j - (-2) = \mathbf{LS_j + 2}$.
7. **PDM Finish-to-Finish ($FF$) Forward Pass**:
   * When an $FF$ link drives, $ES_j = EF_{\text{pred}} + \text{Lag}_{FF} - D_j$. Remember to subtract duration to get Early Start!
8. **Item Rate $\pm 15\%$ Quantity Variation**:
   * The revised unit rate applies **ONLY to the excess quantity above 115%**, NOT retroactively to the baseline 115%!
9. **Liquidated Damages ($LD$) 10% Ceiling**:
   * LD is strictly capped at **10% of the total Contract Sum**. If calculations yield 12%, write 10%!
10. **BOOT vs BOT Collateral Rule**:
    * Under BOOT, the concessionaire **owns** the asset during concession, allowing them to use it as mortgage collateral for commercial bank debt.
11. **CPWD / FIDIC Red Flag Resolution**:
    * Negotiation (14 days) $\rightarrow$ Adjudication / DRB (30 days) $\rightarrow$ Arbitration.
12. **All Activities Critical in Resource Levelling**:
    * If all activities are critical, float is 0. Levelling by shifting cannot be done without **increasing project duration**.

---
*You are 100% prepared for your CVL245 Minor Exam. Stay calm, double-check your arithmetic, and ace it!*
