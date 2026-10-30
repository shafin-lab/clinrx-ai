#!/usr/bin/env python3
"""Project all 87 NCDC clinical sections without turning source cells into prescriptions.

Read-only input: retained NCDC PDF with the expected full SHA-256. Output is
limited to the complete projection, exact section images and coverage report.
The original PDF is authoritative. Operators, conditions, source referrals and
apparent source dose/unit anomalies are retained, never resolved by this script.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / 'frontend/public/assets/infection-sources/ncdc-2025.pdf'
OUT = ROOT / 'frontend/src/infectionLibrary/data/ncdc-complete-guidance.json'
IMAGES = ROOT / 'frontend/public/assets/infection-sources/ncdc-sections'
REPORT = ROOT / 'docs/antibiotics/NCDC-COMPLETE-COVERAGE.md'
SHA256 = '0debe52c37cf08dc5d112b8ef71d4ef322c323f04f712473a57a78f1bb68f90a'
SETTINGS = {'vertical_strategy':'lines','horizontal_strategy':'lines','snap_tolerance':5,'join_tolerance':5}
SCALE = 1.8


def norm(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def content_bottom(page):
    footers = [line['top'] for line in page.extract_text_lines(return_chars=False)
               if line['top'] > page.height - 70 and abs((line['x0']+line['x1'])/2-page.width/2) < 30 and re.fullmatch(r'\d{1,3}', line['text'].strip())]
    return min(footers)-3 if footers else page.height-50


def section_index(pdf):
    sections = []
    for page in pdf.pages[7:11]:
        for line in (page.extract_text() or '').splitlines():
            match = re.match(r'^(\d+\.\d+) (.*?)\s*\.{2}.*?\s(\d+)\s*$', line)
            if match:
                sections.append({'section':match[1], 'name':match[2], 'startPage':int(match[3])+7})
    assert len(sections) == 87
    for section in sections:
        page = pdf.pages[section['startPage']-1]
        candidates = [line for line in page.extract_text_lines(return_chars=False)
                      if line['text'].startswith(section['section']+' ') and
                      norm(line['text'].split(' ',1)[1]).lower()[:8] == norm(section['name']).lower()[:8]]
        assert len(candidates) == 1, section
        section['top'] = max(0,candidates[0]['top']-2)
        section['endBoundary'] = section['top']
        # A new chapter heading must not leak into the preceding subsection.
        if section['section'].endswith('.1'):
            group = section['section'].split('.')[0]
            group_lines = [line for line in page.extract_text_lines(return_chars=False)
                           if re.match(r'^'+group+r'\.\s', line['text']) and line['top'] < section['top']]
            if group_lines:
                section['endBoundary'] = min(line['top'] for line in group_lines)-3
    return sections


def segments(pdf, section, following):
    end_page = following['startPage'] if following else 127
    result = []
    for number in range(section['startPage'],end_page+1):
        if number == 127:
            break
        page = pdf.pages[number-1]
        top = section['top'] if number == section['startPage'] else 50
        bottom = following['endBoundary'] if following and number == end_page else content_bottom(page)
        bottom = min(bottom,content_bottom(page))
        if bottom-top < 3:
            continue
        crop = page.crop((0,top,page.width,bottom))
        # An ending page before its next heading may contain no previous-section content.
        if not any(c['text'].strip() for c in crop.chars) and not crop.images:
            continue
        result.append((number,crop,(0,top,page.width,bottom)))
    return result


def table_columns(table):
    # Grid rows can be taller than their own logical interval because a source
    # comment cell spans several rows. Column centers come from complete body cells.
    for row in table.rows:
        cells = row.cells
        if len(cells) == 4 and all(cells) and all(c[2]-c[0] < (table.bbox[2]-table.bbox[0])*.65 for c in cells):
            return [(c[0]+c[2])/2 for c in cells]
    return None


def unsupported_glyphs(text):
    # A private-use code point has no standard Unicode meaning. Preserve it in
    # source text, but always expose the printed table rather than guessing.
    return any(char == '\ufffd' or unicodedata.category(char) == 'Co' for char in text)


def fullwidth_row(table, row):
    cells = [cell for cell in row.cells if cell]
    return (len(cells) == 1 and abs(cells[0][0]-table.bbox[0]) < 1 and
            abs(cells[0][2]-table.bbox[2]) < 1)


def mrsa_severity_rows(crop, gridrow, fields):
    """Split the visually verified PDF60 cell by its printed severity alignment.

    The frozen source places the second pair of medicines lower in the same
    bordered cell. Source-word coordinates determine the split; no drug text,
    route, frequency or duration is authored here. Its common comment is retained
    for both severity subrows exactly as printed.
    """
    first_box, alternate_box = gridrow.cells[1:3]
    first_words = crop.crop(first_box).extract_words()
    alternate_words = crop.crop(alternate_box).extract_words()
    anchors = [next(word['top'] for word in first_words if word['text'] == 'Vancomycin'),
               next(word['top'] for word in alternate_words if word['text'] == 'Linezolid')]
    split = min(anchors)-1
    prefix = fields[0].split('Mild',1)[0].strip()
    def source_part(box, top, bottom):
        return (crop.crop((box[0],top,box[2],bottom)).extract_text(x_tolerance=2,y_tolerance=3) or '').strip()
    mild = [prefix+'\nMild',source_part(first_box,first_box[1],split),
            source_part(alternate_box,alternate_box[1],split),fields[3]]
    severe = [prefix+'\nModerate to Severe',source_part(first_box,split,first_box[3]),
              source_part(alternate_box,split,alternate_box[3]),fields[3]]
    assert 'Trimethoprim-' in mild[1] and 'Vancomycin' not in mild[1]
    assert 'Doxycycline' in mild[2] and 'Linezolid' not in mild[2]
    assert 'Vancomycin' in severe[1] and 'Trimethoprim' not in severe[1]
    assert 'Linezolid' in severe[2] and 'Doxycycline' not in severe[2]
    return [mild,severe]


def resolved_table_rows(table):
    values = table.extract(x_tolerance=2,y_tolerance=3)
    mapping = {tuple(cell):value or '' for row,fields in zip(table.rows,values)
               for cell,value in zip(row.cells,fields) if cell}
    centers = table_columns(table)
    result = []
    for row,fields in zip(table.rows,values):
        resolved = []
        for index,(cell,value) in enumerate(zip(row.cells,fields)):
            if value is None and centers and index < 4 and not fullwidth_row(table,row):
                point = centers[index], row.bbox[1]+1
                owner = next((box for box in mapping if box[0] <= point[0] <= box[2] and box[1] <= point[1] < box[3]),None)
                value = mapping.get(owner,'')
            resolved.append(value or '')
        result.append((row,resolved))
    return result,centers


def main_header(text):
    first = bool(re.search(r'First Line|First line|Preferred drug', text, re.I))
    empirical = 'Empirical' in text and 'Antimicrobial' in text
    return (first or empirical) and bool(re.search(r'Alternative|Alternate|Comments',text,re.I))


def row_heading(fields):
    nonempty = [field for field in fields if field.strip()]
    return bool(fields[0].strip()) and len(nonempty) == 1 and not re.search(r'\b(mg|IV|IM|PO|q\d|hrly)\b',nonempty[0],re.I)


def append_fields(target, fields, page):
    for key,value in zip(('label','firstLine','alternative','comments'),fields):
        if value.strip():
            if value.strip() != target[key].strip():
                target[key] = (target[key]+'\n'+value).strip()
    if page not in target['pdfPages']:
        target['pdfPages'].append(page)


def project_section(pdf, section, following, render_doc, check):
    output = {'infectionId':'ncdc-'+section['section'].replace('.','-'), 'section':section['section'],
              'name':section['name'], 'pdfPages':[], 'rows':[], 'notes':[], 'figures':[], 'sourceText':''}
    audit = {'mainTables':0,'otherTables':0,'continuations':0,'encoding':False,'pages':[], 'tableSummaries':[]}
    previous = None
    previous_main_page = None
    previous_centers = None
    subheading = ''
    text_chunks = []
    for number,crop,bbox in segments(pdf,section,following):
        output['pdfPages'].append(number)
        audit['pages'].append({'pdfPage':number,'crop':list(bbox)})
        full_text = crop.extract_text(x_tolerance=2,y_tolerance=3) or ''
        text_chunks.append(f'PDF page {number} · printed page {number-7}\n'+full_text)
        if 'in BMT settings' in full_text:
            subheading = 'BMT settings'
        audit['encoding'] |= unsupported_glyphs(full_text)
        clean = crop.filter(lambda obj: obj['object_type'] != 'rect' or obj['width'] < 2 or obj['height'] < 2)
        tables = clean.find_tables(SETTINGS)
        all_table_boxes = [table.bbox for table in tables]
        primary_images = []
        for table in sorted(tables,key=lambda t:t.bbox[1]):
            if not table.rows:
                continue
            rows,centers = resolved_table_rows(table)
            width = len(rows[0][1])
            first = norm(' '.join(rows[0][1]))
            header = main_header(first)
            continuation = (not header and width == 4 and previous is not None and
                            previous_main_page in (number,number-1) and table.bbox[1] < 115 and
                            centers and previous_centers and
                            max(abs(a-b) for a,b in zip(centers,previous_centers)) < 8)
            # A one-row continuation can have no complete source label cell, but
            # all four cell boundaries still yield centers via table_columns.
            accepted = width == 4 and (header or continuation)
            audit['tableSummaries'].append({'pdfPage':number,'columns':width,'gridRows':len(rows),
                                            'structured':accepted,'header':first[:120]})
            if not accepted:
                if table.bbox[2]-table.bbox[0] > 40 and width > 1 and table.bbox[3]-table.bbox[1] > 15:
                    audit['otherTables'] += 1
                    primary_images.append((table.bbox,f'Different-layout source table ({width} columns)'))
                continue
            if any(unsupported_glyphs(value) for _,fields in rows for value in fields):
                primary_images.append((table.bbox,'Original treatment table: text-layer symbols require the printed image'))
            audit['mainTables'] += 1
            if centers:
                previous_centers = centers
            previous_main_page = number
            body = rows[1:] if header else rows
            fourth_is_allergy = 'Penicillin' in first and 'allergy' in first and 'Comments' not in first
            aligned_body = []
            for index,(gridrow,fields) in enumerate(body):
                if section['section'] == '9.3' and number == 60 and 'MRSA risk' in fields[0] and 'Moderate to Severe' in fields[0]:
                    aligned_body.extend((index,gridrow,part) for part in mrsa_severity_rows(crop,gridrow,fields))
                else:
                    aligned_body.append((index,gridrow,fields))
            for index,gridrow,fields in aligned_body:
                if not any(field.strip() for field in fields):
                    continue
                if fullwidth_row(table,gridrow) or row_heading(fields):
                    subheading = norm(fields[0].splitlines()[0])
                    output['notes'].append({'text':fields[0].strip(),'pdfPages':[number]})
                    continue
                if fourth_is_allergy and fields[3]:
                    fields[3] = 'Penicillin allergy column: '+fields[3]
                if previous is None and not fields[0].strip() and not fields[1].strip() and not fields[2].strip() and fields[3].strip():
                    output['notes'].append({'text':'Source table comments: '+fields[3].strip(),'pdfPages':[number]})
                    continue
                first_body_continuation = continuation and index == 0
                lower_fragment = bool(fields[0] and fields[0].lstrip()[0].islower())
                if previous is not None and (not fields[0].strip() or first_body_continuation and lower_fragment):
                    # Keep each column's continuation within that column. No
                    # treatment is assembled from a different source column.
                    append_fields(previous,fields,number)
                    audit['continuations'] += 1
                    continue
                label = fields[0].strip()
                if subheading == 'Viral Keratitis' and norm(label) not in {'Epithelial','Stromal','Endothelial'}:
                    subheading = ''
                if subheading and not label.startswith(subheading):
                    label = subheading+' — '+label
                previous = {'id':output['infectionId']+'-source-row-'+str(len(output['rows'])+1),
                            'label':label, 'firstLine':fields[1].strip(), 'alternative':fields[2].strip(),
                            'comments':fields[3].strip(), 'pdfPages':[number]}
                output['rows'].append(previous)
        if audit['otherTables'] and any(t['pdfPage']==number and not t['structured'] and t['columns']>1 for t in audit['tableSummaries']):
            output['notes'].append({'text':'This page includes a table with a different column layout. Its original layout is shown in the exact source image; complete text remains in the original section details. Columns are not reassigned to first-line/alternative fields.', 'pdfPages':[number]})
        def outside_tables(obj):
            if obj['object_type'] != 'char':
                return True
            x = (obj['x0']+obj['x1'])/2
            y = (obj['top']+obj['bottom'])/2
            return not any(box[0]-1 <= x <= box[2]+1 and box[1]-1 <= y <= box[3]+1 for box in all_table_boxes)
        narrative = crop.filter(outside_tables).extract_text(x_tolerance=2,y_tolerance=3) or ''
        # All discovered table boxes are excluded from narrative notes. Main
        # tables have structured cells; other layouts have primary exact images.
        # Their flattened text remains in original-source details only.
        if narrative.strip():
            output['notes'].append({'text':narrative.strip(),'pdfPages':[number]})
        figure_titles = [line['text'] for line in crop.extract_text_lines(return_chars=False) if re.match(r'^Figure\s+\d',line['text'],re.I)]
        for source_image in crop.images:
            image_box = (source_image['x0'],source_image['top'],source_image['x1'],source_image['bottom'])
            if image_box[2]-image_box[0] > 100 and image_box[3]-image_box[1] > 80:
                primary_images.append((image_box,'; '.join(figure_titles) or 'Original source figure / algorithm'))
        specs = [(bbox,False,'original section image')] + [(box,True,caption) for box,caption in primary_images]
        bitmap = None
        whole = None
        if not check:
            bitmap = render_doc[number-1].render(scale=SCALE)
            whole = bitmap.to_pil()
        for image_index,(image_box,primary,description) in enumerate(specs):
            suffix = '' if not primary else f'-detail-{image_index}'
            filename = f"section-{section['section'].replace('.','-')}-pdf-{number}{suffix}.png"
            target = IMAGES / filename
            if not check:
                image = whole.crop((max(0,math.floor(image_box[0]*SCALE)),max(0,math.floor(image_box[1]*SCALE)),math.ceil(image_box[2]*SCALE),math.ceil(image_box[3]*SCALE)))
                image.save(target,optimize=True)
            elif not target.is_file():
                raise AssertionError(f'Missing exact source image: {target}')
            caption = f"NCDC {section['section']} · printed page {number-7} · PDF page {number} · {description}"
            if figure_titles and not primary:
                caption += ' · '+'; '.join(figure_titles)
            output['figures'].append({'imagePath':'/assets/infection-sources/ncdc-sections/'+filename,'pdfPage':number,'caption':caption,'primary':primary})
        if bitmap:
            bitmap.close()
    output['sourceText'] = '\n\n'.join(text_chunks)
    if audit['encoding']:
        output['notes'].insert(0,{'text':'Some PDF text-layer characters do not decode faithfully. The exact original section images preserve the printed spelling, symbols and units.', 'pdfPages':output['pdfPages'][:]})
    return output,audit


def coverage_report(data,audits):
    total_rows = sum(len(s['rows']) for s in data['sections'])
    images = sum(len(s['figures']) for s in data['sections'])
    all_tables = sum(len(a['tableSummaries']) for a in audits)
    main_tables = sum(a['mainTables'] for a in audits)
    other_tables = sum(a['otherTables'] for a in audits)
    primary_images = sum(f['primary'] for section in data['sections'] for f in section['figures'])
    lines = ['# Complete NCDC source projection', '',
             f"Source: {data['source']['name']} — {data['source']['version']}. SHA-256 `{SHA256}`.", '',
             f'All 19 groups and 87 named clinical subsections are projected. There are {total_rows} structured clinical source rows, {images} exact section/page images and complete section text/notes. First-line, alternative and comment columns remain separate; OR, +, maxima, staged doses, age/weight conditions and referrals are retained as printed source content.', '',
             f'Table-by-table audit: {all_tables} discovered source grids; {main_tables} mapped to separate treatment columns and {other_tables} different-layout grids retained as primary exact-image crops plus complete original source text. There are {primary_images} primary detail images in total, including the nonstandard grids, original algorithms and text-layer-symbol fallbacks. Grid row counts in the detailed audit include table headers.', '',
             'This is a source projection, not a new prescription or a clinical validation. It contains no other guideline source. Existing curated records remain separate and untouched. No renal adjustment, patient matching or prescribing action is performed.', '',
             '## What completeness means', '',
             'Each section is bounded by its actual PDF heading and the next heading, including all intervening pages through the end of neonatal section 19.1 on PDF126. Chapter headings and printed page numbers are excluded from neighboring section content. Every retained segment has an exact raster crop as an independent visual record. These images include every treatment table, alternative column, additional-information paragraph, referral, reference and figure in that segment.', '',
             'Main four-column treatment grids are projected by source column. Vertically merged comment cells are copied only to source rows lying inside that same source cell. Continuation text is appended within its original column, with both PDF pages cited. Nonstandard column layouts are not forced into treatment fields: they remain visible in primary exact images and complete original section text, with surrounding non-table notes retained. No valid row is removed because it contains OR, a combination, a maximum or a conditional instruction.', '',
             'Notes exclude all discovered table rectangles, avoiding dose duplication or flattened nonstandard table associations in the main notes view. Images with primary=true are separate crops of nonstandard tables or source figures/algorithms, suitable for the main section view without repeating the entire structured table; primary=false images are complete section/page proof crops for original-source details. Complete sourceText intentionally retains the entire section for original-source inspection. Text encoding imperfections remain explicit and the raster image is authoritative for those glyphs. Source anomalies such as an unexpected unit are preserved, not silently corrected.', '',
             'The inventory below audits every section and each discovered table layout; the claim is source-content coverage, not that every nonstandard table has been semantically curated into a prescription-ready structure.', '',
             '## Verification', '',
             'TDD RED: all seven initial content/provenance tests failed against the absent new projection. Tests then cover full endocarditis first-line/alternative cells, shared comments, chronic osteomyelitis referrals in both columns, CAP continuation, source-only identity, all section images, algorithms and additional information, and section boundaries.', '',
             'Rebuild with bundled Python: `python tools/build_ncdc_complete_library.py`. Verify deterministic JSON/report and image existence with `--check`. Run focused tests with `python -m unittest tools/test_ncdc_complete_library.py -v`. No frontend full-suite run is part of this source-only task.', '',
             '## Source-semantics regression corrections', '', 'The PDF60 MRSA cellulitis cell is projected as two severity subrows using verified vertical source-word coordinates: mild treatment columns remain distinct from moderate-to-severe treatment columns; their source common comment is retained for both. Full-width merged headings are recognized before cell propagation, so Viral Keratitis is contextual metadata for Epithelial/Stromal/Endothelial and never copied into treatment columns. Subsequent VZV/fungal rows do not inherit that HSV context. All Unicode private-use characters and replacement characters trigger primary exact-table crops; no clinical symbol is guessed. All nonstandard tables remain primary images, with their flattened table text removed from narrative notes.', '', '## Every-section coverage audit', '',
             '| Section | Name | PDF pages | Clinical rows | Main grids / other grids | Column continuations | Image or text considerations |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    for section,audit in zip(data['sections'],audits):
        reasons = []
        if audit['otherTables']:
            reasons.append('Different-layout table(s): notes/text + exact images')
        if audit['encoding']:
            reasons.append('Text-layer glyphs: exact images authoritative')
        if not section['rows']:
            reasons.append('Narrative/referral/algorithm: notes/text + exact images')
        if any('Figure ' in f['caption'] for f in section['figures']):
            reasons.append('Figure included in exact section image')
        lines.append(f"| {section['section']} | {section['name']} | {', '.join(map(str,section['pdfPages']))} | {len(section['rows'])} | {audit['mainTables']} / {audit['otherTables']} | {audit['continuations']} | {'; '.join(reasons) or 'Structured source grid plus original notes/image'} |")
    lines += ['', '## Exact image coverage and table layouts', '']
    for section,audit in zip(data['sections'],audits):
        lines += [f"### {section['section']} {section['name']}", '']
        for page in audit['pages']:
            rect = ', '.join(f'{v:.2f}' for v in page['crop'])
            image = next(f for f in section['figures'] if f['pdfPage']==page['pdfPage'])
            lines.append(f"- PDF {page['pdfPage']} (printed {page['pdfPage']-7}), crop points [{rect}]: [{Path(image['imagePath']).name}](../../frontend/public{image['imagePath']}).")
        for table in audit['tableSummaries']:
            lines.append(f"- PDF {table['pdfPage']}: {table['columns']} grid columns, {table['gridRows']} grid rows; {'projected as source treatment columns' if table['structured'] else 'original table retained in primary image/original source text'}; source header/context: {table['header'].replace('|',' / ')}.")
        lines.append('')
    return '\n'.join(lines).rstrip()+'\n'


def build(pdf_path,check):
    actual_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    assert actual_sha == SHA256, 'Unexpected source PDF; do not silently project another edition'
    if not check:
        IMAGES.mkdir(parents=True,exist_ok=True)
    render_doc = None if check else pdfium.PdfDocument(str(pdf_path))
    outputs,audits = [],[]
    with pdfplumber.open(pdf_path) as pdf:
        index = section_index(pdf)
        for i,section in enumerate(index):
            output,audit = project_section(pdf,section,index[i+1] if i+1<len(index) else None,render_doc,check)
            outputs.append(output); audits.append(audit)
    if render_doc:
        render_doc.close()
    if not check:
        referenced = {Path(f['imagePath']).name for section in outputs for f in section['figures']}
        for stale in IMAGES.glob('section-*.png'):
            if stale.name not in referenced:
                stale.unlink()
    data = {'source':{'id':'ncdc','name':'NCDC / ICMR National Treatment Guidelines for Antimicrobial Use in Infectious Disease Syndromes','version':'Version 2.0 — November 2025','url':'https://ncdc.mohfw.gov.in/uploads/pdf/amr17.pdf','sha256':actual_sha},'sections':outputs}
    return data,audits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf',type=Path,default=PDF)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    data,audits = build(args.pdf,args.check)
    products = {OUT:json.dumps(data,ensure_ascii=False,indent=2)+'\n',REPORT:coverage_report(data,audits)}
    for path,content in products.items():
        if args.check:
            assert path.read_text() == content, f'Generated output differs: {path}'
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)
    print(f"87 sections; {sum(len(s['rows']) for s in data['sections'])} structured source rows; {sum(len(s['figures']) for s in data['sections'])} exact source images")


if __name__ == '__main__':
    main()
