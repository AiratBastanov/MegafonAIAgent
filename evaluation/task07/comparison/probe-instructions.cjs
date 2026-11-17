// One-shot diagnostic client. Deliberately has no turn/start or config override.
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');
const {spawn} = require('child_process');
const readline = require('readline');

const [exeArg, workspaceArg, outputArg] = process.argv.slice(2);
if (!exeArg || !workspaceArg || !outputArg) throw new Error('Usage: node probe-instructions.cjs CODEX_EXE WORKSPACE NEW_OUTPUT_DIR');
const exe = path.resolve(exeArg);
const workspace = path.resolve(workspaceArg);
const output = path.resolve(outputArg);
if (!fs.statSync(workspace).isDirectory()) throw new Error('Workspace missing');
if (!workspace.toLowerCase().startsWith((path.resolve(os.tmpdir()) + path.sep).toLowerCase())) throw new Error('Probe accepts prepared temporary workspaces only');
if (!/^megafon-comparison-[AB]-20261116-01$/.test(path.basename(workspace))) throw new Error('Unexpected prepared workspace');
if (!output.toLowerCase().startsWith((__dirname + path.sep).toLowerCase())) throw new Error('Output must be inside comparison evidence directory');
fs.mkdirSync(output, {recursive:false});
const startedAt = new Date().toISOString();
const start = process.hrtime.bigint();
const ancestry = [];
for (let current = path.dirname(workspace); ; current = path.dirname(current)) {
  for (const name of ['AGENTS.md', 'AGENTS.override.md']) {
    if (fs.existsSync(path.join(current,name))) ancestry.push(path.join(current,name));
  }
  if (path.dirname(current) === current) break;
}
if (ancestry.length) throw new Error('Unexpected instruction ancestor: ' + ancestry.join(', '));

function redactText(text) {
  return String(text)
    .replace(/Bearer\s+[^\s"']+/gi, 'Bearer [REDACTED]')
    .replace(/(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|password|cookie)\b\s*[=:]\s*)[^\s,;]+/gi, '$1[REDACTED]');
}
function scrub(value, key='') {
  if (/^(?:accessToken|refreshToken|idToken|authorization|apiKey|password|cookie|token)$/i.test(key)) return '[REDACTED]';
  if (Array.isArray(value)) return value.map(v=>scrub(v));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,scrub(v,k)]));
  return typeof value === 'string' ? redactText(value) : value;
}
function writeJson(name, value) { fs.writeFileSync(path.join(output,name), JSON.stringify(scrub(value),null,2)+'\n','utf8'); }
function event(direction, value) { fs.appendFileSync(path.join(output,'protocol.jsonl'), JSON.stringify({at:new Date().toISOString(),direction,message:scrub(value)})+'\n','utf8'); }
writeJson('operation.json', {
  started_at:startedAt, executable:exe, args:['app-server','--stdio'], cwd:workspace,
  environment:{os:process.platform, node:process.version, authentication:'normal existing host authentication; no credentials read or supplied', profile:'unchanged'},
  request_scope:'initialize then fresh ephemeral thread/start; no LLM turn, no task input, no config/instruction overrides',
  ancestor_instruction_files:ancestry
});

let successful=false, finished=false, childExit=null;
const child=spawn(exe,['app-server','--stdio'],{cwd:workspace,stdio:['pipe','pipe','pipe'],windowsHide:true});
const timer=setTimeout(()=>finish('timeout',new Error('No complete metadata response within 90 seconds')),90000);
function send(message) { event('sent',message); child.stdin.write(JSON.stringify(message)+'\n'); }
function finish(status,error) {
  if (finished) return;
  finished=true;
  clearTimeout(timer);
  writeJson('result.json',{status,started_at:startedAt,ended_at:new Date().toISOString(),elapsed_seconds:Number(process.hrtime.bigint()-start)/1e9,
    successful_instruction_observation:successful,llm_turn_started:false,child_exit_observed:childExit,error:error?{name:error.name,message:error.message}:null});
  child.stdin.end();
  const cleanup=setTimeout(()=>{if(childExit===null)child.kill();},1500);
  cleanup.unref();
  process.exitCode=successful?0:1;
  console.log(JSON.stringify({status,output,llm_turn_started:false}));
}
const lines=readline.createInterface({input:child.stdout});
lines.on('line',line=>{
  let message;
  try {message=JSON.parse(line);} catch(error) {event('unparsed-stdout',{line:redactText(line)}); return;}
  // The initialize and thread/start results contain non-secret runtime metadata.
  // No account/config APIs are called, and no model history is received.
  event('received',message);
  if (message.error) return finish('protocol-error',new Error(JSON.stringify(message.error)));
  if (message.id===1 && message.result) {
    writeJson('initialize-result.json',message.result);
    send({method:'initialized',params:{}});
    send({method:'thread/start',id:2,params:{cwd:workspace,ephemeral:true}});
  }
  if (message.id===2 && message.result) {
    writeJson('thread-start-result.json',message.result);
    successful=Array.isArray(message.result.instructionSources);
    finish(successful?'instruction-sources-observed':'instruction-sources-field-missing');
  }
});
child.stderr.on('data',chunk=>fs.appendFileSync(path.join(output,'stderr.txt'),redactText(chunk.toString('utf8')),'utf8'));
child.on('error',error=>finish('launch-error',error));
child.on('exit',(code,signal)=>{
  childExit={code,signal};
  writeJson('process-exit.json',{at:new Date().toISOString(),code,signal});
  if(!finished)finish('process-exited-before-result');
  lines.close();
});
send({method:'initialize',id:1,params:{clientInfo:{name:'megafon_instruction_probe',title:'Local instruction provenance check',version:'1.0'}}});
