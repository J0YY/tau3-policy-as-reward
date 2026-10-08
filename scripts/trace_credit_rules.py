"""Trace the credit-offset and investigation-clock clauses into reference records.

Run with python -m scripts.trace_credit_rules. This audit does not alter the
benchmark or invent a new scoring requirement for a rule absent from its tools.
"""
import ast
import hashlib
import inspect
import json
import re
from pathlib import Path

from loguru import logger
from regrade.core import FILING, original_reward, record, replay_actions, tasks
from tau2.domains.banking_knowledge import tools as banking_tools
from tau2.domains.banking_knowledge.utils import KNOWLEDGE_TASK_SET_PATH

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'vendor/tau2-bench/data/tau2/domains/banking_knowledge'
CLOCK = re.compile(r'\b45\s*(?:(?:business|calendar)[ -]*)?days?\b|deadline|investigation[_ ](?:end|due|period|duration)|resolution[_ ](?:due|deadline)', re.I)


def strings(value, path=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path + '/' + key, key
            yield from strings(item, path + '/' + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from strings(item, f'{path}/{i}')
    elif isinstance(value, str):
        yield path, value
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            return
        if isinstance(decoded, (dict, list)):
            yield from strings(decoded, path + '/decoded')


def main():
    logger.remove()
    all_tasks = tasks()
    manifest = {x['path']: x['sha256'] for x in json.loads((ROOT/'data/corpus_manifest.json').read_text())}
    runtime_tasks = Path(KNOWLEDGE_TASK_SET_PATH)
    # Verify the loaded task source as well as the checked-out copy.
    for tid in all_tasks:
        rel = f'tasks/{tid}.json'
        assert hashlib.sha256((CORPUS/rel).read_bytes()).hexdigest() == manifest[rel]
        assert hashlib.sha256((runtime_tasks.parent/'tasks'/f'{tid}.json').read_bytes()).hexdigest() == manifest[rel]
    tool_path = Path(inspect.getfile(banking_tools))
    tool_source = tool_path.read_text()
    assert tool_source == (ROOT/'vendor/tau2-bench/src/tau2/domains/banking_knowledge/tools.py').read_text()
    tree = ast.parse(tool_source)
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == FILING)
    method_source = ast.get_source_segment(tool_source, method)
    rows, summaries, clock_matches = [], [], []
    for tid, task in sorted(all_tasks.items()):
        criteria = task.evaluation_criteria.model_dump(mode='json')
        for path, value in strings(criteria):
            if CLOCK.search(value):
                clock_matches.append({'task': tid, 'path': path, 'value': value})
        filings = [a for a in task.evaluation_criteria.actions or []
                   if a.name == 'call_discoverable_agent_tool' and a.arguments.get('agent_tool_name') == FILING]
        if not filings:
            continue
        env, errors, messages = replay_actions(task)
        db = env.tools.db.model_dump()
        summaries.append({'task': tid, 'reward_basis': [x.value for x in task.evaluation_criteria.reward_basis],
                          'reference_reward': original_reward(task, env, env, messages)[0], 'errors': errors})
        for action in filings:
            args = json.loads(action.arguments['arguments'])
            _, final = record(db, args['transaction_id'])
            rows.append({'task': tid, 'action': action.action_id,
                         'arguments': args, 'final_record': final,
                         'credit_offset': (round(final['disputed_amount'] - final['provisional_credit_amount'], 8)
                                          if final and final['provisional_credit_issued'] else None)})
    issued = [r for r in rows if r['credit_offset'] is not None]
    out = {
        'scope': 'All 97 live task evaluation criteria, all reference debit-dispute filings, and filing-tool implementation.',
        'benchmark_commit': 'fc0055dc4e0a316c3f83133267fbd6faaa770992',
        'tool_source_sha256': hashlib.sha256(tool_source.encode()).hexdigest(),
        'all_task_files_match_corpus_manifest': True,
        'summary': {'tasks_screened': len(all_tasks), 'actions_screened': sum(len(t.evaluation_criteria.actions or []) for t in all_tasks.values()),
                    'tasks_with_filings': len(summaries), 'reference_filings': len(rows),
                    'successful_filings': sum(r['final_record'] is not None for r in rows),
                    'issued_credits': len(issued), 'credits_with_positive_offset': sum(r['credit_offset'] > 0 for r in issued),
                    'deadline_pattern_matches_in_evaluation_criteria': len(clock_matches)},
        'deadline_search_pattern': CLOCK.pattern,
        'deadline_matches': clock_matches,
        'filing_tool_parameters': [a.arg for a in method.args.args if a.arg != 'self'],
        'filing_tool_source': method_source,
        'task_replays': summaries, 'filings': rows,
        'interpretation': 'The reference filings do not deduct liability from provisional credit. The tool records the full disputed amount whenever eligibility is true. Its interface has no investigation deadline or completion field. All evaluation criteria were screened for deadline language, including the only natural-language assertion, which concerns an unrelated account referral. The 45-business-day policy is not an encoded completion deadline in these reference workflows. This does not measure what agents tell customers about investigation timing.'}
    (ROOT/'results/credit_rule_trace.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out['summary'],indent=2))
    for row in issued:
        if row['arguments'].get('customer_max_liability_amount',0) > 50:
            print(row['task'], row['arguments']['disputed_amount'], row['arguments']['customer_max_liability_amount'], row['final_record']['provisional_credit_amount'])

if __name__ == '__main__':
    main()
