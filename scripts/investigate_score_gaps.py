"""Trace published-score gaps to stored rewards, missing runs, and metadata.

Any completion of missing infrastructure trials is a mathematical compatibility
check, never a reconstructed observation or a replacement score.
"""
import argparse
import collections
import hashlib
import json
import math
import statistics
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
META=ROOT/'data/leaderboard/web/leaderboard/public/submissions'
TARGETS=['claude-fable-5_sierra_2026-08-04','claude-opus-4-8_sierra_2026-08-04',
         'gemini-3-1-pro-preview_sierra_2026-05-05','gpt-5-5_sierra_2026-05-05','gpt-5-6-sol_sierra_2026-08-04']

def histogram_from_scores(scores,n_tasks=97,trials=4):
    h={}
    for k in range(trials,0,-1):
        h[k]=round(scores[k-1]*n_tasks/100*math.comb(trials,k)-sum(math.comb(j,k)*h[j] for j in range(k+1,trials+1)))
    h[0]=n_tasks-sum(h.values())
    reconstructed=[sum(math.comb(c,k)*count for c,count in h.items() if c>=k)/math.comb(trials,k)/n_tasks*100 for k in range(1,trials+1)]
    assert all(abs(a-b)<0.005001 for a,b in zip(scores,reconstructed))
    assert all(v>=0 for v in h.values())
    return h

def compatible_completion(groups,target):
    # Bipartite matching of tasks to success-count slots in the target histogram.
    slots=[c for c,count in sorted(target.items()) for _ in range(count)]
    options={}
    for task,rows in groups.items():
        c=int(sum(r.get('r0') or 0 for r in rows))
        m=sum(r['status']=='excluded_infrastructure' for r in rows)
        options[task]=[i for i,v in enumerate(slots) if c<=v<=c+m]
    owners={}
    def assign(task,seen):
        for slot in options[task]:
            if slot in seen:continue
            seen.add(slot)
            if slot not in owners or assign(owners[slot],seen):
                owners[slot]=task;return True
        return False
    if not all(assign(task,set()) for task in sorted(groups,key=lambda t:len(options[t]))):
        return None
    return {task:slots[slot] for slot,task in owners.items()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--trajectories',type=Path,default=ROOT/'data/trajectories');p.add_argument('--fetch-history',action='store_true');p.add_argument('--verify-official',action='store_true');args=p.parse_args()
    output=[]
    for sid in TARGETS:
        rows=json.loads((ROOT/'results/public'/f'{sid}.json').read_text())['rows']
        groups=collections.defaultdict(list)
        for r in rows:groups[r['task']].append(r)
        assert len(groups)==97 and all(len(v)==4 for v in groups.values())
        meta=json.loads((META/sid/'submission.json').read_text())
        published=[meta['results']['banking_knowledge']['pass_'+str(k)] for k in range(1,5)]
        target=histogram_from_scores(published)
        observed=dict(collections.Counter(int(sum(r.get('r0') or 0 for r in rs)) for rs in groups.values()))
        witness=compatible_completion(groups,target)
        path=args.trajectories/sid/'trajectories.json'; raw=json.loads(path.read_text()); sims={s['id']:s for s in raw['simulations']}
        diffs=[];matched=0
        for r in rows:
            stored=(sims[r['simulation']].get('reward_info') or {}).get('reward')
            if stored is None or r.get('r0') is None:continue
            if stored==r['r0']:matched+=1
            else:diffs.append({'task':r['task'],'trial':r['trial'],'simulation':r['simulation'],'stored':stored,'replayed':r['r0'],'termination':sims[r['simulation']]['termination_reason']})
        r={'submission':sid,'model':meta['model_name'],'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
           'archive_commit':raw['info']['git_commit'],'archive_agent':raw['info']['agent_info']['llm'],
           'published_pass_k':published,'replayed_pass_1_excluding_infrastructure':statistics.mean(statistics.mean(x['r0'] for x in rs if x.get('r0') is not None) for rs in groups.values() if any(x.get('r0') is not None for x in rs))*100,
           'replayed_pass_k_with_missing_zero':[sum(math.comb(int(sum(x.get('r0') or 0 for x in rs)),k)/math.comb(len(rs),k) for rs in groups.values())/len(groups)*100 for k in range(1,5)],
           'infrastructure_trials':sum(x['status']=='excluded_infrastructure' for x in rows),
           'stored_reward_matches':matched,'stored_reward_differences':diffs,
           'observed_success_histogram':observed,'published_implied_success_histogram':target,
           'published_vector_compatible_with_only_missing_trial_changes':witness is not None,
           'hypothetical_extra_successes':sum(c*n for c,n in target.items())-sum(c*n for c,n in observed.items()),
           'hypothetical_completion_witness':witness}
        if args.verify_official and diffs:
            from loguru import logger
            from tau2.data_model.simulation import SimulationRun
            from tau2.evaluator.evaluator import evaluate_simulation,EvaluationType
            from tau2.orchestrator.modes import CommunicationMode
            from tau2.runner.build import _derive_read_log_allowlist
            from regrade.core import tasks,normalize_archive_simulation
            logger.remove()
            for diff in diffs:
                task=tasks()[diff['task']]
                assert all(x.value!='NL_ASSERTION' for x in task.evaluation_criteria.reward_basis)
                sim=SimulationRun.model_validate(normalize_archive_simulation(sims[diff['simulation']])[0])
                diff['official_pinned_reward']=evaluate_simulation(simulation=sim,task=task,evaluation_type=EvaluationType.ALL,solo_mode=False,domain='banking_knowledge',mode=CommunicationMode.FULL_DUPLEX if sim.ticks is not None else CommunicationMode.HALF_DUPLEX,env_kwargs={'retrieval_variant':'bm25','read_log_allowlist':_derive_read_log_allowlist(task)},strict_replay=False).reward
                assert diff['official_pinned_reward']==diff['replayed']
        if args.verify_official and sid=='gemini-3-1-pro-preview_sierra_2026-05-05':
            old_task=tasks()['task_074'].model_copy(deep=True)
            edits=0
            for action in old_task.evaluation_criteria.actions:
                if action.name!='call_discoverable_agent_tool' or action.arguments.get('agent_tool_name')!='apply_checking_account_credit_5829':continue
                nested=json.loads(action.arguments['arguments'])
                if nested.get('account_id')=='chk_ar72c5d8e3_2':
                    assert nested['amount']==14.5
                    nested['amount']=8.0
                    action.arguments['arguments']=json.dumps(nested)
                    edits+=1
            assert edits==1
            old_rewards={}
            for source in raw['simulations']:
                if source['task_id']!='task_074':continue
                sim=SimulationRun.model_validate(normalize_archive_simulation(source)[0])
                old_rewards[source['id']]=evaluate_simulation(simulation=sim,task=old_task,evaluation_type=EvaluationType.ALL,solo_mode=False,domain='banking_knowledge',mode=CommunicationMode.HALF_DUPLEX,env_kwargs={'retrieval_variant':'bm25','read_log_allowlist':_derive_read_log_allowlist(old_task)},strict_replay=False).reward
            assert len(old_rewards)==4
            old_groups={t:[old_rewards.get(x['simulation'],x.get('r0') or 0) for x in rs] for t,rs in groups.items()}
            old_scores=[sum(math.comb(int(sum(v)),k)/math.comb(len(v),k) for v in old_groups.values())/len(old_groups)*100 for k in range(1,5)]
            r['earlier_atm_reference_check']={'changed_reference':'task_074 account chk_ar72c5d8e3_2 refund from 14.50 to 8.00 only','official_old_reference_rewards':old_rewards,'pass_k_missing_as_zero':old_scores,'matches_all_published_to_precision':all(abs(a-b)<0.005001 for a,b in zip(old_scores,published)),'interpretation':'Published metrics match the earlier ATM reference. Release history independently documents the single additional success. This identifies a compatible documented grading state, not publication-pipeline timing.'}
            assert r['earlier_atm_reference_check']['matches_all_published_to_precision']
        if args.fetch_history:
            url='https://api.github.com/repos/sierra-research/tau2-bench/commits?path=web/leaderboard/public/submissions/'+sid+'/submission.json&per_page=100'
            req=urllib.request.Request(url,headers={'User-Agent':'tau3-policy-audit'})
            history=json.load(urllib.request.urlopen(req,timeout=30))
            r['metadata_history']=[{'sha':x['sha'],'message':x['commit']['message'],'url':x['html_url']} for x in history]
            r['metadata_history_query']=url
        output.append(r)
        print(sid,'stored differences',len(diffs),'missing-trial compatible',witness is not None,flush=True)
    out={'checked_date':'2026-10-08','rows':output,'duplicate_pass_1_check':{'equal':output[0]['published_pass_k'][0]==output[1]['published_pass_k'][0],'other_pass_k_equal':output[0]['published_pass_k'][1:]==output[1]['published_pass_k'][1:],'conclusion':'Exact pass_1 equality is confirmed. Other metrics differ. Equality alone cannot establish copying. Missing-trial completions are hypothetical, not observed outcomes.'}}
    (ROOT/'results/score_gap_investigation.json').write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
