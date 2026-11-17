"""Queue one local monitor action. JSON read from a supplied UTF-8 file, not shell text."""
from pathlib import Path
import json
import sys
from datetime import datetime,timezone

if __name__=='__main__':
    here=Path(__file__).resolve().parent
    payload=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
    target=here/'inbox'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
    target.parent.mkdir(exist_ok=True)
    with target.open('x',encoding='utf-8') as f:json.dump(payload,f,ensure_ascii=False,indent=2)
    print(target)
