import copy
import csv
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_site
import import_proposal
import sync_metadata

RECORD = {'id': 'test-code', 'name': 'Test software', 'repository_url': 'https://example.org/research-code',
          'summary': 'An experiment package', 'category': 'paper-replication', 'authors': 'Researcher One;Mollá, Researcher',
          'languages': 'Python;R', 'irp_numbers': '14;15', 'paper_urls': 'https://example.org/paper',
          'index': 'not-indexed', 'data_availability': 'restricted', 'data_notes': 'A data agreement is required.'}


class SoftwareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(build_site.ROOT / 'data', self.root / 'data')
        shutil.copytree(build_site.ROOT / 'site', self.root / 'site')
        self.target = self.root / 'data/software.csv'
        self.target.write_text(self.target.read_text().splitlines()[0] + '\n')
        for module in [build_site, import_proposal]:
            patcher = patch.object(module, 'ROOT', self.root); patcher.start(); self.addCleanup(patcher.stop)

    def proposal(self, record=None, action='add'):
        path = self.root / 'proposal.json'
        path.write_text(json.dumps({'kind': 'software', 'action': action, 'record': RECORD if record is None else record}))
        return path

    def apply(self, record=None, write=True, action='add'):
        import_proposal.apply_proposal(self.proposal(record, action), write)

    def test_dry_run_and_invalid_records_preserve_csv(self):
        before = self.target.read_bytes()
        self.apply(write=False)
        self.assertEqual(self.target.read_bytes(), before)
        for change in [{'repository_url': 'javascript:alert(1)'}, {'category': 'invalid'}, {'languages': ''},
                       {'irp_numbers': '999'}, {'irp_numbers': '14;14'}, {'authors': ''}, {'paper_urls': ''},
                       {'publication_ids': 'unknown-id'}, {'working_paper_ids': 'unknown-id'}, {'paper_titles': 'First;Second'},
                       {'data_notes': ''}, {'data_availability': 'unknown'}, {'private_field': 'x'}]:
            with self.subTest(change=change), self.assertRaises(ValueError): self.apply({**RECORD, **change})
            self.assertEqual(self.target.read_bytes(), before)

    def test_partial_update_preserves_authors_and_multiline_notes(self):
        self.apply()
        self.apply({'id': RECORD['id'], 'data_notes': 'Résumé, first line\nSecond line'}, action='update')
        row = build_site.inventory()['software'][0]
        self.assertEqual(row['authors'], RECORD['authors'])
        self.assertEqual(row['data_notes'], 'Résumé, first line\nSecond line')

    def test_doi_normalization_unique_and_distinct_index_rules(self):
        row = {**RECORD, 'index': 'zenodo', 'index_url': 'https://zenodo.org/records/123', 'doi': 'https://doi.org/10.5281/ZENODO.123'}
        self.apply(row)
        self.assertEqual(build_site.inventory()['software'][0]['doi'], '10.5281/zenodo.123')
        with self.assertRaises(ValueError): self.apply({**row, 'id': 'another-code'})
        for change in [{'index': 'not-indexed'}, {'index_url': ''}, {'doi': 'invalid'}]:
            with self.subTest(change=change), self.assertRaises(ValueError): self.apply({**row, **change, 'id': 'new-code'})

    def test_quantlet_record_does_not_require_doi(self):
        self.apply({**RECORD, 'index': 'quantlet', 'index_url': 'https://quantlet.com/project/example'})
        self.assertEqual(build_site.inventory()['software'][0]['index'], 'quantlet')

    def test_optional_plot_needs_direct_public_image_and_alt_text(self):
        for fields in [{'key_image_url': 'https://example.org/plot.png'},
                       {'key_image_alt': 'A plot'},
                       {'key_image_url': 'https://example.org/page.html', 'key_image_alt': 'A plot'},
                       {'key_image_url': 'javascript:alert(1)', 'key_image_alt': 'A plot'}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError): self.apply({**RECORD, **fields})
        self.apply({**RECORD, 'key_image_url': 'https://example.org/plot.png', 'key_image_alt': 'Forecast compared with observations', 'key_image_caption': 'Figure 1, source repository'})
        build_site.build()
        page = (self.root / '_site/index.html').read_text()
        self.assertIn('Forecast compared with observations', page)
        self.assertIn('Figure 1, source repository', page)

    def test_links_to_catalogue_publication_and_working_paper(self):
        papers = {'publications': [{'id': 'published-paper', 'title': 'A published paper'}],
                  'working_papers': [{'id': 'working-paper', 'title': 'A working paper'}]}
        (self.root / 'data/papers.json').write_text(json.dumps(papers))
        self.apply({**RECORD, 'paper_urls': '', 'publication_ids': 'published-paper', 'working_paper_ids': 'working-paper'})
        build_site.build()
        page = (self.root / '_site/index.html').read_text()
        self.assertIn('/Publications/#publication/published-paper', page)
        self.assertIn('/Publications/working-papers.html#working-paper/working-paper', page)

    def test_build_escapes_metadata_and_exports_canonical_identity_fields(self):
        self.apply({**RECORD, 'summary': '<script>alert(1)</script>', 'paper_titles': 'Named paper'})
        build_site.build()
        page = (self.root / '_site/index.html').read_text()
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('>Named paper ↗</a>', page)
        exported = json.loads((self.root / '_site/data/software.json').read_text())['software'][0]
        self.assertIn('Owen Chaffard', exported['researcher_names'])
        self.assertTrue(exported['irp_titles'])
        self.assertIn('researcher_names', (self.root / '_site/data/software.csv').read_text())

    def test_reference_sync_is_atomic_when_upstream_removes_linked_paper(self):
        papers = {'publications': [{'id': 'linked-paper', 'title': 'Linked paper'}], 'working_papers': []}
        (self.root / 'data/papers.json').write_text(json.dumps(papers))
        self.apply({**RECORD, 'paper_urls': '', 'publication_ids': 'linked-paper'})
        people_path, paper_path = self.root / 'data/people.json', self.root / 'data/papers.json'
        before = (people_path.read_bytes(), paper_path.read_bytes())
        updated = json.loads(people_path.read_text()); updated['projects'][0]['title'] = 'A corrected project title'
        with patch.object(sync_metadata, 'fetch_json', side_effect=[updated, {'publications': [], 'working_papers': []}]), self.assertRaises(ValueError): sync_metadata.sync(root=self.root)
        self.assertEqual((people_path.read_bytes(), paper_path.read_bytes()), before)


if __name__ == '__main__':
    unittest.main()
