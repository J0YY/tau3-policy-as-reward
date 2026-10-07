from scripts.trajectory_checks import extract_events, describe_sequence

USER='a7c2f85d91'
ACCOUNT='chk_e5a31c7d82'
HISTORY='get_debit_dispute_status_7483'
FILING='file_debit_card_transaction_dispute_6281'


def call(name,args,cid='c1'):
    return {'role':'assistant','tool_calls':[{'id':cid,'name':name,'arguments':args}]}

def response(cid='c1',content='Dispute ID: example',error=False):
    return {'role':'tool','id':cid,'content':content,'error':error}

def history():
    return call('call_discoverable_agent_tool',{'agent_tool_name':HISTORY,'arguments':'{"user_id":"'+USER+'"}'})

def filing():
    return call(FILING,{'account_id':ACCOUNT},'c2')

def describe(messages):
    return describe_sequence(extract_events(messages,'task_084'),ACCOUNT)

def test_completed_read_precedes_successful_filing():
    assert describe([history(),response(content='History retrieved'),filing(),response('c2')])['read_before_first_target_account_filing']

def test_unlock_is_not_a_read():
    m=call('unlock_discoverable_agent_tool',{'agent_tool_name':HISTORY})
    assert not describe([m,response(),filing(),response('c2')])['history_query_attempted']

def test_wrong_user_not_counted():
    assert not describe([call(HISTORY,{'user_id':'different'}),response()])['history_query_attempted']

def test_credit_card_history_not_counted():
    assert not describe([call('get_user_dispute_history_7291',{'user_id':USER}),response()])['history_query_attempted']

def test_text_error_is_failed_read():
    d=describe([history(),response(content='Error: unavailable'),filing(),response('c2')])
    assert d['history_query_attempted'] and not d['history_read_completed']

def test_pending_response_not_counted():
    assert not describe([history()])['history_read_completed']

def test_parallel_query_is_not_prior_information():
    m=history();m['tool_calls']+=filing()['tool_calls']
    d=describe([m,response(),response('c2')])
    assert d['history_read_completed'] and not d['read_before_first_target_account_filing']

def test_read_after_first_filing_not_prior():
    d=describe([filing(),response('c2'),history(),response()])
    assert d['history_read_completed'] and not d['read_before_first_target_account_filing']

def test_failed_filing_does_not_establish_servicing():
    d=describe([history(),response(),filing(),response('c2',error=True)])
    assert d['history_read_completed'] and not d['read_before_first_target_account_filing']

def test_table_read_requires_target_account_in_response():
    m=call('query_database',{'database_name':'debit_card_disputes'})
    assert describe([m,response(content=ACCOUNT)])['history_read_completed']
    assert not describe([m,response(content='different account')])['history_read_completed']
