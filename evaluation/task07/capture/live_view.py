"""Temporary project-only live monitor; displays real command output, never invents replies.

Controls are explicit JSON files in inbox. Only paths inside this repository are accepted.
The monitor can execute commands or follow an external real-time Codex JSONL stream.
"""
from pathlib import Path
from datetime import datetime, timezone
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPlainTextEdit, QVBoxLayout

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TITLE = 'Агент стратегии — реальная работа с проектом'

def now(): return datetime.now(timezone.utc).isoformat()
def local_path(name):
    p=(ROOT/name).resolve()
    p.relative_to(ROOT)
    return p

class Viewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.resize(1440,900)
        self.move(30,30)
        self.setStyleSheet('QWidget {background:#13263b;color:#f4f7fc} QPlainTextEdit {background:#f3f6fa;color:#152a43;border:0;padding:20px;}')
        layout=QVBoxLayout(self); layout.setContentsMargins(28,22,28,25); layout.setSpacing(15)
        self.heading=QLabel('Реальная работа с проектом'); self.heading.setFont(QFont('Segoe UI',25,QFont.Bold));layout.addWidget(self.heading)
        self.caption=QLabel('Локальное окно показывает вывод выполняемых команд. Учебные бизнес-данные смоделированы.')
        self.caption.setFont(QFont('Segoe UI',16)); self.caption.setWordWrap(True);layout.addWidget(self.caption)
        self.body=QPlainTextEdit();self.body.setReadOnly(True); self.body.setFont(QFont('Consolas',18));layout.addWidget(self.body,1)
        self.status=QLabel('Ожидание команды');self.status.setFont(QFont('Segoe UI',14));layout.addWidget(self.status)
        self.body.setPlainText('Окно готово. Здесь отображаются только реальные команды и их результаты.\n')
        self.done={p.name for p in (HERE/'inbox').glob('*.json')};self.follow=None;self.follow_json=False;self.position=0;self.buffer='';self.recorder=None;self.recorder_log=None
        self.running=None;self.command_output=None;self.command_log=None;self.command_meta=None
        self.events=HERE/'viewer-events.jsonl'
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(150)
        self.show()
        hwnd=int(self.winId()); title=ctypes.create_unicode_buffer(1024)
        ctypes.windll.user32.GetWindowTextW(hwnd,title,1024)
        self.log('viewer_started',pid=os.getpid(),hwnd=hwnd,title=title.value,client_size=[self.width(),self.height()])
        (HERE/'viewer-window.json').write_text(json.dumps({'pid':os.getpid(),'hwnd':hwnd,'title':title.value,'observed_at':now()},ensure_ascii=False,indent=2),encoding='utf-8')
    def log(self,event,**data):
        with self.events.open('a',encoding='utf-8') as f:f.write(json.dumps({'at':now(),'event':event,**data},ensure_ascii=False)+'\n')
    def append(self,text):
        self.body.appendPlainText(text)
        bar=self.body.verticalScrollBar();bar.setValue(bar.maximum())
    def event_text(self,line):
        try: e=json.loads(line)
        except json.JSONDecodeError: return line
        kind=e.get('type','');item=e.get('item',{})
        if kind=='thread.started':return 'Контекст Codex.\nИдентификатор: '+str(e.get('thread_id',''))
        if kind=='turn.started':return 'Агент начал работу.'
        if kind=='turn.completed':
            self.log('turn_completed',usage=e.get('usage',{}))
            self.status.setText('Агент завершил этот шаг; полный журнал сохранён')
            return 'Работа агента завершена.'
        if kind in ('error','turn.failed'):return 'Ошибка: '+json.dumps(e,ensure_ascii=False)
        if item:
            it=item.get('type','')
            if it in ('reasoning','agent_message'):return item.get('text','')
            if it=='command_execution':
                s='Команда агента:\n'+str(item.get('command',''))
                if 'aggregated_output' in item:s+='\n'+str(item['aggregated_output'])
                if 'exit_code' in item:s+='\nКод завершения: '+str(item['exit_code'])
                return s
            return json.dumps(item,ensure_ascii=False,indent=2)
        return line
    def tick(self):
        try:
            for p in sorted((HERE/'inbox').glob('*.json')):
                if p.name in self.done:continue
                self.done.add(p.name)
                job=json.loads(p.read_text(encoding='utf-8-sig'))
                self.log('control',file=p.name,job=job)
                self.control(job)
            if self.follow and self.follow.exists():
                with self.follow.open('r',encoding='utf-8',errors='replace') as f:
                    f.seek(self.position);chunk=f.read();self.position=f.tell()
                if chunk:
                    if self.follow_json or self.follow.suffix in ('.jsonl','.ndjson'):
                        self.buffer+=chunk;lines=self.buffer.split('\n');self.buffer=lines.pop()
                        for line in lines:
                            txt=self.event_text(line)
                            if txt:self.append(txt)
                    else:self.append(chunk.rstrip())
            if self.running and self.running.poll() is not None:
                result=self.running.returncode;self.command_output.close();self.command_output=None
                self.log('command_completed',**self.command_meta,exit_code=result)
                self.status.setText('Команда завершена; код '+str(result));self.running=None
        except Exception as exc:
            self.log('viewer_error',error=repr(exc));self.status.setText('Ошибка окна: '+str(exc))
    def control(self,j):
        op=j['operation']
        if op=='close':
            self.stop();self.close();return
        if op=='stop':self.stop();return
        if op=='record':
            if self.recorder:raise RuntimeError('Recording already active')
            name=j['name']
            if Path(name).name!=name:raise ValueError('Filename required')
            dest=HERE/'raw'/name
            if dest.exists():raise FileExistsError(dest)
            dest.parent.mkdir(exist_ok=True)
            argv=['ffmpeg','-hide_banner','-loglevel','info','-f','gdigrab','-framerate','10','-draw_mouse','0',
                  '-i','hwnd='+str(int(self.winId())),'-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2',
                  '-c:v','libx264','-preset','ultrafast','-crf','18','-pix_fmt','yuv420p',str(dest)]
            self.recorder_log=dest.with_suffix('.ffmpeg.txt').open('x',encoding='utf-8')
            self.recorder=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=self.recorder_log,creationflags=subprocess.CREATE_NO_WINDOW)
            self.log('capture_started',argv=argv,pid=self.recorder.pid)
            self.status.setText('Идёт реальная запись собственного окна');return
        if op in ('follow','run','file'):
            if self.running:raise RuntimeError('Previous command still running')
            self.heading.setText(j.get('title','Работа с проектом'))
            self.caption.setText(j.get('caption','Реальные команды и результаты. Учебные бизнес-данные смоделированы.'))
            self.body.clear();self.follow=None;self.follow_json=False;self.position=0;self.buffer=''
            if j.get('prompt'):self.append('Запрос руководителя:\n'+j['prompt']+'\n')
        if op=='follow':
            self.follow=local_path(j['path']);self.follow_json=j.get('format')=='jsonl';self.status.setText('Ожидание нового вывода агента');return
        if op=='file':
            p=local_path(j['path']);text=p.read_text(encoding='utf-8')
            lines=text.splitlines();first=j.get('first_line',1);last=j.get('last_line',len(lines))
            self.body.setPlainText('\n'.join(lines[first-1:last]));self.status.setText('Чтение сохранённого файла • '+p.name)
            self.log('file_displayed',path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),first_line=first,last_line=last);return
        if op=='run':
            cwd=local_path(j.get('cwd','.'));argv=j['argv'];name=j['id']
            path=HERE/'commands'/f'{name}.stdout.txt';path.parent.mkdir(exist_ok=True)
            self.command_output=path.open('x',encoding='utf-8');self.follow=path
            self.append('Выполняется: '+subprocess.list2cmdline(argv)+'\n')
            self.command_meta={'argv':argv,'cwd':str(cwd),'started_at':now(),'output':str(path.relative_to(ROOT))}
            self.log('command_started',**self.command_meta)
            self.running=subprocess.Popen(argv,cwd=cwd,stdout=self.command_output,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            self.status.setText('Выполняется команда')
    def stop(self):
        if self.recorder:
            try:self.recorder.stdin.write(b'q\n');self.recorder.stdin.flush();self.recorder.wait(timeout=15)
            except Exception as exc:self.log('stop_error',error=repr(exc))
            self.log('capture_stopped',exit_code=self.recorder.poll())
            self.recorder_log.close();self.recorder=None;self.status.setText('Запись завершена')

if __name__=='__main__':
    (HERE/'inbox').mkdir(exist_ok=True)
    app=QApplication(sys.argv);viewer=Viewer();sys.exit(app.exec_())
