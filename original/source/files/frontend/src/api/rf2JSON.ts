/** Duplicate-aware JSON admission for local RF2 replies, before object construction. */
export function parseRF2JSON(text:string):unknown {
 let i=0;
 const whitespace=()=>{while(/[\t\n\r ]/.test(text[i]??'!'))i++;};
 const string=()=>{const start=i;if(text[i++]!=='"')throw Error('JSON string required');while(i<text.length){const c=text[i++];if(c==='\\'){i++;continue;}if(c==='"')return JSON.parse(text.slice(start,i)) as string;}throw Error('Unterminated JSON string');};
 function value(depth:number):unknown {
  if(depth>64)throw Error('JSON nesting limit');whitespace();const c=text[i];
  if(c==='"')return string();
  if(c==='{'){i++;const entries:[string,unknown][]=[];const names=new Set<string>();whitespace();if(text[i]==='}'){i++;return {};}
   while(i<text.length){whitespace();const name=string();if(names.has(name))throw Error('Duplicate JSON member');names.add(name);whitespace();if(text[i++]!==':')throw Error('JSON colon required');entries.push([name,value(depth+1)]);whitespace();const end=text[i++];if(end==='}')return Object.fromEntries(entries);if(end!==',')throw Error('Invalid JSON object');}throw Error('Unterminated JSON object');}
  if(c==='['){i++;const values:unknown[]=[];whitespace();if(text[i]===']'){i++;return values;}while(i<text.length){values.push(value(depth+1));whitespace();const end=text[i++];if(end===']')return values;if(end!==',')throw Error('Invalid JSON array');}throw Error('Unterminated JSON array');}
  const m=/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(i));if(!m)throw Error('Invalid JSON value');i+=m[0].length;return JSON.parse(m[0]) as unknown;
 }
 const result=value(0);whitespace();if(i!==text.length)throw Error('Trailing JSON content');return result;
}
export async function readRF2JSON(response:Response){
 const reader=response.body?.getReader();if(!reader)throw Error('Response body unavailable');const chunks:Uint8Array[]=[];let size=0;
 try{while(true){const next=await reader.read();if(next.done)break;size+=next.value.byteLength;if(size>2097152){await reader.cancel();throw Error('Response size limit');}chunks.push(next.value);}}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of chunks){bytes.set(part,offset);offset+=part.length;}return parseRF2JSON(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
