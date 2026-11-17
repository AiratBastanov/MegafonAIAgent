"""Local observations only: commands, streams, timings, hashes; no agent backend."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, subprocess, time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_new(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
def manifest(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and not any(x in p.parts for x in ('.venv','__pycache__','.git'))}
def run(name, args, cwd=ROOT, timeout=180, stdin=None):
    folder=BASE/'observations'/name
    folder.mkdir(parents=True, exist_ok=False)
    started=now(); counter=time.monotonic()
    meta={'command':args,'cwd':str(cwd),'started_at':started,'stdin':stdin,
          'environment':'inherited; PYTHONIOENCODING=utf-8; credentials not inspected'}
    write_new(folder/'request.json',meta)
    with (folder/'stdout.txt').open('wb') as out, (folder/'stderr.txt').open('wb') as err:
        proc=subprocess.Popen(args,cwd=cwd,stdout=out,stderr=err,stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
            env={**os.environ,'PYTHONIOENCODING':'utf-8'})
        try:
            proc.communicate(stdin.encode('utf-8') if stdin else None,timeout=timeout)
            meta['outcome']='process_exited'
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate(); meta['outcome']='technical_timeout'
    meta.update(ended_at=now(),elapsed_seconds=time.monotonic()-counter,returncode=proc.returncode,
        stdout_sha256=sha(folder/'stdout.txt'),stderr_sha256=sha(folder/'stderr.txt'))
    write_new(folder/'result.json',meta)
    print(json.dumps(meta,ensure_ascii=False))
    print((folder/'stdout.txt').read_text(encoding='utf-8',errors='replace')[-6000:])
    print((folder/'stderr.txt').read_text(encoding='utf-8',errors='replace')[-3000:])
    return meta
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--cwd',type=Path,default=ROOT)
    p.add_argument('--timeout',type=int,default=180);p.add_argument('--stdin-file',type=Path)
    p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    args=a.args[1:] if a.args and a.args[0]=='--' else a.args
    run(a.name,args,a.cwd,a.timeout,a.stdin_file.read_text(encoding='utf-8') if a.stdin_file else None)
