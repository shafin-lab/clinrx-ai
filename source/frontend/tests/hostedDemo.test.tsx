import {afterEach,it,expect,vi} from 'vitest';
import {cleanup,render,screen} from '@testing-library/react';
vi.mock('../src/config',()=>({hostedSyntheticDemo:true,demo:{base:window.location.origin,patient:'synthetic-p1',encounter:'synthetic-e1'}}));
vi.mock('../src/demo/ComprehensiveDemo',()=>({ComprehensiveDemo:()=> <h1>Comprehensive workspace</h1>}));
import App from '../src/App';
afterEach(()=>{cleanup();window.history.replaceState({},'', '/');});
it('opens the comprehensive workspace with explicit hosted transport',()=>{
  render(<App/>);expect(screen.getByRole('heading',{name:'Comprehensive workspace'})).toBeTruthy();
});
it('does not expose the legacy preparation workspace through the query string',()=>{
  window.history.replaceState({},'', '/?workspace=legacy');render(<App/>);
  expect(screen.getByText('The legacy workspace is unavailable in this hosted preview.')).toBeTruthy();
  expect(screen.queryByRole('heading',{name:'Comprehensive workspace'})).toBeNull();
  expect(screen.getByRole('link',{name:'Open the comprehensive demo'}).getAttribute('href')).toBe('/');
});
