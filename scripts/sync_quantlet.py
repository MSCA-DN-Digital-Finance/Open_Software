#!/usr/bin/env python3
"""Incrementally index QuantLet repositories credited to known doctoral candidates.

Only public metadata is read. Repository code, notebooks, YAML and workflows are
never executed. Use --write to replace the validated feed and scan checkpoint.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
import copy
import csv
from datetime import date
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from build_site import ROOT, QUANTLET_DOI_PATTERN, inventory, normalized_doi, paper_inventory, split, validate_url
from directory import load as load_directory, name_key, orcid_id, write_json

OWNER = 'QuantLet'
QUANTLET_API = 'https://quantlet.com/api/cards/home'
# IRP 7 maintains QuantLet broadly; only an explicit full-name author credit
# establishes a research association for this candidate.
AUTHOR_LIST_ONLY_IRPS = {'7'}
FEED = 'quantlet-software.csv'
STATE = '.sync/quantlet-state.json'
USER_AGENT = 'DigitalFinanceQuantLetSync/1.0 (+https://github.com/MSCA-DN-Digital-Finance/Open_Software)'


class BudgetExhausted(Exception):
    pass


class GitHub:
    def __init__(self, budget=750):
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not token:
            result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True)
            if result.returncode:
                raise ValueError('Set GH_TOKEN or authenticate GitHub CLI; no token is written to the cache')
            token = result.stdout.strip()
        self.headers = {'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json',
                        'Authorization': 'Bearer ' + token, 'X-GitHub-Api-Version': '2022-11-28'}
        self.budget, self.requests = budget, 0
        self._lock = threading.Lock()
        self._profile_locks = {}
        self._raw_limit = threading.Semaphore(8)

    def profile_guard(self, login):
        with self._lock:
            return self._profile_locks.setdefault(login, threading.Lock())

    def get(self, path):
        for attempt in range(4):
            with self._lock:
                if self.requests >= self.budget:
                    raise BudgetExhausted('Configured API request budget reached')
                self.requests += 1
            try:
                request = Request('https://api.github.com/' + path.lstrip('/'), headers=self.headers)
                with urlopen(request, timeout=40) as response:
                    remaining = int(response.headers.get('X-RateLimit-Remaining', '1000'))
                    body = response.read()
                    if remaining < 40:
                        with self._lock:
                            self.budget = self.requests
                    return json.loads(body) if body else []
            except HTTPError as exc:
                if exc.code in {403, 429} and exc.headers.get('X-RateLimit-Remaining') == '0':
                    raise BudgetExhausted('GitHub API allowance exhausted; checkpoint will resume next run') from exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                    raise
                delay = exc.headers.get('Retry-After', '')
                time.sleep(min(int(delay) if delay.isdigit() else 2 ** (attempt + 1), 60))
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))

    def pages(self, path):
        rows = []
        for page in range(1, 10001):
            payload = self.get(path + ('&' if '?' in path else '?') + urlencode({'per_page': 100, 'page': page}))
            if not isinstance(payload, list):
                raise ValueError('Invalid GitHub list response')
            rows.extend(payload)
            if len(payload) < 100:
                return rows
        raise ValueError('GitHub pagination exceeded the safety bound')

    def repositories(self):
        expected = self.get(f'orgs/{OWNER}')['public_repos']
        rows = self.pages(f'orgs/{OWNER}/repos?type=public&sort=full_name')
        ids = [row['id'] for row in rows]
        if not rows or len(rows) != expected or len(ids) != len(set(ids)) or any(row.get('private') or row['owner']['login'].casefold() != OWNER.casefold() for row in rows):
            raise ValueError('Incomplete, duplicate or out-of-scope repository list')
        return rows

    def metadata(self, repository, commit, path):
        # Public raw requests use immutable commit IDs and never receive the API token.
        url = f'https://raw.githubusercontent.com/{repository}/{commit}/' + quote(path, safe='/')
        for attempt in range(4):
            try:
                with self._raw_limit:
                    with urlopen(Request(url, headers={'User-Agent': USER_AGENT}), timeout=40) as response:
                        body = response.read(1024 * 1024 + 1)
                if len(body) > 1024 * 1024:
                    raise ValueError(f'Oversized Metainfo file: {repository}/{path}')
                try:
                    return body.decode('utf-8-sig')
                except UnicodeDecodeError:
                    return body.decode('cp1252', errors='replace')
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))


def field_key(value):
    return re.sub(r'[^a-z]', '', value.casefold())


def parse_metainfo(content):
    """Read the plain field/list/block subset; deliberately do not evaluate YAML."""
    fields, current = {}, None
    pattern = r'^([ \t]*)([A-Za-z][A-Za-z0-9 _()/.-]*):\s*(.*)$'
    candidates = [re.match(pattern, line) for line in content.splitlines()]
    indentation = min((len(match[1].expandtabs()) for match in candidates if match), default=0)
    for line in content.replace('\r\n', '\n').splitlines():
        if not line.strip() or line.lstrip().startswith('#') or line.strip() == '---':
            continue
        match = re.match(pattern, line)
        if match and len(match[1].expandtabs()) == indentation:
            current = field_key(match[2])
            fields.setdefault(current, [])
            value = match[3].strip()
            if value not in {'', '|', '>', '|-', '>-'}:
                fields[current].append(value.strip('\"\''))
        elif current:
            fields[current].append(re.sub(r'^\s*-\s*', '', line).strip().strip('\"\''))
    result = {key: '\n'.join(parts).strip() for key, parts in fields.items()}
    # Keep only the fields required for matching and catalogue metadata.
    selected = {key: result[key] for key in ['nameofquantlet', 'name', 'author', 'authors', 'contributors', 'contributor',
                'publishedin', 'publication', 'paper', 'reference', 'datafile', 'softwaredoi'] if key in result}
    selected['description'] = ' '.join(result.get('description', '').split()[:20])
    if 'datafile' in selected:
        selected['datafile'] = ' '.join(selected['datafile'].split()[:20])
    return selected


def fingerprint(repo):
    return {key: repo.get(key) for key in ['id', 'full_name', 'pushed_at', 'default_branch', 'description', 'language', 'license', 'archived']}


def quantlet_repository(url):
    if not isinstance(url, str):
        return ''
    try:
        parsed = urlsplit(url)
        parts = parsed.path.strip('/').split('/')
        if (parsed.scheme in {'http', 'https'} and parsed.hostname in {'github.com', 'www.github.com'}
                and not parsed.username and len(parts) >= 2 and parts[0].casefold() == OWNER.casefold()
                and re.fullmatch(r'[A-Za-z0-9_.-]+', parts[1])):
            return '/'.join(parts[:2]).casefold()
    except ValueError:
        pass
    return ''


def fetch_quantlet_dois():
    request = Request(QUANTLET_API, headers={'Accept': 'application/json', 'User-Agent': USER_AGENT})
    with urlopen(request, timeout=30) as response:
        cards = json.load(response)
    if not isinstance(cards, list) or any(not isinstance(card, dict) or not {'parent_folder_url', 'doi'} <= card.keys() for card in cards):
        raise ValueError('Unexpected QuantLet cards response')
    by_repo = {}
    for card in cards:
        repo = quantlet_repository(card['parent_folder_url'])
        doi = normalized_doi(card['doi']) if isinstance(card['doi'], str) else ''
        if repo and QUANTLET_DOI_PATTERN.fullmatch(doi):
            by_repo.setdefault(repo, set()).add(doi)
    if not by_repo:
        raise ValueError('QuantLet returned no repository DOIs')
    return {repo: ';'.join(sorted(dois)) for repo, dois in by_repo.items()}


def cached_quantlet_dois(root):
    path = root / 'data' / FEED
    if not path.exists():
        return {}
    with path.open(encoding='utf-8-sig', newline='') as source:
        return {quantlet_repository(row['repository_url']): row.get('quantlet_dois', '') for row in csv.DictReader(source)}


def tree_entries(client, full_name, sha):
    # GitHub returns 404 for the canonical empty Git tree, even when the commit
    # exists. An empty tree contains no Metainfo files and is a complete result.
    if sha == '4b825dc642cb6eb9a060e54bf8d69288fbee4904':
        return []
    tree = client.get(f'repos/{full_name}/git/trees/{sha}?recursive=1')
    if not isinstance(tree.get('tree'), list):
        raise ValueError(f'{full_name}: invalid tree')
    if not tree.get('truncated'):
        return tree['tree']
    # Large trees must be walked in full rather than silently dropping metadata.
    entries, pending = [], [('', sha)]
    while pending:
        prefix, tree_sha = pending.pop()
        payload = client.get(f'repos/{full_name}/git/trees/{tree_sha}')
        if payload.get('truncated') or not isinstance(payload.get('tree'), list):
            raise ValueError(f'{full_name}: incomplete tree')
        for entry in payload['tree']:
            path = prefix + entry['path']
            if entry['type'] == 'tree':
                pending.append((path + '/', entry['sha']))
            else:
                entries.append({**entry, 'path': path})
    return entries


def user_profile(client, login, users):
    guard = client.profile_guard(login) if hasattr(client, 'profile_guard') else nullcontext()
    with guard:
        return _user_profile(client, login, users)


def _user_profile(client, login, users):
    if login in users and (date.today() - date.fromisoformat(users[login]['checked_on'])).days < 30:
        return users[login]
    profile = client.get('users/' + quote(login, safe=''))
    text = ' '.join(str(profile.get(key) or '') for key in ['name', 'blog', 'bio'])
    orcids = set(re.findall(r'(?:orcid\.org/)(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])', text))
    result = {'login': profile['login'], 'name': profile.get('name') or '', 'type': profile.get('type'),
              'orcid': orcid_id(next(iter(orcids))) if len(orcids) == 1 else '', 'checked_on': date.today().isoformat()}
    users[login] = result
    return result


def scan_repository(client, repo, users):
    full_name = repo['full_name']
    try:
        branch = client.get(f'repos/{full_name}/branches/' + quote(repo['default_branch'], safe=''))
    except HTTPError as exc:
        if repo.get('size') == 0 and exc.code in {404, 409}:
            return {'fingerprint': fingerprint(repo), 'commit': '', 'metainfo': [], 'contributors': [], 'scanned_on': date.today().isoformat()}
        raise
    commit = branch['commit']['sha']
    entries = tree_entries(client, full_name, branch['commit']['commit']['tree']['sha'])
    paths = sorted(entry['path'] for entry in entries if entry['type'] == 'blob' and PurePosixPath(entry['path']).name.casefold() == 'metainfo.txt')
    with ThreadPoolExecutor(max_workers=6) as executor:
        metadata = list(executor.map(lambda path: {'path': path, 'fields': parse_metainfo(client.metadata(full_name, commit, path))}, paths))
    contributors = []
    for account in client.pages(f'repos/{full_name}/contributors?anon=false'):
        if account.get('type') != 'User' or not account.get('login'):
            continue
        login = account['login']
        if not re.fullmatch(r'[a-zA-Z0-9-]+', login):
            raise ValueError('Unexpected GitHub contributor login')
        user_profile(client, login, users)
        contributors.append(login)
    return {'fingerprint': fingerprint(repo), 'commit': commit, 'metainfo': metadata,
            'contributors': sorted(set(contributors)), 'scanned_on': date.today().isoformat()}


def identities(root, projects):
    result = []
    for project in projects:
        candidate = project.get('candidate')
        if not candidate:
            continue
        handles = []
        for url in candidate.get('links', {}).values():
            match = re.fullmatch(r'https?://(?:www\.)?github\.com/([A-Za-z0-9-]+)/?', url)
            if match:
                handles.append(match[1].casefold())
        result.append({'number': project['number'], 'name': candidate['name'], 'names': [candidate['name']],
                       'orcid': candidate.get('orcid', ''), 'logins': handles, 'candidate_id': candidate['id']})
    path = root / 'data/quantlet-identities.json'
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema_version') != 1 or not isinstance(data.get('identities'), list):
            raise ValueError('Invalid QuantLet identity configuration')
        by_id = {identity['candidate_id']: identity for identity in result}
        for alias in data['identities']:
            identity = by_id.get(alias.get('candidate_id'))
            if not identity or not validate_url(alias.get('source_url', '')):
                raise ValueError('Every identity alias needs a known candidate and a public verification source')
            names, logins = alias.get('names', []), alias.get('github_logins', [])
            if not isinstance(names, list) or any(not isinstance(name, str) or len(name_key(name)) < 2 for name in names):
                raise ValueError('Identity aliases must contain full names')
            if not isinstance(logins, list) or any(not isinstance(login, str) or not re.fullmatch(r'[A-Za-z0-9-]+', login) for login in logins):
                raise ValueError('Invalid verified GitHub handle')
            identity['names'] += names
            identity['logins'] += [login.casefold() for login in logins]
    logins = {}
    for identity in result:
        for login in identity['logins']:
            if login in logins and logins[login] != identity['candidate_id']:
                raise ValueError('A GitHub account cannot identify two candidates')
            logins[login] = identity['candidate_id']
    return result


def name_matches(value, known):
    # Delimited full names, including YAML lists, natural-order comma lists and
    # family-name/given-name pairs. No initials, substrings or fuzzy matching.
    for item in re.split(r'[;\n]|\s+(?:and|&)\s+', value, flags=re.I):
        item = re.sub(r'https?://orcid\.org/\S+', '', item)
        chunks = [part.strip(' \t\"\'[]()') for part in item.split(',')]
        possibilities = chunks + [chunks[i] + ' ' + chunks[i + 1] for i in range(len(chunks) - 1)]
        if any(name_key(candidate) == name_key(name) for candidate in possibilities for name in known):
            return True
    return False


def matches(snapshot, users, known):
    found = {}
    for meta in snapshot['metainfo']:
        fields = meta['fields']
        for field in ['author', 'authors', 'contributor', 'contributors']:
            for identity in known:
                credited = fields.get(field, '')
                if identity['number'] in AUTHOR_LIST_ONLY_IRPS:
                    if field in {'author', 'authors'} and name_matches(credited, identity['names']):
                        found.setdefault(identity['number'], []).append(f'Metainfo {field}: {meta["path"]}')
                    continue
                orcids = {value.upper() for value in re.findall(r'(?<!\d)(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])(?!\d)', credited)}
                handles = {login.casefold() for login in re.findall(r'(?<![\w-])@([A-Za-z0-9-]+)', credited)}
                handles.update(login.casefold() for login in re.findall(r'https?://github\.com/([A-Za-z0-9-]+)(?=[/\s,;\])]|$)', credited, re.I))
                handles.update(part.strip(' \t\"\'[]()').casefold() for part in re.split(r'[;,\n]|\s+(?:and|&)\s+', credited, flags=re.I)
                               if re.fullmatch(r'[A-Za-z0-9-]+', part.strip(' \t\"\'[]()')))
                if (name_matches(credited, identity['names']) or (identity['orcid'] and identity['orcid'] in orcids)
                        or handles.intersection(identity['logins'])):
                    found.setdefault(identity['number'], []).append(f'Metainfo {field}: {meta["path"]}')
    for login in snapshot['contributors']:
        profile = users[login]
        candidates = [identity for identity in known if login.casefold() in identity['logins']]
        if not candidates:
            candidates = [identity for identity in known if
                          (identity['orcid'] and identity['orcid'] == profile.get('orcid')) or name_matches(profile['name'], identity['names'])]
            candidates = [identity for identity in candidates if not (identity['orcid'] and profile.get('orcid') and
                          identity['orcid'] != profile['orcid'])]
        if len(candidates) == 1 and candidates[0]['number'] not in AUTHOR_LIST_ONLY_IRPS:
            found.setdefault(candidates[0]['number'], []).append('GitHub contributor: ' + login)
    # A shared author-name alias must not assign two different people.
    ambiguous = {name_key(name) for identity in known for name in identity['names']
                 if sum(name_key(name) in [name_key(n) for n in other['names']] for other in known) > 1}
    if ambiguous:
        raise ValueError('Ambiguous names in the candidate identity configuration')
    return found


def title_key(value):
    return ' '.join(re.findall(r'[^\W_]+', value.casefold()))


def linked_papers(metadata, papers):
    texts = [meta['fields'].get(key, '') for meta in metadata for key in ['publishedin', 'publication', 'paper', 'reference']]
    title_texts = texts + [meta['fields'].get('nameofquantlet', '') for meta in metadata
                           if len(title_key(meta['fields'].get('nameofquantlet', '')).split()) >= 5]
    urls = set()
    for text in texts:
        for url in re.findall(r'https?://[^\s<>\"\']+', text):
            url = url.rstrip('.,;)')
            if validate_url(url):
                urls.add(url)
        for doi in re.findall(r'\b10\.\d{4,9}/[^\s<>\"\']+', text):
            urls.add('https://doi.org/' + doi.rstrip('.,;)'))
    result = {'publication_ids': [], 'working_paper_ids': [], 'paper_urls': []}
    used = set()
    for kind, field in [('publications', 'publication_ids'), ('working_papers', 'working_paper_ids')]:
        for paper in papers[kind]:
            doi_url = 'https://doi.org/' + normalized_doi(paper.get('doi', '')) if paper.get('doi') else ''
            paper_urls = {value for value in [paper.get('link'), doi_url, paper.get('preprint_url')] if value}
            if any(title_key(text) == title_key(paper['title']) for text in title_texts if text) or any(url.casefold() in {p.casefold() for p in paper_urls} for url in urls):
                result[field].append(paper['id']); used |= paper_urls
    result['paper_urls'] = sorted(url for url in urls if url.casefold() not in {value.casefold() for value in used})
    return {key: ';'.join(values) for key, values in result.items()}


def record(repo, snapshot, users, evidence, fields, papers):
    row = {field: '' for field in fields}
    metadata = snapshot['metainfo']
    primary = next((meta for meta in metadata if '/' not in meta['path']), metadata[0] if metadata else {'fields': {}, 'path': ''})
    full_name = repo['full_name']
    source = f'https://github.com/{full_name}'
    author_values = list(dict.fromkeys(meta['fields'].get('author') or meta['fields'].get('authors') for meta in metadata))
    authors = ';'.join(' '.join(value.split()) for value in author_values if value)
    names = ';'.join((users[login]['name'] + ' (@' + login + ')') if users[login]['name'] else '@' + login for login in snapshot['contributors'])
    description = primary['fields'].get('description') or ' '.join((repo.get('description') or '').split()[:20])
    reference = primary['fields'].get('publishedin', '')
    details = '; '.join(f'IRP {number}: ' + ', '.join(sorted(set(reasons))) for number, reasons in sorted(evidence.items(), key=lambda item: int(item[0])))
    name = (primary['fields'].get('nameofquantlet') or primary['fields'].get('name')) if '/' not in primary['path'] else ''
    row.update(id='quantlet-' + str(repo['id']), name=name or repo['name'],
               repository_url=source, summary=description or f'QuantLet repository associated with {len(evidence)} network IRP(s). See its source metadata for a description.',
               category='quantlet', authors=authors, contributors=names, languages=repo.get('language') or '',
               irp_numbers=';'.join(sorted(evidence, key=int)), index='quantlet', index_url=source,
               license=(repo.get('license') or {}).get('spdx_id') or '', data_availability='not-documented',
               data_notes='Data availability and access conditions have not been independently verified. Consult the repository and its Metainfo files.',
               documentation_url=source + '/blob/' + snapshot['commit'] + '/' + quote(primary['path'], safe='/') if primary['path'] else source,
               repository_created_at=(repo.get('created_at') or '')[:10],
               last_updated=(repo.get('pushed_at') or '')[:10],
               provenance=f'Imported from {source} at commit {snapshot["commit"]}. Matched by {details}. ' +
                          (f'Source Published in: {reference}. ' if reference else '') +
                          'Identities are matched against the shared IRP directory; no authorship, paper status or data access is inferred from repository topics.')
    row.update(linked_papers(metadata, papers))
    if row['license'] in {'NOASSERTION', 'NONE'}:
        row['license'] = ''
    if primary['fields'].get('datafile'):
        row['data_notes'] = 'Source Datafile field: ' + primary['fields']['datafile'] + '. Access conditions have not been independently verified; consult the repository.'
    explicit_dois = {normalized_doi(meta['fields']['softwaredoi']) for meta in metadata if meta['fields'].get('softwaredoi')}
    if len(explicit_dois) == 1:
        doi = next(iter(explicit_dois))
        if re.fullmatch(r'10\.\d{4,9}/\S+', doi):
            row['doi'] = doi
    return row


def sync(client, *, root=None, write=False, max_repositories=100, doi_loader=fetch_quantlet_dois):
    root = root or ROOT
    state_path = root / STATE
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {'schema_version': 1, 'repositories': {}, 'users': {}}
    if state.get('schema_version') != 1 or not isinstance(state.get('repositories'), dict) or not isinstance(state.get('users'), dict):
        raise ValueError('Invalid QuantLet scan checkpoint')
    state = copy.deepcopy(state)
    repos = client.repositories()  # Complete discovery is required before pruning.
    known = identities(root, load_directory(root))
    current = {str(repo['id']): repo for repo in repos}
    state['repositories'] = {rid: snapshot for rid, snapshot in state['repositories'].items() if rid in current}
    pending = [repo for repo in repos if str(repo['id']) not in state['repositories'] or state['repositories'][str(repo['id'])]['fingerprint'] != fingerprint(repo)]
    pending.sort(key=lambda repo: (state['repositories'].get(str(repo['id']), {}).get('scanned_on', ''), repo['full_name'].casefold()))
    completed, errors = 0, []
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(scan_repository, client, repo, state['users']): repo for repo in pending[:max_repositories]}
            for future in as_completed(futures):
                try:
                    snapshot = future.result()
                except BudgetExhausted:
                    continue
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    failed = futures[future]['full_name']
                    errors.append({'repository': failed, 'error': str(exc)})
                    print(f'Retaining previous snapshot for {failed}: {exc}', flush=True)
                    continue
                except BaseException:
                    for other in futures:
                        other.cancel()
                    raise
                state['repositories'][str(futures[future]['id'])] = snapshot
                completed += 1
                if completed % 25 == 0:
                    print(f'Scanned {completed}/{len(pending)} changed repositories; {client.requests} API requests', flush=True)
        for snapshot in state['repositories'].values():
            for login in snapshot['contributors']:
                user_profile(client, login, state['users'])
    except BudgetExhausted as exc:
        print(str(exc), flush=True)
    with (root / 'data/software.csv').open(encoding='utf-8', newline='') as source:
        fields = csv.DictReader(source).fieldnames
    try:
        dois = doi_loader()
    except (OSError, ValueError) as exc:
        print(f'QuantLet DOI API unavailable; retaining previously imported DOIs: {exc}', flush=True)
        dois = cached_quantlet_dois(root)
    papers = paper_inventory(root)
    rows, reports = [], []
    for rid, snapshot in sorted(state['repositories'].items(), key=lambda item: int(item[0])):
        evidence = matches(snapshot, state['users'], known)
        if evidence:
            verified_repo = {**current[rid], **snapshot['fingerprint']}
            verified_repo['name'] = verified_repo['full_name'].rsplit('/', 1)[-1]
            row = record(verified_repo, snapshot, state['users'], evidence, fields, papers)
            row['quantlet_dois'] = dois.get(verified_repo['full_name'].casefold(), '')
            rows.append(row)
            reports.append({'repository': current[rid]['full_name'], 'irps': sorted(evidence, key=int), 'evidence': evidence})
    remaining = len(pending) - completed
    stale_profiles = sum((date.today() - date.fromisoformat(profile['checked_on'])).days >= 30 for profile in state['users'].values())
    report = {'repositories_discovered': len(repos), 'repositories_cached': len(state['repositories']), 'repositories_pending': remaining,
              'repositories_scanned_this_run': completed, 'profiles_pending_refresh': stale_profiles, 'matched_repositories': len(rows), 'api_requests': client.requests, 'matches': reports, 'errors': errors}
    state['pending'] = remaining
    state['repositories'] = dict(sorted(state['repositories'].items(), key=lambda item: int(item[0])))
    state['users'] = dict(sorted(state['users'].items()))
    with tempfile.TemporaryDirectory() as staging:
        staged = Path(staging)
        shutil.copytree(root / 'data', staged / 'data')
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
        content = output.getvalue().encode('utf-8')
        (staged / 'data' / FEED).write_bytes(content)
        combined = inventory(staged)
    if write:
        path = root / 'data' / FEED
        if not path.exists() or path.read_bytes() != content:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                stream.write(content); temporary = Path(stream.name)
            try:
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        write_json(state_path, state)
    summary = (f'QuantLet: {len(repos)} discovered; {completed} scanned; {remaining} pending; '
               f'{len(rows)} matched; {stale_profiles} profile refreshes pending; {len(combined["software"])} combined software records; {client.requests} API requests.')
    print(summary, flush=True)
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        with open(summary_path, 'a', encoding='utf-8') as stream:
            stream.write(summary + '\n\n')
            if remaining:
                stream.write('The scan is incomplete. Previously indexed repositories are retained; rerun or wait for the next daily sync to resume.\n\n')
            for item in reports:
                stream.write(f'- {item["repository"]}: IRP {", ".join(item["irps"])}\n')
            for error in errors:
                stream.write(f'- Pending source retry: {error["repository"]}: {error["error"]}\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--request-budget', type=int, default=750)
    parser.add_argument('--max-repositories', type=int, default=100)
    args = parser.parse_args()
    if args.request_budget < 20 or args.max_repositories < 1:
        parser.error('Use a request budget of at least 20 and a positive repository limit')
    try:
        sync(GitHub(args.request_budget), write=args.write, max_repositories=args.max_repositories)
    except (ValueError, KeyError, TypeError, OSError, BudgetExhausted) as exc:
        raise SystemExit(f'QuantLet sync failed; no repository changes have been committed: {exc}') from exc


if __name__ == '__main__':
    main()
