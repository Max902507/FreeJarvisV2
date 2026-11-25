'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {startBackend,sameOrigin,externalHttp}=require('../desktop/backend.cjs');
const {once}=require('node:events');
const os=require('node:os');
const path=require('node:path');
const fs=require('node:fs');
test('origin restrictions',()=>{
 const origin='http://127.0.0.1:5051';
 assert(sameOrigin(origin+'/oberflaechen/avatar.html',origin));
 for(const url of ['http://127.0.0.1:5052','https://127.0.0.1:5051','http://127.0.0.1.evil:5051','file:///etc/passwd','not a url'])assert(!sameOrigin(url,origin));
 assert(externalHttp('https://example.com'));assert(!externalHttp('file:///etc/passwd'));assert(!externalHttp('javascript:alert(1)'));
});
test('backend handshake and shutdown with test subprocess',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'freejarvis-test-'));
 const b=startBackend({command:process.execPath,args:['-e','console.log("FREEJARVIS_READY "+process.env.JARVIS_DESKTOP_PORT); setInterval(()=>{},1000)'],assetDir:dir,dataDir:dir,port:5051});
 try{const r=await b.ready;assert.equal(r.origin,'http://127.0.0.1:5051');assert.match(r.token,/^[a-f0-9]{64}$/);}finally{const ended=once(b.child,'exit');b.stop();await ended;fs.rmSync(dir,{recursive:true,force:true});}
});
test('failed backend cannot produce valid readiness',async()=>{
 const b=startBackend({command:process.execPath,args:['-e','process.exit(2)'],assetDir:os.tmpdir(),dataDir:os.tmpdir(),timeout:2000});
 await assert.rejects(b.ready,/Backend beendet/);
});
