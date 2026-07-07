"""Publication-oriented plots for the non-hardware BodyShield run."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PALETTE = {
    "nominal": "#4B5563",
    "domain_randomization": "#2C7FB8",
    "grid_worstcase": "#7B3294",
    "robust_control": "#00876C",
    "sysid_retune": "#B8860B",
    "oracle": "#111827",
    "human_effect_prior": "#D95F02",
    "epec": "#CC6677",
    "bodyshield": "#0F766E",
}


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "figure.dpi": 140,
            "savefig.dpi": 240,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.20,
            "grid.linewidth": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save_all(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(path.with_suffix(".png"), bbox_inches="tight")
    plt.close(fig)


def plot_repair_summary(summary: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    subset = summary[summary["bucket"].isin(["nominal", "seen", "heldout"])]
    order = ["nominal", "domain_randomization", "grid_worstcase", "robust_control", "sysid_retune", "human_effect_prior", "epec", "bodyshield"]
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    pivot = subset.pivot_table(index="method_id", columns="bucket", values="success_rate", aggfunc="mean").reindex(order)
    pivot[["nominal", "seen", "heldout"]].plot(
        kind="bar",
        ax=ax,
        color=["#9CA3AF", "#60A5FA", "#0F766E"],
        width=0.76,
    )
    ax.set_ylim(0, 1)
    ax.set_ylabel("Success rate")
    ax.set_xlabel("")
    ax.set_title("BodyShield preserves nominal performance while repairing seen and held-out shifts")
    ax.legend(title="")
    ax.set_xticklabels([label.replace("_", "\n") for label in pivot.index], rotation=0)
    save_all(fig, out_dir / "repair_seen_heldout")


def plot_search_comparison(search: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.5))
    order = ["random", "one_axis", "grid", "bodybreak"]
    found = search[search["notes"] == "found_break"]
    cost_group = found.groupby("search_mode", as_index=False).agg({"breaking_cost": "mean"})
    all_group = search.groupby("search_mode", as_index=False).agg({"trials": "mean", "notes": lambda s: (s == "found_break").mean()})
    grouped = all_group.merge(cost_group, on="search_mode", how="left")
    grouped["search_mode"] = pd.Categorical(grouped["search_mode"], order, ordered=True)
    grouped = grouped.sort_values("search_mode")
    colors = ["#9CA3AF", "#A78BFA", "#60A5FA", "#0F766E"]
    axes[0].bar(grouped["search_mode"], grouped["breaking_cost"], color=colors)
    axes[0].set_ylabel("Estimated breaking cost")
    axes[0].set_title("Found breaks only")
    axes[1].bar(grouped["search_mode"], grouped["notes"], color=colors)
    axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("Break-found rate")
    axes[1].set_title("Search reliability")
    axes[2].bar(grouped["search_mode"], grouped["trials"], color=colors)
    axes[2].set_ylabel("Evaluator calls")
    axes[2].set_title("Budget used")
    for ax in axes:
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=20)
    fig.suptitle("BodyBreak adversarial search vs. random/grid/one-axis baselines", y=1.05)
    save_all(fig, out_dir / "breaking_search_comparison")


def plot_bodybreak_minimality_audit(audit: pd.DataFrame, out_dir: Path) -> None:
    if audit.empty:
        return
    set_style()
    frame = audit.sort_values(["method_id", "bodybreak_cost", "task_id", "robot_id"]).copy()
    method_labels = {"human_effect_prior": "human", "nominal": "nominal", "epec": "epec"}
    task_labels = {
        "constrained_place": "constrained",
        "pick_place_bin": "pick-place",
        "press_button": "press",
        "rotate_object": "rotate",
        "slide_track": "slide",
    }
    robot_labels = {"so101_urdf": "so101", "widowx250_like": "wx250", "franka_panda": "panda"}
    frame["case"] = [
        f"{method_labels.get(str(method), str(method))} / {task_labels.get(str(task), str(task))} / {robot_labels.get(str(robot), str(robot))}"
        for method, task, robot in zip(frame["method_id"], frame["task_id"], frame["robot_id"])
    ]
    y = list(range(len(frame)))
    height = 0.34
    fig, axes = plt.subplots(1, 2, figsize=(12.0, max(5.8, 0.52 * len(frame) + 1.8)))
    axes[0].barh([value - height / 2 for value in y], frame["dense_best_cost"], height=height, color="#60A5FA", label="Confirmed dense audit")
    axes[0].barh([value + height / 2 for value in y], frame["bodybreak_cost"], height=height, color="#0F766E", label="BodyBreak")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(frame["case"])
    axes[0].tick_params(axis="y", labelsize=8)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Breaking cost")
    axes[0].set_title("Representative found-break costs")
    axes[0].legend(frameon=False)

    colors = ["#CC6677" if bool(value) else "#0F766E" for value in frame["lower_cost_break_found"]]
    axes[1].barh(y, frame["bodybreak_cost_regret"], color=colors)
    axes[1].axvline(0.0, color="#111827", linewidth=0.9)
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([])
    axes[1].invert_yaxis()
    axes[1].set_xlabel("BodyBreak cost - dense best cost")
    axes[1].set_title("Dense-search regret")
    fig.suptitle("BodyBreak dense minimality challenge", y=0.99, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save_all(fig, out_dir / "bodybreak_minimality_audit")


def plot_nominal_vs_radius(radius: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    for method, group in radius.groupby("method_id"):
        ax.scatter(
            group["nominal_success"],
            group["robustness_radius"],
            s=48,
            color=PALETTE.get(method, "#374151"),
            label=method,
            alpha=0.88,
            edgecolor="white",
            linewidth=0.6,
        )
    ax.set_xlabel("Nominal success")
    ax.set_ylabel("Estimated robustness radius")
    ax.set_title("Nominal success hides different embodiment assumptions")
    ax.legend(frameon=False, ncol=2)
    save_all(fig, out_dir / "nominal_vs_radius")


def plot_mechanism_diagram(out_dir: Path) -> None:
    set_style()
    fig, ax = plt.subplots(figsize=(8.0, 2.6))
    ax.axis("off")
    boxes = [
        (0.02, "Nominal policy\nsucceeds"),
        (0.27, "BodyBreak\nfinds minimal failure"),
        (0.53, "Failure-axis\nattribution"),
        (0.76, "BodyShield\nrepairs action representation"),
    ]
    for x, text in boxes:
        ax.add_patch(plt.Rectangle((x, 0.34), 0.20, 0.36, facecolor="#F8FAFC", edgecolor="#0F766E", linewidth=1.4))
        ax.text(x + 0.10, 0.52, text, ha="center", va="center", fontsize=10)
    for x in [0.22, 0.48, 0.72]:
        ax.annotate("", xy=(x + 0.045, 0.52), xytext=(x, 0.52), arrowprops=dict(arrowstyle="->", color="#374151", lw=1.5))
    ax.text(0.50, 0.14, "falsify hidden body/control assumption -> repair against discovered and held-out shifts", ha="center", color="#374151")
    save_all(fig, out_dir / "bodyshield_mechanism")


def plot_high_fidelity_summary(high_fidelity: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    mujoco = high_fidelity[high_fidelity["engine"] == "mujoco"].copy()
    planar = high_fidelity[high_fidelity["engine"] == "mujoco_planar"].copy()
    maniskill = high_fidelity[high_fidelity["engine"] == "maniskill"].copy()
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.2))
    method_order = ["nominal", "random_tuning", "domain_randomization", "grid_worstcase", "robust_control", "bodyshield", "oracle"]
    method_labels = {
        "nominal": "Nominal",
        "random_tuning": "Random tune",
        "domain_randomization": "Domain rand.",
        "grid_worstcase": "Grid worst",
        "robust_control": "Robust ctrl",
        "bodyshield": "BodyShield",
        "oracle": "Oracle",
    }
    if not mujoco.empty:
        grouped = mujoco.groupby("method_id", as_index=False)["success_rate"].mean()
        grouped["method_id"] = pd.Categorical(grouped["method_id"], method_order, ordered=True)
        grouped = grouped.sort_values("method_id")
        y = list(range(len(grouped)))
        axes[0].barh(
            y,
            grouped["success_rate"],
            color=[PALETTE.get(str(method), "#64748B") for method in grouped["method_id"]],
        )
        axes[0].set_xlim(0, 1)
        axes[0].set_xlabel("Mean success")
        axes[0].set_yticks(y)
        axes[0].set_yticklabels([method_labels.get(str(method), str(method)) for method in grouped["method_id"]])
        axes[0].invert_yaxis()
        axes[0].set_title("MuJoCo task-shaped probes", pad=8)
    else:
        axes[0].text(0.5, 0.5, "No MuJoCo rows", ha="center", va="center")
        axes[0].axis("off")

    if not planar.empty:
        grouped = planar.groupby("method_id", as_index=False)["success_rate"].mean()
        grouped["method_id"] = pd.Categorical(grouped["method_id"], method_order, ordered=True)
        grouped = grouped.sort_values("method_id")
        y = list(range(len(grouped)))
        axes[1].barh(
            y,
            grouped["success_rate"],
            color=[PALETTE.get(str(method), "#64748B") for method in grouped["method_id"]],
        )
        axes[1].set_xlim(0, 1)
        axes[1].set_xlabel("Mean success")
        axes[1].set_yticks(y)
        axes[1].set_yticklabels([method_labels.get(str(method), str(method)) for method in grouped["method_id"]])
        axes[1].invert_yaxis()
        axes[1].set_title("MuJoCo planar-effector probes", pad=8)
    else:
        axes[1].text(0.5, 0.5, "No planar rows", ha="center", va="center")
        axes[1].axis("off")

    if not maniskill.empty:
        task_labels = [str(task).replace("-v1", "") for task in maniskill["task_id"]]
        y = list(range(len(maniskill)))
        axes[2].barh(y, maniskill["mean_reward"], color="#7C3AED")
        axes[2].set_xlabel("Mean reward")
        axes[2].set_yticks(y)
        axes[2].set_yticklabels(task_labels)
        axes[2].invert_yaxis()
        axes[2].set_title("ManiSkill random-action suite", pad=8)
    else:
        axes[2].text(0.5, 0.5, "No ManiSkill rows", ha="center", va="center")
        axes[2].axis("off")
    fig.suptitle("Bounded high-fidelity simulator checks", y=0.99, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_all(fig, out_dir / "high_fidelity_summary")


def plot_trajectory_wam_summary(rollouts: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.7))
    colors = {"train_seen_or_nominal": "#60A5FA", "heldout": "#0F766E"}
    labels = {"train_seen_or_nominal": "Train/seen", "heldout": "Held-out"}
    for split, group in rollouts.groupby("split"):
        axes[0].scatter(
            group["true_final_error"],
            group["pred_final_error"],
            s=12,
            alpha=0.35,
            color=colors.get(split, "#64748B"),
            label=labels.get(split, split),
            edgecolor="none",
        )
    max_error = float(max(rollouts["true_final_error"].max(), rollouts["pred_final_error"].max()))
    axes[0].plot([0, max_error], [0, max_error], color="#111827", linewidth=1.0, linestyle="--")
    axes[0].set_xlabel("True final error")
    axes[0].set_ylabel("Predicted final error")
    axes[0].set_title("Trajectory rollout calibration")
    axes[0].legend(frameon=False)

    bucket_order = ["nominal", "seen", "heldout"]
    grouped = rollouts.groupby("bucket", as_index=False)["final_xy_error"].mean()
    grouped["bucket"] = pd.Categorical(grouped["bucket"], bucket_order, ordered=True)
    grouped = grouped.sort_values("bucket")
    axes[1].bar(grouped["bucket"].astype(str), grouped["final_xy_error"], color=["#9CA3AF", "#60A5FA", "#0F766E"])
    axes[1].set_ylabel("Mean final XY error")
    axes[1].set_xlabel("")
    axes[1].set_title("Autoregressive held-out drift")
    fig.suptitle("Synthetic trajectory WAM proxy audit", y=1.02, fontsize=13)
    fig.tight_layout()
    save_all(fig, out_dir / "trajectory_wam_summary")


def plot_corrective_adaptation_summary(rollouts: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.7))
    bucket_order = ["nominal", "seen", "heldout"]
    grouped = rollouts.groupby("bucket", as_index=False).agg(
        base_final_error=("base_final_error", "mean"),
        adapted_final_error=("adapted_final_error", "mean"),
    )
    grouped["bucket"] = pd.Categorical(grouped["bucket"], bucket_order, ordered=True)
    grouped = grouped.sort_values("bucket")
    x = list(range(len(grouped)))
    width = 0.36
    axes[0].bar([value - width / 2 for value in x], grouped["base_final_error"], width=width, color="#9CA3AF", label="Base")
    axes[0].bar([value + width / 2 for value in x], grouped["adapted_final_error"], width=width, color="#0F766E", label="Adapted")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(grouped["bucket"].astype(str))
    axes[0].set_ylabel("Mean final error")
    axes[0].set_title("Corrections trade nominal drift for robustness")
    axes[0].legend(frameon=False)

    heldout = rollouts[rollouts["bucket"] == "heldout"]
    method_order = ["nominal", "domain_randomization", "bodyshield"]
    method_labels = {
        "nominal": "Nominal",
        "domain_randomization": "Domain rand.",
        "bodyshield": "BodyShield",
    }
    method_group = heldout.groupby("method_id", as_index=False)["delta_final_error"].mean()
    method_group["method_id"] = pd.Categorical(method_group["method_id"], method_order, ordered=True)
    method_group = method_group.sort_values("method_id")
    axes[1].bar(
        [method_labels.get(str(method), str(method)) for method in method_group["method_id"]],
        method_group["delta_final_error"],
        color=[PALETTE.get(str(method), "#64748B") for method in method_group["method_id"]],
    )
    axes[1].axhline(0.0, color="#111827", linewidth=0.8)
    axes[1].set_ylabel("Held-out final-error reduction")
    axes[1].set_xlabel("")
    axes[1].set_title("Held-out adaptation gain by policy")
    axes[1].tick_params(axis="x", rotation=12)
    fig.suptitle("Synthetic corrective-trace adaptation audit", y=1.02, fontsize=13)
    fig.tight_layout()
    save_all(fig, out_dir / "corrective_adaptation_summary")


def plot_visual_wam_summary(metrics: pd.DataFrame, rollouts: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.7))
    bucket_order = ["nominal", "seen", "heldout"]
    grouped = rollouts.groupby("bucket", as_index=False)["final_centroid_error"].mean()
    grouped["bucket"] = pd.Categorical(grouped["bucket"], bucket_order, ordered=True)
    grouped = grouped.sort_values("bucket")
    axes[0].bar(grouped["bucket"].astype(str), grouped["final_centroid_error"], color=["#9CA3AF", "#60A5FA", "#0F766E"])
    axes[0].set_ylabel("Final centroid error")
    axes[0].set_xlabel("")
    axes[0].set_title("Autoregressive visual rollout drift")

    split_rows = metrics[metrics["slice"].isin(["split=train_seen_or_nominal", "split=heldout"])].copy()
    split_rows["label"] = split_rows["slice"].map({"split=train_seen_or_nominal": "Train/seen", "split=heldout": "Held-out"})
    axes[1].bar(split_rows["label"], split_rows["transition_psnr_db"], color=["#60A5FA", "#0F766E"])
    axes[1].set_ylabel("Transition PSNR (dB)")
    axes[1].set_xlabel("")
    axes[1].set_title("One-step rendered-frame prediction")
    fig.suptitle("Synthetic visual WAM proxy audit", y=1.02, fontsize=13)
    fig.tight_layout()
    save_all(fig, out_dir / "visual_wam_summary")


def plot_neural_wam_summary(metrics: pd.DataFrame, training_curve: pd.DataFrame, rollouts: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.7))
    axes[0].plot(training_curve["epoch"], training_curve["train_latent_mse"], color="#2C7FB8", linewidth=1.8, label="Train/seen")
    axes[0].plot(training_curve["epoch"], training_curve["heldout_latent_mse"], color="#0F766E", linewidth=1.8, label="Held-out")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Latent MSE")
    axes[0].set_title("NumPy MLP training curve")
    axes[0].legend(frameon=False)

    bucket_order = ["nominal", "seen", "heldout"]
    grouped = rollouts.groupby("bucket", as_index=False)["final_centroid_error"].mean()
    grouped["bucket"] = pd.Categorical(grouped["bucket"], bucket_order, ordered=True)
    grouped = grouped.sort_values("bucket")
    axes[1].bar(grouped["bucket"].astype(str), grouped["final_centroid_error"], color=["#9CA3AF", "#60A5FA", "#0F766E"])
    axes[1].set_ylabel("Final centroid error")
    axes[1].set_xlabel("")
    axes[1].set_title("Autoregressive neural rollout drift")
    heldout = metrics[metrics["slice"] == "split=heldout"]
    if not heldout.empty:
        axes[1].text(
            0.03,
            0.94,
            f"Held-out transition error: {float(heldout.iloc[0]['transition_centroid_error']):.3f}",
            transform=axes[1].transAxes,
            ha="left",
            va="top",
            fontsize=8,
            color="#374151",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 2.5},
        )
    fig.suptitle("Neural visual-latent WAM proxy audit", y=1.02, fontsize=13)
    fig.tight_layout()
    save_all(fig, out_dir / "neural_wam_summary")


def plot_mujoco_residual_policy_summary(rollouts: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.7))
    bucket_order = ["nominal", "seen", "heldout"]
    grouped = rollouts.groupby("bucket", as_index=False).agg(
        base_final_error=("base_final_error", "mean"),
        adapted_final_error=("adapted_final_error", "mean"),
    )
    grouped["bucket"] = pd.Categorical(grouped["bucket"], bucket_order, ordered=True)
    grouped = grouped.sort_values("bucket")
    x = list(range(len(grouped)))
    width = 0.36
    axes[0].bar([value - width / 2 for value in x], grouped["base_final_error"], width=width, color="#9CA3AF", label="Base")
    axes[0].bar([value + width / 2 for value in x], grouped["adapted_final_error"], width=width, color="#0F766E", label="Adapted")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(grouped["bucket"].astype(str))
    axes[0].set_ylabel("Mean final error")
    axes[0].set_title("MuJoCo gated residual rollout error")
    axes[0].legend(frameon=False)

    heldout = rollouts[rollouts["bucket"] == "heldout"]
    method_order = ["nominal", "domain_randomization", "bodyshield"]
    method_labels = {
        "nominal": "Nominal",
        "domain_randomization": "Domain rand.",
        "bodyshield": "BodyShield",
    }
    method_group = heldout.groupby("method_id", as_index=False)["delta_final_error"].mean()
    method_group["method_id"] = pd.Categorical(method_group["method_id"], method_order, ordered=True)
    method_group = method_group.sort_values("method_id")
    axes[1].bar(
        [method_labels.get(str(method), str(method)) for method in method_group["method_id"]],
        method_group["delta_final_error"],
        color=[PALETTE.get(str(method), "#64748B") for method in method_group["method_id"]],
    )
    axes[1].axhline(0.0, color="#111827", linewidth=0.8)
    axes[1].set_ylabel("Held-out final-error reduction")
    axes[1].set_xlabel("")
    axes[1].set_title("Held-out simulator adaptation gain")
    axes[1].tick_params(axis="x", rotation=12)
    fig.suptitle("Learned gated MuJoCo residual policy audit", y=1.02, fontsize=13)
    fig.tight_layout()
    save_all(fig, out_dir / "mujoco_residual_policy_summary")


def plot_mujoco_residual_gate_ablation(ablation: pd.DataFrame, out_dir: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.7))
    variant_order = ["residual_off", "always_on", "non_nominal_only", "gated_default"]
    variant_labels = {
        "residual_off": "Off",
        "always_on": "Always on",
        "non_nominal_only": "No nominal",
        "gated_default": "Gated",
    }
    colors = {
        "residual_off": "#9CA3AF",
        "always_on": "#CC6677",
        "non_nominal_only": "#2C7FB8",
        "gated_default": "#0F766E",
    }
    heldout = ablation[ablation["slice"] == "bucket=heldout"].copy()
    nominal = ablation[ablation["slice"] == "bucket=nominal"].copy()
    for frame in [heldout, nominal]:
        frame["variant"] = pd.Categorical(frame["variant"], variant_order, ordered=True)
        frame.sort_values("variant", inplace=True)

    axes[0].bar(
        [variant_labels.get(str(value), str(value)) for value in heldout["variant"]],
        heldout["delta_final_error"],
        color=[colors.get(str(value), "#64748B") for value in heldout["variant"]],
    )
    axes[0].axhline(0.0, color="#111827", linewidth=0.8)
    axes[0].set_ylabel("Held-out final-error reduction")
    axes[0].set_title("Held-out gain")

    axes[1].bar(
        [variant_labels.get(str(value), str(value)) for value in nominal["variant"]],
        nominal["delta_success_rate"],
        color=[colors.get(str(value), "#64748B") for value in nominal["variant"]],
    )
    axes[1].axhline(0.0, color="#111827", linewidth=0.8)
    axes[1].set_ylabel("Nominal success delta")
    axes[1].set_title("Nominal preservation")
    for ax in axes:
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=12)
    fig.suptitle("MuJoCo residual gate ablation", y=1.02, fontsize=13)
    fig.tight_layout()
    save_all(fig, out_dir / "mujoco_residual_gate_ablation")
