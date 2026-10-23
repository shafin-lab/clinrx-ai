/** Compare explicit instants without discarding source fractional precision. */
export function compareRespiratoryInstants(a:string,b:string):number|null {
 function parts(value:string){
  if(value.length>128)return null;
  const match=/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if(!match||Number(match[2])>23||Number(match[3])>59||Number(match[4])>59)return null;
  const day=Date.parse(match[1]+'T00:00:00Z');
  if(!Number.isFinite(day)||new Date(day).toISOString().slice(0,10)!==match[1])return null;
  const seconds=Date.parse(`${match[1]}T${match[2]}:${match[3]}:${match[4]}${match[6]}`);
  return Number.isFinite(seconds)?{seconds,fraction:(match[5]??'').replace(/0+$/,'')}:null;
 }
 const x=parts(a),y=parts(b);if(!x||!y)return null;
 if(x.seconds!==y.seconds)return x.seconds<y.seconds?-1:1;
 const digits=Math.max(x.fraction.length,y.fraction.length),xf=x.fraction.padEnd(digits,'0'),yf=y.fraction.padEnd(digits,'0');
 return xf===yf?0:xf<yf?-1:1;
}
