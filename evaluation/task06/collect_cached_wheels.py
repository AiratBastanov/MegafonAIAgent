"""Copy only three declared wheel distributions from pip's package-body cache.

Reads ZIP package metadata/RECORD, never cache HTTP headers or credential files.
No installation or network access; destination files are immutable.
"""
import argparse
import base64
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import zipfile

EXPECTED={'openpyxl':('3.1.5','openpyxl-3.1.5-py2.py3-none-any.whl'),
          'pypdf':('7.1.0','pypdf-7.1.0-py3-none-any.whl'),
          'et_xmlfile':('2.0.0','et_xmlfile-2.0.0-py3-none-any.whl')}

def collect(cache,destination):
    destination.mkdir(parents=True,exist_ok=False)
    found={}
    for path in cache.rglob('*.body'):
        if path.stat().st_size>2*1024*1024:continue
        with path.open('rb') as f:
            if f.read(4)!=b'PK\x03\x04':continue
        try:
            with zipfile.ZipFile(path) as z:
                meta=next((n for n in z.namelist() if n.endswith('.dist-info/METADATA')),None)
                if not meta:continue
                fields={}
                for line in z.read(meta).decode('utf-8').splitlines():
                    if ': ' in line:
                        key,value=line.split(': ',1)
                        if key in ('Name','Version'):fields[key]=value
                name=fields.get('Name','').lower().replace('-','_')
                if name not in EXPECTED or fields.get('Version')!=EXPECTED[name][0]:continue
                record=meta.removesuffix('METADATA')+'RECORD'
                checked=0
                for item,checksum,size in csv.reader(io.StringIO(z.read(record).decode('utf-8'))):
                    if not checksum:continue
                    alg,encoded=checksum.split('=',1)
                    data=z.read(item)
                    assert base64.urlsafe_b64encode(hashlib.new(alg,data).digest()).decode().rstrip('=')==encoded
                    assert len(data)==int(size);checked+=1
                wheel=destination/EXPECTED[name][1]
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if name in found:
                    assert found[name]['sha256']==digest
                    continue
                shutil.copyfile(path,wheel)
                found[name]={'file':wheel.name,'version':fields['Version'],'sha256':digest,
                    'bytes':wheel.stat().st_size,'record_entries_checked':checked,
                    'provenance':'Existing pip http-v2 package body cache; no network download in TASK06; cache headers not read.'}
        except zipfile.BadZipFile:
            continue
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'packages':found,
            'missing':sorted(set(EXPECTED)-set(found)),
            'scope':'RECORD consistency and pinned metadata; origin integrity must be checked against publisher hashes separately.'}
    with (destination/'PROVENANCE.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False))
    return bool(result['missing'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();raise SystemExit(collect(a.cache,a.output))
