"""Refresh the generated software index in README.md."""
from pathlib import Path
import sys
from urllib.parse import quote
sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
from build_site import ROOT, CATEGORIES, inventory, split


def main():
    rows = inventory()['software']
    start, end = '<!-- BEGIN SOFTWARE -->', '<!-- END SOFTWARE -->'
    target = ROOT / 'README.md'
    before, rest = target.read_text(encoding='utf-8').split(start, 1)
    _, after = rest.split(end, 1)
    lines = [f'{len(rows)} software record(s).', '', '| Software | Category | IRP | Language | Repository created | DOI |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in rows:
        name = row['name'].replace('|', '\\|').replace('\n', ' ')
        dois = list(dict.fromkeys(filter(None, [row.get('doi'), *split(row.get('quantlet_dois'))])))
        doi_cell = '—'
        if len(dois) == 1:
            doi_cell = f'[{dois[0].replace("|", "&#124;")}](https://doi.org/{quote(dois[0], safe="/")})'
        elif dois:
            doi_cell = f'[{len(dois)} DOIs](https://msca-dn-digital-finance.github.io/Open_Software/#software/{row["id"]})'
        created = row.get('repository_created_at') or '—'
        lines.append(f'| [{name}]({row["repository_url"]}) | {CATEGORIES[row["category"]]} | {row["irp_numbers"]} | {row["languages"]} | {created} | {doi_cell} |')
    target.write_text(before + start + '\n' + '\n'.join(lines) + '\n' + end + after, encoding='utf-8')


if __name__ == '__main__':
    main()
