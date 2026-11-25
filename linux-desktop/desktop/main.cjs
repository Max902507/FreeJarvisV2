'use strict';
const {app,BrowserWindow,dialog,session,shell,ipcMain}=require('electron');
const path=require('node:path');
const fs=require('node:fs');
const {startBackend,sameOrigin,externalHttp}=require('./backend.cjs');
let backend,win,quitting=false,origin;
const PORT=5051;
// Native Wayland/X11 default selection stays unchanged after successful DEV 1 rendering.
// The original web application keeps preferences in localStorage; keep this origin stable.
app.setName('FreeJarvis');
if(process.platform==='linux')app.setDesktopName?.('de.freejarvis.desktop');
const profile=path.join(app.getPath('appData'),'FreeJarvis');
fs.mkdirSync(profile,{recursive:true,mode:0o700});
app.setPath('userData',profile);
if(!app.requestSingleInstanceLock()){app.quit();}else{
app.on('second-instance',()=>{if(win){if(win.isMinimized())win.restore();win.focus();}});
app.on('before-quit',()=>{quitting=true;backend?.stop();});
app.on('window-all-closed',()=>app.quit());
app.whenReady().then(async()=>{
  const root=app.isPackaged?process.resourcesPath:path.resolve(__dirname,'..','stage');
  const assets=path.join(root,app.isPackaged?'jarvis':'assets');
  const data=path.join(app.getPath('userData'),'data');
  fs.mkdirSync(data,{recursive:true,mode:0o700});
  fs.chmodSync(data,0o700);
  const log=path.join(data,'desktop.log');
  const onLog=(s)=>{try{fs.appendFileSync(log,`${new Date().toISOString()} ${s}\n`,{mode:0o600});}catch{}};
  const cmd=app.isPackaged?path.join(root,'backend','freejarvis-backend'):process.env.FREEJARVIS_PYTHON||'python3';
  backend=startBackend({command:cmd,args:app.isPackaged?[]:[path.join(assets,'desktop_server.py')],assetDir:assets,dataDir:data,port:PORT,onLog});
  const info=await backend.ready;origin=info.origin;
  backend.child.once('exit',()=>{if(!quitting){dialog.showErrorBox('FreeJarvis','Das lokale Backend wurde beendet. Details: '+log);app.quit();}});
  const ses=session.fromPartition('persist:freejarvis');
  // No secrets in renderer JavaScript. Send session token only to our own server.
  ses.webRequest.onBeforeSendHeaders({urls:[origin+'/*']},(details,cb)=>cb({requestHeaders:{...details.requestHeaders,'X-FreeJarvis-Desktop':info.token}}));
  ses.webRequest.onBeforeRequest({urls:['http://*/*','https://*/*']},(d,cb)=>cb({cancel:!sameOrigin(d.url,origin)}));
  function allowMedia(permission,requestingOrigin,details){return permission==='media'&&sameOrigin(requestingOrigin,origin)&&!(details?.mediaTypes||[]).includes('video')&&details?.mediaType!=='video';}
  let microphoneAllowed=false,micDecision=null;
  ses.setPermissionCheckHandler((wc,p,o,d)=>Boolean(microphoneAllowed&&wc===win?.webContents&&allowMedia(p,o,d)));
  ses.setPermissionRequestHandler((wc,p,cb,d)=>{
    if(wc!==win?.webContents||!allowMedia(p,d.requestingUrl||wc.getURL(),d)){cb(false);return;}
    if(microphoneAllowed){cb(true);return;}
    if(!micDecision)micDecision=dialog.showMessageBox(win,{type:'question',buttons:['Erlauben','Ablehnen'],defaultId:1,cancelId:1,title:'FreeJarvis',message:'FreeJarvis Zugriff auf das Mikrofon erlauben? Die Desktop-Spracherkennung verarbeitet Audio lokal.'}).then(r=>microphoneAllowed=r.response===0,()=>false);
    micDecision.then(cb);
  });
  // Native Electron dialog, using XDG portals where supported; no KDE/GNOME executable required.
  ipcMain.handle('freejarvis:pick-path',async(event,art)=>{
    if(!win||event.sender!==win.webContents||!event.senderFrame||event.senderFrame!==win.webContents.mainFrame||!sameOrigin(event.senderFrame.url,origin)||!['ordner','programm'].includes(art))throw new Error('Nicht erlaubte Dateiauswahl.');
    const result=await dialog.showOpenDialog(win,{title:art==='ordner'?'Ordner für Jarvis freigeben':'Programm für Jarvis freigeben',defaultPath:app.getPath('home'),properties:[art==='ordner'?'openDirectory':'openFile']});
    return result.canceled||!result.filePaths.length?{ok:false,pfad:'',fehler:'Nichts ausgewählt.'}:{ok:true,pfad:result.filePaths[0],fehler:''};
  });
  win=new BrowserWindow({width:1280,height:800,minWidth:640,minHeight:480,show:false,autoHideMenuBar:true,title:'FreeJarvis',webPreferences:{preload:path.join(__dirname,'preload.cjs'),session:ses,nodeIntegration:false,contextIsolation:true,sandbox:true,webSecurity:true,allowRunningInsecureContent:false}});
  win.webContents.on('will-navigate',(e,url)=>{if(!sameOrigin(url,origin)){e.preventDefault();}});
  win.webContents.on('will-redirect',(e,url)=>{if(!sameOrigin(url,origin))e.preventDefault();});
  win.webContents.on('will-attach-webview',e=>e.preventDefault());
  win.webContents.setWindowOpenHandler(({url})=>{if(externalHttp(url)&&!sameOrigin(url,origin))shell.openExternal(url).catch(()=>{});return {action:'deny'};});
  win.once('ready-to-show',()=>win?.show());
  win.on('closed',()=>{win=null;});
  await win.loadURL(origin+'/');
}).catch(e=>{dialog.showErrorBox('FreeJarvis – Startfehler',String(e.message||e)+'\nPort '+PORT+' muss frei sein.');app.quit();});
}
