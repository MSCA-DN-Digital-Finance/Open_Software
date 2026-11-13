"""Refresh the generated software index in README.md."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
from build_site import ROOT, CATEGORIES, inventory


def main():
    rows = inventory()['software']
    start, end = '<!-- BEGIN SOFTWARE -->', '<!-- END SOFTWARE -->'
    target = ROOT / 'README.md'
    before, rest = target.read_text(encoding='utf-8').split(start, 1)
    _, after = rest.split(end, 1)
    lines = [f'{len(rows)} software record(s).', '', '| Software | Category | IRP | Language |', '| --- | --- | --- | --- |']
    for row in rows:
        name = row['name'].replace('|', '\\|').replace('\n', ' ')
        lines.append(f'| [{name}]({row["repository_url"]}) | {CATEGORIES[row["category"]]} | {row["irp_numbers"]} | {row["languages"]} |')
    target.write_text(before + start + '\n' + '\n'.join(lines) + '\n' + end + after, encoding='utf-8')


if __name__ == '__main__':
    main()
