import copy
import csv
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_site
import import_proposal
import sync_zenodo as zenodo


def record(rid=101, concept=100, doi='10.5281/zenodo.101'):
    return {'id': rid, 'conceptrecid': str(concept), 'status': 'published', 'modified': '2026-11-12T10:00:00Z',
            'metadata': {'title': 'Example software', 'doi': doi, 'publication_date': '2026-11-01',
                'resource_type': {'type': 'software'}, 'communities': [{'id': 'digitalfinance'}],
                'creators': [{'name': 'Chaffard, Owen', 'orcid': '0009-0005-5509-8652'}],
                'description': '<p>A software description.</p><p>Paper: <a href="https://doi.org/10.1234/paper">paper</a>.</p>',
                'custom': {'code:codeRepository': 'https://github.com/Example/Software',
                           'code:programmingLanguage': [{'id': 'python', 'title': {'en': 'Python'}}]},
                'version': 'v1.0', 'language': 'eng', 'access_right': 'open', 'license': {'id': 'mit-license'}}}


def page(records, total):
    return {'hits': {'hits': records, 'total': total}}


class FetchTests(unittest.TestCase):
    def test_anonymous_request_identifies_client(self):
        with patch.object(zenodo, 'urlopen', return_value=io.StringIO('{"ok": true}')) as open_url:
            self.assertEqual(zenodo.request_json(zenodo.API), {'ok': True})
        request = open_url.call_args.args[0]
        self.assertIsNone(request.get_header('Authorization'))
        self.assertEqual(request.get_header('User-agent'), zenodo.USER_AGENT)

    def test_paginates_and_requests_only_latest_community_software(self):
        records = [record(), record(201, 200, '10.1234/second')]
        with patch.object(zenodo, 'request_json', side_effect=[page(records[:1], 2), page(records[1:], {'value': 2, 'relation': 'eq'})]) as request, patch.object(zenodo.time, 'sleep'):
            self.assertEqual(zenodo.fetch_records(), records)
        from urllib.parse import parse_qs, urlsplit
        queries = [parse_qs(urlsplit(call.args[0]).query) for call in request.call_args_list]
        self.assertEqual([q['page'] for q in queries], [['1'], ['2']])
        self.assertEqual(queries[0]['communities'], ['digitalfinance'])
        self.assertEqual(queries[0]['all_versions'], ['false'])
        self.assertEqual(queries[0]['type'], ['software'])
        self.assertEqual(queries[0]['size'], ['25'])

    def test_incomplete_duplicate_and_changing_responses_fail(self):
        for responses in [[page([record()], 2), page([], 2)],
                          [page([record()], 2), page([record()], 2)],
                          [page([record()], 2), page([], 3)]]:
            with self.subTest(responses=responses), patch.object(zenodo, 'request_json', side_effect=responses), patch.object(zenodo.time, 'sleep'), self.assertRaises(ValueError):
                zenodo.fetch_records()

    def test_rejects_records_outside_community_or_software_scope(self):
        for key, value in [('communities', []), ('resource_type', {'type': 'dataset'})]:
            item = record(); item['metadata'][key] = value
            with self.subTest(key=key), patch.object(zenodo, 'request_json', return_value=page([item], 1)), self.assertRaises(ValueError):
                zenodo.fetch_records()

    def test_retries_rate_limits_but_not_authentication_errors(self):
        throttled = HTTPError(zenodo.API, 429, 'Rate limited', {'Retry-After': '7'}, None)
        with patch.object(zenodo, 'urlopen', side_effect=[throttled, io.StringIO('{}')]), patch.object(zenodo.time, 'sleep') as sleep:
            self.assertEqual(zenodo.request_json(zenodo.API), {})
            sleep.assert_called_once_with(7)
        with patch.object(zenodo, 'urlopen', side_effect=HTTPError(zenodo.API, 403, 'Forbidden', {}, None)) as request, self.assertRaises(HTTPError):
            zenodo.request_json(zenodo.API)
        self.assertEqual(request.call_count, 1)


class SyncTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''})
        patcher.start(); self.addCleanup(patcher.stop)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(build_site.ROOT / 'data', self.root / 'data')
        shutil.copytree(build_site.ROOT / 'site', self.root / 'site')
        for path in (self.root / 'data').glob('*.csv'):
            path.write_text(path.read_text().splitlines()[0] + '\n')
        with (self.root / 'data/software.csv').open() as stream:
            self.fields = next(csv.reader(stream))
        self.papers = {'publications': [{'id': 'published-paper', 'title': 'A paper', 'doi': '10.1234/paper'}],
                       'working_papers': [{'id': 'draft-paper', 'title': 'A draft', 'doi': '10.2139/ssrn.5703882'}]}
        (self.root / 'data/papers.json').write_text(json.dumps(self.papers))
        for module in [build_site, import_proposal]:
            patcher = patch.object(module, 'ROOT', self.root)
            patcher.start(); self.addCleanup(patcher.stop)
        self.target = self.root / 'data' / zenodo.CACHE

    def sync(self, records, write=True):
        return zenodo.sync_records(records, root=self.root, write=write)

    def rows(self):
        return build_site.inventory(self.root)['software']

    def test_metadata_irps_software_doi_and_paper_doi_are_distinct(self):
        self.sync([record()])
        row = self.rows()[0]
        self.assertEqual(row['irp_numbers'], '14')
        self.assertEqual(row['doi'], '10.5281/zenodo.101')
        self.assertEqual(row['publication_ids'], 'published-paper')
        self.assertEqual(row['languages'], 'Python')
        self.assertEqual(row['summary'], 'A software description.')
        self.assertEqual(row['version'], 'v1.0')
        self.assertEqual(row['index'], 'zenodo')
        self.assertEqual(row['data_availability'], 'not-documented')
        build_site.build()
        export = json.loads((self.root / '_site/data/software.json').read_text())['software'][0]
        self.assertEqual(export['researcher_names'], 'Owen Chaffard')

    def test_dry_run_no_change_and_repeat_sync_is_byte_identical(self):
        before = {p.name: p.read_bytes() for p in (self.root / 'data').iterdir()}
        self.sync([record()], write=False)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / 'data').iterdir()})
        self.assertTrue(self.sync([record()]))
        before = self.target.read_bytes()
        self.assertFalse(self.sync([record()]))
        self.assertEqual(self.target.read_bytes(), before)

    def test_new_version_keeps_concept_id_and_removal_prunes_only_generated_feed(self):
        self.sync([record()])
        self.sync([record(102, doi='10.5281/zenodo.102')])
        self.assertEqual(self.rows()[0]['id'], 'zenodo-100')
        self.assertEqual(self.rows()[0]['index_url'], 'https://zenodo.org/records/102')
        self.sync([])
        self.assertEqual(self.rows(), [])

    def test_invalid_records_and_ambiguous_versions_preserve_existing_feed(self):
        self.sync([record()]); before = self.target.read_bytes()
        for changes in [{'doi': 'invalid'}, {'publication_date': '2026-13-01'}, {'publication_date': '2026-13'},
                        {'title': ''}, {'custom': {'code:codeRepository': 'javascript:alert(1)'}},
                        {'resource_type': {'type': 'publication'}}, {'communities': []}]:
            invalid = record(); invalid['metadata'].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.sync([invalid])
            self.assertEqual(self.target.read_bytes(), before)
        with self.assertRaises(ValueError): self.sync([record(), record(102)])
        self.assertEqual(self.target.read_bytes(), before)

    def test_archive_only_records_without_irp_or_language_are_shown_without_guesses(self):
        item = record(); item['metadata'].update(custom={}, creators=[{'name': 'Unknown Author'}])
        self.sync([item])
        row = self.rows()[0]
        self.assertEqual(row['irp_numbers'], '')
        self.assertEqual(row['languages'], '')  # metadata.language is a natural language.
        self.assertEqual(row['repository_url'], 'https://zenodo.org/records/101')
        build_site.build()
        page = (self.root / '_site/index.html').read_text()
        self.assertIn('IRP not assigned', page)
        self.assertIn('Software archive', page)

    def test_contributors_can_assign_irp_and_initials_do_not(self):
        item = record(); item['metadata']['creators'] = [{'name': 'O. Chaffard'}]
        self.sync([item]); self.assertEqual(self.rows()[0]['irp_numbers'], '')
        item['metadata']['contributors'] = [{'name': 'Chaffard, Owen', 'type': 'Researcher'}]
        self.sync([item]); self.assertEqual(self.rows()[0]['irp_numbers'], '14')

    def test_software_relations_and_own_doi_do_not_become_papers(self):
        item = record(); item['metadata']['description'] = '<p>https://doi.org/10.5281/zenodo.101</p>'
        item['metadata']['related_identifiers'] = [
            {'identifier': 'https://github.com/QuantLet/Example', 'scheme': 'url', 'relation': 'isSupplementTo', 'resource_type': 'software'},
            {'identifier': '10.1234/dataset', 'scheme': 'doi', 'relation': 'references', 'resource_type': 'dataset'},
            {'identifier': '10.2139/ssrn.5703882', 'scheme': 'doi', 'relation': 'isSupplementTo', 'resource_type': 'publication-preprint'}]
        item['metadata']['custom'] = {}
        self.sync([item]); row = self.rows()[0]
        self.assertEqual(row['repository_url'], 'https://github.com/QuantLet/Example')
        self.assertEqual(row['working_paper_ids'], 'draft-paper')
        self.assertEqual(row['paper_urls'], '')

    def test_overlap_merges_quantlet_credits_and_category_with_zenodo_doi(self):
        item = record(); item['metadata']['custom']['code:codeRepository'] = 'https://github.com/QuantLet/Example'
        quantlet = zenodo.software(item, self.fields, zenodo.load_directory(self.root), self.papers)
        quantlet.update(id='quantlet-123', category='quantlet', irp_numbers='14;16', index='quantlet',
                        index_url='https://github.com/QuantLet/Example', doi='', contributors='@jpcreil')
        with (self.root / 'data/quantlet-software.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fields); writer.writeheader(); writer.writerow(quantlet)
        self.sync([item])
        self.assertEqual(len(self.rows()), 1)
        merged = self.rows()[0]
        self.assertEqual(merged['id'], 'quantlet-123')
        self.assertEqual(merged['category'], 'quantlet')
        self.assertEqual(merged['irp_numbers'], '14;16')
        self.assertEqual(merged['doi'], '10.5281/zenodo.101')
        self.assertEqual(merged['index_url'], 'https://zenodo.org/records/101')
        self.assertEqual(merged['contributors'], '@jpcreil')

    def test_curated_update_survives_later_sync_and_is_not_overwritten(self):
        self.sync([record()])
        proposal = self.root / 'proposal.json'
        proposal.write_text(json.dumps({'kind': 'software', 'action': 'update', 'record': {'id': 'zenodo-100', 'name': 'Reviewed name'}}))
        import_proposal.apply_proposal(proposal, True)
        before = (self.root / 'data/software.csv').read_bytes()
        self.sync([record(102)])
        self.assertEqual([row['name'] for row in self.rows()], ['Reviewed name'])
        self.assertEqual((self.root / 'data/software.csv').read_bytes(), before)

    def test_distinct_software_in_shared_repo_and_versioned_project_paths(self):
        first, second = record(), record(201, 200, '10.5281/zenodo.201')
        first['metadata']['custom']['code:codeRepository'] = 'https://github.com/Org/Repo/tree/aaa/IRP1/code'
        second['metadata']['custom']['code:codeRepository'] = 'https://github.com/Org/Repo/tree/bbb/IRP2/code'
        self.sync([first, second]); self.assertEqual(len(self.rows()), 2)
        self.assertEqual(build_site.repository_key(first['metadata']['custom']['code:codeRepository']),
                         build_site.repository_key('https://github.com/org/repo/tree/newversion/IRP1/code'))


if __name__ == '__main__':
    unittest.main()

