"""Tool-call checks of dispute-cap omission and archived liability-date fields.

No speech-compliance or legal labels. Read-before-filing requires a completed,
non-error debit-history response for the target user/account before the call.
"""
import collections
import json
from pathlib import Path

from loguru import logger
from tau2.data_model.simulation import SimulationRun
from regrade.core import EXTRA, FILING, LIABILITY, normalize_archive_simulation, trajectory_messages

ROOT = Path(__file__).resolve().parents[1]
HISTORY = 'get_debit_dispute_status_7483'


def parse_object(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def unpack_call(call):
    name = call['name']
    args = parse_object(call.get('arguments'))
    if name == 'call_discoverable_agent_tool':
        return args.get('agent_tool_name'), parse_object(args.get('arguments'))
    return name, args


def successful(response):
    if response is None or response.get('error'):
        return False
    content = str(response.get('content', '')).strip().strip('"').lower()
    return bool(content) and not content.startswith(('error', 'tool error'))


def extract_events(messages, tid):
    target = EXTRA[tid]
    # Preserve order, including simultaneous call groups: a response returned
    # after a filing request is not a prior read for that request.
    responses = {}
    for i, m in enumerate(messages):
        if m.get('role') == 'tool':
            responses[m.get('id')] = (i, m)
    events = []
    for i, m in enumerate(messages):
        if m.get('role') != 'assistant':
            continue
        for call in m.get('tool_calls') or []:
            name, args = unpack_call(call)
            ri, response = responses.get(call.get('id'), (None, None))
            kind = None
            if name == HISTORY and args.get('user_id') == target['user_id']:
                kind = 'debit_history'
            if name == 'query_database' and args.get('database_name') == 'debit_card_disputes':
                # A broad table read counts only if the target account actually
                # appears in the response; a different user's read never counts.
                body = str((response or {}).get('content', ''))
                if target['account_id'] in body:
                    kind = 'debit_history'
            if name == FILING:
                kind = 'filing'
            if kind:
                events.append({'kind': kind, 'name': name, 'call_id': call.get('id'),
                               'call_index': i, 'response_index': ri,
                               'success': successful(response), 'arguments': args})
    return events


def describe_sequence(events, target_account):
    reads = [e for e in events if e['kind'] == 'debit_history']
    completed = [e for e in reads if e['success'] and e['response_index'] is not None]
    filings = [e for e in events if e['kind'] == 'filing' and e['success']
               and e['arguments'].get('account_id') == target_account]
    first = min((e['call_index'] for e in filings), default=None)
    return {
        'history_query_attempted': bool(reads),
        'history_read_completed': bool(completed),
        'read_before_first_target_account_filing': first is not None and any(e['response_index'] < first for e in completed),
        'successful_target_account_filing_count': len(filings),
    }


def main():
    logger.remove()
    state = json.loads((ROOT/'results/state_outcomes.json').read_text())
    state_rows = {(r['submission'], r['simulation']): r for r in state['rows']}
    extra = json.loads((ROOT/'results/extra_state_replays.json').read_text())
    rows = []
    method_names = collections.Counter()
    for f in sorted((ROOT/'results/public').glob('*.json')):
        saved = json.loads(f.read_text())
        sid = f.stem
        wanted = {r['simulation']: r for r in saved['rows'] if r['status'] == 'ok' and r['task'] in EXTRA}
        path = ROOT/saved['provenance']['source']
        archive = json.loads(path.read_text())
        sims = archive.get('simulations') or [json.loads((path.parent/'simulations'/f'{i}.json').read_text()) for i in wanted]
        for raw in sims:
            if raw['id'] not in wanted:
                continue
            record = wanted[raw['id']]
            tid = record['task']
            sim = SimulationRun.model_validate(normalize_archive_simulation(raw)[0])
            messages = [m.model_dump(mode='json', exclude_none=True) for m in trajectory_messages(sim)]
            events = extract_events(messages, tid)
            for m in messages:
                for c in m.get('tool_calls') or []:
                    if m.get('role') == 'assistant':method_names[unpack_call(c)[0]] += 1
            disputes = record.get('disputes', extra.get(raw['id'],{}).get('disputes',[]))
            sr = state_rows[(sid,raw['id'])]
            target = EXTRA[tid]
            target_records = [r for r in disputes if r.get('account_id') == target['account_id']]
            tech = [r for r in disputes if r.get('transaction_id') == LIABILITY[tid]]
            row = {'submission':sid,'simulation':raw['id'],'task':tid,
                   'omitted_claim':not sr['extra'+tid[-3:]], 'termination_reason':record['termination_reason'],
                   **describe_sequence(events,target['account_id']),
                   'target_account_transaction_ids':sorted(r.get('transaction_id','') for r in target_records),
                   'target_account_record_count':len(target_records),
                   'target_account_open_record_count':sum(r.get('status')=='OPEN' for r in target_records),
                   'events':events,'techworld_records':tech,
                   'target_predicate_pass':record.get('r2_details',{}).get('predicate_pass'),
                   'primary_alternative_pass':record.get('r2')}
            # Preserve date-bearing customer utterances as inspectable evidence,
            # not as an automatic intent or compliance classification.
            if sr.get('liability_category') == '-1' and tid == 'task_086':
                row['date_utterances']=[{'message_index':i,'text':m.get('content')} for i,m in enumerate(messages)
                                       if m.get('role')=='user' and isinstance(m.get('content'),str)
                                       and any(x in m['content'].lower() for x in ('january','01/12','october','november','techworld'))]
            rows.append(row)
        print(sid, 'checked',len(wanted),flush=True)
    counts={}
    for tid in sorted(EXTRA):
        subset=[r for r in rows if r['task']==tid]
        assert len(subset)==111
        groups={}
        for omitted in (True,False):
            rs=[r for r in subset if r['omitted_claim']==omitted]
            groups['omitted' if omitted else 'filed']={
                'n':len(rs),
                'read_completed':sum(r['history_read_completed'] for r in rs),
                'read_before_first_target_account_filing':sum(r['read_before_first_target_account_filing'] for r in rs),
                'no_completed_read':sum(not r['history_read_completed'] for r in rs),
                'record_counts_after_prior_read':dict(collections.Counter(r['target_account_record_count'] for r in rs if r['read_before_first_target_account_filing'])),
                'two_open_records_after_prior_read':sum(r['target_account_open_record_count']==2 for r in rs if r['read_before_first_target_account_filing']),
            }
        counts[tid]=groups
    unlimited=[r for r in rows if r['task']=='task_086' and any(t.get('customer_max_liability_amount')==-1 for t in r['techworld_records'])]
    low_other=[r for r in rows if r['task']=='task_084' and any(t.get('customer_max_liability_amount')==47.5 for t in r['techworld_records'])]
    date_counts=collections.defaultdict(collections.Counter)
    for r in rows:
        if r['task']=='task_086':
            for t in r['techworld_records']:
                date_counts[t.get('discovery_date')][f"{t.get('customer_max_liability_amount'):g}"]+=1
    output={'method':'Successful debit-history read for the target customer/account; prior means response before first successful filing request on the capped account. Unlocking a tool and credit-card history queries do not count.',
            'cohort':'All 111 scored trials per task 084/086; premature stops included.',
            'counts':counts,'tool_names':dict(method_names),'rows':rows,
            'unlimited086':[{'submission':r['submission'],'simulation':r['simulation'],'records':r['techworld_records'],'date_utterances':r.get('date_utterances',[])} for r in unlimited],
            'liability47_50_cases':low_other,'task086_date_liability_counts':dict(date_counts)}
    (ROOT/'results/trajectory_checks.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'counts':counts,'unlimited086_n':len(unlimited),'liability47_50_n':len(low_other)},indent=2))


if __name__=='__main__':main()
