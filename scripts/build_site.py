#!/usr/bin/env python3
"""Validate the software catalogue and build its GitHub Pages site."""
import csv
from datetime import date
import html
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote, urlsplit

from directory import enrich, load as load_directory

ROOT = Path(__file__).resolve().parents[1]
FILES = {'software': 'software.csv'}
CATEGORIES = {'paper-replication': 'Paper replication software', 'data-collection': 'Data collection software',
              'package-release': 'Package / release', 'application': 'Application', 'quantlet': 'QuantLet', 'other': 'Other'}
AVAILABILITY = {'public': 'Public data', 'on-request': 'Data on request', 'restricted': 'Restricted data',
                'not-required': 'No external data required', 'not-documented': 'Data availability not documented'}
INDICES = {'not-indexed': 'Not indexed', 'zenodo': 'Zenodo', 'quantlet': 'QuantLet', 'other': 'Other index'}
QUANTLET_DOI_PATTERN = re.compile(r'10\.\d{4,9}/[^\s;]+')


def split(value):
    return [part.strip() for part in (value or '').split(';') if part.strip()]


def normalized_doi(value):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', value.strip(), flags=re.I).lower()


def validate_url(value):
    parsed = urlsplit(value)
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc) and not parsed.username and not parsed.password and not any(c.isspace() for c in value)


def paper_inventory(root=None):
    data = json.loads(((root or ROOT) / 'data/papers.json').read_text(encoding='utf-8'))
    for kind in ['publications', 'working_papers']:
        if not isinstance(data.get(kind), list):
            raise ValueError(f'Invalid paper dictionary: {kind} must be a list')
        ids = set()
        for row in data[kind]:
            if not isinstance(row, dict) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', row.get('id', '')) or not row.get('title') or row['id'] in ids:
                raise ValueError('Invalid or duplicate paper in dictionary')
            ids.add(row['id'])
    return data


def read_records(root=None, *, quantlet=False, feed=None):
    root = root or ROOT
    papers = paper_inventory(root)
    projects = load_directory(root)
    known_irps = {p['number'] for p in projects}
    imported = quantlet or feed is not None
    filename = feed or ('quantlet-software.csv' if quantlet else 'software.csv')
    with (root / 'data' / filename).open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError('Missing or duplicate software CSV columns')
        rows = list(reader)
    ids, dois = set(), set()
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f'software.csv:{line}: malformed CSV row')
        row.update({key: value.strip() for key, value in row.items()})
        required = ['id', 'name', 'repository_url', 'summary', 'category', 'data_availability', 'data_notes', 'index']
        if not imported:
            required += ['authors', 'languages', 'irp_numbers']
        for field in required:
            if not row.get(field):
                raise ValueError(f'software.csv:{line}: {field} is required')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', row['id']) or row['id'] in ids:
            raise ValueError('Invalid or duplicate software ID')
        ids.add(row['id'])
        if row['category'] not in CATEGORIES or row['data_availability'] not in AVAILABILITY or row['index'] not in INDICES:
            raise ValueError('Invalid category, data availability or index')
        numbers = split(row['irp_numbers'])
        if (row['irp_numbers'] and not re.fullmatch(r'[1-9]\d*(?:;[1-9]\d*)*', row['irp_numbers'])) or len(numbers) != len(set(numbers)) or set(numbers) - known_irps:
            raise ValueError('IRPs must be known, distinct numbers separated by semicolons')
        for field, value in row.items():
            if field.endswith('_url') and value and not validate_url(value):
                raise ValueError(f'{field} must be a public HTTP(S) URL')
        if not imported and not (split(row.get('publication_ids')) or split(row.get('working_paper_ids')) or split(row.get('paper_urls'))):
            raise ValueError('Link at least one published paper, working paper or external paper URL')
        for field, kind in [('publication_ids', 'publications'), ('working_paper_ids', 'working_papers')]:
            unknown = set(split(row.get(field))) - {p['id'] for p in papers[kind]}
            if unknown:
                raise ValueError(f'Unknown {field}: {sorted(unknown)}')
        if any(not validate_url(url) for url in split(row.get('paper_urls'))):
            raise ValueError('External paper links must be public HTTP(S) URLs')
        if row.get('paper_titles') and len(split(row['paper_titles'])) != len(split(row.get('paper_urls'))):
            raise ValueError('Supply one external paper title for each external paper URL')
        if row['index'] == 'not-indexed' and (row.get('index_url') or row.get('doi')):
            raise ValueError('Choose an index when supplying an index URL or software DOI')
        if row['index'] != 'not-indexed' and not row.get('index_url'):
            raise ValueError('Indexed software requires an index URL; DOI is optional')
        if row.get('doi'):
            row['doi'] = normalized_doi(row['doi'])
            if not re.fullmatch(r'10\.\d{4,9}/\S+', row['doi']) or row['doi'] in dois:
                raise ValueError('Invalid or duplicate software DOI')
            dois.add(row['doi'])
        quantlet_dois = [normalized_doi(doi) for doi in split(row.get('quantlet_dois'))]
        if any(not QUANTLET_DOI_PATTERN.fullmatch(doi) for doi in quantlet_dois):
            raise ValueError('Invalid QuantLet DOI')
        row['quantlet_dois'] = ';'.join(dict.fromkeys(quantlet_dois))
        created_at = row.setdefault('repository_created_at', '')
        if created_at:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', created_at):
                raise ValueError('Repository creation date must be YYYY-MM-DD')
            date.fromisoformat(created_at)
        if row.get('key_image_url') and not row.get('key_image_alt'):
            raise ValueError('An image needs descriptive alt text')
        if not row.get('key_image_url') and (row.get('key_image_alt') or row.get('key_image_caption')):
            raise ValueError('Image text requires an image URL')
        if row.get('key_image_url') and not re.search(r'\.(?:png|jpe?g|gif|webp)$', urlsplit(row['key_image_url']).path, re.I):
            raise ValueError('Use a direct PNG, JPEG, GIF or WebP image URL')
        if row.get('last_updated'):
            date.fromisoformat(row['last_updated'])
    return rows


def repository_key(url):
    parsed = urlsplit(url)
    path = parsed.path.rstrip('/')
    if parsed.hostname and parsed.hostname.lower() in {'github.com', 'www.github.com'}:
        parts = path.split('/')
        if len(parts) > 2 and parts[1].casefold() == 'quantlet':
            path = '/'.join(parts[:3])  # QuantLet entries index a whole repository.
        elif len(parts) >= 5 and parts[3] in {'tree', 'blob', 'releases'}:
            # Retain distinct software projects in a shared repository, but not
            # the release/commit that changes between Zenodo versions.
            path = '/'.join(parts[:3] + parts[5:])
    return ((parsed.hostname or '').lower(), re.sub(r'\.git$', '', path, flags=re.I).lower())


def merge_imports(existing, incoming):
    """Combine matching automated sources while keeping the QuantLet record ID."""
    merged = {key: existing.get(key) or value for key, value in incoming.items()}
    for field in ['authors', 'contributors', 'languages', 'irp_numbers', 'publication_ids', 'working_paper_ids']:
        merged[field] = ';'.join(dict.fromkeys(split(existing.get(field)) + split(incoming.get(field))))
    titles = {}
    for row in [existing, incoming]:
        labels = split(row.get('paper_titles'))
        for i, url in enumerate(split(row.get('paper_urls'))):
            titles.setdefault(url, labels[i] if labels else url)
    merged['paper_urls'] = ';'.join(titles)
    merged['paper_titles'] = ';'.join(titles.values())
    if incoming['index'] == 'zenodo':
        for field in ['index', 'index_url', 'doi', 'version']:
            merged[field] = incoming.get(field) or merged.get(field, '')
    merged['last_updated'] = max(existing.get('last_updated', ''), incoming.get('last_updated', ''))
    merged['provenance'] = existing.get('provenance', '') + ' ' + incoming.get('provenance', '')
    return merged


def inventory(root=None):
    root = root or ROOT
    curated = read_records(root)
    combined = list(curated)
    for feed in ['quantlet-software.csv', 'zenodo-software.csv']:
        if not (root / 'data' / feed).exists():
            continue
        for row in read_records(root, feed=feed):
            matches = [i for i, old in enumerate(combined) if old['id'] == row['id'] or
                       repository_key(old['repository_url']) == repository_key(row['repository_url']) or
                       (row.get('doi') and old.get('doi') and normalized_doi(old['doi']) == normalized_doi(row['doi']))]
            if len(matches) > 1:
                raise ValueError('Software sources identify conflicting duplicate records; review their repository URLs and DOIs')
            if not matches:
                combined.append(row)
            elif matches[0] >= len(curated):
                combined[matches[0]] = merge_imports(combined[matches[0]], row)
            elif feed == 'quantlet-software.csv':
                existing = combined[matches[0]]
                if repository_key(existing['repository_url']) == repository_key(row['repository_url']):
                    existing['quantlet_dois'] = row['quantlet_dois']
                    existing['repository_created_at'] = row['repository_created_at'] or existing['repository_created_at']
    return {'software': combined}


def e(value):
    return html.escape(str(value or ''), quote=True)


def render_record(row, papers):
    def link(url, label, css=''):
        return f'<a class="{css}" href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(label)} ↗</a>' if url else ''
    def fact(label, value):
        return f'<div><dt>{e(label)}</dt><dd>{e(value) if value else "Not documented"}</dd></div>'
    related = []
    for field, kind, path, route in [('publication_ids', 'publications', '/Publications/', 'publication'),
                                      ('working_paper_ids', 'working_papers', '/Publications/working-papers.html', 'working-paper')]:
        by_id = {p['id']: p for p in papers[kind]}
        related += [f'<li><a href="{path}#{route}/{rid}">{e(by_id[rid]["title"])}</a></li>' for rid in split(row.get(field))]
    external_titles = split(row.get('paper_titles'))
    related += ['<li>' + link(url, external_titles[i] if external_titles else 'External paper · ' + urlsplit(url).netloc) + '</li>'
                for i, url in enumerate(split(row.get('paper_urls')))]
    research = '<ul>' + ''.join(related) + '</ul>' if related else '<p class="muted">Paper link not yet documented. See the source metadata for its research context.</p>'
    tags = ''.join('<span class="tag">' + e(language) + '</span>' for language in split(row['languages']))
    irps = ''.join(f'<a class="irp-pill" href="/irps/irp-{number}.html">IRP {number}</a>' for number in split(row['irp_numbers']))
    irps = irps or '<span class="tag">IRP not assigned</span>'
    image = f'<figure class="software-figure"><img src="{e(row["key_image_url"])}" alt="{e(row["key_image_alt"])}" loading="lazy" decoding="async" referrerpolicy="no-referrer"><figcaption>{e(row.get("key_image_caption"))}</figcaption></figure>' if row.get('key_image_url') else ''
    facts = ''.join(fact(label, row.get(field)) for label, field in [('Authors', 'authors'), ('Contributors', 'contributors'),
        ('Doctoral candidates', 'researcher_names'), ('Research projects', 'irp_titles'), ('Languages', 'languages'),
        ('Software licence', 'license'), ('Version / release', 'version'), ('Last metadata update', 'last_updated')])
    source_label = 'Software archive' if urlsplit(row['repository_url']).hostname == 'zenodo.org' else 'Source repository'
    links = link(row['repository_url'], source_label, 'button small') + link(row.get('documentation_url'), 'Documentation') + link(row.get('index_url'), INDICES[row['index']])
    if row.get('doi'):
        links += link('https://doi.org/' + row['doi'], 'DOI: ' + row['doi'])
    date_html = ''
    if row.get('repository_created_at'):
        created = e(row['repository_created_at'])
        date_html = f'<span class="software-created">Repository created <time datetime="{created}">{created}</time></span>'
    quantlet_dois = split(row.get('quantlet_dois'))
    quantlet_html = ''
    if quantlet_dois:
        doi_links = [link('https://doi.org/' + quote(doi, safe='/'), doi) for doi in quantlet_dois]
        if len(doi_links) == 1:
            quantlet_html = f'<p class="quantlet-citations">QuantLet DOI {doi_links[0]}</p>'
        else:
            items = ''.join(f'<li>{item}</li>' for item in doi_links)
            quantlet_html = f'<details class="quantlet-citations"><summary>{len(doi_links)} QuantLet DOIs</summary><ul>{items}</ul></details>'
    data = '<section class="software-data"><h3>Data availability</h3><strong>' + e(AVAILABILITY[row['data_availability']]) + '</strong><p>' + e(row['data_notes']) + '</p>' + link(row.get('data_url'), 'Data location / access instructions') + '</section>'
    return f'''<article class="software-card" data-record-id="{row['id']}" id="software-{row['id']}"><div class="entry-top"><span class="entry-type">{e(CATEGORIES[row['category']])}</span>{irps}{date_html}</div><h2><a href="{e(row['repository_url'])}" target="_blank" rel="noopener noreferrer">{e(row['name'])} ↗</a></h2><p class="software-authors">{e('; '.join(split(row['authors']))) or 'Authors not documented in source metadata'}</p><p>{e(row['summary'])}</p><div class="tags">{tags}</div>{quantlet_html}{image}<section class="software-papers"><h3>Linked research</h3>{research}</section><details class="software-details"><summary>Software details & data access</summary><dl class="detail-grid">{facts}{fact('Index', INDICES[row['index']])}{fact('Software DOI', row.get('doi'))}</dl>{data}<div class="software-links">{links}</div><p class="provenance">{e(row.get('provenance'))}</p></details><div class="software-actions"><a href="contribute.html?id={row['id']}">Suggest an update ↗</a><button class="text-button" data-copy="software/{row['id']}">Copy record link</button></div></article>'''


def build():
    data = inventory()
    people = load_directory(ROOT)
    data['software'] = [enrich(row, people) for row in data['software']]
    papers = paper_inventory()
    config = json.loads((ROOT / 'site/config.json').read_text())
    out = ROOT / '_site'
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / 'site', out, ignore=shutil.ignore_patterns('config.json'))
    payload = json.dumps({**data, 'people': people, 'papers': papers, 'config': config, 'categories': CATEGORIES,
                          'availability': AVAILABILITY, 'indices': INDICES}, ensure_ascii=False).replace('<', '\\u003c')
    cards = ''.join(render_record(row, papers) for row in data['software'])
    for page in out.glob('*.html'):
        page.write_text(page.read_text().replace('<!-- SOFTWARE_DATA -->', '<script type="application/json" id="software-data">' + payload + '</script>').replace('<!-- RECORDS -->', cards), encoding='utf-8')
    shutil.copytree(ROOT / 'data', out / 'data')
    (out / 'data/software.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (ROOT / 'data/software.csv').open(encoding='utf-8', newline='') as source:
        fields = csv.DictReader(source).fieldnames + ['researcher_names', 'irp_titles']
    with (out / 'data/software.csv').open('w', encoding='utf-8', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
        writer.writeheader(); writer.writerows(data['software'])
    (out / '.nojekyll').touch()
    print(f'Built {len(data["software"])} software records → {out}')


if __name__ == '__main__':
    build()
