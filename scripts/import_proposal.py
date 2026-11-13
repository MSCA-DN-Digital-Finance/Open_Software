#!/usr/bin/env python3
"""Validate a software proposal, or atomically apply it with --write."""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import tempfile

from build_site import ROOT, inventory, normalized_doi


def apply_proposal(path, write=False):
    proposal = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(proposal, dict) or set(proposal) != {'kind', 'action', 'record'} or proposal['kind'] != 'software' or proposal['action'] not in {'add', 'update'} or not isinstance(proposal['record'], dict):
        raise ValueError('Expected kind software, action add/update, and a record object')
    record = dict(proposal['record'])
    target = ROOT / 'data/software.csv'
    with target.open(encoding='utf-8', newline='') as source:
        reader = csv.DictReader(source)
        fields, rows = reader.fieldnames, list(reader)
    if set(record) - set(fields) or not all(isinstance(value, str) for value in record.values()):
        raise ValueError('Unknown software field or non-string value')
    if record.get('doi'):
        record['doi'] = normalized_doi(record['doi'])
    matches = [i for i, row in enumerate(rows) if row['id'] == record.get('id')]
    if proposal['action'] == 'add':
        if matches:
            raise ValueError('Software ID already exists; use an update')
        rows.append({field: record.get(field, '') for field in fields})
    else:
        if not matches:
            imported = [row for row in inventory()['software'] if row['id'] == record.get('id')]
            if len(imported) == 1:
                matches = [len(rows)]
                rows.append({field: imported[0].get(field, '') for field in fields})
        if len(matches) != 1:
            raise ValueError('An update must use an existing software ID')
        rows[matches[0]].update(record)
    with tempfile.TemporaryDirectory() as staging:
        root = Path(staging)
        shutil.copytree(ROOT / 'data', root / 'data')
        staged = root / 'data/software.csv'
        with staged.open('w', encoding='utf-8', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
        inventory(root)
        if write:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
                temporary = Path(output.name); output.write(staged.read_bytes())
            try:
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
    print(f'{"Applied" if write else "Valid dry run for"} {proposal["action"]}: software/{record["id"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('proposal', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    apply_proposal(args.proposal, args.write)
