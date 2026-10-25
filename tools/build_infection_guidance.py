#!/usr/bin/env python3
"""Build a non-executable infection reference from frozen, read-only PDF snapshots.

Requires pdfplumber 0.11.x. No network, patient data, renal calculator or legacy
reference-data imports. Thin rectangle borders are retained; filled text backing
rectangles are excluded to avoid spurious cell subdivisions. Hand-curated cases
below override extraction only where source branch scope was checked explicitly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT.parent / 'clinrx-antibiotics-prototype/evidence'
OUTPUT = ROOT / 'frontend/src/infectionLibrary/data/infection-guidance.json'
MAPPING = ROOT / 'docs/antibiotics/INFECTION-SOURCE-MAPPING.md'
FLAGS = {'executable': False, 'clinical_use_eligible': False, 'review_status': 'unreviewed'}


def normal(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def toc(pages):
    groups, sections = [], []
    for page in pages[7:11]:
        for line in page['text'].splitlines():
            m = re.match(r'^(\d+)\. (.*?)\s*\.{2}.*?\s(\d+)\s*$', line)
            if m:
                groups.append({'id': f'group-{m[1]}', 'name': m[2]})
            m = re.match(r'^(\d+\.\d+) (.*?)\s*\.{2}.*?\s(\d+)\s*$', line)
            if m:
                sections.append({'number': m[1], 'name': m[2], 'printPage': int(m[3])})
    assert len(groups) == 19 and len(sections) == 87
    return groups, sections


def case(infection, label, pages, source='ncdc', raw='', notes=None, gaps=None, instructions=None, duration=None):
    ident = f"{infection['id']}-case-{len(infection['cases']) + 1}"
    offset = 7
    entry = {'id': ident, 'label': normal(label), 'sourceId': source,
             'locator': f"{'NCDC section ' + infection.get('ncdcSection', '')}; printed p. {', '.join(str(p-offset) for p in pages)}; PDF p. {', '.join(map(str, pages))}",
             'pdfPages': pages, 'regimens': [], 'notes': notes or [], 'gaps': gaps or [], **FLAGS}
    if instructions:
        for index, instruction in enumerate(instructions):
            rgaps = []
            if not re.search(r'\b(IV|IM|PO|orally|oral|topical|intravenous|intravitreal|ointment|cream|troches)\b', instruction, re.I) and re.search(r'\d\s*(mg|g|MU|million)', instruction):
                rgaps.append('Route not supplied in this primary treatment cell; do not infer it.')
            if not duration and not re.search(r'\b(days?|weeks?|months?|single dose|stat)\b', instruction, re.I):
                rgaps.append('Duration not supplied as a fixed value in this primary treatment cell.')
            entry['regimens'].append({'id': f'{ident}-regimen-{index+1}', 'label': f'Primary source option {index+1}', 'instructions': instruction, 'duration': duration, 'gaps': rgaps, **FLAGS})
    elif raw:
        entry['_raw'] = raw
    infection['cases'].append(entry)
    return entry


def finalize(entry):
    raw = entry.pop('_raw', '')
    if not raw:
        return
    raw = re.sub(r'\bf\s+or\b', 'for', raw.strip())
    # Preserve defective source amounts as explicit holds; never guess units or an unnamed agent.
    anomaly = None
    if re.search(r'Cefazolin\s*[—-]\s*1-2 g IV\+500 mg', raw):
        anomaly = 'Ambiguous source dose: the additional 500 mg has no identified agent; source clarification is required.'
    elif re.search(r'Ceftriaxone 500\s+IM|Penicillin V 250-500\s+q6h', raw):
        anomaly = 'Source dose unit is missing for ceftriaxone or penicillin V; no unit is inferred.'
    if anomaly:
        entry['gaps'].append(anomaly)
        entry['notes'].insert(0, 'Primary treatment source text (held for review): ' + raw)
        return
    # A source cross-reference never borrows a regimen from another source.
    crossref = bool(re.search(r'\b(as per|same as|as mentioned|refer|see table|as above)\b', raw, re.I))
    conditional = bool(re.search(r'\b(if|depending|based on|consider|followed|initially|mild|severe|PMA|PNA|neonat|maximum)\b|[±]|\+/-', raw, re.I))
    # Unit slashes are dose facts, not alternative treatments.
    branch_text = re.sub(r'(mg|g|units?|micrograms?)\s*/\s*(kg|day|dose|ml)', '', raw, flags=re.I)
    branch_text = re.sub(r'/\s*(day|dose|kg|ml)\b', '', branch_text, flags=re.I)
    branch = bool(re.search(r'\bor\b|/|\n\s*•', branch_text, re.I))
    options = re.split(r'\n\s*Or\s*\n', raw, flags=re.I)
    simple_options = len(options) > 1 and '+' not in raw and not re.search(r'\b(plus|and)\b', raw, re.I) and not re.search(r'\bor\b|/', re.sub(r'\n\s*Or\s*\n', '', branch_text, flags=re.I), re.I)
    if simple_options and not (crossref or conditional or '\ufffd' in raw or entry.get('_hold', False)):
        duration_match = re.search(r'\nDuration(?: of therapy)?:\s*(.+)$', options[-1], re.I | re.S)
        duration = duration_match[1].strip() if duration_match else None
        if duration_match:
            options[-1] = options[-1][:duration_match.start()].strip()
        entry['regimens'] = [{'id': entry['id'] + f'-regimen-{index+1}', 'label': f'Primary source option {index+1}', 'instructions': option.strip(), 'duration': duration, 'gaps': ['Source treatment fields retained verbatim; missing routes or durations are not inferred.'], **FLAGS} for index, option in enumerate(options)]
        return
    broken = '\ufffd' in raw or '\uf0b3' in raw or len(raw) > 1100
    if crossref or conditional or branch or broken or entry.pop('_hold', False):
        reason = 'Primary source text has unresolved alternatives, conditional branches, cross-references, or extraction continuity; source review is required before selecting a regimen.'
        entry['gaps'].append(reason)
        entry['notes'].insert(0, 'Primary treatment source text (held for review): ' + raw)
        return
    entry['regimens'] = [{'id': entry['id'] + '-regimen-1', 'label': 'Primary source treatment', 'instructions': raw, 'duration': None, 'gaps': [], **FLAGS}]
    regimen = entry['regimens'][0]
    if re.search(r'\d\s*(mg|g|MU|million)', raw) and not re.search(r'\b(IV|IM|PO|oral|orally|topical|intravenous|intravitreal|cream|ointment|troches)\b', raw, re.I):
        regimen['gaps'].append('Route not supplied in this primary treatment cell; do not infer it.')
    if re.search(r'\d\s*(mg|g|MU|million)', raw) and not re.search(r'\b(days?|weeks?|months?|stat|single dose)\b', raw, re.I):
        regimen['gaps'].append('Duration not supplied as a fixed value in this primary treatment cell; inspect the source comments.')


def extract_ncdc(pdf_path, sections):
    infections = [{'id': 'ncdc-' + s['number'].replace('.', '-'), 'groupId': 'group-' + s['number'].split('.')[0], 'name': s['name'], 'ncdcSection': s['number'], 'aliases': [], 'cases': []} for s in sections]
    by_number = {s['number']: inf for s, inf in zip(sections, infections)}
    headings = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_no in range(21, 126):
            page = pdf.pages[page_no-1]
            for line in page.extract_text_lines():
                match = re.match(r'^(\d{1,2}\.\d+)\s+(.+)', line['text'])
                if match and match[1] in by_number:
                    section = next(s for s in sections if s['number'] == match[1])
                    # Reject doses such as "4.5 MU" and require the TOC's start page.
                    if page_no == section['printPage'] + 7 and normal(match[2])[:8].lower() == normal(section['name'])[:8].lower():
                        headings.append((page_no, line['top'], match[1]))
        assert len(headings) == 87, f'Unlocated headings: {87-len(headings)}'
        active_case = None
        active_section = None
        for page_no in range(21, 126):
            page = pdf.pages[page_no-1]
            filtered = page.filter(lambda obj: obj['object_type'] != 'rect' or obj['width'] < 2 or obj['height'] < 2)
            tables = filtered.find_tables({'vertical_strategy': 'lines', 'horizontal_strategy': 'lines', 'snap_tolerance': 5, 'join_tolerance': 5})
            for table in sorted(tables, key=lambda item: item.bbox[1]):
                prior = [h for h in headings if (h[0], h[1]) <= (page_no, table.bbox[1])]
                if not prior:
                    continue
                number = prior[-1][2]
                infection = by_number[number]
                if number != active_section:
                    active_case, active_section = None, number
                if number == '10.7' and page_no in (73, 74):
                    continue  # Operation tables have pathogen/antibiotic/dose semantics, curated separately.
                rows = table.extract()
                if not rows or len(rows[0]) != 4:
                    continue
                header = normal(' '.join(cell or '' for cell in rows[0]))
                is_header = bool(re.search(r'First Line|Empirical.*Antimicrobial|Preferred drug', header, re.I))
                # Other four-column grids include prophylaxis/etiology/reference tables.
                if not is_header and (table.bbox[1] > 100 or active_case is None):
                    continue
                for row in rows[1:] if is_header else rows:
                    label, primary, alternative, comment = [cell or '' for cell in row]
                    if not label.strip():
                        if active_case and (primary or comment):
                            if primary:
                                active_case['_raw'] = active_case.get('_raw', '') + '\n' + primary
                            if comment:
                                active_case['notes'].append('Source comments (continuation): ' + comment)
                            if page_no not in active_case['pdfPages']:
                                active_case['pdfPages'].append(page_no)
                                active_case['_hold'] = True
                        continue
                    if not primary.strip():
                        # A subtype heading spanning all columns is not a prescription.
                        if all(not cell for cell in row[1:]):
                            continue
                    notes = []
                    if alternative:
                        notes.append('Alternative column is not imported as competing primary guidance; consult source for alternatives.')
                    if comment:
                        notes.append('Source comments: ' + comment)
                    active_case = case(infection, label, [page_no], raw=primary, notes=notes,
                                       gaps=[] if primary else ['Primary treatment cell not supplied or not reliably extracted; source review required.'])
                    # Source cells running off the page must not become a final dose.
                    if table.bbox[3] > 755 and row is rows[-1]:
                        active_case['_hold'] = True
        for infection in infections:
            for entry in infection['cases']:
                finalize(entry)
                entry.pop('_hold', None)
                pages = entry['pdfPages']
                entry['locator'] = f"NCDC section {infection['ncdcSection']}; printed p. {', '.join(str(p-7) for p in pages)}; PDF p. {', '.join(map(str,pages))}"
    return infections


def curate(infections):
    by = {i['ncdcSection']: i for i in infections}
    # Source referrals are deliberate coverage records, never fabricated doses.
    referrals = {'4.3': ('National Guidelines on Diagnosis and Management of Viral Hepatitis', 40),
                 '6.1': ('NACO STI/RTI 2024, pp. 52–55', 47), '6.2': ('NACO STI/RTI 2024, pp. 91–92', 47),
                 '6.4': ('NACO STI/RTI 2024, pp. 41–43', 48), '6.6': ('NACO STI/RTI 2024, pp. 47–50', 49),
                 '6.9': ('NACO STI/RTI 2024, pp. 34–38', 51)}
    for sec, (target, page) in referrals.items():
        by[sec]['cases'] = []
        case(by[sec], 'External guideline referral in NCDC', [page], gaps=[f'NCDC refers to {target}; no standalone primary dose is supplied in this section. Referenced document is outside this catalogue.'])
    by['3.3']['cases'] = []
    case(by['3.3'], 'PUO', [36], instructions=['No antibiotics suggested unless the patient has features of sepsis'], gaps=['Sepsis changes the source context; no antibiotic dose is supplied for uncomplicated PUO.'])
    by['3.1']['cases'] = []
    case(by['3.1'], 'Day 1 or 2 of fever onset', [33], instructions=['Defer investigations or use of antimicrobials.'], gaps=['Later management is conditional on fever duration, localization, investigations, and the figure on PDF p. 34; no fixed empirical dose imported from the figure.'])
    case(by['3.1'], 'Fever beyond day 2 / source flowchart', [33,34], gaps=['Source review required: management algorithm is a figure; do not substitute an unconditional dose.'])
    by['18.5']['cases'] = []
    case(by['18.5'], 'Antibiotic associated diarrhoea — management', [117], instructions=['Oral vancomycin 125mg QID'], gaps=['Duration not supplied in this section.', 'Conditional addition of IV metronidazole 500 mg TDS is specified for toxic megacolon, ileus or hypotension; it is not part of the unconditional primary selection.'], notes=['NCDC encourages discontinuation of antibiotics and stool testing for C. difficile.'])
    cap = by['12.5']; cap['aliases'] = ['CAP', 'pneumonia']; cap['cases'] = []
    shared = ['Duration of therapy is 5–7 days; longer courses may be considered for bacteremic pneumonia, S. aureus, Legionella, abscess, empyema or complications. The source specifies conditional stability criteria for stopping by day 5.']
    case(cap, 'Without comorbidities: OPD management', [90], instructions=['Amoxicillin 1g q8h for 5-7 days'], duration='5-7 days', notes=shared)
    case(cap, 'With comorbidities – OPD management', [90], instructions=['Amoxicillin-clavulanate 1g BD + Doxycycline 100mg BD', 'Amoxicillin-clavulanate 1g BD + Azithromycin 500mg daily'], duration='5-7 days', notes=shared)
    for label in ['Inpatient ward', 'Inpatient ICU']:
        case(cap, label, [90], instructions=['Ceftriaxone 2g OD IV + Azithromycin 500mg daily', 'Ceftriaxone 2g OD IV + Doxycycline 100mg q12h'], duration='5-7 days', notes=shared + (['Add MRSA agent if necrotizing pneumonia preceding influenza infection; this conditional branch requires source review and is not added automatically.'] if label.endswith('ICU') else []), gaps=['Azithromycin / doxycycline route is not supplied in the source first-line cell; do not inherit the ceftriaxone IV route.'])
    case(cap, 'Inpatient ICU with risk factors for Pseudomonas aeruginosa', [90,91], instructions=['Piperacillin-tazobactam 4.5g IV q6h + Azithromycin 500mg daily', 'Piperacillin-tazobactam 4.5g IV q6h + Doxycycline 100mg q12h'], duration='7 days', notes=['Source risk factors: structural lung disease such as bronchiectasis, healthcare exposure or antibiotics in the last 90 days, immunocompromise.', 'Source continuation on printed p.84 completes the doxycycline option and states duration 7 days.', 'MRSA addition is conditional on necrotizing pneumonia preceding influenza infection.'], gaps=['Azithromycin / doxycycline route is not supplied in this source first-line cell.'])
    for i in infections:
        if not i['cases']:
            section = next(s for s in SECTIONS if s['number'] == i['ncdcSection'])
            case(i, 'Source section — extraction hold', [section['printPage']+7], gaps=['Source review required: no reliable primary treatment grid was extracted from this named section; no regimen inferred.'])


    # Join first-column page-break fragments; never expose a continuation tail as a new case.
    for sec, prefix in [('3.4', 'specific infection'), ('9.3', 'like bullae')]:
        cs = by[sec]['cases']
        for idx in range(len(cs)-1,0,-1):
            if cs[idx]['label'].startswith(prefix):
                continuation = cs.pop(idx); previous = cs[idx-1]
                previous['label'] += ' ' + continuation['label']
                previous['pdfPages'] = sorted(set(previous['pdfPages'] + continuation['pdfPages']))
                previous['regimens'] = []
                previous['notes'] += continuation['notes']
                previous['gaps'].append('Page-break condition/combination continuation held for source review; no isolated continuation dose selected.')
    for c in by['1.4']['cases']:
        c['regimens'] = []
        c['gaps'].append('Source primary cell places weight-dependent benzathine penicillin and penicillin V without an explicit connector; branch scope requires review.')
    for c in by['10.3']['cases']:
        c['regimens'] = []
        if c['label'].startswith('arise in traumatized'):
            c['label'] = 'Spontaneous gas gangrene — source row continues traumatic-gangrene text'
        c['gaps'].append('Traumatic/spontaneous source condition spans pages 68–69; exact branch attachment held for source review.')
    # Recover the operation table using its own explicit column headings.
    with pdfplumber.open(NCDC_PATH) as pdf:
        for page_no in (73,74):
            page = pdf.pages[page_no-1]
            clean = page.filter(lambda o:o['object_type'] != 'rect' or o['width'] < 2 or o['height'] < 2)
            for table in clean.find_tables({'snap_tolerance':5,'join_tolerance':5}):
                rows = table.extract()
                if len(rows[0]) != 4:
                    continue
                header = normal(' '.join(c or '' for c in rows[0]))
                if page_no == 73 and 'Specific operations' not in header:
                    continue
                for row in rows[1:] if page_no == 73 else rows:
                    if not row[0]:
                        continue
                    if not row[2] or not row[3]:
                        case(by['10.7'], normal(row[0]) + ' — adult surgical prophylaxis', [page_no],
                             notes=['Source antibiotic cell: ' + normal(row[2]), 'Source adult dosage cell: ' + (normal(row[3]) or 'blank')],
                             gaps=['Source adult dosage is missing or incomplete; conditional prophylaxis guidance requires source review. No dose is inferred.'])
                        continue
                    entry = case(by['10.7'], normal(row[0]) + ' — adult surgical prophylaxis', [page_no], raw=normal(row[2]) + ' — ' + normal(row[3]), notes=['Source table headers: Specific operations; Expected organism; Antibiotic of choice; Dosage in adults.', 'This is prophylaxis, not infection treatment. Source timing and duration context on PDF72 must be reviewed.'])
                    finalize(entry)
    by['1.1']['name'] = 'Infective Endocarditis'
    by['1.1']['aliases'].append('Infective Endocarditis (Empirical therapy pending blood culture results)')
    for c in by['12.6']['cases']:
        # Both primary/secondary source comment cells explicitly state this duration (PDF91).
        for regimen in c['regimens']:
            regimen['duration'] = '4-6 weeks'
            regimen['gaps'] = [gap for gap in regimen['gaps'] if not gap.startswith('Duration not supplied')]
    for c in by['11.1']['cases']:
        if c['label'] in ('Epithelial','Stromal','Endothelial'):
            c['label'] = 'Viral Keratitis — ' + c['label']
            if c['label'].endswith('Stromal'):
                c['gaps'].append('Source mixes pediatric age/weight and adult acyclovir doses; select only after source review.')
                c['regimens'] = []
    for c in by['17.4']['cases']:
        if min(c['pdfPages']) >= 108:
            c['label'] = 'BMT / HSCT setting — ' + c['label']
            c['gaps'].append('BMT/HSCT-specific source context; population/timing matching requires review.')
            c['regimens'] = []
    for label,pages in [('BMT pre-engraftment and post-engraftment — antifungal prophylaxis',[108]), ('BMT pre-engraftment and post-engraftment — antiviral prophylaxis',[108]), ('BMT pre-engraftment and post-engraftment — CMV surveillance / pre-emptive treatment',[108,109]), ('BMT / HSCT — Pneumocystis prophylaxis',[109])]:
        case(by['17.4'], label, pages, gaps=['Three-column BMT prophylaxis grid has transplant-specific timing/conditional branches. Source review required; no population or treatment dose inferred.'])
    by['12.7']['cases'] = []
    case(by['12.7'], 'Para-pneumonic effusion or empyema', [92,93], instructions=['Ceftriaxone 2g OD IV', 'Inj Amoxicillin-clavulanate 1.2g IV TDS'], duration='4 weeks', gaps=['MRSA coverage is conditional and is not automatically added.'], notes=['Pleural fluid microbiology, source control and pleural drainage/VATS decisions are specified in source comments. Page93 contains continuation of procedural comments, not the primary dose.'])


def mapping(data):
    contexts = [c for i in data['infections'] for c in i['cases']]
    source = data['sources'][0]
    lines = ['# NCDC infection source mapping', '',
             'NCDC is the sole source for the active infection library. Unreviewed, non-executable reference content; not approved hospital policy.', '',
             f"Coverage: {len(data['groups'])} clinical groups; {len(data['infections'])}/87 named NCDC subsections; {len(contexts)} contexts; {sum(len(c['regimens']) for c in contexts)} selectable source options; {sum(not c['regimens'] for c in contexts)} contexts held for source review.", '',
             f"Frozen source: {source['name']} — {source['version']}. SHA256 `{source['sha256']}`. [Publisher PDF]({source['url']}). Printed page = PDF page minus 7.", '',
             'Heading coverage is not completed treatment curation. Endocarditis combination branches remain held, and the chronic osteomyelitis cross-reference remains unresolved. Removing supplemental guidance does not correct those NCDC extraction problems. Missing fields are not inferred. CRRT and monographs remain deferred.', '',
             '## NCDC inventory', '', '| Section | Infection | PDF pages | Contexts / options / holds |', '| --- | --- | --- | --- |']
    for infection in data['infections']:
        cs = infection['cases']
        pages = sorted({p for c in cs for p in c['pdfPages']})
        lines.append(f"| {infection['ncdcSection']} | {infection['name']} | {', '.join(map(str,pages))} | {len(cs)} / {sum(len(c['regimens']) for c in cs)} / {sum(not c['regimens'] for c in cs)} |")
    lines += ['', '## Held contexts', '']
    for infection in data['infections']:
        for c in infection['cases']:
            if not c['regimens']:
                lines.append(f"- {infection['name']} — {c['label']} ({c['locator']}): {' '.join(c['gaps'])}")
    lines += ['', 'Rebuild with `python tools/build_infection_guidance.py`; compare deterministic output with `--check`. Only the NCDC PDF and its extracted page-text file are read. Original source evidence is read-only.']
    return '\n'.join(lines)+'\n'


def build(evidence):
    ncdc = evidence / 'drug-specific-guidance/ncdc-2025.pdf'
    pages = json.loads((evidence / 'drug-specific-guidance/ncdc-2025-pages.json').read_text())
    global SECTIONS, NCDC_PATH
    NCDC_PATH = ncdc
    groups, SECTIONS = toc(pages)
    infections = extract_ncdc(ncdc, SECTIONS)
    curate(infections)
    sources = [{'id':'ncdc','name':'NCDC / ICMR National Treatment Guidelines for Antimicrobial Use in Infectious Disease Syndromes','version':'Version 2.0 — November 2025','url':'https://ncdc.mohfw.gov.in/uploads/pdf/amr17.pdf','sha256':hashlib.sha256(ncdc.read_bytes()).hexdigest()}]
    return {'version':'2026-10-25.2-ncdc-only', **FLAGS, 'sources':sources, 'groups':groups, 'infections':infections}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = build(args.evidence_root)
    products = {OUTPUT: json.dumps(data, ensure_ascii=False, indent=2)+'\n', MAPPING:mapping(data)}
    for path, content in products.items():
        if args.check:
            assert path.read_text() == content, f'Generated output differs: {path}'
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    contexts = [c for i in data['infections'] for c in i['cases']]
    print(f"{len(data['groups'])} groups, {len(data['infections'])} infections, {len(contexts)} contexts, {sum(len(c['regimens']) for c in contexts)} options, {sum(not c['regimens'] for c in contexts)} held contexts")

if __name__ == '__main__':
    main()
