import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
// Shared workspaces load lazy modules and verify source digests before rendering.
// Allow that real asynchronous work to finish on a busy verification host.
configure({asyncUtilTimeout:5000});
const lockTails=new Map<string,Promise<unknown>>();
Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(name:string,callback:()=>unknown)=>{const previous=lockTails.get(name)??Promise.resolve();const next=previous.then(callback);lockTails.set(name,next.then(()=>undefined,()=>undefined));return next;}}});
afterEach(()=>{cleanup();vi.restoreAllMocks();localStorage.clear();});
HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
