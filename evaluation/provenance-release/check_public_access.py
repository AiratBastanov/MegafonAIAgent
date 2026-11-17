"""Ограниченное чтение публичных адресов без учётных данных и изменений."""
from datetime import datetime, timezone
from pathlib import Path
import json
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent
rows = []
for name, url in [
    ('official-case', 'https://challenge.mgimo.ai/cabinet/nominations/ai-project'),
    ('official-rules', 'https://challenge.mgimo.ai/rules'),
    ('github', 'https://github.com/AiratBastanov/MegafonAIAgent'),
    ('github-api', 'https://api.github.com/repos/AiratBastanov/MegafonAIAgent'),
]:
    row = dict(requested_url=url, at=datetime.now(timezone.utc).isoformat(), method='anonymous HTTPS GET')
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'MegafonAIAgent-local-readiness-check'})
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read(2_000_000)
            row.update(status=response.status, final_url=response.url, bytes=len(data))
            with (BASE/(name+'.html' if name!='github-api' else name+'.json')).open('xb') as stream:
                stream.write(data)
    except Exception as exc:
        row.update(error=f'{type(exc).__name__}: {exc}')
    rows.append(row)
with (BASE/'external-access-supported.json').open('x', encoding='utf-8') as stream:
    json.dump(rows, stream, ensure_ascii=False, indent=2)
print(json.dumps(rows, ensure_ascii=True))
