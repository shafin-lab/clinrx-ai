/** Bounded decimal arithmetic for display-only chart reconciliation. No binary float quantities. */
export type Fraction={n:bigint;d:bigint};
const gcd=(a:bigint,b:bigint):bigint=>{a=a<0n?-a:a;while(b){const r=a%b;a=b;b=r;}return a||1n;};
function reduced(n:bigint,d:bigint):Fraction{if(d<=0n)throw Error('Invalid denominator');const g=gcd(n,d);return {n:n/g,d:d/g};}
export function decimal(text:string):Fraction{
 if(text.length>90||!/^[-+]?(?:0|[1-9]\d*)(?:\.\d{1,30})?$/.test(text))throw Error('Unsupported decimal');
 const negative=text.startsWith('-'),parts=text.replace(/^[-+]/,'').split('.');return reduced(BigInt(parts.join(''))*(negative?-1n:1n),10n**BigInt(parts[1]?.length??0));
}
export const plus=(a:Fraction,b:Fraction)=>reduced(a.n*b.d+b.n*a.d,a.d*b.d);
export const minus=(a:Fraction,b:Fraction)=>reduced(a.n*b.d-b.n*a.d,a.d*b.d);
export const times=(a:Fraction,b:Fraction)=>reduced(a.n*b.n,a.d*b.d);
export const divide=(a:Fraction,b:Fraction)=>{if(b.n<=0n)throw Error('Invalid divisor');return reduced(a.n*b.d,a.d*b.n);};
export const zero=():Fraction=>({n:0n,d:1n});
export function formatNumber(v:Fraction,digits=2,trim=true){
 const scale=10n**BigInt(digits),negative=v.n<0n,a=negative?-v.n:v.n;
 const whole=a*scale/v.d,remainder=a*scale%v.d,rounded=whole+(2n*remainder>=v.d?1n:0n);
 const raw=rounded.toString().padStart(digits+1,'0'),body=digits?raw.slice(0,-digits)+'.'+raw.slice(-digits):raw;
 return (negative&&rounded!==0n?'-':'')+(trim?body.replace(/(\.\d*?)0+$/,'$1').replace(/\.$/,''):body);
}
