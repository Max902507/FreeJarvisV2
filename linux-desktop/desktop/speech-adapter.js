/* Desktop-only Web Speech compatibility; no DOM or theme modifications. */
(() => {
  'use strict';
  const caps = window.__freejarvisSpeechCaps;
  const post = async (op, data, signal) => {
    const r = await fetch('/api/desktop/speech/' + op, {method:'POST', headers:{'Content-Type':'application/json','X-Jarvis':'1'},body:JSON.stringify(data),signal});
    if (!r.ok) { let msg='Lokaler Sprachdienst: HTTP '+r.status; try {msg=(await r.json()).error||msg;} catch {} throw new Error(msg); }
    return op === 'tts' ? r.blob() : r.json();
  };
  function pcm16(samples, rate) {
    const count=Math.floor(samples.length*16000/rate), out=new Uint8Array(count*2), view=new DataView(out.buffer);
    for(let i=0;i<count;i++) {
      const a=Math.floor(i*rate/16000), b=Math.min(samples.length,Math.max(a+1,Math.floor((i+1)*rate/16000)));
      let v=0;for(let j=a;j<b;j++)v+=samples[j];v=Math.max(-1,Math.min(1,v/(b-a)));
      view.setInt16(i*2,Math.round(v*(v<0?32768:32767)),true);
    }
    let s='';for(let i=0;i<out.length;i++)s+=String.fromCharCode(out[i]);return btoa(s);
  }
  class LocalRecognition {
    constructor(){this.lang='de-DE';this.continuous=false;this.interimResults=false;this.running=false;this.gen=0;this.pending=0;}
    async start(){
      if(this.running)return; this.running=true;const g=++this.gen;this.pending=0;this.queue=Promise.resolve();
      const active=()=>this.running&&g===this.gen;
      try {
        if(!caps.stt.includes(this.lang.split('-')[0].toLowerCase()))throw new Error('Sprachpaket fehlt: '+this.lang);
        const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
        if(!active()){stream.getTracks().forEach(t=>t.stop());return;}this.stream=stream;
        const s=await post('start',{lang:this.lang});
        if(!active()){post('stop',{id:s.id}).catch(()=>{});return;}this.sid=s.id;
        this.ctx=new AudioContext();await this.ctx.resume();if(!active())return;
        this.src=this.ctx.createMediaStreamSource(stream);this.proc=this.ctx.createScriptProcessor(4096,1,1);
        this.mute=this.ctx.createGain();this.mute.gain.value=0;
        this.proc.onaudioprocess=e=>{
          if(!active())return;
          if(this.pending>=12){this.fail('audio-capture','Lokale Spracherkennung ist überlastet.');return;}
          const pcm=pcm16(e.inputBuffer.getChannelData(0),this.ctx.sampleRate), id=this.sid;this.pending++;
          this.queue=this.queue.then(async()=>{
            if(!active())return;
            const r=await post('chunk',{id,pcm}); if(!active()||!r.text)return;
            if(r.final||this.interimResults){const row=[{transcript:r.text,confidence:1}];row.isFinal=r.final;this.onresult?.({resultIndex:0,results:[row]});}
            if(r.final&&!this.continuous&&active())this.abort();
          }).catch(err=>{if(active())this.fail('audio-capture',err.message);}).finally(()=>{if(g===this.gen)this.pending--;});
        };
        this.src.connect(this.proc);this.proc.connect(this.mute);this.mute.connect(this.ctx.destination);
        this.onstart?.();
      } catch(err){if(active())this.fail(err.name==='NotAllowedError'?'not-allowed':'audio-capture',err.message);}
    }
    fail(error,message){console.warn('FreeJarvis Sprache:',message);this.onerror?.({error,message});this.abort();}
    stop(){this.abort();}
    abort(){
      if(!this.running)return;this.running=false;++this.gen;
      const sid=this.sid;this.sid=null;if(sid)post('stop',{id:sid}).catch(()=>{});
      this.stream?.getTracks().forEach(t=>t.stop());this.stream=null;
      if(this.proc){this.proc.onaudioprocess=null;this.proc.disconnect();}this.src?.disconnect();this.mute?.disconnect();
      this.ctx?.close().catch(()=>{});this.ctx=null;this.proc=null;this.src=null;this.mute=null;
      queueMicrotask(()=>this.onend?.());
    }
  }
  // Never fall back silently to the nonfunctional Google service in Electron.
  for(const key of ['SpeechRecognition','webkitSpeechRecognition'])Object.defineProperty(window,key,{value:LocalRecognition,configurable:true});
  if(caps.tts){
    const voices=[{name:'Deutsch · lokale Systemstimme',lang:'de-DE',localService:true,default:true,voiceURI:'desktop-de'},{name:'English · local system voice',lang:'en-US',localService:true,default:false,voiceURI:'desktop-en'}];
    let current=null;
    function cancel(){if(!current)return;const c=current;current=null;c.ctrl.abort();c.audio?.pause();if(c.url)URL.revokeObjectURL(c.url);}
    const synth={getVoices:()=>voices.slice(),cancel,onvoiceschanged:null,
      speak(u){cancel();const c={ctrl:new AbortController(),audio:null,url:null};current=c;
        const finish=(error)=>{if(current!==c)return;current=null;if(c.url)URL.revokeObjectURL(c.url);if(error)u.onerror?.({error});else u.onend?.();};
        if(!u.text.trim()){queueMicrotask(()=>finish());return;}
        post('tts',{text:u.text,lang:u.voice?.lang||u.lang,rate:u.rate,pitch:u.pitch},c.ctrl.signal).then(blob=>{
          if(current!==c)return;c.url=URL.createObjectURL(blob);c.audio=new Audio(c.url);c.audio.volume=Math.max(0,Math.min(1,u.volume??1));
          c.audio.onended=()=>finish();c.audio.onerror=()=>finish('audio-hardware');c.audio.onplaying=()=>u.onstart?.();
          return c.audio.play();
        }).catch(()=>finish('synthesis-failed'));
      }};
    class Utterance {constructor(text=''){this.text=String(text);this.lang='de-DE';this.rate=1;this.pitch=1;this.volume=1;this.voice=null;}}
    Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
    Object.defineProperty(window,'SpeechSynthesisUtterance',{value:Utterance,configurable:true});
  }
})();
