"""Read target GitHub metadata using Git's existing credential helper, never logging credentials.

No credential store or config file is opened. No login, visibility or rules are changed.
The helper's result is used in memory only for the exact authorized repository API.
"""
from pathlib import Path
from datetime import datetime, timezone
import base64
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[2]
REPO='AiratBastanov/MegafonAIAgent'

def get(path, authorization=None):
    headers={'User-Agent':'MegafonAIAgent-publication-check','Accept':'application/vnd.github+json'}
    if authorization:
        headers['Authorization']=authorization
    try:
        with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+REPO+path,headers=headers),timeout=30) as response:
            value=json.load(response)
            if path=='':
                value={k:value.get(k) for k in ('full_name','html_url','private','visibility','default_branch','size','archived','permissions')}
            return {'status':response.status,'value':value}
    except urllib.error.HTTPError as error:
        return {'status':error.code,'diagnostic':json.loads(error.read()).get('message')}
    except urllib.error.URLError as error:
        return {'status':'network_error','diagnostic':str(error.reason)}

def main():
    output=Path(sys.argv[1])
    assert output.resolve().is_relative_to(ROOT) and not output.exists()
    env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never')
    request='protocol=https\nhost=github.com\npath='+REPO+'\n\n'
    result=subprocess.run(['git','-C',str(ROOT/'_publication/repository'),'credential','fill'],
                          input=request,text=True,capture_output=True,env=env,timeout=30)
    authorization=None
    if result.returncode==0:
        fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        if fields.get('username') and fields.get('password'):
            authorization='Basic '+base64.b64encode((fields['username']+':'+fields['password']).encode()).decode()
        fields.clear()
    result=None
    report={'at':datetime.now(timezone.utc).isoformat(),'repository':REPO,
            'credential_method':'normal git credential helper; response never saved or printed',
            'existing_auth_available':authorization is not None,'anonymous':get(''),
            'authenticated':get('',authorization) if authorization else None,
            'branches':get('/branches',authorization) if authorization else None,
            'rulesets':get('/rulesets?includes_parents=true',authorization) if authorization else None,
            'main_protection':get('/branches/main/protection',authorization) if authorization else None}
    authorization=None
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
