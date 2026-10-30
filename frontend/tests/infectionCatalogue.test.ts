import { describe, expect, it } from 'vitest';
import sourceCatalogue from '../src/infectionLibrary/data/infection-guidance.json';

const catalogue = (): any => structuredClone(sourceCatalogue);

describe('source-owned infection catalogue', () => {
  it('holds source dose anomalies instead of offering incomplete drug amounts', () => {
    const data = catalogue();
    for (const section of ['10.7', '6.7', '9.3']) {
      const infection = data.infections.find((item: any) => item.ncdcSection === section);
      const anomaly = infection.cases.filter((context: any) => context.regimens.some((regimen: any) => /1-2 g IV\+500 mg|Ceftriaxone 500\s+IM|Penicillin V 250-500/.test(regimen.instructions)) || context.notes.some((note: string) => /1-2 g IV\+500 mg|Ceftriaxone 500\s+IM|Penicillin V 250-500/.test(note)));
      expect(anomaly.length, `${section} source anomaly retained`).toBeGreaterThan(0);
      for (const context of anomaly) {
        expect(context.regimens).toHaveLength(0);
        expect(context.gaps.join(' ')).toMatch(/unit|unattributed|ambiguous/i);
      }
    }
  });

  it('shows verified lung-abscess duration and neutral endocarditis heading', () => {
    const data = catalogue();
    expect(data.infections.find((item: any) => item.ncdcSection === '1.1').name).toBe('Infective Endocarditis');
    const lung = data.infections.find((item: any) => item.ncdcSection === '12.6');
    expect(lung.cases.flatMap((context: any) => context.regimens).every((regimen: any) => regimen.duration === '4-6 weeks')).toBe(true);
  });

  it('retains urological prophylaxis rows with missing doses as explicit holds', () => {
    const infection = catalogue().infections.find((item: any) => item.ncdcSection === '10.7');
    for (const pattern of [/Urology.*clean.*with entry/i, /Urology.*clean.*without entry/i, /Genitourinary.*instrumentation/i]) {
      const context = infection.cases.find((item: any) => pattern.test(item.label));
      expect(context).toBeDefined();
      expect(context.regimens).toHaveLength(0);
      expect(context.gaps.join(' ')).toMatch(/dose|dosage|missing/i);
      expect(context.pdfPages).toContain(74);
    }
  });

  it('covers all 19 NCDC groups and all 87 named TOC subsections', () => {
    const data = catalogue();
    expect(data.groups).toHaveLength(19);
    const sections = data.infections.filter((infection: any) => infection.ncdcSection);
    expect(sections).toHaveLength(87);
    for (let group = 1; group <= 19; group++) {
      expect(sections.some((infection: any) => infection.ncdcSection.startsWith(`${group}.`))).toBe(true);
    }
    expect(sections.map((infection: any) => infection.ncdcSection)).toContain('6.10');
    expect(sections.map((infection: any) => infection.ncdcSection)).toContain('18.7');
  });

  it('retains full source hashes, locators, unique identifiers and static eligibility flags', () => {
    const data = catalogue();
    expect(data.review_status).toBe('unreviewed');
    expect(data.executable).toBe(false);
    expect(data.clinical_use_eligible).toBe(false);
    expect(data.sources.map((source: any) => source.id)).toEqual(['ncdc']);
    for (const source of data.sources) expect(source.sha256).toMatch(/^[a-f0-9]{64}$/);
    const ids: string[] = [];
    for (const infection of data.infections) {
      ids.push(infection.id);
      expect(data.groups.some((group: any) => group.id === infection.groupId)).toBe(true);
      expect(infection.cases.length).toBeGreaterThan(0);
      for (const context of infection.cases) {
        ids.push(context.id);
        expect(context.locator).toMatch(/PDF/);
        expect(context.pdfPages.length).toBeGreaterThan(0);
        expect(context.pdfPages.every((page: number) => Number.isInteger(page) && page > 0 && page <= (context.sourceId === 'ncdc' ? 157 : 104))).toBe(true);
        expect(context.regimens.length > 0 || context.gaps.length > 0 || !!context.reference).toBe(true);
        for (const regimen of context.regimens) {
          ids.push(regimen.id);
          expect(regimen.instructions.trim().length).toBeGreaterThan(0);
        }
      }
    }
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('keeps NCDC CAP acquisition and severity contexts distinct with factual primary fields', () => {
    const infection = catalogue().infections.find((item: any) => item.ncdcSection === '12.5');
    expect(infection).toBeDefined();
    expect(infection.cases.every((context: any) => context.sourceId === 'ncdc')).toBe(true);
    expect(infection.cases.some((context: any) => /OPD/.test(context.label))).toBe(true);
    expect(infection.cases.some((context: any) => /ward/i.test(context.label))).toBe(true);
    expect(infection.cases.some((context: any) => /ICU/.test(context.label))).toBe(true);
    expect(JSON.stringify(infection)).toMatch(/Amoxicillin/i);
    expect(infection.cases[0].regimens[0].instructions).toBe('Amoxicillin 1g q8h for 5-7 days');
    expect(JSON.stringify(infection)).toMatch(/500mg|500 mg/);
    expect(infection.cases.some((context: any) => context.pdfPages.includes(90))).toBe(true);
  });

  it('splits unambiguous lung-abscess primary OR choices without copying alternative columns', () => {
    const infection = catalogue().infections.find((item: any) => item.ncdcSection === '12.6');
    const primary = infection.cases.find((context: any) => /Primary lung abscess/i.test(context.label));
    expect(primary.regimens).toHaveLength(2);
    expect(primary.regimens[0].instructions).toMatch(/Clindamycin 600mg IV/);
    expect(primary.regimens[1].instructions).toMatch(/Amoxicillin-\s*clavulanate 1.2g IV/);
    expect(primary.regimens.every((regimen: any) => !/Piperacillin/i.test(regimen.instructions))).toBe(true);
  });

  it('keeps unresolved source branches explicit instead of inventing missing dosing fields', () => {
    const infections = catalogue().infections;
    expect(infections.some((item: any) => item.cases.some((context: any) => context.gaps.length > 0))).toBe(true);
    const all = JSON.stringify(infections);
    expect(all).toMatch(/source review|not supplied|conditional|unresolved/i);
    expect(all).not.toMatch(/CRRT|continuous renal replacement/i);
  });

  it('exposes only NCDC infections and contexts, without supplemental source entries', () => {
    const data = catalogue();
    expect(data.infections).toHaveLength(87);
    expect(data.infections.every((infection: any) => infection.ncdcSection && infection.cases.every((context: any) => context.sourceId === 'ncdc'))).toBe(true);
    expect(JSON.stringify(data)).not.toMatch(/jipmer/i);
    const endocarditis = data.infections.find((item: any) => item.ncdcSection === '1.1');
    expect(endocarditis.cases).toHaveLength(3);
  });

  it('does not treat surgical expected pathogens or isolated continuation tails as treatment regimens', () => {
    const data = catalogue();
    const prophylaxis = data.infections.find((item: any) => item.ncdcSection === '10.7');
    const appendectomy = prophylaxis.cases.find((context: any) => /Appendectomy/.test(context.label));
    expect(appendectomy.regimens[0].instructions).toBe('Cefuroxime — 1-2 g IV');
    expect(data.infections.flatMap((item: any) => item.cases).some((context: any) => /^like bullae|^specific infection/.test(context.label))).toBe(false);
    const fungal = data.infections.find((item: any) => item.ncdcSection === '17.4');
    expect(fungal.cases.filter((context: any) => context.pdfPages.includes(110)).every((context: any) => /BMT|HSCT/.test(context.label))).toBe(true);
  });
});
