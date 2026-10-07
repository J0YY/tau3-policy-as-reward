"""Generate publication tables and figures from saved audit outputs."""

import json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/generated"
FIG = ROOT / "paper/figures"


def esc(x):
    return str(x).replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")


def label(s):
    sid = s["submission"]
    if "gpt-5-2-none" in sid:
        return "GPT-5.2 (none)"
    if sid == "gpt-5-2_sierra_2026-02-26":
        return "GPT-5.2 (high)"
    if "gpt-live-1-astra" in sid:
        return "GPT-live-1 (Astra, high)"
    if "gpt-live-1-diamond" in sid:
        return "GPT-live-1 (Diamond)"
    if "gemini-3-1-flash-live" in sid:
        return "Gemini 3.1 Flash Live (high)"
    return s["model"]


def stacked(ax, names, vals, labels, colors):
    left = np.zeros(len(names))
    for values, lab, col in zip(np.asarray(vals).T, labels, colors):
        ax.barh(
            np.arange(len(names)), values, left=left, height=0.5, color=col, label=lab
        )
        for j, v in enumerate(values):
            if v >= 5:
                ax.text(
                    left[j] + v / 2,
                    j,
                    str(int(v)),
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white"
                    if col in ("#25445a", "#3b7183", "#587747")
                    else "#15232d",
                )
        left += values
    ax.set_yticks(range(len(names)), names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 111)
    ax.set_xticks([0, 25, 50, 75, 100, 111])
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(
        ncol=min(len(labels), 3),
        loc="upper left",
        bbox_to_anchor=(0, -0.27),
        frameon=False,
        fontsize=8,
    )


def main():
    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    d = json.loads((ROOT / "results/summary.json").read_text())
    s = json.loads((ROOT / "results/state_outcomes.json").read_text())
    subs = d["submissions"]
    matches = sum(x["matches_published"] for x in subs)
    (OUT / "results.tex").write_text(
        "\n".join(
            "\\newcommand{\\" + k + "}{" + v + "}"
            for k, v in {
                "NumRuns": f"{d['total_simulations']:,}",
                "NumSubs": str(len(subs)),
                "NumMatches": str(matches),
                "NumGains": "0",
            }.items()
        )
        + "\n"
    )
    rows = [
        r
        for p in (ROOT / "results/public").glob("*.json")
        for r in json.loads(p.read_text())["rows"]
    ]
    infra = sum(r["status"] == "excluded_infrastructure" for r in rows)
    (OUT / "coverage.tex").write_text(
        f"We replay {d['total_simulations']:,} simulations from {len(subs)} submissions. Under the upstream metric convention, {infra} infrastructure failures are excluded; all remaining simulations have resolved replay outcomes. The pinned evaluator reproduces {matches} published submission scores to their recorded precision. The main state analysis uses all accessible submissions, and reproduced-score sensitivities are reported separately.\n"
    )
    c = s["counts"]
    a = c["task_084"]
    b = c["task_086"]
    p = c["task_082"]
    text = f"The \\$275 transaction has a dispute record in {a['extra084']} of 111 runs ({100 * a['extra084'] / 111:.1f}\\%); the \\$350 transaction is recorded in {b['extra086']} ({100 * b['extra086'] / 111:.1f}\\%). The remaining runs omit the named record. An omission is compatible with the reference cap, but can also arise from incomplete execution.\n\n"
    text += f"For TechWorld in task 084, {a['liability_category'].get('412.88', 0)} runs record the reference \\$412.88, {a['liability_category'].get('500', 0)} record \\$500, {a['liability_category'].get('50', 0)} record \\$50, and {a['liability_category'].get('0', 0)} records zero. Three use other values (one \\$47.50 and two unlimited-liability sentinels); 26 have no record. In task 086, 50 record the reference \\$500, 16 record \\$50, six record zero, 11 use the unlimited-liability sentinel, and 28 have no record.\n\n"
    text += f"The lost-wallet record uses \\code{{yes\\_shared}} in {p['pin_category']['yes_shared']} runs, \\code{{yes\\_observed}} in {p['pin_category']['yes_observed']}, and \\code{{unknown}} in {p['pin_category']['unknown']}; {p['pin_category']['missing record']} have no record. Thus {p['nonshared082']} runs avoid the shared-PIN category. These are stored classifications; their wording does not establish how the PIN was actually compromised.\n\n"
    text += (
        r"\begin{figure}[!htbp]\centering\includegraphics[width=.98\linewidth]{figures/state_outcomes.pdf}\caption{What agents recorded beneath a shared zero task score. Each row uses all 111 scored trials for its task. Counts include premature stops; missing records stay visible. Other liability means \$47.50 or the unlimited-liability sentinel on task 084, and the sentinel on task 086.}\label{fig:states}\end{figure}"
        + "\n"
    )
    (OUT / "state_results.tex").write_text(text)
    fig, axs = plt.subplots(
        3, 1, figsize=(7.5, 5.6), gridspec_kw={"height_ratios": [1, 1, 0.65]}
    )
    stacked(
        axs[0],
        ["084: $275 transfer", "086: $350 charge"],
        [[a["extra084"], 111 - a["extra084"]], [b["extra086"], 111 - b["extra086"]]],
        ["Record present", "Record absent"],
        ["#3b7183", "#d9dfe3"],
    )
    axs[0].set_title(
        "A. Requested claim", loc="left", fontsize=10, fontweight="bold", pad=10
    )
    cats = ["412.88", "500", "50", "0", "other", "missing record"]
    vals = []
    for x in (a, b):
        h = x["liability_category"]
        vals.append(
            [
                h.get(k, 0)
                if k != "other"
                else sum(
                    v
                    for k2, v in h.items()
                    if k2 not in ["412.88", "500", "50", "0", "missing record"]
                )
                for k in cats
            ]
        )
    stacked(
        axs[1],
        ["084: TechWorld", "086: TechWorld"],
        vals,
        ["$412.88", "$500", "$50", "$0", "Other", "No record"],
        ["#25445a", "#3b7183", "#b7cfbd", "#80b4a0", "#d7b892", "#d9dfe3"],
    )
    axs[1].set_title(
        "B. Maximum liability in the TechWorld record",
        loc="left",
        fontsize=10,
        fontweight="bold",
        pad=10,
    )
    stacked(
        axs[2],
        ["082: lost wallet"],
        [
            [
                p["pin_category"].get(k, 0)
                for k in ("yes_shared", "yes_observed", "unknown", "missing record")
            ]
        ],
        ["Shared", "Observed", "Unknown", "No record"],
        ["#25445a", "#80b4a0", "#d7b892", "#d9dfe3"],
    )
    axs[2].set_title(
        "C. PIN classification", loc="left", fontsize=10, fontweight="bold", pad=10
    )
    fig.subplots_adjust(left=0.22, right=0.98, top=0.94, bottom=0.12, hspace=1.45)
    fig.savefig(FIG / "state_outcomes.pdf")
    plt.close(fig)
    names = {
        "extra084": r"\$275 claim recorded (084)",
        "extra086": r"\$350 claim recorded (086)",
        "low084": r"TechWorld liability $0$--$50$ (084)",
        "low086": r"TechWorld liability $0$--$50$ (086)",
        "nonshared082": "Nonshared PIN category (082)",
    }
    lines = [
        r"\begin{table}[!htbp]\centering\small",
        r"\begin{tabular}{p{.40\linewidth}rrr}",
        r"\toprule Recorded outcome & Spearman $\rho$ & Family-centered & Family bootstrap \\",
        r" & & rank correlation & interval for $\rho$ \\",
        r"\midrule",
    ]
    for metric, name in names.items():
        v = s["associations"][metric]
        lo, hi = v["raw_spearman_family_bootstrap_95_percentile"]
        lines.append(
            f"{name} & {v['spearman']:.2f} & {v['family_centered_rank_correlation']:.2f} & [{lo:.2f}, {hi:.2f}] "
            + r"\\"
        )
    lines += [
        r"\bottomrule\end{tabular}",
        r"\caption{Capability and recorded state across 32 submissions. Capability uses the same 81 unaffected tasks for every submission. Outcome rates are unconditional over scored trials. Intervals are 95\% percentile sensitivities from resampling nine model families; they refer to ordinary Spearman, not the centered statistic.}\label{tab:capability}\end{table}",
    ]
    v = s["associations"]
    l1 = v["extra084"]["raw_spearman_leave_one_family_out_range"]
    l2 = v["extra086"]["raw_spearman_leave_one_family_out_range"]
    lines += [
        f"Higher unaffected-task scores are associated with less frequent recording of the two omitted claims: Spearman $\\rho={v['extra084']['spearman']:.2f}$ for the \\$275 transfer and ${v['extra086']['spearman']:.2f}$ for the \\$350 charge. Within-family rank adjustment preserves both signs ({v['extra084']['family_centered_rank_correlation']:.2f} and {v['extra086']['family_centered_rank_correlation']:.2f}). Leaving out one family at a time gives ranges [{l1[0]:.2f}, {l1[1]:.2f}] and [{l2[0]:.2f}, {l2[1]:.2f}], respectively.\n"
    ]
    lines += [
        f"The other outcomes move in the opposite direction. Higher scores are associated with more frequent liability values between zero and \\$50 ($\\rho={v['low084']['spearman']:.2f}$ and ${v['low086']['spearman']:.2f}$), and weakly with a nonshared PIN category ($\\rho={v['nonshared082']['spearman']:.2f}$). Table~\\ref{{tab:capability}} shows the family sensitivities. There is no single pattern in which stronger agents uniformly reproduce or uniformly depart from the contested reference records.\n"
    ]
    lines += [
        r"\begin{figure}[!htbp]\centering\includegraphics[width=.98\linewidth]{figures/capability.pdf}\caption{Recorded-state rates against performance on 81 common unaffected tasks. Each panel contains 32 submissions; some points overlap at 0\% and 100\%. Colors identify model-name families. Missing affected-task records count as absence of the plotted outcome. All rates use the 111-trial-per-task cohort, aggregated within submission.}\label{fig:capability}\end{figure}"
    ]
    (OUT / "capability_results.tex").write_text("\n".join(lines) + "\n")
    families = sorted({x["family"] for x in s["submissions"]})
    colors = dict(zip(families, plt.cm.tab10.colors))
    titles = [
        "$275 claim recorded (084)",
        "$350 claim recorded (086)",
        "Liability $0-50 (084)",
        "Liability $0-50 (086)",
        "PIN not shared (082)",
    ]
    fig, axs = plt.subplots(2, 3, figsize=(8.4, 4.7), sharex=True, sharey=True)
    for ax, metric, title in zip(axs.flat, names, titles):
        for sub in s["submissions"]:
            ax.scatter(
                sub["unaffected_score"],
                100 * sub["rates"][metric],
                color=colors[sub["family"]],
                s=24,
                alpha=0.6,
                edgecolors="white",
                linewidths=0.4,
            )
        ax.set_title(title, fontsize=9)
        ax.set_ylim(-5, 105)
        ax.set_yticks([0, 50, 100])
        ax.set_xlim(0, 65)
        ax.set_xticks([0, 20, 40, 60])
        ax.grid(alpha=0.15)
        ax.spines[["top", "right"]].set_visible(False)
    axs[1, 2].axis("off")
    axs[1, 2].legend(
        handles=[Patch(color=colors[f], label=f) for f in families],
        loc="center",
        ncol=2,
        frameon=False,
        fontsize=8,
    )
    fig.supxlabel("Pass rate on common unaffected tasks (%)", fontsize=10)
    fig.supylabel("Runs with recorded outcome (%)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "capability.pdf")
    plt.close(fig)
    full = [
        r"\clearpage\section{Per-submission scores}",
        r"\small",
        r"\begin{longtable}{p{.38\linewidth}rrrr}",
        r"\toprule Submission & Published & Replay$^\dagger$ & Drop tasks & Stricter liability \\",
        r"\midrule\endhead",
    ]
    for x in sorted(subs, key=lambda x: -x["r0"]):
        assert x["r0"] == x["r2_pass1"] == x["r4_pass1"]
        lab = esc(label(x)) + (" $^*$" if not x["matches_published"] else "")
        full.append(
            lab
            + " & "
            + " & ".join(
                f"{float(x[k]):.2f}"
                for k in ["published", "r0", "r1_pass1", "r3_pass1"]
            )
            + r" \\"
        )
    full += [
        r"\bottomrule\end{longtable}",
        r"\normalsize $^\dagger$ Original, primary alternative, and accept-either scores are identical for every submission and share this column. $^*$ Replay does not reproduce the published score. All values are percentages. Higher-$k$ scores, trial coverage, and bootstrap intervals appear in the replication tables.",
    ]
    (OUT / "full_table.tex").write_text("\n".join(full) + "\n")


if __name__ == "__main__":
    main()
