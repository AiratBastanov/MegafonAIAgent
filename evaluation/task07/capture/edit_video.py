"""Make a documented cut of real captures; no synthetic screens or speech."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import subprocess

def command(argv,log):
    begin=datetime.now(timezone.utc).isoformat()
    p=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace')
    with log.open('a',encoding='utf-8') as f:
        f.write(json.dumps({'at':begin,'argv':argv,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr},ensure_ascii=False)+'\n')
    if p.returncode:raise RuntimeError(p.stderr)
    return p.stdout

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan');parser.add_argument('output');args=parser.parse_args()
    planpath=Path(args.plan).resolve();plan=json.loads(planpath.read_text(encoding='utf-8'))
    output=Path(args.output).resolve();work=output.parent/(output.stem+'-edit')
    work.mkdir(parents=True,exist_ok=False);log=work/'commands.jsonl';pieces=[];timeline=[];cursor=0
    for i,part in enumerate(plan['segments'],1):
        source=(planpath.parent/part['source']).resolve();speed=float(part.get('speed',1));start=float(part['start']);end=float(part['end'])
        if speed<=0 or start<0 or end<=start:raise ValueError('Invalid interval')
        piece=work/f'{i:02d}.mp4';caption=work/f'{i:02d}.txt'
        label=part.get('label','')
        if speed>1:label+='  •  Ускорено ×'+str(speed).rstrip('0').rstrip('.')
        if speed<1:label+='  •  Замедлено для чтения'
        if part.get('cut_before'):label+='  •  Ожидание сокращено'
        filters=[f'setpts=(PTS-STARTPTS)/{speed}']
        if part.get('crop'):
            x,y,w,h=part['crop']
            filters.extend([f'crop={w}:{h}:{x}:{y}',
                            'scale=1440:900:force_original_aspect_ratio=decrease',
                            'pad=1440:900:(ow-iw)/2:(oh-ih)/2:color=0x13263B'])
            label+='  •  Кадрировано'
        filters.append('pad=iw:ih+54:0:0:color=0x13263B')
        if label:
            caption.write_text(label,encoding='utf-8')
            textpath=caption.as_posix().replace(':',r'\:')
            filters.append("drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':textfile='"+textpath+"':fontcolor=white:fontsize=22:box=1:boxcolor=0x13263B@0.95:boxborderw=12:x=28:y=h-44")
        command(['ffmpeg','-hide_banner','-v','error','-ss',str(start),'-to',str(end),'-i',str(source),
                 '-vf',','.join(filters),'-r','10','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p',str(piece)],log)
        pieces.append(piece);expected_duration=(end-start)/speed
        duration=float(command(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(piece)],log).strip())
        timeline.append({**part,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                         'expected_duration_seconds':expected_duration,'encoded_duration_seconds':duration,
                         'output_start':cursor,'output_end':cursor+duration});cursor+=duration
    concat=work/'concat.txt'
    concat.write_text(''.join("file '"+p.name+"'\n" for p in pieces),encoding='utf-8')
    command(['ffmpeg','-hide_banner','-v','error','-f','concat','-i',str(concat),'-c','copy','-movflags','+faststart',str(output)],log)
    (work/'timeline.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),
        'note':'Cuts from actual local capture; edited duration is not runtime; no generated transcript or document render substituted.',
        'sum_encoded_duration_seconds':cursor,'segments':timeline,'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
    print(output)
