"""Video evidence only: metadata, full decode, hashes and inspection contact sheets."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import subprocess
import time
from fractions import Fraction

def run(argv):
    start=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
    p=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace')
    return {'argv':argv,'started_at':start,'elapsed_seconds':time.monotonic()-tick,
            'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('video');parser.add_argument('output')
    parser.add_argument('--max-seconds',type=float);parser.add_argument('--sheets-every',type=float,default=3)
    args=parser.parse_args();video=Path(args.video).resolve();out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    probe=run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)])
    decode=run(['ffmpeg','-hide_banner','-v','error','-i',str(video),'-f','null','NUL'])
    meta=json.loads(probe['stdout']) if probe['exit_code']==0 else None
    length=float(meta['format']['duration']) if meta else None
    stream=next(s for s in meta['streams'] if s['codec_type']=='video') if meta else {}
    frame_interval=max(1,round(float(Fraction(stream.get('avg_frame_rate','10/1')))*args.sheets_every))
    sheets=run(['ffmpeg','-hide_banner','-v','error','-i',str(video),'-vf',
                f"select='not(mod(n,{frame_interval}))',scale=720:-1,tile=2x4",'-fps_mode','vfr',str(out/'sequence-%03d.png')])
    result={'video':str(video),'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
            'bytes':video.stat().st_size,'metadata':meta,'metadata_command':probe,'full_decode':decode,
            'duration_seconds':length,'duration_limit':args.max_seconds,
            'duration_within_limit':args.max_seconds is None or (length is not None and length<=args.max_seconds),
            'contact_sheet_command':sheets,'sheet_step_seconds':args.sheets_every,
            'visual_inspection':'Not asserted by script; an agent or human must inspect actual images.'}
    (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['bytes','duration_seconds','duration_within_limit','sha256']},ensure_ascii=False))
    raise SystemExit(0 if all(x['exit_code']==0 for x in [probe,decode,sheets]) and result['duration_within_limit'] else 1)
