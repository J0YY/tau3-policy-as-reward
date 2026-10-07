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
        ncol=min(len(labels), 4),
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
        f"We replay {d['total_simulations']:,} public runs from {len(subs)} submissions and reproduce {matches} published scores. We follow the benchmark's convention of excluding {infra} infrastructure failures. The replay returns a result for every remaining run. We use all accessible submissions for the main record analysis and check the reproduced-score subset separately.\n"
    )
    c = s["counts"]
    a = c["task_084"]
    b = c["task_086"]
    p = c["task_082"]
    text = f"Agents file the \\$275 transfer in {a['extra084']} of 111 attempts, or about three in ten. They file the \\$350 charge in {b['extra086']} attempts, or about two in ten. The remaining attempts leave the claim unfiled. Either applying the cap or stopping early could produce an omission.\n\n"
    text += "The TechWorld records also vary. Many agents choose the reference liability, while others choose \\$50 or less. Some record unlimited liability, and others leave no record. The appendix gives every count.\n\n"
    text += f"In the lost-wallet case, {p['pin_category']['yes_shared']} runs classify the PIN as shared. Another {p['nonshared082']} choose observed or unknown, avoiding the reference's sharing category. The remaining {p['pin_category']['missing record']} create no record. These categories describe the agent's entry in the database. They cannot establish how someone obtained the PIN.\n\n"
    text += (
        r"\begin{figure}[!htbp]\centering\includegraphics[width=.98\linewidth]{figures/state_outcomes.pdf}\caption{Agents make different decisions even when they all fail the task. Each row counts 111 attempts at the named scenario, including early stops. Green segments in the liability panel span zero to \$50. The tool uses $-1$ to represent unlimited liability.}\label{fig:states}\end{figure}"
        + "\n"
    )
    (OUT / "state_results.tex").write_text(text)
    details = [
        r"\begin{table}[!htbp]\centering\small",
        r"\begin{tabular}{lrrrrrrr}\toprule Scenario & \$412.88 & \$500 & \$50 & \$47.50 & \$0 & Unlimited & Missing\\\midrule",
    ]
    for name, counts in [(r"\$275 case (084)", a), (r"\$350 case (086)", b)]:
        values = [str(counts['liability_category'].get(k, 0)) for k in ['412.88', '500', '50', '47.5', '0', '-1', 'missing record']]
        details.append(name + " & " + " & ".join(values) + r"\\")
    details += [
        r"\bottomrule\end{tabular}\caption{How much liability agents assign to the TechWorld fraud claim in each capped-claim scenario. Every row sums to 111 runs. Missing means the agent leaves no matching dispute record.}\end{table}",
        r"In the lost-wallet scenario, agents choose \code{yes\_shared} in 54 runs, \code{yes\_observed} in 32, and \code{unknown} in five. Twenty runs leave no record. The observed and unknown categories account for the 37 runs that avoid voluntary sharing.",
    ]
    (OUT / "outcome_details.tex").write_text("\n".join(details) + "\n")
    fig, axs = plt.subplots(
        3, 1, figsize=(7.5, 5.6), gridspec_kw={"height_ratios": [1, 1, 0.65]}
    )
    stacked(
        axs[0],
        ["$275 transfer (084)", "$350 charge (086)"],
        [[a["extra084"], 111 - a["extra084"]], [b["extra086"], 111 - b["extra086"]]],
        ["Record present", "Record absent"],
        ["#3b7183", "#d9dfe3"],
    )
    axs[0].set_title(
        "A. Requested claim", loc="left", fontsize=10, fontweight="bold", pad=10
    )
    cats = ["412.88", "500", "50", "47.5", "0", "-1", "missing record"]
    vals = [[x["liability_category"].get(k, 0) for k in cats] for x in (a, b)]
    assert all(sum(row) == 111 for row in vals)
    stacked(
        axs[1],
        ["$275 case (084)", "$350 case (086)"],
        vals,
        ["$412.88", "$500", "$50", "$47.50", "$0", "Unlimited", "No record"],
        ["#25445a", "#3b7183", "#b7cfbd", "#d8e8c9", "#80b4a0", "#d7b892", "#d9dfe3"],
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
        ["Lost wallet (082)"],
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
        "low084": r"TechWorld $0$--$50$, \$275 case",
        "low086": r"TechWorld $0$--$50$, \$350 case",
        "nonshared082": "Lost-wallet PIN not shared",
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
        r"\caption{How each recorded decision relates to performance on 81 other banking tasks. Positive correlations mean higher-scoring submissions record the outcome more often. Negative correlations mean they do so less often. Each submission contributes one rate, using all its scored attempts. We obtain the 95\% intervals by resampling the nine model families. They describe ordinary Spearman correlation.}\label{tab:capability}\end{table}",
    ]
    v = s["associations"]
    l1 = v["extra084"]["raw_spearman_leave_one_family_out_range"]
    l2 = v["extra086"]["raw_spearman_leave_one_family_out_range"]
    lines += [
        f"Higher-scoring submissions file the omitted claims less often. The correlation is $\\rho={v['extra084']['spearman']:.2f}$ for the \\$275 transfer and ${v['extra086']['spearman']:.2f}$ for the \\$350 charge. Both remain negative after adjusting for model-family averages or leaving out one family at a time. Table~\\ref{{tab:capability}} gives the estimates and intervals.\n",
        "Higher-scoring submissions more often assign at most \\$50 to the TechWorld claim. Their lost-wallet PIN choices have a weaker association with broader performance. Figure~\\ref{fig:capability} shows each submission.\n",
        r"\begin{figure}[!htbp]\centering\includegraphics[width=.98\linewidth]{figures/capability.pdf}\caption{Each point represents a submission. The horizontal axis shows its pass rate on the same 81 other tasks. The vertical axis shows how often it records the named outcome in the disputed scenario. Colors identify model families. Some points overlap at zero and 100\%. Missing records count as absence of the outcome. The panels use all 111 attempts per scenario, grouped by submission.}\label{fig:capability}\end{figure}",
    ]
    robustness = (
        f"The filing correlations stay negative when we leave out one family at a time. For the \\$275 claim they range from {l1[0]:.2f} to {l1[1]:.2f}. For the \\$350 claim they range from {l2[0]:.2f} to {l2[1]:.2f}.\n"
    )
    (OUT / "capability_results.tex").write_text("\n".join(lines) + "\n")
    restricted = json.loads((ROOT / "results/restricted_correlations.json").read_text())
    restricted_lines = [
        r"\subsection{Trial-count sensitivity}\label{sec:trial-sensitivity}",
        robustness,
        r"We repeat the comparison using only submissions with at least three scored attempts at each main scenario. This leaves 27 submissions and 106 trials per scenario. All five submissions we exclude use voice and give the agent access to every tool. The restriction therefore changes the evaluation setup as well as trial count. We keep the same 81 comparison tasks and give each submission equal weight. Both claim-filing correlations become more negative, while the lower-liability correlations stay positive.",
        r"\begin{table}[!htbp]\centering\small",
        r"\begin{tabular}{p{.39\linewidth}rrr}\toprule Recorded outcome & Spearman $\rho$ & Family-centered & Family bootstrap \\",
        r" & & rank correlation & interval for $\rho$ \\\midrule",
    ]
    for metric,name in names.items():
        v=restricted['associations'][metric]; lo,hi=v['raw_spearman_family_bootstrap_95_percentile']
        restricted_lines.append(f"{name} & {v['spearman']:.2f} & {v['family_centered_rank_correlation']:.2f} & [{lo:.2f}, {hi:.2f}] " + r"\\")
    restricted_lines += [r"\bottomrule\end{tabular}\caption{The pattern persists among submissions with at least three attempts per main scenario. We resample model families to obtain the intervals.}\label{tab:restricted}\end{table}"]
    (OUT/'restricted_results.tex').write_text('\n'.join(restricted_lines)+'\n')
    families = sorted({x["family"] for x in s["submissions"]})
    colors = dict(zip(families, plt.cm.tab10.colors))
    titles = [
        "$275 claim recorded (084)",
        "$350 claim recorded (086)",
        "TechWorld in $275 case\nLiability at most 50 dollars",
        "TechWorld in $350 case\nLiability at most 50 dollars",
        "Lost-wallet PIN not shared",
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
    fig.supxlabel("Pass rate on the same 81 other banking tasks (%)", fontsize=10)
    fig.supylabel("Attempts with the named outcome (%)", fontsize=10)
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
