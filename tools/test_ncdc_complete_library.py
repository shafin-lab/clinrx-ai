#!/usr/bin/env python3
"""Content and provenance tests for the complete NCDC source projection."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'frontend/src/infectionLibrary/data/ncdc-complete-guidance.json'
PUBLIC = ROOT / 'frontend/public'


def norm(value):
    return re.sub(r'\s+', ' ', value)


class CompleteNcdcLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text()) if DATA.exists() else {'source': {}, 'sections': []}
        cls.sections = {s['section']: s for s in cls.data['sections']}

    def section(self, number):
        self.assertIn(number, self.sections, 'Named NCDC section must be projected')
        return self.sections[number]

    def test_all_87_sections_in_all_19_groups_have_source_content_and_images(self):
        counts = [4, 5, 4, 9, 2, 10, 6, 1, 7, 7, 4, 7, 4, 2, 2, 1, 4, 7, 1]
        expected = {f'{group}.{section}' for group,count in enumerate(counts,1) for section in range(1,count+1)}
        self.assertEqual(set(self.sections), expected)
        ids = []
        for section in self.sections.values():
            self.assertGreater(len(section['sourceText']), 50)
            self.assertEqual(section['infectionId'], 'ncdc-' + section['section'].replace('.', '-'))
            self.assertTrue(section['pdfPages'])
            self.assertEqual({f['pdfPage'] for f in section['figures']}, set(section['pdfPages']))
            for figure in section['figures']:
                self.assertTrue((PUBLIC / figure['imagePath'].lstrip('/')).is_file())
            for row in section['rows']:
                self.assertTrue(row['label'].strip(), 'Unlabelled shared comment must be a visible table note')
                ids.append(row['id'])
                self.assertTrue(set(row['pdfPages']).issubset(section['pdfPages']))
                self.assertTrue(row['firstLine'] or row['alternative'] or row['comments'])
        self.assertEqual(len(ids), len(set(ids)))

    def test_frozen_source_identity_and_ncdc_only_content(self):
        self.assertEqual(self.data['source'].get('id'), 'ncdc')
        self.assertEqual(self.data['source'].get('sha256'), '0debe52c37cf08dc5d112b8ef71d4ef322c323f04f712473a57a78f1bb68f90a')
        self.assertNotIn('jipmer', json.dumps(self.data).lower())
        self.assertNotIn('held for review', json.dumps(self.data).lower())

    def test_endocarditis_all_three_rows_preserve_full_separate_source_columns(self):
        rows = self.section('1.1')['rows']
        self.assertEqual(len(rows), 3)
        native, prosthetic, severe = rows
        self.assertIn('Native valve', norm(native['label']))
        self.assertIn('Penicillin G 4 million units', norm(native['firstLine']))
        self.assertIn('Ampicillin 2g IV 4 hrly', norm(native['firstLine']))
        self.assertIn('Gentamicin 1mg/kg', norm(native['firstLine']))
        self.assertIn('Prosthetic valve', norm(prosthetic['label']))
        self.assertIn('for 6 weeks', norm(prosthetic['firstLine']))
        self.assertIn('Daptomycin', prosthetic['alternative'])
        text = norm(severe['firstLine'])
        for expected in ['Vancomycin 15mg/kg IV', 'Meropenem 1g IV q8h', 'Teicoplanin 12mg/kg IV', '12 hrly x 3 doses', '6 - 12mg OD', 'Gentamicin 1mg/kg', '4-6 weeks']:
            self.assertIn(expected, text)
        self.assertRegex(text, r'\bOr\b')
        self.assertIn('+', text)
        self.assertIn('Daptomycin', severe['alternative'])
        self.assertNotIn('Daptomycin', severe['firstLine'])
        for row in rows:
            self.assertIn('synergism', row['comments'])

    def test_chronic_osteomyelitis_keeps_referral_in_both_source_columns(self):
        row = self.section('10.2')['rows'][0]
        self.assertIn('Acute on chronic', norm(row['label']))
        self.assertIn('Empirical therapy', row['firstLine'])
        self.assertIn('acute osteomyelitis', norm(row['firstLine']).lower())
        self.assertIn('acute osteomyelitis', norm(row['alternative']).lower())

    def test_shared_comments_and_page_continuations_keep_scope(self):
        rows = self.section('12.5')['rows']
        ward = next(r for r in rows if norm(r['label']) == 'Inpatient ward')
        self.assertIn('Duration of therapy is 5-7 days', norm(ward['comments']))
        pseudo = next(r for r in rows if 'Pseudomonas' in r['label'])
        for column in ('firstLine', 'alternative'):
            self.assertIn('Doxycycline 100mg', norm(pseudo[column]))
            self.assertIn('Duration: 7 days', norm(pseudo[column]))
        self.assertEqual(pseudo['pdfPages'], [90,91])
        for section in self.sections.values():
            for row in section['rows']:
                self.assertNotRegex(norm(row['label']), r'^(specific infection|like bullae)')

    def test_nonstandard_tables_algorithms_and_additional_information_remain_visible(self):
        aufi = self.section('3.1')
        self.assertTrue(any(f['pdfPage'] == 34 for f in aufi['figures']))
        self.assertIn('Day 1 or 2', aufi['sourceText'])
        prophylaxis = self.section('10.7')
        self.assertIn('Paediatric dose', prophylaxis['sourceText'])
        self.assertIn('Cefazolin', prophylaxis['sourceText'])
        self.assertTrue(any('table' in n['text'].lower() for n in prophylaxis['notes']))
        fungal = self.section('17.4')
        self.assertIn('Letermovir', fungal['sourceText'])
        self.assertIn('CMV', '\n'.join(n['text'] for n in fungal['notes']))
        ie_notes = '\n'.join(n['text'] for n in self.section('1.1')['notes'])
        self.assertIn('Echocardiography', ie_notes)
        self.assertIn('Host factors', ie_notes)

    def test_unstructured_tables_and_algorithms_have_separate_primary_images(self):
        for number in ['2.5','3.1','10.7','13.2','17.4']:
            section = self.section(number)
            self.assertTrue(any(f.get('primary') for f in section['figures']), number)
        bmt = self.section('17.4')
        self.assertTrue(any('BMT settings' in r['label'] and 'pneumonia' in r['label'].lower() for r in bmt['rows']))
        self.assertFalse(any(len(f['caption']) == 0 for s in self.sections.values() for f in s['figures']))

    def test_comment_only_continuation_is_not_lost_as_an_empty_heading(self):
        row = self.section('12.7')['rows'][0]
        self.assertIn('open-thoracotomy', row['comments'])
        self.assertIn(93,row['pdfPages'])
        for section in self.sections.values():
            for note in section['notes']:
                self.assertTrue(note['text'].strip())

    def test_adjacent_section_content_and_annexures_do_not_bleed(self):
        self.assertNotIn('1.3 Pericarditis', self.section('1.2')['sourceText'])
        self.assertNotIn('6.10 Chorio', self.section('6.9')['sourceText'])
        self.assertNotIn('12.6 Lung Abscess', self.section('12.5')['sourceText'])
        self.assertLessEqual(max(self.section('19.1')['pdfPages']),126)
        self.assertNotIn('ANNEXURE A', self.section('19.1')['sourceText'])


if __name__ == '__main__':
    unittest.main()
