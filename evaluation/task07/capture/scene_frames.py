"""Extract actual scene changes and times for reviewable editing, without rewriting capture."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,re,subprocess

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('video');p.add_argument('output');p.add_argument('--threshold',default='0.02');a=p.parse_args()
    video=Path(a.video).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    argv=['ffmpeg','-hide_banner','-i',str(video),'-vf',f"select='gt(scene,{a.threshold})',showinfo,scale=720:-1",'-fps_mode','vfr',str(out/'scene-%03d.png')]
    r=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (out/'ffmpeg.stderr.txt').write_text(r.stderr,encoding='utf-8')
    frames=[]
    for match in re.finditer(r'\bn:\s*(\d+)\s+pts:\s*\d+\s+pts_time:([\d.]+)',r.stderr):
        n=int(match[1])+1;frames.append({'image':f'scene-{n:03d}.png','at_seconds':float(match[2])})
    result={'at':datetime.now(timezone.utc).isoformat(),'argv':argv,'exit_code':r.returncode,'frames':frames}
    (out/'frames.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'frames':len(frames),'exit_code':r.returncode}));raise SystemExit(r.returncode)
