import json
from api_extractor.evidence import audit_endpoints
from api_extractor.jsonl_logger import JsonlLogger


def make_entry(url='https://app.example.com/api/items', method='GET', code=200, idx=0):
    return {'request': {'url': url, 'method': method},
            'response': {'status': code}, '_requestIndex': idx, '_resourceType': 'xhr'}


def make_output(tmp_path, row):
    p = tmp_path/'evidence'/'dynamic.har'
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({'log':{'entries':[row]}}))
    return {'method':'GET','host':'app.example.com','path':'/api/items',
            'evidence':[{'type':'har','file':'evidence/dynamic.har','request_index':0}]}


def log_request(log, url='https://app.example.com/api/items', idx=0, status=200):
    log.write('GET', url, status, 'dynamic', request_index=idx)


def test_valid_log_har_identity(tmp_path):
    entry = make_output(tmp_path, make_entry())
    log=JsonlLogger(tmp_path/'tool.log')
    log_request(log)
    offset=log.start_offset
    log.close()
    clean,bad,dropped = audit_endpoints([entry],tmp_path,offset)
    assert clean==[entry] and (bad,dropped)==(0,0)


def test_stale_previous_run_log_cannot_confirm_current_har(tmp_path):
    entry = make_output(tmp_path, make_entry())
    path=tmp_path/'tool.log'
    old=JsonlLogger(path)
    log_request(old)
    old.close()
    new=JsonlLogger(path)
    start = new.start_offset
    new.write('GET','https://app.example.com/api/different',200,'dynamic',request_index=0)
    new.close()
    clean,bad,dropped=audit_endpoints([entry],tmp_path,start)
    assert clean==[] and (bad,dropped)==(1,1)


def test_har_wrong_status_is_rejected(tmp_path):
    entry = make_output(tmp_path, make_entry(code=403))
    log=JsonlLogger(tmp_path/'tool.log')
    log_request(log,status=200)
    log.close()
    assert audit_endpoints([entry],tmp_path)[0]==[]


def test_har_wrong_index_is_rejected(tmp_path):
    entry = make_output(tmp_path, make_entry())
    log=JsonlLogger(tmp_path/'tool.log')
    log_request(log,idx=1)
    log.close()
    assert audit_endpoints([entry],tmp_path)[0]==[]


def test_unauthorized_and_failed_requests_rejected(tmp_path):
    entry=make_output(tmp_path,make_entry(code=404))
    log=JsonlLogger(tmp_path/'tool.log')
    log_request(log,status=404)
    log.close()
    assert audit_endpoints([entry],tmp_path)[0]==[]


def test_401_auth_challenge_remains_valid_evidence(tmp_path):
    entry=make_output(tmp_path,make_entry(code=401))
    log=JsonlLogger(tmp_path/'tool.log')
    log_request(log,status=401)
    log.close()
    assert audit_endpoints([entry],tmp_path)[0]==[entry]


def test_source_without_log_still_accepted(tmp_path):
    p = tmp_path/'evidence'/'js'/'app.js'
    p.parent.mkdir(parents=True)
    p.write_text('fetch("/api/items")')
    entry={'method':'GET','host':'app.example.com','path':'/api/items',
            'evidence':[{'type':'bundle','file':'evidence/js/app.js','snippet':'fetch("/api/items")'}]}
    assert audit_endpoints([entry],tmp_path)[0]==[entry]
