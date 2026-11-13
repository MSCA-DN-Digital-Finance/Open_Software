#!/usr/bin/env python3
"""Refresh shared IRP and paper dictionaries after validating the full catalogue."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from build_site import ROOT, inventory
from directory import DIRECTORY_URL, fetch_json, load, validate, write_json


def sync(local=False, root=None):
    root = root or ROOT
    if local:
        people = json.loads((root.parent / 'MSCA-DN-Digital-Finance.github.io/data/people.json').read_text(encoding='utf-8'))
        papers = json.loads((root.parent / 'Publications/_site/data/research.json').read_text(encoding='utf-8'))
    else:
        people = fetch_json(DIRECTORY_URL)
        papers = fetch_json('https://msca-dn-digital-finance.github.io/Publications/data/research.json')
    validate(people)
    if {p['number'] for p in load(root)} - {p['number'] for p in people['projects']}:
        raise ValueError('Shared dictionary unexpectedly removed IRPs')
    with tempfile.TemporaryDirectory() as staging:
        staged = Path(staging)
        shutil.copytree(root / 'data', staged / 'data')
        write_json(staged / 'data/people.json', people)
        write_json(staged / 'data/papers.json', papers)
        inventory(staged)
    changed = write_json(root / 'data/people.json', people)
    changed = write_json(root / 'data/papers.json', papers) or changed
    print('Shared metadata ' + ('updated' if changed else 'unchanged'))
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='Read sibling local repositories instead of published feeds')
    sync(parser.parse_args().local)
