# Analysis plan recorded before trajectory download

Date: 2026-10-07. This is a local prospective analysis plan, **not an OSF
preregistration**. The investigator was already exposed to the supplied seed
findings. New screening and transcript analyses are exploratory.

## Scope and estimands

Pin tau2-bench v1.0.1 at fc0055dc4e0a316c3f83133267fbd6faaa770992.
Freeze the current leaderboard metadata separately and report retrieval,
modality, missing downloads, embedded task versions, and trial counts.
Enumerate all 97 tasks and all policy documents. Machine screening is triage;
it is not an exhaustive human legal audit. No human codes, expert signatures,
inter-rater reliability, or preregistration will be invented.

Primary computational estimands: (1) executable gold failures; (2) changes in
the official reward from controlled, minimally edited actions; (3) observed
public-run success under original and explicitly specified alternative
predicates. Distinguish attempted calls from successful state changes.

## Regimes

R0: pinned official evaluation, retaining independent reward components.
R1: remove tasks 082, 084, 086 (candidate conflicts); sensitivity additionally
removes 085, 087, 088, 091. Report changing denominator explicitly.
R2-state: preserve unaffected state and require the candidate predicates on
082, 084, 086. This is a state-only sensitivity, not complete legal compliance.
R3-state: add contested card-held liability and non-fraud-error fields.
R4-state: original pass OR R2-state pass. This is permissive accommodation,
not certification of lawfulness. A separate human speech annotation can later
add the spec's no-rights-misstatement condition; absent annotations are unknown.

Preserve unrelated fields, user DB, read requirements, actions and assertions.
Masking must handle the filing log and generated IDs, but must not erase
unrelated writes or permit malformed or fabricated disputes. Test both
acceptable changes and adversarial unrelated changes.

## Reporting and uncertainty

Validate R0 against at least three available submission scores. If mismatches
remain, report them rather than forcing agreement. Show pass^1 through pass^4
with their correct combination estimator and actual trials per task. Bootstrap
paired task units with seed 20261007 and 10,000 resamples for sensitivity
deltas. Scores and rank changes are descriptive for this fixed benchmark.

Report predicate passes/failures separately from retained-state failures.
No qualifying public run is also a substantive result. Do not equate null
results with absence of a scoring incentive. Separate controlled constructions
from observed agent behavior and state-only behavior from speech judgments.

Legal directions and clusters remain candidate classifications until the
specified human process is complete. A 50/50 exact binomial calculation can
be a sensitivity illustration; it is not a calibrated test of systematic
bank favoritism. Do not infer real-world consumer harm from simulated dollars.

## Release conditions

Draft the maintainer disclosure but do not send it without user authorization.
Do not post a preprint or claim the disclosure waiting period has elapsed.
Independent AI review is a methodological review, not legal expert sign-off.

## Author amendment after computational results — 7 October 2026

The author removed human coding, expert sign-off, and human-validated speech
analysis as study requirements. The original plan above is retained as a
historical record, not rewritten as though this decision preceded the results.
The manuscript now states the computational scope directly. Legal predicates
remain motivated alternatives, without claims of expert certification. The
primary R4 null, selection limits, and all numerical results are unchanged.
Human coding packets are optional legacy preparation artifacts, not blockers.

## Post hoc extension — 8 October 2026

In response to review, screen all 698 document titles and bodies for explicit
Regulation E, Reg E, and 1005 section references. Review every substantive
line in each matching document, including consistent and customer-benefiting
clauses, under the documented precedence rule. Publish exact text, source
hashes, legal pinpoints, dispositions, and a line-coverage check. This is a
post hoc expansion, not a preregistered or independently coded legal audit.
Keep the three existing mechanism cases and alternative grading predicates
fixed. Investigate the four outstanding score gaps against archived rewards,
metadata histories, and the pinned upstream evaluator. Treat possible missing
trial completions as mathematical diagnostics, never as observed scores.
