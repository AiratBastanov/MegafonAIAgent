"""Temporary capture probe: records only its own live command window."""
from pathlib import Path
from datetime import datetime, timezone
import ctypes
import json
import os
import subprocess
import sys
import time
import tkinter as tk

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TITLE = 'Проверка записи — работа с файлами проекта'

def now():
    return datetime.now(timezone.utc).isoformat()

def main():
    started = now()
    root = tk.Tk()
    root.title(TITLE)
    root.geometry('1440x900+40+40')
    root.configure(bg='#122238')
    tk.Label(root, text='Проверка захвата окна проекта', font=('Segoe UI', 25, 'bold'),
             bg='#122238', fg='white', anchor='w').pack(fill='x', padx=30, pady=(24,10))
    tk.Label(root, text='Ниже выполняются реальные локальные команды. Это проба записи, не демонстрация агента.',
             font=('Segoe UI', 17), bg='#122238', fg='#aac6e8', anchor='w').pack(fill='x', padx=30, pady=(0,20))
    output = tk.Text(root, font=('Consolas', 18), bg='#f3f6fa', fg='#182b42', wrap='word',
                     padx=22, pady=20, borderwidth=0)
    output.pack(fill='both', expand=True, padx=30, pady=(0,30))
    output.insert('end', 'Ожидание начала захвата собственного окна…\n')
    root.update()
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
    observed_title = ctypes.create_unicode_buffer(1024)
    ctypes.windll.user32.GetWindowTextW(hwnd, observed_title, 1024)
    (HERE/'probe-window.json').write_text(json.dumps({'started_at':started, 'pid':os.getpid(),
        'hwnd':hwnd, 'title':observed_title.value, 'client_width':root.winfo_width(),
        'client_height':root.winfo_height(), 'root':str(ROOT)}, ensure_ascii=False, indent=2), encoding='utf-8')
    video=HERE/'sample-01.mp4'
    if video.exists():
        raise FileExistsError(video)
    argv=['ffmpeg','-hide_banner','-loglevel','info','-f','gdigrab','-framerate','10',
          '-draw_mouse','0','-i',f'hwnd={hwnd}','-t','9','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2',
          '-c:v','libx264','-preset','ultrafast','-crf','18','-pix_fmt','yuv420p',str(video)]
    log=(HERE/'sample-01.ffmpeg.stderr.txt').open('x',encoding='utf-8')
    process=subprocess.Popen(argv,stdout=subprocess.DEVNULL,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    records=[]
    def run():
        command=[sys.executable,'-X','utf8','scripts/project_state.py','load','--project','projects/task06-rehearsal']
        output.delete('1.0','end')
        output.insert('end','Команда: python scripts/project_state.py load\nПроект: projects/task06-rehearsal\n\n')
        root.update()
        begin=now()
        result=subprocess.run(command,cwd=ROOT,text=True,encoding='utf-8',capture_output=True,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        (HERE/'sample-01.loader.stdout.txt').write_text(result.stdout,encoding='utf-8')
        (HERE/'sample-01.loader.stderr.txt').write_text(result.stderr,encoding='utf-8')
        records.append({'argv':command,'cwd':str(ROOT),'started_at':begin,'ended_at':now(),'exit_code':result.returncode})
        output.insert('end',result.stdout[:2200]+'\n' if result.stdout else result.stderr)
        output.insert('end',f'\nКод завершения: {result.returncode}\nПолный вывод сохранён рядом с исходной записью.\n')
        output.see('1.0')
    def finish():
        if process.poll() is None:
            root.after(500,finish)
            return
        log.close()
        (HERE/'sample-01.result.json').write_text(json.dumps({'started_at':started,'ended_at':now(),
            'capture_argv':argv,'capture_exit_code':process.returncode,'commands':records,
            'note':'Actual gdigrab capture of a dedicated local window showing a command executed during capture; not a fabricated transcript and not the complete agent demo.'},ensure_ascii=False,indent=2),encoding='utf-8')
        root.destroy()
    root.after(1400,run)
    root.after(10500,finish)
    root.mainloop()

if __name__=='__main__':
    main()
