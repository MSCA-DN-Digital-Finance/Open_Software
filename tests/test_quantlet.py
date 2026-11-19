import copy
import csv
from datetime import date
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_site
import import_proposal
import sync_quantlet as quantlet


def repo(rid=101, name='Example'):
    return {'id': rid, 'full_name': 'QuantLet/' + name, 'name': name, 'owner': {'login': 'QuantLet'},
            'private': False, 'default_branch': 'main', 'size': 10, 'pushed_at': '2026-11-01T10:00:00Z',
            'language': 'Python', 'license': {'spdx_id': 'MIT'}, 'description': 'An example repository', 'archived': False}


class FakeClient:
    def __init__(self, repos=None, metadata=None, contributors=None, profiles=None):
        self.repos = repos or [repo()]
        self.meta = metadata if metadata is not None else {'Metainfo.txt': 'Name of Quantlet: Test software\nAuthor: Owen Chaffard\nPublished in: Example Paper\nDescription: Example research code'}
        self.contributors = contributors or []
        self.profiles = profiles or {}
        self.requests = 0
        self.calls = []

    def repositories(self):
        self.requests += 1
        return copy.deepcopy(self.repos)

    def get(self, path):
        self.requests += 1; self.calls.append(path)
        if '/branches/' in path:
            return {'commit': {'sha': 'a' * 40, 'commit': {'tree': {'sha': 'b' * 40}}}}
        if '/git/trees/' in path:
            return {'truncated': False, 'tree': [{'type': 'blob', 'path': name} for name in self.meta]}
        if path.startswith('users/'):
            return copy.deepcopy(self.profiles[path.split('/')[-1]])
        raise AssertionError(path)

    def pages(self, path):
        self.requests += 1
        return copy.deepcopy(self.contributors)

    def metadata(self, repository, commit, path):
        return self.meta[path]


class QuantLetTests(unittest.TestCase):
    def setUp(self):
        summary = patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''})
        summary.start(); self.addCleanup(summary.stop)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(build_site.ROOT / 'data', self.root / 'data')
        (self.root / 'data/quantlet-software.csv').unlink(missing_ok=True)
        (self.root / 'data/zenodo-software.csv').unlink(missing_ok=True)
        self.curated = self.root / 'data/software.csv'
        self.curated.write_text(self.curated.read_text().splitlines()[0] + '\n')
        papers = {'publications': [{'id': 'example-paper', 'title': 'Example Paper', 'doi': '10.1234/paper'}],
                  'working_papers': [{'id': 'draft-paper', 'title': 'Draft Paper', 'link': 'https://example.org/draft'}]}
        (self.root / 'data/papers.json').write_text(json.dumps(papers))
        (self.root / 'data/quantlet-identities.json').write_text('{"schema_version":1,"identities":[]}')

    def sync(self, client=None, write=True, limit=100, doi_loader=lambda: {}):
        return quantlet.sync(client or FakeClient(), root=self.root, write=write, max_repositories=limit,
                             doi_loader=doi_loader)

    def test_cards_api_matches_exact_repository_and_keeps_all_distinct_dois(self):
        def card(url, doi):
            return {'parent_folder_url': url, 'doi': doi}

        payload = [card('https://github.com/QuantLet/Example/blob/main/first', 'https://doi.org/10.1234/A'),
                   card('https://github.com/quantlet/example/tree/main/second', '10.1234/b'),
                   card('https://github.com/QuantLet/Example', '10.1234/a'),
                   card('https://github.com/QuantLet/Example', 'Not yet assigned'),
                   card('https://github.com/QuantLet/Example', None),
                   card('https://github.com/QuantLet/Example-other', '10.1234/other'),
                   card('https://github.com/another/Example', '10.1234/unrelated'),
                   card('https://example.org/QuantLet/Example', '10.1234/other-host')]
        with patch.object(quantlet, 'urlopen', return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            self.assertEqual(quantlet.fetch_quantlet_dois(), {'quantlet/example': '10.1234/a;10.1234/b',
                                                             'quantlet/example-other': '10.1234/other'})
        self.assertEqual(request.call_args.args[0].full_url, quantlet.QUANTLET_API)
        self.assertNotIn('Authorization', request.call_args.args[0].headers)

    def test_cached_repository_gets_creation_date_and_retains_dois_during_api_failure(self):
        def unavailable():
            raise OSError('API unavailable')

        client = FakeClient()
        self.sync(client, doi_loader=lambda: {'quantlet/example': '10.1234/a;10.1234/b'})
        client.repos[0]['created_at'] = '2025-01-15T18:23:00Z'
        client.calls.clear()
        self.sync(client, doi_loader=unavailable)
        row = build_site.inventory(self.root)['software'][0]
        self.assertEqual(client.calls, [])
        self.assertEqual(row['repository_created_at'], '2025-01-15')
        self.assertEqual(row['last_updated'], '2026-11-01')
        self.assertEqual(row['quantlet_dois'], '10.1234/a;10.1234/b')
        self.assertEqual(row['doi'], '')
        rendered = build_site.render_record(row, build_site.paper_inventory(self.root))
        self.assertIn('<time datetime="2025-01-15">', rendered)
        self.assertIn('2 QuantLet DOIs', rendered)
        self.assertIn('https://doi.org/10.1234/b', rendered)

    def test_parser_handles_crlf_yaml_lists_blocks_and_never_executes_yaml(self):
        parsed = quantlet.parse_metainfo('Author:\r\n  - "Owen Chaffard"\r\n  - Jens Reil\r\nDescription: >\r\n  A multiline\r\n  description\r\nPublished in: Example Paper\r\nInput: !!python/object/apply:os.system ["never-run"]')
        self.assertEqual(parsed['author'], 'Owen Chaffard\nJens Reil')
        self.assertEqual(parsed['description'], 'A multiline description')
        self.assertEqual(parsed['publishedin'], 'Example Paper')
        self.assertNotIn('input', parsed)
        indented = quantlet.parse_metainfo('  Author: Owen Chaffard\n  Description: >\n    An indented description')
        self.assertEqual(indented['author'], 'Owen Chaffard')

    def test_full_name_matching_accepts_order_accents_lists_but_not_initials(self):
        for value in ['Owen Chaffard', 'Chaffard, Owen', 'Other Author, Owen Chaffard', '["Other Author", "Owen Chaffard"]', 'Other Author;Owen Chaffard']:
            self.assertTrue(quantlet.name_matches(value, ['Owen Chaffard']), value)
        for value in ['O. Chaffard', 'Owen Chaffardson', 'Owen Other Chaffard', 'Submitted by Owen Chaffard']:
            self.assertFalse(quantlet.name_matches(value, ['Owen Chaffard']), value)
        self.assertTrue(quantlet.name_matches('Researcher Molla', ['Researcher Mollá']))

    def test_nested_case_insensitive_metainfo_author_adds_repo_and_links_paper(self):
        client = FakeClient(metadata={'Metainfo.txt': 'Author: Other Scholar', 'nested/METAINFO.TXT': 'Author: Chaffard, Owen\nPublished in: Example Paper'})
        report = self.sync(client)
        rows = build_site.inventory(self.root)['software']
        self.assertEqual(report['matched_repositories'], 1)
        self.assertEqual(rows[0]['id'], 'quantlet-101')
        self.assertEqual(rows[0]['irp_numbers'], '14')
        self.assertEqual(rows[0]['category'], 'quantlet')
        self.assertEqual(rows[0]['publication_ids'], 'example-paper')
        self.assertIn('nested/METAINFO.TXT', rows[0]['provenance'])

    def test_contributor_profile_can_match_without_metainfo_or_paper(self):
        client = FakeClient(metadata={}, contributors=[{'login': 'known-person', 'type': 'User'}],
                            profiles={'known-person': {'login': 'known-person', 'name': 'Owen Chaffard', 'type': 'User'}})
        self.sync(client)
        row = build_site.inventory(self.root)['software'][0]
        self.assertEqual(row['irp_numbers'], '14')
        self.assertEqual(row['authors'], '')
        self.assertEqual(row['paper_urls'], '')
        self.assertIn('GitHub contributor: known-person', row['provenance'])
        self.assertIn('Paper link not yet documented', build_site.render_record(row, build_site.paper_inventory(self.root)))

    def test_irp7_requires_full_name_in_author_list_with_accents_and_name_order_variants(self):
        known = quantlet.identities(self.root, quantlet.load_directory(self.root))
        for field in ['author', 'authors']:
            for credit in ['Ștefan Găman', 'Stefan Gaman', 'Ştefan Găman', 'Gaman, Stefan',
                           'STEFAN GAMAN', 'Other Scholar;Ștefan Găman', '["Other Scholar", "Stefan Gaman"]']:
                snapshot = {'metainfo': [{'path': 'nested/Metainfo.txt', 'fields': {field: credit}}], 'contributors': []}
                with self.subTest(field=field, credit=credit):
                    self.assertEqual(quantlet.matches(snapshot, {}, known), {'7': [f'Metainfo {field}: nested/Metainfo.txt']})

    def test_irp7_contributor_credits_handles_orcid_and_partial_author_names_do_not_qualify(self):
        known = quantlet.identities(self.root, quantlet.load_directory(self.root))
        irp7 = next(identity for identity in known if identity['number'] == '7')
        fields = [{'contributor': 'Ștefan Găman'}, {'contributors': 'Stefan Gaman'}, {'author': '@StefanGam'},
                  {'authors': 'https://github.com/StefanGam'}, {'author': 'StefanGam'}, {'author': 'S. Gaman'},
                  {'author': 'Stefan Gamanson'}, {'author': irp7['orcid']}, {}]
        profiles = {'StefanGam': {'name': 'Ștefan Găman', 'orcid': irp7['orcid']},
                    'other-account': {'name': 'Stefan Gaman', 'orcid': irp7['orcid']}}
        for metadata in fields:
            snapshot = {'metainfo': [{'path': 'Metainfo.txt', 'fields': metadata}], 'contributors': list(profiles)}
            with self.subTest(fields=metadata):
                self.assertEqual(quantlet.matches(snapshot, profiles, known), {})

    def test_irp7_maintenance_does_not_remove_other_candidates_and_cached_feed_is_corrected(self):
        client = FakeClient(metadata={'Metainfo.txt': 'Author: Owen Chaffard'},
                            contributors=[{'login': 'StefanGam', 'type': 'User'}],
                            profiles={'StefanGam': {'login': 'StefanGam', 'name': 'Stefan Gaman', 'type': 'User'}})
        # Simulate a feed produced by the previous contributor-matching policy.
        with patch.object(quantlet, 'AUTHOR_LIST_ONLY_IRPS', set()):
            self.sync(client)
        self.assertEqual(build_site.inventory(self.root)['software'][0]['irp_numbers'], '7;14')
        client.calls.clear()
        self.sync(client)
        row = build_site.inventory(self.root)['software'][0]
        self.assertEqual(row['irp_numbers'], '14')
        self.assertNotIn('IRP 7:', row['provenance'])
        self.assertEqual(client.calls, [])

    def test_irp7_maintenance_only_repository_is_pruned_on_cached_refresh(self):
        client = FakeClient(metadata={'Metainfo.txt': 'Author: Other Scholar'},
                            contributors=[{'login': 'StefanGam', 'type': 'User'}],
                            profiles={'StefanGam': {'login': 'StefanGam', 'name': 'Stefan Gaman', 'type': 'User'}})
        with patch.object(quantlet, 'AUTHOR_LIST_ONLY_IRPS', set()):
            self.sync(client)
        self.assertEqual(build_site.inventory(self.root)['software'][0]['irp_numbers'], '7')
        client.calls.clear()
        self.sync(client)
        self.assertEqual(build_site.inventory(self.root)['software'], [])
        self.assertEqual(client.calls, [])

    def test_non_candidate_authors_and_anonymous_handles_do_not_qualify(self):
        client = FakeClient(metadata={'Metainfo.txt': 'Author: Other Scholar\nSubmitted: Owen Chaffard'},
                            contributors=[{'login': 'unknown-person', 'type': 'User'}],
                            profiles={'unknown-person': {'login': 'unknown-person', 'name': 'O. Chaffard', 'type': 'User'}})
        self.sync(client)
        self.assertEqual(build_site.inventory(self.root)['software'], [])

    def test_conflicting_profile_orcid_does_not_match_by_name(self):
        client = FakeClient(metadata={}, contributors=[{'login': 'different-person', 'type': 'User'}],
                            profiles={'different-person': {'login': 'different-person', 'name': 'Owen Chaffard',
                                      'bio': 'https://orcid.org/0000-0002-9123-3883', 'type': 'User'}})
        self.sync(client)
        self.assertEqual(build_site.inventory(self.root)['software'], [])

    def test_shared_github_handle_matches_case_insensitively_without_public_name(self):
        people_path = self.root / 'data/people.json'
        people = json.loads(people_path.read_text())
        candidate = next(p['candidate'] for p in people['projects'] if p['number'] == '14')
        candidate['links']['GitHub'] = 'https://github.com/Known-Account'
        people_path.write_text(json.dumps(people))
        client = FakeClient(metadata={}, contributors=[{'login': 'known-account', 'type': 'User'}],
                            profiles={'known-account': {'login': 'known-account', 'name': None, 'type': 'User'}})
        self.sync(client)
        self.assertEqual(build_site.inventory(self.root)['software'][0]['irp_numbers'], '14')
        # Existing scan is re-matched against changed identities without rescanning.
        candidate['links'].pop('GitHub')
        people_path.write_text(json.dumps(people))
        client.calls.clear()
        self.sync(client)
        self.assertEqual(build_site.inventory(self.root)['software'], [])
        self.assertEqual(client.calls, [])

    def test_verified_handle_takes_precedence_over_incidental_profile_name(self):
        known = quantlet.identities(self.root, quantlet.load_directory(self.root))
        snapshot = {'metainfo': [], 'contributors': ['OCHAFF']}
        users = {'OCHAFF': {'name': 'Mathis Jander', 'orcid': '0000-0002-9123-3883'}}
        self.assertEqual(set(quantlet.matches(snapshot, users, known)), {'14'})

    def test_explicit_metainfo_author_handles_use_shared_mapping(self):
        known = quantlet.identities(self.root, quantlet.load_directory(self.root))
        for credit in ['@OCHAFF', 'ochaff', 'Other Author;https://github.com/ochaff', 'Other Author and @ochaff']:
            snapshot = {'metainfo': [{'path': 'Metainfo.txt', 'fields': {'author': credit}}], 'contributors': []}
            with self.subTest(credit=credit):
                self.assertEqual(set(quantlet.matches(snapshot, {}, known)), {'14'})
        for credit in ['ochaff-someone', '@ochaff-someone', 'Submitted by ochaff']:
            snapshot = {'metainfo': [{'path': 'Metainfo.txt', 'fields': {'author': credit}}], 'contributors': []}
            with self.subTest(credit=credit):
                self.assertEqual(quantlet.matches(snapshot, {}, known), {})

    def test_request_budget_retains_old_snapshots_and_records_pending_work(self):
        self.sync()
        path = self.root / 'data/quantlet-software.csv'; before = path.read_bytes()
        client = FakeClient(repos=[repo(), repo(102, 'Second')])
        with patch.object(client, 'get', side_effect=quantlet.BudgetExhausted('Budget reached')): report = self.sync(client)
        self.assertEqual(report['repositories_pending'], 1)
        self.assertEqual(path.read_bytes(), before)

    def test_incomplete_org_enumeration_is_rejected_before_any_file_changes(self):
        client = quantlet.GitHub.__new__(quantlet.GitHub)
        with patch.object(client, 'get', return_value={'public_repos': 2}), patch.object(client, 'pages', return_value=[repo()]), self.assertRaises(ValueError): client.repositories()

    def test_raw_metadata_request_never_receives_api_authorization(self):
        import threading
        client = quantlet.GitHub.__new__(quantlet.GitHub)
        client.headers = {'Authorization': 'Bearer never-send-to-raw-host'}
        client._raw_limit = threading.Semaphore(1)
        with patch.object(quantlet, 'urlopen', return_value=io.BytesIO(b'Author: Owen Chaffard')) as open_url:
            self.assertEqual(client.metadata('QuantLet/Example', 'abc', 'nested/Metainfo.txt'), 'Author: Owen Chaffard')
        request = open_url.call_args.args[0]
        self.assertIsNone(request.get_header('Authorization'))
        self.assertEqual(request.full_url, 'https://raw.githubusercontent.com/QuantLet/Example/abc/nested/Metainfo.txt')

    def test_verified_alias_needs_a_source_and_can_match_a_contributor_handle(self):
        path = self.root / 'data/quantlet-identities.json'
        config = {'schema_version': 1, 'identities': [{'candidate_id': 'owen-chaffard', 'github_logins': ['verified-person'], 'source_url': 'https://example.org/verified-profile'}]}
        path.write_text(json.dumps(config))
        client = FakeClient(metadata={}, contributors=[{'login': 'verified-person', 'type': 'User'}],
                            profiles={'verified-person': {'login': 'verified-person', 'name': '', 'type': 'User'}})
        self.sync(client)
        self.assertEqual(build_site.inventory(self.root)['software'][0]['irp_numbers'], '14')
        config['identities'][0]['source_url'] = ''
        path.write_text(json.dumps(config))
        with self.assertRaises(ValueError): self.sync(client)

    def test_dry_run_writes_neither_feed_nor_checkpoint(self):
        before = self.curated.read_bytes()
        self.sync(write=False)
        self.assertFalse((self.root / 'data/quantlet-software.csv').exists())
        self.assertFalse((self.root / quantlet.STATE).exists())
        self.assertEqual(self.curated.read_bytes(), before)

    def test_unchanged_repo_uses_cache_and_feed_is_byte_identical(self):
        self.sync()
        path = self.root / 'data/quantlet-software.csv'; before = path.read_bytes()
        client = FakeClient()
        report = self.sync(client)
        self.assertEqual(report['repositories_scanned_this_run'], 0)
        self.assertEqual(client.calls, [])
        self.assertEqual(path.read_bytes(), before)

    def test_bounded_scan_resumes_without_deleting_previous_matches(self):
        repos = [repo(), repo(102, 'Second')]
        first = self.sync(FakeClient(repos=repos), limit=1)
        self.assertEqual(first['repositories_pending'], 1)
        self.assertEqual(len(build_site.inventory(self.root)['software']), 1)
        second = self.sync(FakeClient(repos=repos), limit=1)
        self.assertEqual(second['repositories_pending'], 0)
        self.assertEqual(len(build_site.inventory(self.root)['software']), 2)

    def test_one_repository_failure_keeps_its_snapshot_and_feed_for_retry(self):
        self.sync()
        paths = [self.root / 'data/quantlet-software.csv', self.root / quantlet.STATE]
        before = paths[0].read_bytes()
        previous = json.loads(paths[1].read_text())['repositories']
        changed = repo(); changed['pushed_at'] = '2026-11-02T10:00:00Z'
        client = FakeClient(repos=[changed])
        with patch.object(client, 'metadata', side_effect=OSError('Network failure')): report = self.sync(client)
        self.assertEqual(paths[0].read_bytes(), before)
        self.assertEqual(json.loads(paths[1].read_text())['repositories'], previous)
        self.assertEqual(report['repositories_pending'], 1)
        self.assertEqual(report['errors'][0]['repository'], 'QuantLet/Example')

    def test_curated_override_and_approved_promotion_survive_later_syncs(self):
        self.sync()
        proposal = self.root / 'proposal.json'
        proposal.write_text(json.dumps({'kind': 'software', 'action': 'update', 'record': {'id': 'quantlet-101', 'name': 'Curated name'}}))
        with patch.object(import_proposal, 'ROOT', self.root), patch.object(build_site, 'ROOT', self.root): import_proposal.apply_proposal(proposal, True)
        client = FakeClient(metadata={'Metainfo.txt': 'Author: Owen Chaffard\nPublished in: Example Paper\nName of Quantlet: Changed remote name'})
        client.repos[0].update(pushed_at='2026-11-02T10:00:00Z', created_at='2025-01-15T18:23:00Z')
        self.sync(client, doi_loader=lambda: {'quantlet/example': '10.1234/new'})
        row, = build_site.inventory(self.root)['software']
        self.assertEqual(row['name'], 'Curated name')
        self.assertEqual(row['repository_created_at'], '2025-01-15')
        self.assertEqual(row['quantlet_dois'], '10.1234/new')

    def test_title_doi_and_url_linking_never_treats_paper_doi_as_software_doi(self):
        client = FakeClient(metadata={'Metainfo.txt': 'Author: Owen Chaffard\nPublished in: https://doi.org/10.1234/paper and https://example.org/draft'})
        self.sync(client)
        row = build_site.inventory(self.root)['software'][0]
        self.assertEqual(row['publication_ids'], 'example-paper')
        self.assertEqual(row['working_paper_ids'], 'draft-paper')
        self.assertEqual(row['doi'], '')
        fields = [{'fields': {'nameofquantlet': 'An exact full research paper title', 'publishedin': 'Project shorthand'}}]
        papers = {'publications': [{'id': 'named-paper', 'title': 'An exact full research paper title'}], 'working_papers': []}
        self.assertEqual(quantlet.linked_papers(fields, papers)['publication_ids'], 'named-paper')

    def test_truncated_tree_is_walked_completely(self):
        client = FakeClient()
        with patch.object(client, 'get', side_effect=[{'truncated': True, 'tree': []},
             {'tree': [{'path': 'nested', 'type': 'tree', 'sha': 'nested-sha'}]},
             {'tree': [{'path': 'Metainfo.txt', 'type': 'blob'}]}]):
            entries = quantlet.tree_entries(client, 'QuantLet/Example', 'root-sha')
        self.assertEqual(entries[0]['path'], 'nested/Metainfo.txt')
        self.assertEqual(quantlet.tree_entries(client, 'QuantLet/Empty', '4b825dc642cb6eb9a060e54bf8d69288fbee4904'), [])

    def test_repository_key_deduplicates_case_trailing_slash_git_and_subdirectories(self):
        self.assertEqual(build_site.repository_key('https://github.com/QuantLet/Example.git/'), build_site.repository_key('https://github.com/quantlet/example/tree/main/subfolder'))


if __name__ == '__main__':
    unittest.main()
