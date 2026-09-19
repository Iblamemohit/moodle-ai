import os
import time
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path as MplPath
import numpy as np
import networkx as nx

from src.config import WORKSPACE_DIR

DIAGRAMS_DIR = Path(WORKSPACE_DIR) / "output" / "diagrams"
DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)


def _get_output_path(filename: Optional[str], default_stem: str) -> Path:
    if filename:
        p = Path(filename)
        if not p.is_absolute():
            p = DIAGRAMS_DIR / p.name
        if p.suffix.lower() != ".png":
            p = p.with_suffix(".png")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    timestamp = int(time.time() * 1000)
    return DIAGRAMS_DIR / f"{default_stem}_{timestamp}.png"


# =====================================================================
# 1. Structural Mechanics (CVL341): SFD & BMD
# =====================================================================

def generate_sfd_bmd(
    beam_type: str = "simply_supported",
    length: float = 6.0,
    loads: Optional[List[Dict[str, Any]]] = None,
    filename: Optional[str] = None,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Solves and plots high-resolution (300 DPI) Shear Force Diagrams (SFD)
    and Bending Moment Diagrams (BMD) for simply supported or cantilever beams.
    Loads support point loads and uniform distributed loads (UDLs).
    """
    if length <= 0:
        length = 6.0

    if loads is None:
        # Default representative engineering problem
        if beam_type.lower() == "cantilever":
            loads = [
                {"type": "udl", "start": 0.0, "end": length, "magnitude": 10.0},
                {"type": "point", "position": length, "magnitude": 25.0}
            ]
        else:
            loads = [
                {"type": "udl", "start": 0.0, "end": length, "magnitude": 15.0},
                {"type": "point", "position": length / 2.0, "magnitude": 40.0}
            ]

    # Support Reactions Calculation
    total_force = 0.0
    moment_about_a = 0.0  # At x = 0

    for ld in loads:
        l_type = ld.get("type", "point").lower()
        if l_type == "point":
            p = float(ld.get("magnitude", 0.0))
            x = float(ld.get("position", 0.0))
            x = max(0.0, min(length, x))
            total_force += p
            moment_about_a += p * x
        elif l_type == "udl":
            w = float(ld.get("magnitude", 0.0))
            a = max(0.0, min(length, float(ld.get("start", 0.0))))
            b = max(0.0, min(length, float(ld.get("end", length))))
            if b > a:
                load_mag = w * (b - a)
                centroid = (a + b) / 2.0
                total_force += load_mag
                moment_about_a += load_mag * centroid

    is_cantilever = (beam_type.lower() == "cantilever")
    if is_cantilever:
        ra = total_force
        rb = 0.0
        ma = -moment_about_a  # Reaction moment at fixed support
    else:
        rb = moment_about_a / length
        ra = total_force - rb
        ma = 0.0

    # Numerical grid for SFD and BMD
    n_pts = 1001
    xs = np.linspace(0.0, length, n_pts)
    sfd = np.zeros(n_pts)
    bmd = np.zeros(n_pts)

    for i, x in enumerate(xs):
        # Shear Force V(x): Sum of vertical forces to the left of section x
        # Sign convention: Upward forces on left = positive shear
        v = ra if x > 1e-6 else ra

        # Bending Moment M(x): Sum of moments of left forces about section x
        # Sign convention: Sagging = positive (+), Hogging = negative (-)
        m = ra * x + (ma if is_cantilever else 0.0)

        for ld in loads:
            l_type = ld.get("type", "point").lower()
            if l_type == "point":
                p_mag = float(ld.get("magnitude", 0.0))
                p_pos = float(ld.get("position", 0.0))
                if x >= p_pos:
                    v -= p_mag
                    m -= p_mag * (x - p_pos)
            elif l_type == "udl":
                w = float(ld.get("magnitude", 0.0))
                u_start = float(ld.get("start", 0.0))
                u_end = float(ld.get("end", length))
                if x > u_start:
                    effective_end = min(x, u_end)
                    if effective_end > u_start:
                        u_len = effective_end - u_start
                        u_force = w * u_len
                        u_centroid = u_start + u_len / 2.0
                        v -= u_force
                        m -= u_force * (x - u_centroid)

        sfd[i] = v
        bmd[i] = m

    max_moment = float(np.max(bmd))
    min_moment = float(np.min(bmd))
    abs_peak_m = max_moment if abs(max_moment) >= abs(min_moment) else min_moment
    peak_idx = int(np.argmax(np.abs(bmd)))
    x_peak = float(xs[peak_idx])

    # Plot Setup: 3 Subplots (Beam Loading, SFD, BMD)
    fig, (ax_beam, ax_sfd, ax_bmd) = plt.subplots(3, 1, figsize=(10, 8), dpi=300, sharex=True)
    fig.patch.set_facecolor("#FFFFFF")
    for ax in (ax_beam, ax_sfd, ax_bmd):
        ax.set_facecolor("#FAFAFA")
        ax.grid(True, linestyle="--", alpha=0.5, color="#CCCCCC")

    # 1. Beam Layout Plot
    ax_beam.plot([0, length], [0, 0], color="#2C3E50", linewidth=6, solid_capstyle="round")
    ax_beam.set_xlim(-0.5, length + 0.5)
    ax_beam.set_ylim(-2.0, 2.5)
    ax_beam.set_ylabel("Beam Loading", fontsize=10, fontweight="bold", color="#2C3E50")
    ax_beam.set_yticks([])

    # Supports
    if is_cantilever:
        # Hatching wall at x=0
        ax_beam.plot([0, 0], [-1.2, 1.2], color="#2C3E50", linewidth=4)
        for wy in np.linspace(-1.2, 1.2, 9):
            ax_beam.plot([-0.2, 0], [wy - 0.2, wy], color="#7F8C8D", linewidth=1.5)
        ax_beam.text(0, -1.6, f"Fixed Support (A)\n$R_A={ra:.1f}$ kN, $M_A={abs(ma):.1f}$ kN·m",
                     ha="center", fontsize=8, color="#2C3E50")
    else:
        # Pin support at A (x=0)
        pin = patches.Polygon([(-0.2, -0.6), (0.2, -0.6), (0, 0)], closed=True,
                              facecolor="#BDC3C7", edgecolor="#2C3E50", linewidth=1.5)
        ax_beam.add_patch(pin)
        ax_beam.plot([-0.3, 0.3], [-0.6, -0.6], color="#2C3E50", linewidth=2)
        ax_beam.text(0, -1.1, f"$R_A={ra:.1f}$ kN", ha="center", fontsize=8, fontweight="bold", color="#27AE60")

        # Roller support at B (x=length)
        roller = patches.Polygon([(length - 0.2, -0.4), (length + 0.2, -0.4), (length, 0)], closed=True,
                                 facecolor="#BDC3C7", edgecolor="#2C3E50", linewidth=1.5)
        ax_beam.add_patch(roller)
        ax_beam.add_patch(patches.Circle((length - 0.1, -0.55), 0.08, facecolor="#7F8C8D"))
        ax_beam.add_patch(patches.Circle((length + 0.1, -0.55), 0.08, facecolor="#7F8C8D"))
        ax_beam.plot([length - 0.3, length + 0.3], [-0.65, -0.65], color="#2C3E50", linewidth=2)
        ax_beam.text(length, -1.1, f"$R_B={rb:.1f}$ kN", ha="center", fontsize=8, fontweight="bold", color="#27AE60")

    # Draw Loads
    for ld in loads:
        l_type = ld.get("type", "point").lower()
        if l_type == "point":
            p_mag = float(ld.get("magnitude", 0.0))
            p_pos = float(ld.get("position", 0.0))
            ax_beam.annotate(
                f"{p_mag:.1f} kN",
                xy=(p_pos, 0.1), xytext=(p_pos, 1.3),
                arrowprops=dict(facecolor="#E74C3C", edgecolor="#C0392B", width=2, headwidth=7),
                ha="center", fontsize=8, fontweight="bold", color="#C0392B"
            )
        elif l_type == "udl":
            w_mag = float(ld.get("magnitude", 0.0))
            u_start = float(ld.get("start", 0.0))
            u_end = float(ld.get("end", length))
            # Draw UDL arrows and top bracket
            u_xs = np.linspace(u_start, u_end, max(4, int((u_end - u_start) * 3)))
            for ux in u_xs:
                ax_beam.annotate(
                    "", xy=(ux, 0.05), xytext=(ux, 0.7),
                    arrowprops=dict(facecolor="#2980B9", edgecolor="#1F618D", width=1, headwidth=4),
                )
            ax_beam.plot([u_start, u_end], [0.7, 0.7], color="#1F618D", linewidth=2)
            ax_beam.text((u_start + u_end) / 2.0, 0.85, f"w = {w_mag:.1f} kN/m",
                         ha="center", fontsize=8, fontweight="bold", color="#1F618D")

    # 2. Shear Force Diagram (SFD)
    ax_sfd.plot(xs, sfd, color="#2980B9", linewidth=2)
    ax_sfd.axhline(0, color="#7F8C8D", linewidth=1, linestyle="-")
    ax_sfd.fill_between(xs, sfd, 0, where=(sfd >= 0), color="#3498DB", alpha=0.3, label="Positive (+)")
    ax_sfd.fill_between(xs, sfd, 0, where=(sfd < 0), color="#E67E22", alpha=0.3, label="Negative (-)")
    ax_sfd.set_ylabel("Shear Force (kN)", fontsize=10, fontweight="bold", color="#2C3E50")
    ax_sfd.text(0.05 * length, max(sfd) * 0.8 if max(sfd) > 0 else 5, f"$V_{{left}} = {sfd[0]:.1f}$ kN",
                fontsize=8, color="#2980B9", fontweight="bold")
    ax_sfd.text(0.85 * length, min(sfd) * 0.8 if min(sfd) < 0 else -5, f"$V_{{right}} = {sfd[-1]:.1f}$ kN",
                fontsize=8, color="#D35400", fontweight="bold")

    # 3. Bending Moment Diagram (BMD)
    ax_bmd.plot(xs, bmd, color="#8E44AD", linewidth=2.5)
    ax_bmd.axhline(0, color="#7F8C8D", linewidth=1, linestyle="-")
    ax_bmd.fill_between(xs, bmd, 0, color="#9B59B6", alpha=0.25)
    ax_bmd.plot(x_peak, abs_peak_m, "ro", markersize=6)
    ax_bmd.annotate(
        f"$M_{{max}} = {abs_peak_m:.1f}$ kN·m\nat $x = {x_peak:.2f}$ m",
        xy=(x_peak, abs_peak_m),
        xytext=(x_peak + 0.3 * (1 if x_peak < length / 2 else -1), abs_peak_m * 1.1),
        arrowprops=dict(facecolor="#8E44AD", arrowstyle="->", lw=1.5),
        fontsize=9, fontweight="bold", color="#8E44AD"
    )
    ax_bmd.set_ylabel("Bending Moment (kN·m)", fontsize=10, fontweight="bold", color="#2C3E50")
    ax_bmd.set_xlabel("Beam Span $x$ (meters)", fontsize=10, fontweight="bold", color="#2C3E50")

    diagram_title = title or f"Shear Force & Bending Moment Diagrams ({beam_type.replace('_', ' ').title()})"
    fig.suptitle(diagram_title, fontsize=12, fontweight="bold", color="#2C3E50", y=0.98)
    fig.tight_layout()

    out_path = _get_output_path(filename, "sfd_bmd")
    fig.savefig(str(out_path), bbox_inches="tight", dpi=300)
    plt.close(fig)

    return {
        "status": "success",
        "diagram_type": "sfd_bmd",
        "beam_type": beam_type,
        "length": length,
        "reactions": {"R_A": round(ra, 2), "R_B": round(rb, 2), "M_A": round(ma, 2)},
        "max_bending_moment": round(abs_peak_m, 2),
        "peak_location_m": round(x_peak, 2),
        "image_path": str(out_path.resolve()),
        "image_url": out_path.resolve().as_uri(),
        "markdown_link": f"![{diagram_title}]({out_path.resolve().as_uri()})"
    }


# =====================================================================
# 2. RCC Design (CVL243): IS 456 Concrete Stress Block
# =====================================================================

def generate_is456_stress_block(
    b: float = 250.0,
    d: float = 450.0,
    fck: float = 25.0,
    fy: float = 415.0,
    Ast: float = 942.0,
    D: Optional[float] = None,
    xu: Optional[float] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Renders the exact IS 456:2000 Limit State Design parabolic-rectangular
    concrete stress block and cross-section diagram with all design forces and strains.
    """
    if D is None:
        D = d + 50.0  # Default 50mm effective cover

    # Limiting neutral axis ratio (IS 456 Cl. 38.1)
    if fy <= 250:
        xu_max_ratio = 0.53
    elif fy <= 415:
        xu_max_ratio = 0.48
    else:
        xu_max_ratio = 0.46
    xu_max = xu_max_ratio * d

    # Actual neutral axis depth (C = T)
    # 0.36 * fck * b * xu = 0.87 * fy * Ast
    if xu is None:
        xu = (0.87 * fy * Ast) / (0.36 * fck * b)

    is_under_reinforced = (xu <= xu_max)
    section_type = "Under-Reinforced" if xu < xu_max else ("Balanced" if abs(xu - xu_max) < 1e-2 else "Over-Reinforced")

    # Compressive force resultant C and Tensile force resultant T
    design_xu = min(xu, xu_max)
    c_force = 0.36 * fck * b * design_xu / 1000.0  # in kN
    t_force = 0.87 * fy * Ast / 1000.0  # in kN
    lever_arm = d - 0.42 * design_xu  # in mm
    mu_knm = (t_force * lever_arm) / 1000.0  # in kN·m

    # Plotting 3 side-by-side columns:
    # 1. Cross-Section, 2. Strain Diagram, 3. IS 456 Stress Block
    fig, (ax_sec, ax_strain, ax_stress) = plt.subplots(1, 3, figsize=(11, 6), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    for ax in (ax_sec, ax_strain, ax_stress):
        ax.set_facecolor("#FAFAFA")
        ax.set_ylim(-D - 20, 40)
        ax.set_yticks([])

    # 1. Cross Section
    ax_sec.set_xlim(-b / 2 - 40, b / 2 + 40)
    # Concrete beam rectangle
    beam_rect = patches.Rectangle((-b / 2, -D), b, D, facecolor="#EAEDED", edgecolor="#2C3E50", linewidth=2)
    ax_sec.add_patch(beam_rect)
    # Neutral Axis dashed line
    ax_sec.plot([-b / 2 - 25, b / 2 + 25], [-xu, -xu], color="#C0392B", linestyle="-.", linewidth=1.5)
    ax_sec.text(b / 2 + 5, -xu + 5, f"N.A. ($x_u={xu:.1f}$ mm)", fontsize=8, color="#C0392B", fontweight="bold")
    # Tension Rebar Circles
    rebar_y = -d
    rebar_xs = np.linspace(-b / 2 + 40, b / 2 - 40, 3)
    for rx in rebar_xs:
        ax_sec.add_patch(patches.Circle((rx, rebar_y), 12, facecolor="#2C3E50", edgecolor="#1A252F", zorder=4))
    ax_sec.text(0, rebar_y - 25, f"$A_{{st}}={Ast:.0f}$ mm²", ha="center", fontsize=8, color="#2C3E50", fontweight="bold")

    # Dimensions
    ax_sec.annotate("", xy=(-b / 2, 15), xytext=(b / 2, 15),
                    arrowprops=dict(arrowstyle="<->", color="#2C3E50", lw=1))
    ax_sec.text(0, 20, f"$b = {b:.0f}$ mm", ha="center", fontsize=8, fontweight="bold")
    ax_sec.annotate("", xy=(-b / 2 - 20, 0), xytext=(-b / 2 - 20, -d),
                    arrowprops=dict(arrowstyle="<->", color="#2980B9", lw=1))
    ax_sec.text(-b / 2 - 30, -d / 2, f"$d={d:.0f}$", ha="right", va="center", fontsize=8, color="#2980B9", fontweight="bold")
    ax_sec.set_title("Cross Section", fontsize=10, fontweight="bold", color="#2C3E50")
    ax_sec.axis("off")

    # 2. Strain Profile
    ax_strain.set_xlim(-0.001, 0.007)
    # Neutral Axis line
    ax_strain.plot([-0.001, 0.007], [-xu, -xu], color="#C0392B", linestyle="-.", linewidth=1.5)
    # Central reference axis
    ax_strain.axvline(0, color="#7F8C8D", linewidth=1)
    # Linear Strain triangle
    eps_cu = 0.0035
    eps_y = 0.002
    eps_st = 0.002 + (0.87 * fy / 200000.0)
    ax_strain.plot([eps_cu, 0, -eps_st], [0, -xu, -d], color="#2980B9", linewidth=2.5)
    ax_strain.fill_betweenx([0, -xu], [eps_cu, 0], color="#3498DB", alpha=0.2)
    ax_strain.fill_betweenx([-xu, -d], [0, -eps_st], color="#E67E22", alpha=0.2)

    ax_strain.text(eps_cu, 10, r"$\epsilon_{cu} = 0.0035$", ha="center", fontsize=8, fontweight="bold", color="#2980B9")
    ax_strain.text(-eps_st - 0.0005, -d, r"$\epsilon_{st} \geq \frac{0.87f_y}{E_s}+0.002$", ha="right", fontsize=8, fontweight="bold", color="#D35400")
    ax_strain.set_title("Strain Profile", fontsize=10, fontweight="bold", color="#2C3E50")
    ax_strain.axis("off")

    # 3. IS 456 Stress Block
    ax_stress.set_xlim(-10, 35)
    ax_stress.axvline(0, color="#7F8C8D", linewidth=1)
    ax_stress.plot([-10, 35], [-xu, -xu], color="#C0392B", linestyle="-.", linewidth=1.5)

    # Rectangular zone: 0 to (3/7)*xu
    y_rect_end = -(3.0 / 7.0) * xu
    rect_stress = 0.446 * fck
    ax_stress.plot([0, rect_stress, rect_stress], [0, 0, y_rect_end], color="#27AE60", linewidth=2)

    # Parabolic zone: (3/7)*xu to xu
    n_curve = 100
    y_parab = np.linspace(y_rect_end, -xu, n_curve)
    # Parabola formula according to IS 456
    # stress = 0.446 * fck * [1 - ((y - y_rect_end) / (xu - 3/7 xu))^2]
    rel_y = (y_parab - y_rect_end) / (-xu - y_rect_end)
    parab_stress = rect_stress * (1.0 - rel_y ** 2)
    ax_stress.plot(parab_stress, y_parab, color="#27AE60", linewidth=2)
    ax_stress.plot([0, 0], [0, -xu], color="#27AE60", linewidth=2)

    # Fill stress block
    stress_x = np.concatenate([[rect_stress], parab_stress])
    stress_y = np.concatenate([[0], y_parab])
    ax_stress.fill_betweenx(stress_y, stress_x, 0, color="#2ECC71", alpha=0.3)

    # Compressive force resultant C
    y_c = -0.42 * xu
    ax_stress.annotate(
        f"$C = {c_force:.1f}$ kN\n($0.36 f_{{ck}} b x_u$)",
        xy=(0, y_c), xytext=(18, y_c + 10),
        arrowprops=dict(facecolor="#27AE60", edgecolor="#1E8449", width=2, headwidth=6),
        fontsize=8, fontweight="bold", color="#1E8449"
    )

    # Tensile force resultant T
    ax_stress.annotate(
        f"$T = {t_force:.1f}$ kN\n($0.87 f_y A_{{st}}$)",
        xy=(0, -d), xytext=(18, -d - 10),
        arrowprops=dict(facecolor="#E74C3C", edgecolor="#C0392B", width=2, headwidth=6),
        fontsize=8, fontweight="bold", color="#C0392B"
    )

    # Lever arm z
    ax_stress.annotate("", xy=(-5, y_c), xytext=(-5, -d),
                       arrowprops=dict(arrowstyle="<->", color="#8E44AD", lw=1.5))
    ax_stress.text(-6, (y_c - d) / 2.0, f"Lever Arm $z = {lever_arm:.1f}$ mm",
                   ha="right", va="center", fontsize=8, color="#8E44AD", fontweight="bold", rotation=90)

    ax_stress.text(rect_stress, 10, f"$0.446 f_{{ck}} = {rect_stress:.1f}$ MPa",
                   ha="center", fontsize=8, color="#27AE60", fontweight="bold")
    ax_stress.set_title("IS 456 Stress Block", fontsize=10, fontweight="bold", color="#2C3E50")
    ax_stress.axis("off")

    title_text = f"IS 456:2000 Concrete Stress Block ({section_type} Section: $M_{{u}}={mu_knm:.1f}$ kN·m)"
    fig.suptitle(title_text, fontsize=12, fontweight="bold", color="#2C3E50", y=0.98)
    fig.tight_layout()

    out_path = _get_output_path(filename, "is456_stress_block")
    fig.savefig(str(out_path), bbox_inches="tight", dpi=300)
    plt.close(fig)

    return {
        "status": "success",
        "diagram_type": "is456_stress_block",
        "parameters": {
            "b_mm": b, "d_mm": d, "D_mm": D,
            "fck_MPa": fck, "fy_MPa": fy, "Ast_mm2": Ast
        },
        "results": {
            "xu_mm": round(xu, 2),
            "xu_max_mm": round(xu_max, 2),
            "section_type": section_type,
            "C_force_kN": round(c_force, 2),
            "T_force_kN": round(t_force, 2),
            "lever_arm_mm": round(lever_arm, 2),
            "Mu_kNm": round(mu_knm, 2)
        },
        "image_path": str(out_path.resolve()),
        "image_url": out_path.resolve().as_uri(),
        "markdown_link": f"![{title_text}]({out_path.resolve().as_uri()})"
    }


# =====================================================================
# 3. Construction Management (CVL245): CPM Network Diagram
# =====================================================================

def generate_cpm_network(
    activities: Optional[List[Dict[str, Any]]] = None,
    filename: Optional[str] = None,
    title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes Early Start (ES), Early Finish (EF), Late Start (LS), Late Finish (LF),
    Total Float (TF), and the Critical Path. Renders a publication-grade (300 DPI)
    Activity-on-Node (AON) network diagram using networkx and matplotlib.
    """
    if not activities:
        # Default representative construction project
        activities = [
            {"id": "A", "name": "Site Prep", "duration": 3, "predecessors": []},
            {"id": "B", "name": "Excavation", "duration": 4, "predecessors": ["A"]},
            {"id": "C", "name": "Substructure", "duration": 5, "predecessors": ["B"]},
            {"id": "D", "name": "Procurement", "duration": 6, "predecessors": ["A"]},
            {"id": "E", "name": "Superstructure", "duration": 7, "predecessors": ["C", "D"]},
            {"id": "F", "name": "Finishing", "duration": 3, "predecessors": ["E"]}
        ]

    # Build Graph
    G = nx.DiGraph()
    act_dict = {}
    for act in activities:
        a_id = act["id"]
        dur = float(act.get("duration", 1))
        name = act.get("name", a_id)
        preds = act.get("predecessors", [])
        act_dict[a_id] = {
            "id": a_id, "name": name, "duration": dur,
            "predecessors": preds, "es": 0, "ef": 0, "ls": 0, "lf": 0, "tf": 0, "ff": 0,
            "is_critical": False
        }
        G.add_node(a_id)
        for p in preds:
            G.add_edge(p, a_id)

    # Forward Pass (Topological Order)
    topo_order = list(nx.topological_sort(G))
    for node in topo_order:
        preds = list(G.predecessors(node))
        if not preds:
            es = 0.0
        else:
            es = max(act_dict[p]["ef"] for p in preds)
        ef = es + act_dict[node]["duration"]
        act_dict[node]["es"] = es
        act_dict[node]["ef"] = ef

    project_duration = max(act_dict[node]["ef"] for node in topo_order)

    # Backward Pass (Reverse Topological Order)
    for node in reversed(topo_order):
        succs = list(G.successors(node))
        if not succs:
            lf = project_duration
        else:
            lf = min(act_dict[s]["ls"] for s in succs)
        ls = lf - act_dict[node]["duration"]
        tf = ls - act_dict[node]["es"]
        act_dict[node]["lf"] = lf
        act_dict[node]["ls"] = ls
        act_dict[node]["tf"] = tf
        act_dict[node]["is_critical"] = (abs(tf) < 1e-4)

    critical_path = [n for n in topo_order if act_dict[n]["is_critical"]]

    # Layered layout using topological generations
    generations = list(nx.topological_generations(G))
    pos = {}
    x_gap = 3.5
    y_gap = 2.2

    for gen_idx, gen in enumerate(generations):
        num_in_gen = len(gen)
        y_start = (num_in_gen - 1) * y_gap / 2.0
        for i, node in enumerate(gen):
            pos[node] = (gen_idx * x_gap, y_start - i * y_gap)

    # Plot AON Network
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFAFA")

    # Draw Edges
    for u, v in G.edges():
        is_crit_edge = act_dict[u]["is_critical"] and act_dict[v]["is_critical"] and abs(act_dict[u]["ef"] - act_dict[v]["es"]) < 1e-4
        color = "#C0392B" if is_crit_edge else "#7F8C8D"
        lw = 2.5 if is_crit_edge else 1.2
        p1 = pos[u]
        p2 = pos[v]
        ax.annotate(
            "", xy=p2, xytext=p1,
            arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=15,
                            connectionstyle="arc3,rad=0.0")
        )

    # Draw Nodes as 3-row Information Boxes
    box_w = 2.2
    box_h = 1.2

    for node, (x, y) in pos.items():
        data = act_dict[node]
        is_crit = data["is_critical"]
        header_color = "#C0392B" if is_crit else "#2C3E50"
        bg_color = "#FDEDEC" if is_crit else "#EBF5FB"
        edge_color = "#922B21" if is_crit else "#2980B9"

        # Main box
        rect = patches.FancyBboxPatch(
            (x - box_w / 2.0, y - box_h / 2.0), box_w, box_h,
            boxstyle="round,pad=0.05,rounding_size=0.1",
            facecolor=bg_color, edgecolor=edge_color, linewidth=2, zorder=3
        )
        ax.add_patch(rect)

        # Dividing horizontal lines
        y_div1 = y + box_h / 6.0
        y_div2 = y - box_h / 6.0
        ax.plot([x - box_w / 2.0, x + box_w / 2.0], [y_div1, y_div1], color=edge_color, lw=0.8, zorder=4)
        ax.plot([x - box_w / 2.0, x + box_w / 2.0], [y_div2, y_div2], color=edge_color, lw=0.8, zorder=4)

        # Top row: ES | Dur | EF
        ax.text(x - box_w / 3.0, y + box_h / 3.0, f"ES: {int(data['es'])}", ha="center", va="center", fontsize=7, color="#2C3E50", fontweight="bold", zorder=5)
        ax.text(x, y + box_h / 3.0, f"D: {int(data['duration'])}", ha="center", va="center", fontsize=7, color="#7F8C8D", fontweight="bold", zorder=5)
        ax.text(x + box_w / 3.0, y + box_h / 3.0, f"EF: {int(data['ef'])}", ha="center", va="center", fontsize=7, color="#2C3E50", fontweight="bold", zorder=5)

        # Middle row: Activity ID and Name
        ax.text(x, y, f"{data['id']}: {data['name']}", ha="center", va="center", fontsize=8, color=header_color, fontweight="bold", zorder=5)

        # Bottom row: LS | TF | LF
        ax.text(x - box_w / 3.0, y - box_h / 3.0, f"LS: {int(data['ls'])}", ha="center", va="center", fontsize=7, color="#2C3E50", zorder=5)
        ax.text(x, y - box_h / 3.0, f"TF: {int(data['tf'])}", ha="center", va="center", fontsize=7, color=header_color, fontweight="bold", zorder=5)
        ax.text(x + box_w / 3.0, y - box_h / 3.0, f"LF: {int(data['lf'])}", ha="center", va="center", fontsize=7, color="#2C3E50", zorder=5)

    # Critical Path Legend & Info
    crit_path_str = " -> ".join(critical_path)
    ax.text(
        0.02, 0.05,
        f"Critical Path: {crit_path_str} | Total Duration: {int(project_duration)} days\nRed Boxes = Critical Activities (Zero Float)",
        transform=ax.transAxes, fontsize=9, fontweight="bold", color="#C0392B",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FDEDEC", edgecolor="#C0392B", alpha=0.9)
    )

    all_x = [p[0] for p in pos.values()]
    all_y = [p[1] for p in pos.values()]
    ax.set_xlim(min(all_x) - 2.0, max(all_x) + 2.0)
    ax.set_ylim(min(all_y) - 2.0, max(all_y) + 2.0)
    ax.axis("off")

    diagram_title = title or f"CPM Activity-on-Node Network Diagram (Duration: {int(project_duration)} days)"
    fig.suptitle(diagram_title, fontsize=12, fontweight="bold", color="#2C3E50", y=0.96)
    fig.tight_layout()

    out_path = _get_output_path(filename, "cpm_network")
    fig.savefig(str(out_path), bbox_inches="tight", dpi=300)
    plt.close(fig)

    table_data = []
    for node in topo_order:
        d = act_dict[node]
        table_data.append({
            "activity": d["id"], "name": d["name"], "duration": d["duration"],
            "ES": d["es"], "EF": d["ef"], "LS": d["ls"], "LF": d["lf"], "TF": d["tf"],
            "critical": d["is_critical"]
        })

    return {
        "status": "success",
        "diagram_type": "cpm_network",
        "project_duration": project_duration,
        "critical_path": critical_path,
        "critical_path_str": crit_path_str,
        "activities": table_data,
        "image_path": str(out_path.resolve()),
        "image_url": out_path.resolve().as_uri(),
        "markdown_link": f"![{diagram_title}]({out_path.resolve().as_uri()})"
    }
