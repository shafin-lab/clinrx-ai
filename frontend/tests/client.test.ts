import {it,expect,vi} from 'vitest';
import {ReviewClient,ApiFailure} from '../src/api/client';
import fixture from './fixtures.json';
const id=fixture.execution.execution_id, command='OPAQUE.DO.NOT.DECODE';
const prepared={status:'prepared' as const,execution_id:id,inference_reference:fixture.execution.provenance.inference.reference,command};
const reply=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status});
it('preserves exact offset/precision in state query and has no caller cutoff',async()=>{const fetcher=vi.fn<typeof fetch>().mockResolvedValue(reply(fixture.state));const client=new ReviewClient('http://localhost:8000','p /','e?',fetcher);await client.state('2026-10-08T08:00:00.123456+05:30','2026-10-08T10:00:00+05:30');const url=new URL(String(fetcher.mock.calls[0][0]));expect(url.searchParams.get('review_start')).toBe('2026-10-08T08:00:00.123456+05:30');expect([...url.searchParams.keys()]).toEqual(['review_start','review_end']);expect(url.pathname).toContain('p%20%2F');});
it.each(['execute','reconcile'] as const)('%s posts opaque command unchanged',async(op)=>{const fetcher=vi.fn<typeof fetch>().mockResolvedValue(reply(op==='execute'?fixture.execution:{status:'committed_match',execution:fixture.execution}));await new ReviewClient('http://localhost:8000','p','e',fetcher)[op](prepared);expect(fetcher.mock.calls[0][1]?.body).toBe(JSON.stringify({command}));expect(fetcher).toHaveBeenCalledTimes(1);});
it.each(['not_found','execution_conflict','storage_integrity_failure','completion_unknown','made_up'])('bounds %s error text and fields',async(code)=>{const fetcher=vi.fn<typeof fetch>().mockResolvedValue(reply({code,message:'PRIVATE SQL command',fields:[{path:'PRIVATE',code:'invalid_value'},{path:'body.command',code:'invalid_value'}]},503));try{await new ReviewClient('http://localhost:8000','p','e',fetcher).lookup(id);throw Error('missing rejection');}catch(e){expect(e).toBeInstanceOf(ApiFailure);const error=e as ApiFailure;expect(error.message).not.toContain('PRIVATE');expect(error.fields).toEqual([{path:'body.command',code:'invalid_value'}]);}expect(fetcher).toHaveBeenCalledTimes(1);});
it('does not retry dropped execution',async()=>{const fetcher=vi.fn<typeof fetch>().mockRejectedValue(Error('PRIVATE'));await expect(new ReviewClient('http://localhost:8000','p','e',fetcher).execute(prepared)).rejects.toMatchObject({code:'network_error'});expect(fetcher).toHaveBeenCalledTimes(1);});
it('rejects a mismatched execution receipt',async()=>{const fetcher=vi.fn<typeof fetch>().mockResolvedValue(reply({...fixture.execution,execution_id:'wrong'}));await expect(new ReviewClient('http://localhost:8000','p','e',fetcher).execute(prepared)).rejects.toMatchObject({code:'invalid_response'});});
it.each(['https://external.example','http://user:secret@localhost:8000','http://localhost:8000/?command=secret'])('rejects non-demo origin %s',base=>{expect(()=>new ReviewClient(base,'p','e')).toThrow();});

it('invokes browser fetch without a client-object receiver',async()=>{
  const fetcher: typeof fetch = async function(this: unknown) {
    if (this !== undefined) throw new TypeError('Illegal invocation');
    return reply(fixture.state);
  };
  await expect(new ReviewClient('http://localhost:8000','p','e',fetcher).state('start','end')).resolves.toMatchObject({data:fixture.state});
});
