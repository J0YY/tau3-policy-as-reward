"""Checks for the missing-trial compatibility diagnostic, not imputed scores."""
from scripts.investigate_score_gaps import histogram_from_scores, compatible_completion


def row(reward, missing=False):
    return {'r0':reward,'status':'excluded_infrastructure' if missing else 'ok'}


def test_recover_histogram_from_all_four_reliability_values():
    # One task always passes, one passes twice, one never passes.
    result=histogram_from_scores([50,100*7/18,100/3,100/3],n_tasks=3)
    assert result=={4:1,3:0,2:1,1:0,0:1}


def test_missing_attempt_can_complete_but_observed_failure_cannot():
    target={0:0,1:0,2:0,3:0,4:1}
    assert compatible_completion({'a':[row(1),row(1),row(1),row(None,True)]},target)=={'a':4}
    assert compatible_completion({'a':[row(1),row(1),row(1),row(0)]},target) is None


def test_matching_must_preserve_every_task_and_cannot_remove_success():
    groups={'a':[row(1),row(0),row(None,True),row(None,True)],
            'b':[row(1),row(1),row(1),row(None,True)]}
    witness=compatible_completion(groups,{1:1,4:1})
    assert witness=={'a':1,'b':4}
    assert compatible_completion(groups,{0:1,4:1}) is None
