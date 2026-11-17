"""Independent process: check saved result/provenance and capture observable CLI evidence."""
import json, sys
from pathlib import Path
from observe import ROOT,BASE,sha,manifest,write_new,now
sys.path.insert(0,str(ROOT/'scripts'))
from project_state import load_state

workspace=BASE/'demo-workspace';project=workspace/'projects/task06-rehearsal'
before=json.loads((BASE/'continuation-before.json').read_text(encoding='utf-8'))
events=[json.loads(x) for x in (BASE/'observations/continuation-cli/stdout.txt').read_text(encoding='utf-8').splitlines() if x.strip()]
run=json.loads((BASE/'observations/continuation-cli/result.json').read_text(encoding='utf-8'))
state=load_state(project)
assert state['revision']>1
assert events[0]['type']=='thread.started'
assert any(e['type']=='turn.completed' for e in events)
changed=[p for p,h in before['files'].items() if sha(workspace/p)!=h]
assert changed==['projects/task06-rehearsal/state/current.json'],changed
known={x['id'] for x in json.loads((project/'state/history/r000001.json').read_text(encoding='utf-8'))['artifacts']}
added=[x for x in state['artifacts'] if x['id'] not in known]
notes=[x for x in added if x['path'].endswith('.md') and x['path']!='project.md']
assert notes and all((project/x['path']).stat().st_size>100 for x in notes)
commands=[e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution']
messages=[e['item']['text'] for e in events if e.get('item',{}).get('type')=='agent_message']
result={'checked_at':now(),'thread_id':events[0]['thread_id'],'before_revision':1,'after_revision':state['revision'],
 'before_files':before['files'],'after_files':manifest(workspace),'changed_original_files':changed,
 'new_registered_artifacts':added,'first_response':messages[0], 'final_response':messages[-1],
 'command_outcomes':[{'command':x['command'],'exit_code':x.get('exit_code'),'status':x.get('status')} for x in commands],
 'llm_usage':[e.get('usage') for e in events if e['type']=='turn.completed'],
 'elapsed_seconds':run['elapsed_seconds'],'model_config_observed':'gpt-6-astra (doctor-host)',
 'effective_server_model_id':None,'separate_loader_pass':True,'original_sources_unchanged':True,
 'scope':'Checks integrity and actual session events; analytical content reviewed separately by coordinator.'}
write_new(BASE/'continuation-result.json',result)
print(json.dumps({k:result[k] for k in ('thread_id','before_revision','after_revision','new_registered_artifacts','llm_usage','elapsed_seconds','separate_loader_pass')},ensure_ascii=False,indent=2))
