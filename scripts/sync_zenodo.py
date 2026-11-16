#!/usr/bin/env python3
"""Sync public DIGITAL community software metadata; dry-run unless --write."""
import argparse
import csv
from datetime import date
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from build_site import ROOT, inventory, normalized_doi, paper_inventory, validate_url
from sync_quantlet import linked_papers
from directory import load as load_directory, match_creators

COMMUNITY = 'digitalfinance'
API = 'https://zenodo.org/api/records'
CACHE = 'zenodo-software.csv'
USER_AGENT = 'DigitalFinanceSoftware/1.0 (+https://github.com/MSCA-DN-Digital-Finance/Open_Software)'
PAGE_SIZE = 25  # Anonymous search limit; no Zenodo credentials needed.


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.hidden += 1
        if tag in {'p', 'div', 'br', 'li'}:
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {'p', 'div', 'li'}:
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def text(value):
    parser = PlainText()
    parser.feed(str(value or ''))
    return ' '.join(''.join(parser.parts).split())


def request_json(url):
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': USER_AGENT})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=45) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            retry_after = exc.headers.get('Retry-After', '')
            delay = float(retry_after) if retry_after.isdigit() else 3 * 2 ** attempt
            time.sleep(min(max(delay, 2.1), 60))
        except (URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(3 * 2 ** attempt)


def fetch_records():
    records, ids = [], set()
    expected = None
    for page in range(1, 1001):
        params = {'communities': COMMUNITY, 'type': 'software', 'status': 'published',
                  'all_versions': 'false', 'sort': 'mostrecent', 'size': PAGE_SIZE, 'page': page}
        payload = request_json(API + '?' + urlencode(params))
        hits = payload['hits']
        total = hits['total']
        if isinstance(total, dict):
            if total.get('relation', 'eq') != 'eq':
                raise ValueError('Zenodo returned an inexact total; refusing a partial sync')
            total = total['value']
        if type(total) is not int or total < 0 or not isinstance(hits['hits'], list):
            raise ValueError('Invalid Zenodo search response')
        if expected is not None and total != expected:
            raise ValueError('Community changed during pagination; rerun the sync')
        expected = total
        for record in hits['hits']:
            rid = str(record['id'])
            if rid in ids:
                raise ValueError('Duplicate record across pages; rerun the sync')
            ids.add(rid)
            metadata = record['metadata']
            if (COMMUNITY not in {c['id'] for c in metadata.get('communities', [])} or
                    metadata.get('resource_type', {}).get('type') != 'software' or
                    record.get('status') != 'published'):
                raise ValueError('Zenodo returned a record outside the requested software scope')
            records.append(record)
        if len(records) == expected:
            return records
        if not hits['hits'] or len(records) > expected:
            raise ValueError('Incomplete Zenodo search response; refusing a partial sync')
        time.sleep(2.1)  # Stay below the documented 30 search requests/minute.
    raise ValueError('Community exceeds the sync pagination limit')


def repository_url(metadata, archive):
    custom = metadata.get('custom') or {}
    value = custom.get('code:codeRepository')
    if value:
        if not isinstance(value, str) or not validate_url(value):
            raise ValueError('Invalid Zenodo code repository URL')
        return value
    for related in metadata.get('related_identifiers', []):
        url = related.get('identifier', '')
        if (related.get('scheme') == 'url' and related.get('resource_type') == 'software'
                and related.get('relation') in {'isSupplementTo', 'isIdenticalTo', 'isDerivedFrom'} and validate_url(url)):
            return url
    return archive


def paper_links(metadata, papers):
    # A software deposit's own DOI and software/data relations are never papers.
    values = []
    for related in metadata.get('related_identifiers', []):
        if related.get('resource_type', '').split('-')[0] != 'publication':
            continue
        if related.get('relation') not in {'isSupplementTo', 'isDocumentedBy', 'references', 'isDerivedFrom'}:
            continue
        value = related.get('identifier', '')
        if related.get('scheme') == 'doi':
            value = 'https://doi.org/' + normalized_doi(value)
        if validate_url(value):
            values.append(value)
    # Explicit DOI links in the description include preprints (e.g. SSRN).
    values += ['https://doi.org/' + doi.rstrip('.,;)') for doi in
               re.findall(r'\b10\.\d{4,9}/[^\s<>"\']+', metadata.get('description') or '')]
    own_dois = {normalized_doi(metadata.get(key) or '') for key in ['doi', 'conceptdoi']}
    values = [url for url in values if normalized_doi(url) not in own_dois]
    return linked_papers([{'fields': {'reference': '\n'.join(values)}}], papers)


def software(record, fields, projects, papers):
    metadata = record['metadata']
    if (metadata.get('resource_type', {}).get('type') != 'software' or record.get('status') != 'published'
            or COMMUNITY not in {c['id'] for c in metadata.get('communities', [])}):
        raise ValueError('Only published community software records can enter this feed')
    rid, concept = str(record['id']), str(record.get('conceptrecid') or record['id'])
    if not rid.isdigit() or not concept.isdigit():
        raise ValueError('Invalid Zenodo record/concept ID')
    published = str(metadata['publication_date'])
    if not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?', published):
        raise ValueError('Invalid software publication date')
    if len(published) == 10:
        date.fromisoformat(published)
    elif len(published) == 7:
        date.fromisoformat(published + '-01')
    modified = str(record.get('modified') or record.get('updated') or '')
    updated = modified[:10] if modified else published if len(published) == 10 else ''
    if updated:
        date.fromisoformat(updated)
    archive = f'https://zenodo.org/records/{rid}'
    custom = metadata.get('custom') or {}
    languages = []
    for language in custom.get('code:programmingLanguage', []):
        label = (language.get('title') or language.get('id', '')) if isinstance(language, dict) else language
        if isinstance(label, dict):
            label = label.get('en') or next(iter(label.values()), '')
        if label:
            languages.append(text(label).replace(';', ','))
    creators = metadata['creators']
    contributors = metadata.get('contributors', [])
    matched = match_creators(creators + contributors, projects)
    description = metadata.get('description') or ''
    paragraphs = [text(value) for value in re.findall(r'<p\b[^>]*>(.*?)</p>', description, re.I | re.S)]
    summary = next((value for value in paragraphs if value), text(description))
    row = {field: '' for field in fields}
    row.update(id='zenodo-' + concept, name=text(metadata['title']), repository_url=repository_url(metadata, archive),
               summary=' '.join(summary.split()[:60]) or 'Software archived in the Digital Finance Zenodo community. See the deposit for its description.',
               category='other', authors=';'.join(text(c['name']).replace(';', ',') for c in creators),
               contributors=';'.join(text(c['name']).replace(';', ',') for c in contributors),
               languages=';'.join(dict.fromkeys(languages)), irp_numbers=';'.join(p['number'] for p in matched),
               index='zenodo', index_url=archive, doi=normalized_doi(metadata.get('doi') or record.get('doi') or ''),
               license=text((metadata.get('license') or {}).get('id')), version=text(metadata.get('version')),
               data_availability='not-documented',
               data_notes='Input data availability is not established by a software deposit. Consult the source repository and Zenodo record for data files and access conditions.',
               documentation_url=archive, last_updated=updated,
               provenance=f'Zenodo community {COMMUNITY}: {archive}. Source metadata modified: {modified or "not supplied"}. ' +
                          'Candidate/IRP identities matched by ORCID or exact full creator/contributor name against the shared people dictionary. ' +
                          'Software purpose and input data access are not inferred from archive access rights.')
    row.update(paper_links({**metadata, 'doi': row['doi'], 'conceptdoi': record.get('conceptdoi') or metadata.get('conceptdoi', '')}, papers))
    return row


def sync_records(records, *, root=None, write=False):
    root = root or ROOT
    target = root / 'data' / CACHE
    with (root / 'data/software.csv').open(encoding='utf-8', newline='') as source:
        fields = csv.DictReader(source).fieldnames
    projects, papers = load_directory(root), paper_inventory(root)
    rows, concepts, dois = [], set(), set()
    ordered = sorted(records, key=lambda r: (str(r.get('modified') or r.get('updated') or ''), str(r['id'])), reverse=True)
    for record in ordered:
        row = software(record, fields, projects, papers)
        if row['id'] in concepts:
            raise ValueError('Multiple versions of one software concept returned; refusing ambiguous sync')
        concepts.add(row['id'])
        if row['doi'] and row['doi'] in dois:
            continue
        if row['doi']:
            dois.add(row['doi'])
        rows.append(row)
    rows.sort(key=lambda row: row['id'])
    with tempfile.TemporaryDirectory() as staging:
        staged = Path(staging)
        shutil.copytree(root / 'data', staged / 'data')
        path = staged / 'data' / CACHE
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
        combined = inventory(staged)
        content = path.read_bytes()
    changed = not target.exists() or target.read_bytes() != content
    if write and changed:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name); stream.write(content)
        try:
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    summary = (f'{"Synced" if write else "Dry run:"} {len(rows)} Zenodo software record(s); '
               f'{len(combined["software"])} combined catalogue record(s); {"changes found" if changed else "unchanged"}.')
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(summary + '\n\n')
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Replace the validated Zenodo software feed')
    args = parser.parse_args()
    try:
        sync_records(fetch_records(), write=args.write)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise SystemExit(f'Zenodo software sync failed; existing data was preserved: {exc}') from exc


if __name__ == '__main__':
    main()

