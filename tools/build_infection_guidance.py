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
    offset = 7 if source == 'ncdc' else 8
    entry = {'id': ident, 'label': normal(label), 'sourceId': source,
             'locator': f"{'NCDC section ' + infection.get('ncdcSection', '') if source == 'ncdc' else 'JIPMER'}; printed p. {', '.join(str(p-offset) for p in pages)}; PDF p. {', '.join(map(str, pages))}",
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


def jipmer_additions(infections):
    for name in ['Perinephric abscess', 'Renal abscess']:
        inf = {'id': 'jipmer-' + slug(name), 'groupId': 'group-5', 'name': name, 'aliases': [], 'cases': []}
        case(inf, 'Secondary to pyelonephritis', [49], source='jipmer', instructions=['As for pyelonephritis (uncomplicated or complicated)'], duration='At least 2 to 3 weeks; depends on extent of disease, clinical response and fall in inflammatory markers', gaps=['This is a JIPMER source cross-reference, not a standalone dose. No NCDC regimen is substituted into it. Source-owned dose resolution remains held for review.'], notes=['Source entries UTI-06 (perinephric) / UTI-07 (renal). Diagnostic aspiration and drainage thresholds differ by abscess type; inspect the original source.'])
        case(inf, 'Secondary to bacteraemia', [49], source='jipmer', instructions=['As per the primary focus'], gaps=['Primary focus and dose are not supplied in this row; no fixed regimen inferred.'])
        infections.append(inf)
    inf = {'id': 'jipmer-aspiration-pneumonia', 'groupId': 'group-12', 'name': 'Aspiration Pneumonia', 'aliases': [], 'cases': []}
    case(inf, 'Community acquired — RES-06', [44], source='jipmer', instructions=['Amoxicillin-Clavulanate 1.2g IV Q8H followed by 625mg PO TDS for a minimum of 7 days'], duration='Minimum of 7 days', gaps=['Severe-disease branch has separate piperacillin/tazobactam guidance and requires source review.'], notes=['JIPMER distinguishes aspiration pneumonia from early chemical pneumonitis; the source gives antibiotic indications for severe illness, lack of improvement at 48 hours or secondary worsening.'])
    case(inf, 'Hospital acquired — RES-06', [44], source='jipmer', instructions=['Piperacillin tazobactam 4.5g IV Q6H', 'Meropenem 1g IV Q8H'], gaps=['Conditional vancomycin addition if MRSA is considered is held; no fixed combination is inferred.', 'Duration not supplied in this row.'])
    infections.append(inf)
    for name, firstlabel in [('Subdural Empyema', 'Following sinusitis'), ('Epidural Abscess', 'Following sinusitis or otitis')]:
        inf = {'id': 'jipmer-' + slug(name), 'groupId': 'group-2', 'name': name, 'aliases': [], 'cases': []}
        case(inf, firstlabel, [69], source='jipmer', gaps=['Source review required: metronidazole Q8H/6H and optional vancomycin are unresolved conditional choices. No fixed regimen selected.'], notes=['JIPMER provides ceftriaxone 2g IV Q12H with metronidazole 500mg IV Q8H/6H, with optional vancomycin. Urgent drainage guidance applies.'])
        case(inf, 'Following neurosurgery' + (' or head injury' if name.startswith('Subdural') else ''), [69], source='jipmer', instructions=['Inj. Meropenem 2g IV Q8H AND Vancomycin 15 to 20mg/kg IV Q8H (single dose not exceeding 2 g)'], duration='Minimum of 3 to 4 weeks after drainage' if name.startswith('Subdural') else '3 to 6 weeks after drainage', gaps=['Associated osteomyelitis may require longer therapy.'])
        infections.append(inf)

    by = {i.get('ncdcSection'): i for i in infections if i.get('ncdcSection')}
    for label in ['Cellulitis (suspected Vibrio vulnificus infection) — sea water laceration — SSI-08', 'Cellulitis (suspected Aeromonas infection) — fresh water laceration — SSI-09']:
        case(by['9.3'], label, [59], source='jipmer', gaps=['Distinct pathogen/exposure context absent from the NCDC cellulitis primary rows. JIPMER severity-dependent alternatives and optional combination require source review; no fixed regimen selected.'])
    for label in ['Type I — polymicrobial — SSI-13', 'Type II — Group A Streptococcus — SSI-14', 'Type III — Aeromonas hydrophila / fresh water — SSI-15', 'Type III — Vibrio vulnificus / sea water — SSI-15']:
        case(by['9.4'], 'Organism-specific necrotizing fasciitis: ' + label, [64], source='jipmer', gaps=['JIPMER organism-specific context extends the generic NCDC syndrome row. Combination scope, route choices or Q8H/Q6H intervals are unresolved; source review required.'])
    additions = [
        ('Cholera', '4', 52, 'Pathogen-specific watery / rice-water diarrhoea', 'Duration scope of doxycycline/azithromycin versus ciprofloxacin is unresolved; source review required.'),
        ('Shigella gastroenteritis', '4', 52, 'Moderate or severe disease only', 'Source-specific pathogen treatment choices and susceptibility conditions require review; no unconditional antibiotic selected.'),
        ('Non-typhoid Salmonella gastroenteritis', '4', 52, 'Severe/invasive disease or risk for invasion', 'Treatment indications, AST-dependent alternatives, bacteraemia and duration branches require review.'),
        ('Campylobacter gastroenteritis', '4', 53, 'Severe illness or source-listed risk factors', 'JIPMER supplies azithromycin 500mg PO OD x 1–3 days, but treatment is restricted to listed severity/risk conditions; source review required before selecting the branch.'),
        ('Enterotoxigenic / enteropathogenic / entero-invasive E. coli diarrhoea', '4', 53, 'Pathogen-specific or traveller’s diarrhoea', 'Pathogen-specific choice and applicability require source review; EHEC must not inherit this guidance.'),
        ('Enterohemorrhagic E. coli diarrhoea', '4', 53, 'Shiga toxin producing E. coli, including O157:H7', 'Source advises no antibiotics because of HUS risk; no dose supplied.'),
        ('Vibrio parahaemolyticus gastroenteritis', '4', 53, 'Severe illness; shellfish-associated', 'Three source antibiotic alternatives require review; no unconditional treatment selected.'),
        ('Yersinia gastroenteritis', '4', 53, 'Immunocompromised host / bacteraemia / pseudo-appendicitis', 'Source alternative branches differ for bacteraemia and AST; source review required.'),
        ('Intra-abdominal abscess', '4', 56, 'GIT-10 — source matching hold', 'Source-match review required against NCDC appendicular/splenic abscess and secondary/tertiary peritonitis before determining a genuinely uncovered context. No JIPMER regimen displaces NCDC.'),
        ('Snake Bite Cellulitis', '14', 62, 'SSI-12 — snake bite cellulitis', 'NCDC bite headings cover mammals and insects, not this named snake-bite context. JIPMER route and interval alternatives require source review; no fixed regimen selected.'),
        ('Arthritis-Acute polyarticular arthritis', '10', 66, 'BJI-02 — aetiology-dependent', 'Source guidance depends on suspected aetiology; no broad empirical regimen inferred. Source mentions gonococcus and melioidosis separately.'),
        ('Chronic Monoarthritis', '10', 66, 'BJI-03 — tuberculosis / Brucella', 'Pathogen-specific treatment is not supplied in this row; source review required.'),
        ('Vertebral Osteomyelitis +/- epidural abscess', '10', 66, 'BJI-06 — anatomical context', 'Distinct vertebral context; source review required to confirm applicability and duration. Do not confuse spinal epidural extension with the cranial epidural abscess entry.'),
    ]
    for name, group, page, label, gap in additions:
        inf = {'id':'jipmer-'+slug(name), 'groupId':'group-'+group, 'name':name, 'aliases':[], 'cases':[]}
        if name == 'Enterohemorrhagic E. coli diarrhoea':
            case(inf, label, [page], source='jipmer', instructions=['Treatment not recommended. Antibiotic use associated with higher risk of HUS.'], gaps=[gap])
        else:
            case(inf, label, [page], source='jipmer', gaps=[gap])
        infections.append(inf)
    definitive = [
        ('Streptococci-Penicillin Susceptible; S. gallolyticus (MIC ≤0.12 μg/mL) — CVS-07',72),
        ('Streptococci-Relatively Penicillin Resistant (MIC >0.12 and <0.5 μg/mL) — CVS-08',72),
        ('Streptococci-Moderately Penicillin Resistant (MIC ≥0.5 and <8 μg/mL); Granulicatella, Abiotrophia or Gemella — CVS-09',72),
        ('Enterococci — CVS-10',73),
        ('MSSA infecting native valves (no foreign devices) — CVS-11',73),
        ('MRSA infecting native valves (no foreign devices) — CVS-11',73),
        ('MSSA infecting prosthetic valves — CVS-12',73),
        ('MRSA infecting prosthetic valves — CVS-12',73),
        ('HACEK organisms — CVS-13',73),
    ]
    for label,page in definitive:
        case(by['1.1'], 'Definitive therapy: '+label, [page], source='jipmer', gaps=['Distinct organism/AST-directed definitive context; NCDC 1.1 is explicitly empirical pending blood cultures. Source choices, MIC thresholds, valve type, dose anomalies and combination durations require source review; no fixed regimen selected.'])


JIPMER_ROW_NAMES = {
 'SYS':['Sepsis (community acquired)','Septic shock (community acquired)','Septic shock (hospital acquired)','CRBSI','AUFI without sepsis/organ dysfunction','AUFI with sepsis/organ dysfunction','Suspected enteric fever','Suspected scrub typhus','Suspected leptospirosis — mild / moderate to severe'],
 'RES':['CAP — OPD','CAP — inpatient non-ICU','CAP — ICU','VAP','HAP without VAP','Aspiration pneumonia — community / hospital','Lung abscess — primary / secondary','Acute pharyngitis','Acute sinusitis','Acute otitis media','Acute bronchitis','AECOPD'],
 'UTI':['Uncomplicated cystitis','Complicated cystitis','Pyelonephritis','Complicated pyelonephritis','Urosepsis','Perinephric abscess','Renal abscess','CAUTI'],
 'GIT':['Non-bloody diarrhoea','Bloody diarrhoea with fever','Bloody diarrhoea without fever — E. histolytica / EHEC','SBP (primary)','Secondary bacterial peritonitis','Liver abscess — amoebic','Liver abscess — pyogenic','Acute cholecystitis','Cholangitis','Intra-abdominal abscess'],
 'SSI':['Mild non-purulent cellulitis','Moderate/severe non-purulent cellulitis','Mild purulent cellulitis','Moderate/severe purulent cellulitis','Carbuncle, furuncle and abscess','Impetigo — non-bullous','Impetigo — bullous','Vibrio vulnificus cellulitis — sea water','Aeromonas cellulitis — fresh water','Infected post-traumatic wound — mild/moderate / severe','Diabetic foot — noninfected / mild / moderate / severe','Snake bite cellulitis / animal and human bites','Necrotizing fasciitis type I','Necrotizing fasciitis type II','Necrotizing fasciitis type III — Aeromonas / Vibrio'],
 'BJI':['Septic arthritis — acute monoarthritis; infants / children-adults / melioidosis','Acute polyarticular arthritis','Chronic monoarthritis','Prosthetic joint infection','Extremity osteomyelitis','Vertebral osteomyelitis +/- epidural abscess'],
 'CNS':['Acute bacterial meningitis','Brain abscess','Subdural empyema','Epidural abscess'],
 'CVS':['Native valve endocarditis — community acute','Native valve endocarditis — community subacute','Native valve endocarditis — healthcare associated','Prosthetic valve endocarditis — early <1 year','Prosthetic valve endocarditis — late >1 year','Culture-negative endocarditis','Definitive streptococcal penicillin-susceptible / S. gallolyticus','Definitive streptococcal relatively penicillin-resistant','Definitive streptococcal moderately penicillin-resistant / Granulicatella / Abiotrophia / Gemella','Definitive enterococci','Definitive MSSA / MRSA native valve','Definitive MSSA / MRSA prosthetic valve','Definitive HACEK'],
}


def row_decision(prefix, number):
    if prefix == 'SYS':
        return 'NCDC 18.4 precedence' if number == 4 else 'NCDC 3.1–3.4 precedence; organism/severity-specific matching held where only a figure/broad row is available'
    if prefix == 'RES':
        return {6:'Added JIPMER aspiration contexts; severe/MRSA branches held',7:'NCDC 12.6 precedence',8:'NCDC 7.2 pharyngitis rows precede',9:'NCDC 7.3 precedes',10:'NCDC 7.4 precedes',11:'NCDC 12.1 precedes',12:'NCDC 12.3 precedes'}.get(number,'NCDC 12.5 precedes' if number <= 3 else 'NCDC 18.3 precedes')
    if prefix == 'UTI':
        return 'Added precise JIPMER named source cross-reference contexts' if number in (6,7) else ('NCDC 18.6 precedes' if number == 8 else 'NCDC 5.1/5.2 and 3.4 retained; finer complicated/urosepsis matching held')
    if prefix == 'GIT':
        return 'Searchable source-match hold against NCDC abscess/peritonitis contexts' if number == 10 else ('NCDC 4.2 precedes empirical syndrome; distinct pathogen-specific extensions separately listed' if number <= 3 else 'NCDC 4.4/4.7 precede')
    if prefix == 'SSI':
        return {5:'NCDC 9.6 furuncle/carbuncle rows precede; abscess cross-reference unresolved',8:'Added held JIPMER pathogen/exposure context in NCDC cellulitis entry',9:'Added held JIPMER pathogen/exposure context in NCDC cellulitis entry',10:'NCDC 10.5 precedes; finer severity source matching held',11:'NCDC 9.7 precedes',12:'Snake-bite context added as hold; mammal/human bites NCDC 14.1 precedes',13:'Generic syndrome NCDC 9.4 precedes; distinct type I context added held',14:'Generic syndrome NCDC 9.4 precedes; distinct type II context added held',15:'Generic syndrome NCDC 9.4 precedes; distinct organism/exposure contexts added held'}.get(number,'NCDC 9.2/9.3 precede; finer purulence/severity matching held')
    if prefix == 'BJI':
        return {1:'NCDC 10.4 precedes; infant/Gram-stain/melioidosis finer match held',2:'Added JIPMER named aetiology-dependent hold',3:'Added JIPMER named no-dose hold',4:'NCDC 10.6 implant infection context retained; definitive species matching held',5:'NCDC 10.1/10.2 precede',6:'Added JIPMER vertebral anatomical context hold'}[number]
    if prefix == 'CNS':
        return 'NCDC 2.1–2.5 precedence' if number <= 2 else 'Added JIPMER named sinus/otitis and postoperative contexts; ambiguous interval/optional branch held'
    if prefix == 'CVS':
        return 'NCDC 1.1 empirical precedence; finer acquisition/valve timing match held' if number <= 6 else 'Added held JIPMER definitive organism/AST context within endocarditis entry; no empirical displacement'


def mapping(data):
    cases = [c for i in data['infections'] for c in i['cases']]
    holds = [c for c in cases if not c['regimens']]
    lines = ['# Infection source mapping', '', 'Static educational reference. All entries are unreviewed, non-executable, and ineligible for clinical use; this is not local policy.', '',
             f"Coverage: 19 NCDC groups; 87/87 named NCDC TOC subsections; {len(data['infections'])} total infection entries; {len(cases)} clinical-context records; {sum(len(c['regimens']) for c in cases)} selectable source-treatment options; {len(holds)} contexts have no selectable regimen and an explicit review hold.", '',
             'Heading coverage is not a claim that every treatment branch is fully transcribed. Conditional/ambiguous cells and missing field values remain visible as gaps. The neonatal section is present, but complex age/PMA/PNA dosing is held. Supplemental standard-dose tables are not attached to infections by inference. Source drug monographs, renal adjustments and dialysis references are deferred.', '', '## Frozen sources', '']
    for s in data['sources']:
        lines += [f"- {s['name']} — {s['version']}; SHA-256 `{s['sha256']}`; [publisher PDF]({s['url']})."]
    lines += ['', 'NCDC printed page = PDF page minus 7; JIPMER system therapy pages used here = PDF page minus 8. Locators refer to the frozen snapshots, not an assumed current web version.', '',
              '## Precedence and JIPMER crosswalk', '',
              '| JIPMER scope (printed pages / PDF pages) | Mapping decision |', '| --- | --- |',
              '| Sepsis 21–22 / 29–30; AUFI 26–29 / 34–37 | NCDC 3.1–3.4 owns overlapping empirical syndromes. JIPMER does not replace NCDC conditional/figure holds. |',
              '| Bacteraemia principles 23 / 31 | Not a standalone fixed-dose infection entry. Pathogen-specific/definitive bacteremia context requires detailed source matching before any future addition. |',
              '| CRBSI 24–25 / 32–33 | Maps to NCDC 18.4; NCDC precedence. Catheter/organism duration branches not merged. |',
              '| CAP, HAP/VAP 30–35 / 38–43 | NCDC 12.5 and 18.3 own overlapping severity/acquisition contexts. No JIPMER CAP regimens exposed as peers. |',
              '| Aspiration pneumonia RES-06, 36 / 44 | Added with community/hospital contexts: distinct named syndrome not supplied as NCDC pneumonia context. NCDC lung-abscess aspiration discussion is not aspiration-pneumonia treatment. Severe/MRSA branches held. |',
              '| Lung abscess RES-07, 36 / 44 | NCDC 12.6 primary/secondary contexts take precedence. |',
              '| Pharyngitis, sinusitis, otitis, bronchitis, AECOPD 37 / 45 | NCDC 7.2 (includes pharyngitis Centor rows), 7.3, 7.4, 12.1, 12.3 take precedence. |',
              '| Cystitis UTI-01/02, pyelonephritis UTI-03/04, urosepsis UTI-05, CAUTI UTI-08, 40–41 / 48–49 | NCDC 5.1/5.2, 3.4 and 18.6 retained. JIPMER complicated-UTI and urosepsis fine-grained overlap needs further matching; these are not asserted to be uncovered simply because NCDC headings are broader. |',
              '| Perinephric abscess UTI-06; renal abscess UTI-07, 41 / 49 | Added as precise separate names, each with pyelonephritis/bacteraemia source branches. JIPMER supplies cross-references, not standalone doses; no cross-source dose substitution. |',
              '| Diarrhoea GIT-01–03 and pathogen-specific treatment, 42–45 / 50–53 | Empirical syndrome overlap with NCDC 4.2. Distinct pathogen-specific entries are searchable, mostly held pending branch review; amoebic dysentery remains NCDC-owned because NCDC 4.2 explicitly supplies a metronidazole adjunct. |',
              '| SBP/secondary peritonitis, liver abscess, cholecystitis, cholangitis GIT-04–09, 46–48 / 54–56 | NCDC 4.4 and 4.7 context rows take precedence. |',
              '| Intra-abdominal abscess GIT-10, 48 / 56 | Searchable source-match hold pending comparison with NCDC 4.5–4.8 and 18.7 acquisition/source-control contexts. |',
              '| Cellulitis SSI-01–04; impetigo SSI-06/07; diabetic foot SSI-11; animal bites, 50–54 / 58–62 | NCDC 9.2, 9.3, 9.7 and 14.1 take precedence. Purulent/severity subgroups remain source-owned. |',
              '| Carbuncle/furuncle/abscess SSI-05; Vibrio/Aeromonas injuries SSI-08–10; snake bite SSI-12, 51–54 / 59–62 | NCDC 9.6 supplies furuncle/carbuncle rows. Distinct Vibrio/Aeromonas and snake-bite contexts are searchable held additions; post-trauma overlap remains NCDC 10.5-owned. |',
              '| Necrotizing fasciitis SSI-13–15, 55–56 / 63–64 | NCDC 9.4 owns syndrome. Distinct organism-specific type/exposure branches are searchable JIPMER held contexts. |',
              '| Septic arthritis BJI-01–06, 57–58 / 65–66 | NCDC 10.4 owns empirical syndrome. Infant/organism/Gram-stain subgroups are not merged across sources; finer review deferred. |',
              '| Meningitis CNS-01; brain abscess CNS-02, 59–60 / 67–68 | NCDC 2.1–2.5 precede overlapping contexts. |',
              '| Subdural empyema CNS-03; epidural abscess CNS-04, 61 / 69 | Added as named intracranial infections not named NCDC treatment entries, with sinus/otitis and postoperative contexts separated. Ambiguous interval/optional agent branch held. |',
              '| Endocarditis initial/definitive CVS-01–13, 62–65 / 70–73 | NCDC 1.1 empirical context takes precedence. Distinct organism/AST-specific definitive contexts are searchable JIPMER held cases in the same infection entry. |',
              '| Duration appendix, dosing, surgical and endocarditis prophylaxis, 66–93 / 74–101 | Not used to backfill missing infection fields. NCDC 10.7 surgical-prophylaxis heading remains present; additional JIPMER prophylaxis contexts deferred. |', '',
              '## JIPMER disease-row audit', '', '| Source row | Named context(s) | PDF page(s) | Decision |', '| --- | --- | --- | --- |', *[f"| {code} | {name} | {', '.join(map(str, JIPMER_CODE_PAGES[code]))} | {row_decision(code.split('-')[0], int(code.split('-')[1]))} |" for prefix,names in JIPMER_ROW_NAMES.items() for index,name in enumerate(names) for code in [f'{prefix}-{index+1:02}']], '', 'Repeated source IDs preserve the named variants in this row audit (for example UTI-06 secondary to pyelonephritis/bacteraemia and SSI-12 snake/mammal bites); a repeated ID is not treated as a unique infection identifier.', '', 'Unnumbered JIPMER pathogen-specific diarrhoea tables PDF52–53: cholera, Shigella, NTS, Campylobacter, E. coli pathotypes, EHEC, Vibrio parahaemolyticus and Yersinia have searchable records; amoebic dysentery overlaps the explicit metronidazole adjunct in NCDC4.2 and remains NCDC-owned pending exact luminal-agent context review. Enteric fever remains NCDC3.2-owned.', '', '## Extraction and curation', '',
              'TOC names and section numbers are authoritative for navigation. Actual heading coordinates assign each four-column grid to a section; a section-number-like dose is rejected unless its page and name prefix match the TOC. Thin rectangle borders recover the table structure without duplicate backing rectangles. Separate continuation pages are retained in locators and held when source-cell continuity needs review.', '',
              'Safe NCDC first-line cells are retained as source instructions. Unresolved OR/slash/conditional/cross-reference cells have zero selectable regimens and retain source text in notes. Alternative treatment columns are not promoted to primary peer regimens. CAP primary branch scope and page-91 continuation were explicitly curated into selectable full combinations. Routes absent for CAP oral agents remain absent. Source dose anomalies are not silently corrected.', '',
              'TDD: five content/coverage tests failed against the missing catalogue before implementation. Critical numerical/source checks: CAP PDF90–91 (amoxicillin 1g q8h, ceftriaxone 2g OD IV, doxycycline 100mg q12h; 5–7 days or 7 days in pseudomonal-risk context); urinary NCDC PDF46; JIPMER UTI-06/07 PDF49 (source cross-references, at least 2–3 weeks); JIPMER aspiration PDF44; intracranial abscess PDF69. These checks do not constitute clinical validation.', '',
              '## NCDC heading inventory and extraction holds', '', '| Section | Infection | PDF page(s) | Contexts / options / held contexts |', '| --- | --- | --- | --- |']
    for inf in data['infections']:
        if 'ncdcSection' not in inf:
            continue
        cs = inf['cases']; pages = sorted({p for c in cs for p in c['pdfPages']})
        lines.append(f"| {inf['ncdcSection']} | {inf['name']} | {', '.join(map(str,pages))} | {len(cs)} / {sum(len(c['regimens']) for c in cs)} / {sum(not c['regimens'] for c in cs)} |")
    lines += ['', 'Every context below has zero selectable treatment options. Read its source locator and gap before extending the catalogue.', '']
    for inf in data['infections']:
        for c in inf['cases']:
            if not c['regimens']:
                lines.append(f"- {inf['name']} — {c['label']} ({c['locator']}): {' '.join(c['gaps'])}")
    lines += ['', 'Rebuild: `python tools/build_infection_guidance.py --evidence-root /path/to/read-only/evidence`; verify determinism with `--check`. The builder only writes its owned JSON and this mapping file. All source material is opened read-only.']
    return '\n'.join(lines) + '\n'


def build(evidence):
    ncdc = evidence / 'drug-specific-guidance/ncdc-2025.pdf'
    jipmer = evidence / 'icu-priority-renal-crrt/jipmer-antibiotic-policy-2026.pdf'
    pages = json.loads((evidence / 'drug-specific-guidance/ncdc-2025-pages.json').read_text())
    global SECTIONS, NCDC_PATH, JIPMER_CODE_PAGES
    NCDC_PATH = ncdc
    JIPMER_CODE_PAGES = {}
    for page in json.loads((evidence / 'icu-priority-renal-crrt/jipmer-antibiotic-policy-2026-pages.json').read_text())[29:73]:
        for found in re.findall(r'\b(?:SYS|RES|UTI|GIT|SSI|BJI|CNS|CVS)-\s*\d+', page['text']):
            code = re.sub(r'\s+', '', found)
            JIPMER_CODE_PAGES.setdefault(code, [])
            if page['page'] not in JIPMER_CODE_PAGES[code]:
                JIPMER_CODE_PAGES[code].append(page['page'])
    expected_codes = {f'{prefix}-{index+1:02}' for prefix,names in JIPMER_ROW_NAMES.items() for index in range(len(names))}
    assert set(JIPMER_CODE_PAGES) == expected_codes, 'JIPMER disease-row crosswalk must account for every source code'
    groups, SECTIONS = toc(pages)
    infections = extract_ncdc(ncdc, SECTIONS)
    curate(infections)
    jipmer_additions(infections)
    sources = [{'id':'ncdc','name':'NCDC / ICMR National Treatment Guidelines for Antimicrobial Use in Infectious Disease Syndromes','version':'Version 2.0 — November 2025','url':'https://ncdc.mohfw.gov.in/uploads/pdf/amr17.pdf','sha256':hashlib.sha256(ncdc.read_bytes()).hexdigest()},
               {'id':'jipmer','name':'JIPMER Antibiotic Policy','version':'2026 edition — Version 1.0 (202604061000), 15 April 2026','url':'https://www.jipmer.edu.in/sites/default/files/JIPMER%20Antibiotic%20Policy%202026.pdf','sha256':hashlib.sha256(jipmer.read_bytes()).hexdigest()}]
    return {'version':'2026-10-25.1', **FLAGS, 'sources':sources, 'groups':groups, 'infections':infections}


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
    cases = [c for i in data['infections'] for c in i['cases']]
    print(f"{len(data['groups'])} groups, {len(data['infections'])} infections, {len(cases)} contexts, {sum(len(c['regimens']) for c in cases)} options, {sum(not c['regimens'] for c in cases)} held contexts")

if __name__ == '__main__':
    main()
