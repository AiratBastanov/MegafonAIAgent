"""Развернуть frozen-v2, выдать очередной prompt или снять наблюдение.

Только файловые операции; запуск LLM выполняет доступный host/UI.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import shutil

BASE = Path(__file__).resolve().parent
FROZEN = BASE/'frozen-v2'


def manifest(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','stage','snapshot'])
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--condition',choices=['A','B'],required=True)
    parser.add_argument('--phase',choices=['q1','q2','q3'],default='q1')
    parser.add_argument('--output')
    args=parser.parse_args()
    workspace=Path(args.workspace).resolve()
    if args.action=='prepare':
        if workspace.exists():
            raise SystemExit('Нужна новая папка; существующая не перезаписывается')
        if any((p/'AGENTS.md').exists() for p in workspace.parents):
            raise SystemExit('Нужна папка вне ancestry AGENTS проекта')
        shutil.copytree(FROZEN/args.condition,workspace)
    if args.action in {'prepare','stage'}:
        for source in sorted((FROZEN/'events'/args.phase).glob('*')):
            dest=workspace/'inbox'/args.phase/source.name
            dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists() and dest.read_bytes()!=source.read_bytes():
                raise SystemExit('Существующий вход отличается')
            if not dest.exists():
                shutil.copyfile(source,dest)
        dest=workspace/('request-'+args.phase+'.txt')
        if dest.exists():
            raise SystemExit('Prompt уже выдан; не повторять автоматически')
        shutil.copyfile(FROZEN/'prompts'/args.condition/(args.phase+'.txt'),dest)
        print(str(dest))
    else:
        if not args.output:
            raise SystemExit('Нужен --output (новая папка наблюдения)')
        out=Path(args.output)
        out.mkdir(parents=True,exist_ok=False)
        meta={'observed_at':datetime.now(timezone.utc).isoformat(),'workspace':str(workspace),
            'condition':args.condition,'phase':args.phase,'files':manifest(workspace)}
        (out/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        # Первый ответ/мета сохраняются немедленно; большие tools и полный workspace отдельно.
        for rel in [f'responses/{args.phase}.md',f'responses/{args.phase}-meta.json']:
            source=workspace/rel
            if source.exists():
                shutil.copyfile(source,out/source.name)
        if args.condition=='A':
            for branch in ('familiar','variant'):
                source=workspace/'branches'/branch/'projects/task04-followup/state/current.json'
                shutil.copyfile(source,out/(branch+'-state.json'))
        print(str(out))


if __name__=='__main__':
    main()
