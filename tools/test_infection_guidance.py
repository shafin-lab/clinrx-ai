"""Regression checks for source extraction semantics; no PDF or patient writes."""
import unittest
from build_infection_guidance import finalize


class CrossReferenceTests(unittest.TestCase):
    def test_pdf_wrap_does_not_turn_a_referral_into_a_complete_regimen(self):
        raw = 'Empirical therapy as\nper guidelines for acute\nosteomyelitis.'
        entry = {'id':'referral', '_raw':raw, 'regimens':[], 'gaps':[], 'notes':[]}
        finalize(entry)
        self.assertEqual(entry['regimens'], [])
        self.assertTrue(entry['gaps'])
        self.assertIn(raw, entry['notes'][0])


if __name__ == '__main__':
    unittest.main()
