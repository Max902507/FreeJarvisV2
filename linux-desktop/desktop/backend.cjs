'use strict';
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const { createInterface } = require('node:readline');
const path = require('node:path');
function startBackend({command,args=[],assetDir,dataDir,port=5051,timeout=15000,onLog=()=>{}}) {
  const token = randomBytes(32).toString('hex');
  const child = spawn(command,args,{cwd:assetDir,env:{...process.env,JARVIS_DESKTOP_TOKEN:token,JARVIS_ASSET_DIR:assetDir,JARVIS_DATA_DIR:dataDir,JARVIS_DESKTOP_PORT:String(port),PYTHONUNBUFFERED:'1'},stdio:['ignore','pipe','pipe'],windowsHide:true});
  let stopping=false;
  const ready = new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>fail(new Error('FreeJarvis-Backend meldet sich nicht.')),timeout);
    function fail(err){clearTimeout(timer); stop(); reject(err);}
    child.once('error',fail);
    child.once('exit',(code,signal)=>fail(new Error(`Backend beendet (${code ?? signal}).`)));
    const lines=createInterface({input:child.stdout});
    lines.on('line',line=>{
      if(line===`FREEJARVIS_READY ${port}`){clearTimeout(timer);resolve({origin:`http://127.0.0.1:${port}`,token});}
      else onLog(line);
    });
    child.stderr.on('data',b=>onLog(b.toString()));
  });
  function stop(){if(stopping)return;stopping=true;if(child.exitCode===null&&child.signalCode===null){child.kill('SIGTERM');const t=setTimeout(()=>{if(child.exitCode===null&&child.signalCode===null)child.kill('SIGKILL');},2500);t.unref();}}
  return {child,ready,stop};
}
function sameOrigin(url,origin){try{return new URL(url).origin===origin;}catch{return false;}}
function externalHttp(url){try{return ['https:','http:'].includes(new URL(url).protocol);}catch{return false;}}
module.exports={startBackend,sameOrigin,externalHttp};
