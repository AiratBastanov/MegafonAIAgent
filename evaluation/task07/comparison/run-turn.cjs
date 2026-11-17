// Temporary client for one measured turn; no strategy, evaluator notes or model override.
'use strict';
const fs=require('fs'), path=require('path'), os=require('os'), crypto=require('crypto');
const {spawn}=require('child_process');
const readline=require('readline');
const [exeArg,workspaceArg,outputArg,condition,phase,resumeThreadId]=process.argv.slice(2);
if(!exeArg||!workspaceArg||!outputArg||!['A','B'].includes(condition)||!['q1','q2','q3'].includes(phase))
  throw new Error('Usage: node run-turn.cjs CODEX_EXE WORKSPACE NEW_OUTPUT_DIR A|B q1|q2|q3 [THREAD_ID]');
if((phase==='q1')===Boolean(resumeThreadId))throw new Error('q1 must start fresh; subsequent phases must resume their own participant');
const exe=path.resolve(exeArg),workspace=path.resolve(workspaceArg),output=path.resolve(outputArg);
if(!workspace.toLowerCase().startsWith((path.resolve(os.tmpdir())+path.sep).toLowerCase())||path.basename(workspace)!==`megafon-comparison-${condition}-20261116-01`)
  throw new Error('Only the authorized prepared temporary workspace is accepted');
if(!output.toLowerCase().startsWith((__dirname+path.sep).toLowerCase()))throw new Error('Output outside comparison evidence');
if(!fs.statSync(workspace).isDirectory())throw new Error('Workspace missing');
for(let folder=path.dirname(workspace);;folder=path.dirname(folder)){
  for(const name of ['AGENTS.md','AGENTS.override.md'])if(fs.existsSync(path.join(folder,name)))throw new Error('Unexpected ancestor instruction '+path.join(folder,name));
  if(path.dirname(folder)===folder)break;
}
const requestPath=path.join(workspace,`request-${phase}.txt`);
if(!fs.existsSync(requestPath))throw new Error('Phase request not staged');
if(phase==='q1'&&(fs.existsSync(path.join(workspace,'request-q2.txt'))||fs.existsSync(path.join(workspace,'request-q3.txt'))))throw new Error('Future phase exposed');
if(phase==='q2'&&fs.existsSync(path.join(workspace,'request-q3.txt')))throw new Error('Future phase exposed');
fs.mkdirSync(output,{recursive:false});
const startedAt=new Date().toISOString(),startedHr=process.hrtime.bigint();
const prompt=`Прочитай request-${phase}.txt и RUNTIME.md как UTF-8 и выполни запрос; работай только в этой папке`;
const hashes={};
for(const name of [`request-${phase}.txt`,'RUNTIME.md'])hashes[name]=crypto.createHash('sha256').update(fs.readFileSync(path.join(workspace,name))).digest('hex');
function redactText(value){return String(value).replace(/Bearer\s+[^\s"']+/gi,'Bearer [REDACTED]').replace(/(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|password|cookie)\b\s*[=:]\s*)[^\s,;]+/gi,'$1[REDACTED]');}
function scrub(value,key=''){
  if(/^(?:accessToken|refreshToken|idToken|authorization|apiKey|password|cookie|token)$/i.test(key))return '[REDACTED]';
  if(Array.isArray(value))return value.map(v=>scrub(v));
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,scrub(v,k)]));
  return typeof value==='string'?redactText(value):value;
}
function json(name,value){fs.writeFileSync(path.join(output,name),JSON.stringify(scrub(value),null,2)+'\n','utf8');}
function event(direction,value){fs.appendFileSync(path.join(output,'protocol.jsonl'),JSON.stringify({at:new Date().toISOString(),direction,message:scrub(value)})+'\n','utf8');}
function status(value){json('live-status.json',{at:new Date().toISOString(),threadId,turnId,...value});}
let finished=false,closing=false,childExit=null,threadId=null,turnId=null,turnStartedAt=null,lastEventAt=Date.now(),tokenUsage=null;
const items=new Map(),agentMessages=[];
json('operation.json',{started_at:startedAt,executable:exe,args:['app-server','--stdio'],cwd:workspace,condition,phase,
  auth:'normal existing host authentication; no credential/config reads or overrides',thread_request:phase==='q1'?'thread/start':'thread/resume',resume_thread_id:resumeThreadId||null,
  bootstrap:prompt,input_hashes:hashes,model_override:null,instruction_overrides:null,workspace_policy:'workspace-write explicitly supplied to start and resume',
  driver_sha256:crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex'),
  environment:{os:process.platform,node:process.version}});
fs.writeFileSync(path.join(output,'bootstrap.txt'),prompt+'\n','utf8');
const child=spawn(exe,['app-server','--stdio'],{cwd:workspace,stdio:['pipe','pipe','pipe'],windowsHide:true});
function send(message){event('sent',message);child.stdin.write(JSON.stringify(message)+'\n');}
const pendingRequests=new Map();
const poll=setInterval(()=>{
  for(const [key,request] of pendingRequests){
    const responseFile=path.join(output,`request-${key}.response.json`);
    if(!fs.existsSync(responseFile))continue;
    try{const response=JSON.parse(fs.readFileSync(responseFile,'utf8'));send({id:request.id,result:response});pendingRequests.delete(key);event('manual-response-file',{file:path.basename(responseFile)});}
    catch(error){event('response-file-error',{message:error.message});}
  }
  if(!finished&&Date.now()-lastEventAt>30*60*1000){
    event('technical-timeout',{reason:'No protocol activity for 30 minutes; not a research quota'});
    if(threadId&&turnId)send({method:'turn/interrupt',id:90,params:{threadId,turnId}});
    finish('technical-inactivity-timeout');
  }
},500);
function finish(outcome,error){
  if(finished)return;
  finished=true;clearInterval(poll);
  json('items.json',Array.from(items.values()));
  json('agent-messages.json',agentMessages);
  json('token-usage.json',tokenUsage);
  const finals=agentMessages.filter(m=>m.phase==='final_answer');
  if(agentMessages.length)json('first-agent-message.json',agentMessages[0]);
  if(finals.length){json('first-final-answer.json',finals[0]);fs.writeFileSync(path.join(output,'first-final-answer.md'),finals[0].text+'\n','utf8');}
  json('result.json',{outcome,condition,phase,thread_id:threadId,turn_id:turnId,started_at:startedAt,turn_started_at:turnStartedAt,
    ended_at:new Date().toISOString(),elapsed_seconds:Number(process.hrtime.bigint()-startedHr)/1e9,child_exit_observed:childExit,
    agent_message_count:agentMessages.length,final_answer_count:finals.length,completed_items:items.size,token_usage:tokenUsage,
    pending_client_requests:pendingRequests.size,error:error?{name:error.name,message:error.message}:null});
  status({state:'finished',outcome});
  closing=true;child.stdin.end();
  const cleanup=setTimeout(()=>{if(childExit===null)child.kill();},2000);cleanup.unref();
  process.exitCode=outcome==='completed'?0:1;
  console.log(JSON.stringify({outcome,condition,phase,threadId,output}));
}
const lines=readline.createInterface({input:child.stdout});
lines.on('line',line=>{
  lastEventAt=Date.now();
  let m;try{m=JSON.parse(line);}catch(error){event('unparsed-stdout',{line});return;}
  event('received',m);
  if(m.error&&m.id!==undefined)return finish('protocol-error',new Error(JSON.stringify(m.error)));
  if(m.method&&m.id!==undefined){
    const key=String(m.id).replace(/[^a-zA-Z0-9_-]/g,'_');pendingRequests.set(key,m);json(`request-${key}.json`,m);
    status({state:'client-request-pending',requestId:m.id,method:m.method});
    console.log(JSON.stringify({pending_request:key,condition,phase,method:m.method,output}));return;
  }
  if(m.id===1&&m.result){
    json('initialize-result.json',m.result);send({method:'initialized',params:{}});
    if(phase==='q1')send({method:'thread/start',id:2,params:{cwd:workspace,sandbox:'workspace-write'}});
    else send({method:'thread/resume',id:2,params:{threadId:resumeThreadId,excludeTurns:true,sandbox:'workspace-write'}});
  }
  if(m.id===2&&m.result){
    json('thread-result.json',m.result);threadId=m.result.thread?.id;
    const expectedSources=condition==='A'?[path.join(workspace,'AGENTS.md')]:[];
    const sourceMatch=JSON.stringify((m.result.instructionSources||[]).map(p=>path.normalize(p).toLowerCase()))===JSON.stringify(expectedSources.map(p=>p.toLowerCase()));
    const settingsMatch=m.result.model==='gpt-6-astra'&&m.result.modelProvider==='openai'&&m.result.reasoningEffort==='max'&&path.resolve(m.result.cwd)===workspace&&m.result.sandbox?.type==='workspaceWrite';
    const freshMatch=phase!=='q1'||(!m.result.thread?.forkedFromId&&m.result.thread?.sessionId===threadId);
    json('context-check.json',{sourceMatch,settingsMatch,freshMatch,expectedSources,actualSources:m.result.instructionSources,model:m.result.model,reasoningEffort:m.result.reasoningEffort});
    if(!sourceMatch||!settingsMatch||!freshMatch)return finish('context-preflight-rejected');
    turnStartedAt=new Date().toISOString();send({method:'turn/start',id:3,params:{threadId,input:[{type:'text',text:prompt}]}});
    status({state:'turn-requested'});
  }
  if(m.id===3&&m.result){turnId=m.result.turn?.id;json('turn-start-result.json',m.result);status({state:'running'});}
  if(m.method==='turn/started'){turnId=m.params?.turn?.id||turnId;status({state:'running'});}
  if(m.method==='item/completed'){
    const item=m.params?.item;if(item?.id)items.set(item.id,item);
    if(item?.type==='agentMessage'){
      const record={at:new Date().toISOString(),id:item.id,phase:item.phase||null,text:item.text||''};agentMessages.push(record);
      if(agentMessages.length===1)json('first-agent-message.json',record);
      if(record.phase==='final_answer'&&!fs.existsSync(path.join(output,'first-final-answer.json')))json('first-final-answer.json',record);
    }
    status({state:'running',completedItems:items.size,lastCompletedType:item?.type});
  }
  if(m.method==='thread/tokenUsage/updated'){tokenUsage=m.params;json('token-usage-live.json',tokenUsage);}
  if(m.method==='turn/completed'){
    json('turn-completed.json',m.params);const turn=m.params?.turn;
    setTimeout(()=>finish(turn?.status||'unknown-turn-status',turn?.error?new Error(JSON.stringify(turn.error)):undefined),400);
  }
});
child.stderr.on('data',chunk=>fs.appendFileSync(path.join(output,'stderr.txt'),redactText(chunk.toString('utf8')),'utf8'));
child.on('error',error=>finish('launch-error',error));
child.on('exit',(code,signal)=>{childExit={code,signal};json('process-exit.json',{at:new Date().toISOString(),code,signal});if(!closing&&!finished)finish('process-exited-before-result');lines.close();});
send({method:'initialize',id:1,params:{clientInfo:{name:'megafon_comparison_run',title:'Local paired comparison',version:'1.0'}}});
