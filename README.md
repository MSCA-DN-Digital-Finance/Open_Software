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
hyphens. Curated entries require a source repository, authors, description,
language, IRP, category, data availability and notes, and at least one linked paper.
Automatic QuantLet entries may have undocumented authors, language or paper links;
these gaps are shown explicitly until a maintainer supplies the missing metadata.

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

`data/software.csv` contains curated entries. `data/quantlet-software.csv` is the
generated QuantLet feed. The site, CSV download and JSON export combine both, with
curated entries taking precedence by stable ID, repository URL or software DOI.
Approved updates to imported entries create curated overrides that survive later
syncs. Do not edit the generated feed directly.

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

## Daily QuantLet synchronization

**Sync QuantLet software** runs daily at **06:23 UTC** and supports a manual run
from Actions. It enumerates all public repositories in [QuantLet](https://github.com/QuantLet),
including forks and archived repositories, and scans `Metainfo.txt` at any depth
(case insensitive filename matching). Truncated recursive trees are walked fully.
An entry qualifies when a Metainfo author/contributor matches a current doctoral
candidate, or an actual GitHub repository contributor matches the shared dictionary.

Matching uses complete names, allowing accents, punctuation and reversed name
order, or a matching public ORCID. Initials, partial names, submitter credits,
repository topics and inferred usernames do not establish membership. Contributor
profiles are fetched from GitHub and cached for up to 30 days; only their public
display name, handle, type and any explicit ORCID are retained, not email addresses.
Verified alternative credits or GitHub handles can be added to
`data/quantlet-identities.json` with `candidate_id`, `names`, `github_logins` and a
public `source_url` supporting the mapping. No aliases are guessed automatically.

Each repository gets a stable `quantlet-<GitHub repository ID>` record. Author
credits and descriptions come from Metainfo, languages/licences from GitHub, and
the index is Quantlet. Multiple Quantlets in one repository are combined into one
repository entry. Category defaults to **Other**, and data access remains
**Not documented** unless curated; a source Datafile note is shown when available.
Paper IDs are linked only on an exact normalized title, DOI or URL match. A long
`Name of Quantlet` is also compared when it is identical to a full paper title. Explicit
publication URLs become external paper links. A study title without a resolvable
paper link is retained in provenance, with a visible missing-link message. A paper
DOI is never reused as the software DOI; only an explicit `Software DOI` field can
populate that value. Source code, notebooks and YAML objects are never executed.

`.sync/quantlet-state.json` is the committed incremental checkpoint. Unchanged
repositories are reused and candidate matching is reevaluated against the current
dictionary on every run. The workflow refreshes at most 100 changed repositories
and uses at most 750 REST requests per run, leaving room within the built-in
GitHub Actions token allowance. A bounded scan preserves previously indexed
repositories and records pending work for the next run. Its Actions summary reports
discovery, matches and remaining work; rerun manually to advance the checkpoint.
Repositories removed from QuantLet are pruned only after complete organization
enumeration. An individual repository fetch failure retains its previous snapshot
and is reported as pending for retry; other completed scans can still be saved.
Failed organization discovery or catalogue validation leaves all files unchanged.
The checkpoint lives outside public site data. Both data sync workflows share a
concurrency group, and rejected pushes are retried against the latest main.

No extra API key or personal token is required in Actions: the workflow uses
`GITHUB_TOKEN` automatically and dispatches Pages after applying changes. For a
local run, use an authenticated GitHub CLI or an existing `GH_TOKEN` environment
variable. The token is sent only to GitHub's API, never to raw metadata URLs or
stored in the checkpoint.

```sh
python3 scripts/sync_quantlet.py                 # Validated preview; writes nothing
python3 scripts/sync_quantlet.py --write         # Refresh feed and checkpoint
python3 update_README.py
python3 scripts/build_site.py
```

<!-- BEGIN SOFTWARE -->
34 software record(s).

| Software | Category | IRP | Language |
| --- | --- | --- | --- |
| [TSFM causal analysis](https://github.com/MSCA-DN-Digital-Finance/tsfm_causal_analysis) | Paper replication software | 1 | Python;Jupyter Notebook;PowerShell |
| [MSM](https://github.com/QuantLet/MSM) | Other | 12;13 | Jupyter Notebook |
| [SFE_class_2015](https://github.com/QuantLet/SFE_class_2015) | Other | 7;15 | Jupyter Notebook |
| [SFE](https://github.com/QuantLet/SFE) | Other | 14;15 | R |
| [SPM](https://github.com/QuantLet/SPM) | Other | 7 | Jupyter Notebook |
| [DeepLearning](https://github.com/QuantLet/DeepLearning) | Other | 12 | Jupyter Notebook |
| [DigitalEconomyDecisionAnalytics](https://github.com/QuantLet/DigitalEconomyDecisionAnalytics) | Other | 8 | HTML |
| [Metcalfe_Law_and_LPPL_Crypto](https://github.com/QuantLet/Metcalfe_Law_and_LPPL_Crypto) | Other | 15 | Jupyter Notebook |
| [Crypto_Currency_Returns](https://github.com/QuantLet/Crypto_Currency_Returns) | Other | 7 | Jupyter Notebook |
| [ETH_Event_Study](https://github.com/QuantLet/ETH_Event_Study) | Other | 7 | R |
| [LLM4Forecasting](https://github.com/QuantLet/LLM4Forecasting) | Other | 12 | Jupyter Notebook |
| [Quantlet_The_Code_Snippet_Knowledge_Platform](https://github.com/QuantLet/Quantlet_The_Code_Snippet_Knowledge_Platform) | Other | 7 | Python |
| [Hierarchical Loan forecasting : A study of End-to-End coherent models](https://github.com/QuantLet/Hierarchical-Loan-Forecasting) | Other | 14 | Jupyter Notebook |
| [Decomposing-Stock-Factors](https://github.com/QuantLet/Decomposing-Stock-Factors) | Other | 15 | Jupyter Notebook |
| [CentralBank2StockMarket](https://github.com/QuantLet/CentralBank2StockMarket) | Other | 12 | Jupyter Notebook |
| [WP3_eXplainable_and_Fair_AI](https://github.com/QuantLet/WP3_eXplainable_and_Fair_AI) | Other | 1 |  |
| [Courses](https://github.com/QuantLet/Courses) | Other | 1;11;14 | Jupyter Notebook |
| [GRU](https://github.com/QuantLet/GRU) | Other | 12 | Jupyter Notebook |
| [Stable_Distribution](https://github.com/QuantLet/Stable_Distribution) | Other | 7;12 | Jupyter Notebook |
| [Proper Scoring Rules](https://github.com/QuantLet/Proper-Scoring-Rules) | Other | 14 | Jupyter Notebook |
| [LLMs-for-BTC-TS](https://github.com/QuantLet/LLMs-for-BTC-TS) | Other | 14 | Jupyter Notebook |
| [Hierarchical Time Series : A geometric approach](https://github.com/QuantLet/HTS_visualization) | Other | 14 | Jupyter Notebook |
| [Whitepaper_CC_Indices](https://github.com/QuantLet/Whitepaper_CC_Indices) | Other | 7 | Python |
| [A_New_EMD_Approach](https://github.com/QuantLet/A_New_EMD_Approach) | Other | 8 | Jupyter Notebook |
| [01 FINDER-LLM](https://github.com/QuantLet/FINDER-LLM) | Other | 7;12 | Jupyter Notebook |
| [Onchain Insights](https://github.com/QuantLet/onchain-insights) | Other | 14 | Jupyter Notebook |
| [Transparent-Movie](https://github.com/QuantLet/Transparent-Movie-Instruction) | Other | 8 | Jupyter Notebook |
| [Network_Centrality](https://github.com/QuantLet/Network_Centrality) | Other | 14 | Jupyter Notebook |
| [XAI_beyond_SHAP](https://github.com/QuantLet/XAI_beyond_SHAP) | Other | 14 |  |
| [MSR](https://github.com/QuantLet/MSR) | Other | 7 | Jupyter Notebook |
| [FATED-Polymarket](https://github.com/QuantLet/FATED-Polymarket) | Other | 7;14 | Jupyter Notebook |
| [STMS_Delta](https://github.com/QuantLet/Delta-Method) | Other | 15 | Jupyter Notebook |
| [Electricity-Portfolio-Hedging](https://github.com/QuantLet/Electricity-Portfolio-Hedging) | Other | 8 | Jupyter Notebook |
| [Polymarked](https://github.com/QuantLet/Polymarked) | Other | 14 |  |
<!-- END SOFTWARE -->
