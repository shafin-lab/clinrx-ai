import type {ExactRef} from '../api/circulatoryTypes';

/** Parse this flat, string-only contract before duplicates can be discarded.
 * JSON.parse is used only on individual string tokens, never on the object.
 * Decoded member names make escaped equivalents duplicates as well.
 */
export function retainedReassessmentReference(input:unknown):ExactRef|undefined{
 if(typeof input!=='string')return undefined;
 let offset=0;
 const whitespace=()=>{while(offset<input.length&&/[\x20\t\r\n]/.test(input[offset]))offset++;};
 const consume=(char:string)=>{whitespace();if(input[offset]!==char)return false;offset++;return true;};
 const string=():string|undefined=>{
  whitespace();
  const token=input.slice(offset).match(/^"(?:[^"\\\u0000-\u001f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"/);
  if(!token)return undefined;
  offset+=token[0].length;
  return JSON.parse(token[0]) as string;
 };
 if(!consume('{'))return undefined;
 const members=new Map<string,string>();
 for(let count=0;count<3;count++){
  const name=string();
  if(name===undefined||!['kind','id','version'].includes(name)||members.has(name)||!consume(':'))return undefined;
  const value=string();if(value===undefined||value.length===0)return undefined;
  members.set(name,value);
  if(consume('}')){
   whitespace();
   if(offset!==input.length||members.size!==3)return undefined;
   return {kind:members.get('kind')!,id:members.get('id')!,version:members.get('version')!};
  }
  if(!consume(','))return undefined;
 }
 return undefined;
}
