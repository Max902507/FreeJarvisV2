'use strict';
const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('freejarvisDesktop',Object.freeze({
  pickPath:art=>['ordner','programm'].includes(art)?ipcRenderer.invoke('freejarvis:pick-path',art):Promise.reject(new Error('Ungültiger Dialogtyp.'))
}));
