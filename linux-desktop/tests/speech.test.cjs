'use strict';
const test=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const js=fs.readFileSync(path.join(__dirname,'../desktop/speech-adapter.js'),'utf8');
test('desktop recognition uses local PCM endpoint and releases microphone',async()=>{
 let proc,stopped=0,started=0,ended=0,transcript='';const req=[];
 class AC{constructor(){this.sampleRate=48000;this.destination={};}resume(){return Promise.resolve();}close(){return Promise.resolve();}createMediaStreamSource(){return {connect(){},disconnect(){}};}createScriptProcessor(){return proc={connect(){},disconnect(){}};}createGain(){return {gain:{},connect(){},disconnect(){}};}}
 const win={__freejarvisSpeechCaps:{stt:['de','en'],tts:false},SpeechRecognition:class{start(){throw Error('Online recognizer must not run');}}};
 const ctx={window:win,navigator:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop(){stopped++;}}]})}},AudioContext:AC,fetch:async(url,opts)=>{const body=JSON.parse(opts.body);req.push({url,body});return {ok:true,json:async()=>url.endsWith('/start')?{id:'local'}:url.endsWith('/chunk')?{text:'hallo jarvis',final:true}:{ok:true}};},console,btoa,queueMicrotask};
 vm.runInNewContext(js,ctx);const rec=new win.SpeechRecognition();rec.onstart=()=>started++;rec.onend=()=>ended++;rec.onresult=e=>transcript=e.results[0][0].transcript;
 await rec.start();assert.equal(started,1);proc.onaudioprocess({inputBuffer:{getChannelData:()=>new Float32Array(4800).fill(.2)}});await rec.queue;await new Promise(r=>setImmediate(r));
 assert.equal(transcript,'hallo jarvis');assert.equal(stopped,1);assert.equal(ended,1);assert.equal(req[1].url,'/api/desktop/speech/chunk');assert.equal(Buffer.from(req[1].body.pcm,'base64').length,3200);assert(req.some(r=>r.url.endsWith('/stop')));
});
test('local voice adapter identifies voices as offline',()=>{
 const win={__freejarvisSpeechCaps:{stt:['de','en'],tts:true}};vm.runInNewContext(js,{window:win,console,queueMicrotask});assert.equal(win.speechSynthesis.getVoices().length,2);assert(win.speechSynthesis.getVoices().every(v=>v.localService));
});
