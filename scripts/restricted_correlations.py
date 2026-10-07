"""Repeat the state associations after excluding one-trial submissions."""
import json
from pathlib import Path
from scripts.state_outcomes import associations

ROOT=Path(__file__).resolve().parents[1]

def main():
    state=json.loads((ROOT/'results/state_outcomes.json').read_text())
    subs=[s for s in state['submissions'] if all(n>=3 for n in s['denominators'].values())]
    assert len(subs)==27
    result={'selection':'At least three scored trials on every primary task; same 81 common unaffected tasks, rates, families, and weighting as main analysis.',
            'n_submissions':len(subs),'n_trials_per_primary_task':sum(s['denominators']['extra084'] for s in subs),
            'submissions':[s['submission'] for s in subs], 'associations':associations(subs)}
    (ROOT/'results/restricted_correlations.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
