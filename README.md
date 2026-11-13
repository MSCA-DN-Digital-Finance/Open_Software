# DIGITAL · Open Software

Research software catalogue for the MSCA Digital Finance network.

- Website: https://msca-dn-digital-finance.github.io/Open_Software/
- Candidate and IRP profiles: https://msca-dn-digital-finance.github.io/irps/

## Catalogue metadata

`data/software.csv` indexes software names, source repository links, descriptions,
authors and contributors, programming languages, IRPs, linked publications and
working papers, software index records (Quantlet, Zenodo or another index), software
DOIs, licences/releases, and data availability notes and links. An optional key
image can show a plot from the source repository, with alt text and a caption/credit.

Categories are `paper-replication`, `data-collection`, `package-release`,
`application` and `other`. Data availability is `public`, `on-request`, `restricted`,
`not-required` or `not-documented`. Multiple names, languages, IRPs, paper IDs and
external paper URLs use semicolons. Optional `paper_titles` label external paper
links, in the same order as `paper_urls`. Record IDs use lowercase letters, numbers and
hyphens. A source repository, authors, description, language, IRP, category, data
availability and notes, and at least one linked paper are required.

Link papers using stable `publication_ids` and `working_paper_ids` from the
Publications catalogue, or `paper_urls` for papers not yet listed there. One software
record can support multiple papers and IRPs. The software DOI is separate from its
paper's DOI. Choose `not-indexed` if there is no software index record. Indexed
software requires an `index_url`; a DOI remains optional. The catalogue does not
assert that a paper is published merely because its code is public.

`key_image_url` must be a direct public PNG, JPEG, GIF or WebP URL (for example,
`raw.githubusercontent.com` rather than a GitHub HTML `blob` page). Images are
optional and must have meaningful `key_image_alt` text. Use images permitted for
reuse and credit the plot source in `key_image_caption`. Code and research data
remain in their source repositories; the catalogue does not copy them. Missing
licences and archive identifiers are displayed as undocumented.

## Contribute and approve

Use **Add software** or **Suggest an update** to prepare a GitHub issue. The form
supports paper selection, multiple IRPs, draft saving and a JSON download. Review
and submit the issue. A maintainer with write, maintain or admin access applies
`software-approved`; the approval workflow validates the immutable proposal,
updates the CSV and this index, commits to `main`, requests Pages deployment and
closes the issue. Reapplying an approved proposal is idempotent. If the issue is
edited after approval, review it and remove/re-add the approval label.

Only plain metadata is imported; issue text is never executed. Invalid records,
unknown IRPs/paper IDs and duplicate software DOIs leave the CSV unchanged. An
external paper URL can be used while a paper is waiting to enter the shared catalogue.

## Shared dictionaries and deployment

`data/people.json` is a snapshot of the hub's canonical candidate/IRP dictionary.
`data/papers.json` is a snapshot of the Publications JSON export. Daily metadata
synchronization validates both snapshots against all software references before
replacing them, commits changes and requests deployment. It preserves the previous
metadata if upstream references are invalid or removed. No personal access token
is needed; automation uses the repository's automatic `GITHUB_TOKEN`.

Enable **Settings → Pages → Source → GitHub Actions**. Builds/tests run on pull
requests; pushes to `main` deploy. The bot needs permission to commit and dispatch
workflows, and branch rules must allow those commits. The JSON export at
`data/software.json` is used by the hub's individual IRP pages. Candidate names and
project titles in the site and exports are resolved from the shared dictionary.

Python 3.9+ and its standard library are sufficient:

```sh
python3 scripts/build_site.py
python3 -m unittest discover -s tests -v
python3 scripts/sync_metadata.py           # Refresh from published shared feeds
python3 scripts/sync_metadata.py --local   # Or sibling local repositories
python3 scripts/import_proposal.py /path/to/proposal.json          # Dry run
python3 scripts/import_proposal.py /path/to/proposal.json --write  # Apply
python3 update_README.py
python3 -m http.server 8000 --directory _site
```

The initial entry is sourced from its repository README/citation and GitHub
metadata. Archives, figures, contributors and paper associations are only added
when documented; no relationship is invented to populate the catalogue.

<!-- BEGIN SOFTWARE -->
1 software record(s).

| Software | Category | IRP | Language |
| --- | --- | --- | --- |
| [TSFM causal analysis](https://github.com/MSCA-DN-Digital-Finance/tsfm_causal_analysis) | Paper replication software | 1 | Python;Jupyter Notebook;PowerShell |
<!-- END SOFTWARE -->
