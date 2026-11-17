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
`application`, `quantlet` and `other`. Data availability is `public`, `on-request`, `restricted`,
`not-required` or `not-documented`. Multiple names, languages, IRPs, paper IDs and
external paper URLs use semicolons. Optional `paper_titles` label external paper
links, in the same order as `paper_urls`. Record IDs use lowercase letters, numbers and
hyphens. Curated entries require a source repository, authors, description,
language, IRP, category, data availability and notes, and at least one linked paper.
Automatic QuantLet and Zenodo entries may have undocumented authors, language or paper links;
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

`data/software.csv` contains curated entries. `data/quantlet-software.csv` and
`data/zenodo-software.csv` are the generated feeds. The site, CSV download and JSON export combine them, with
curated entries taking precedence by stable ID, repository URL or software DOI.
Approved updates to imported entries create curated overrides that survive later
syncs. Do not edit the generated feed directly.

When both automated feeds describe the same software, the combined entry keeps
the stable QuantLet ID and category, combines documented IRPs and credits, and adds
the Zenodo software DOI, release and index link. GitHub software subprojects in a
shared repository remain distinct; versioned URLs for the same subproject deduplicate.

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

**IRP 7 exception:** Ștefan Găman contributes to QuantLet maintenance broadly.
Associate IRP 7 only when a `Metainfo.txt` **Author** or **Authors** list explicitly
credits his full name. Accent, case, punctuation and name-order variations such as
`Ștefan Găman`, `Stefan Gaman` and `Gaman, Stefan` match. GitHub contributions,
Metainfo contributor credits, usernames, initials or an ORCID alone do not qualify
IRP 7. A repository can still qualify through another candidate; only its IRP 7
association is removed when this author requirement is not met. Cached repositories
are reevaluated on every run, so the rule also corrects existing imported entries.

Matching uses complete names, allowing accents, punctuation and reversed name
order, or a matching public ORCID. Initials, partial names, submitter credits,
repository topics and inferred usernames do not establish membership. Contributor
profiles are fetched from GitHub and cached for up to 30 days; only their public
display name, handle, type and any explicit ORCID are retained, not email addresses.
The hub's maintained `data/github-accounts.json` populates GitHub profile links in
the shared directory. These explicitly assigned accounts match actual repository
contributors case insensitively, even without a public display name. The maintained
handle takes precedence over incidental names or ORCIDs in a profile biography.
Verified alternative credits or GitHub handles can be added to
`data/quantlet-identities.json` with `candidate_id`, `names`, `github_logins` and a
public `source_url` supporting the mapping. No aliases are guessed automatically.

Each repository gets a stable `quantlet-<GitHub repository ID>` record. Author
credits and descriptions come from Metainfo, languages/licences from GitHub, and
the index is Quantlet. Multiple Quantlets in one repository are combined into one
repository entry. Category is **QuantLet**, and data access remains
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
The checkpoint lives outside public site data. All data sync workflows share a
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

## Daily Zenodo synchronization

**Sync Zenodo software** runs daily at **06:43 UTC** and can also be run manually.
It reads published `software` records directly from the
[Digital Finance community](https://zenodo.org/communities/digitalfinance/), using
the public [Zenodo Records API](https://developers.zenodo.org/#records). No Zenodo
API key is needed. It requests the latest version of each deposit and paginates in
batches of 25, retries rate limits, and rejects incomplete or changing results
before replacing the generated feed. A concept ID keeps the catalogue entry stable
across releases; only a complete successful response can remove missing entries.

The importer fills documented creators/contributors, repository URLs, software DOIs,
versions, licences, programming languages and paper links. The deposit's natural
language is not treated as a programming language. ORCIDs and exact full names
assign known IRPs; unmatched community deposits remain visible with **IRP not
assigned**. When no repository is documented, the software archive is linked.
Purpose defaults to **Other** and input data availability to **Not documented**;
open access to code does not establish access to its input data. Known paper DOIs
link into Publications, and other explicit paper DOIs remain external links.

Reviewed overrides survive both source synchronizations. The workflow shares the
same concurrency group as the QuantLet and metadata workflows, validates the
combined catalogue before committing, retries rejected pushes against the latest
main, and requests Pages deployment after changes. Source code and notebooks are
never downloaded or executed by this importer.

```sh
python3 scripts/sync_zenodo.py          # Dry run
python3 scripts/sync_zenodo.py --write  # Refresh the generated feed
```

<!-- BEGIN SOFTWARE -->
47 software record(s).

| Software | Category | IRP | Language |
| --- | --- | --- | --- |
| [TSFM causal analysis](https://github.com/MSCA-DN-Digital-Finance/tsfm_causal_analysis) | Paper replication software | 1 | Python;Jupyter Notebook;PowerShell |
| [Hierarchical Loan forecasting : A study of End-to-End coherent models](https://github.com/QuantLet/Hierarchical-Loan-Forecasting) | Paper replication software | 14 | Python |
| [MSM](https://github.com/QuantLet/MSM) | QuantLet | 12;13 | Jupyter Notebook |
| [SFE_class_2015](https://github.com/QuantLet/SFE_class_2015) | QuantLet | 7;12;15 | Jupyter Notebook |
| [SFM2-SS16-ToDo](https://github.com/QuantLet/SFM2-SS16-ToDo) | QuantLet | 11 | Jupyter Notebook |
| [SFE](https://github.com/QuantLet/SFE) | QuantLet | 14;15 | R |
| [MVA](https://github.com/QuantLet/MVA) | QuantLet | 8 | Jupyter Notebook |
| [SPM](https://github.com/QuantLet/SPM) | QuantLet | 7 | Jupyter Notebook |
| [DeepLearning](https://github.com/QuantLet/DeepLearning) | QuantLet | 12 | Jupyter Notebook |
| [DigitalEconomyDecisionAnalytics](https://github.com/QuantLet/DigitalEconomyDecisionAnalytics) | QuantLet | 8 | HTML |
| [DEDA_2022_NYCU](https://github.com/QuantLet/DEDA_2022_NYCU) | QuantLet | 8 | Jupyter Notebook |
| [FRM-Taiwan](https://github.com/QuantLet/FRM-Taiwan) | QuantLet | 8 | Jupyter Notebook |
| [DEDA_2024_NYCU](https://github.com/QuantLet/DEDA_2024_NYCU) | QuantLet | 8 | Python |
| [Metcalfe_Law_and_LPPL_Crypto](https://github.com/QuantLet/Metcalfe_Law_and_LPPL_Crypto) | QuantLet | 15 | Jupyter Notebook |
| [Crypto_Currency_Returns](https://github.com/QuantLet/Crypto_Currency_Returns) | QuantLet | 7;8 | Jupyter Notebook |
| [ETH_Event_Study](https://github.com/QuantLet/ETH_Event_Study) | QuantLet | 7 | R |
| [LLM4Forecasting](https://github.com/QuantLet/LLM4Forecasting) | QuantLet | 12 | Jupyter Notebook |
| [Quantlet_The_Code_Snippet_Knowledge_Platform](https://github.com/QuantLet/Quantlet_The_Code_Snippet_Knowledge_Platform) | QuantLet | 7 | Python |
| [Decomposing-Stock-Factors](https://github.com/QuantLet/Decomposing-Stock-Factors) | QuantLet | 15 | Jupyter Notebook |
| [CentralBank2StockMarket](https://github.com/QuantLet/CentralBank2StockMarket) | QuantLet | 12 | Jupyter Notebook |
| [Fraud Detection](https://github.com/QuantLet/Fraud-Detection-Demo) | QuantLet | 8 | Jupyter Notebook |
| [WP3_eXplainable_and_Fair_AI](https://github.com/QuantLet/WP3_eXplainable_and_Fair_AI) | QuantLet | 1;12;17 |  |
| [Courses](https://github.com/QuantLet/Courses) | QuantLet | 1;8;9;11;12;13;14 | Jupyter Notebook |
| [GRU](https://github.com/QuantLet/GRU) | QuantLet | 12 | Jupyter Notebook |
| [DEDA_2025_CUEB](https://github.com/QuantLet/DEDA_2025_CUEB) | QuantLet | 8 | Jupyter Notebook |
| [Stable_Distribution](https://github.com/QuantLet/Stable_Distribution) | QuantLet | 7;12 | Jupyter Notebook |
| [Proper Scoring Rules](https://github.com/QuantLet/Proper-Scoring-Rules) | QuantLet | 14 | Jupyter Notebook |
| [LLMs-for-BTC-TS](https://github.com/QuantLet/LLMs-for-BTC-TS) | QuantLet | 14 | Jupyter Notebook |
| [2025_HTW_ESG_Portfolio_Optimization](https://github.com/QuantLet/ESG-Portfolio-Optimization) | QuantLet | 8;12 | Jupyter Notebook |
| [Hierarchical Time Series : A geometric approach](https://github.com/QuantLet/HTS_visualization) | QuantLet | 14 | Jupyter Notebook |
| [Whitepaper_CC_Indices](https://github.com/QuantLet/Whitepaper_CC_Indices) | QuantLet | 7 | Python |
| [A_New_EMD_Approach](https://github.com/QuantLet/A_New_EMD_Approach) | QuantLet | 8 | Jupyter Notebook |
| [01 FINDER-LLM](https://github.com/QuantLet/FINDER-LLM) | QuantLet | 7;8;12 | Jupyter Notebook |
| [fulvio-PhD](https://github.com/QuantLet/fulvio-PhD) | QuantLet | 13 |  |
| [Onchain Insights](https://github.com/QuantLet/onchain-insights) | QuantLet | 8;14 | Jupyter Notebook |
| [Transparent-Movie](https://github.com/QuantLet/Transparent-Movie-Instruction) | QuantLet | 8 | Jupyter Notebook |
| [AI_Listening2CB](https://github.com/QuantLet/AI_Listening2CB) | QuantLet | 12 | Jupyter Notebook |
| [Network_Centrality](https://github.com/QuantLet/Network_Centrality) | QuantLet | 14 | Jupyter Notebook |
| [TSFM_VaR_CEE](https://github.com/QuantLet/TSFM_VaR_CEE) | QuantLet | 8 | Jupyter Notebook |
| [XAI_beyond_SHAP](https://github.com/QuantLet/XAI_beyond_SHAP) | QuantLet | 14 |  |
| [MSR](https://github.com/QuantLet/MSR) | QuantLet | 7 | Jupyter Notebook |
| [FATED-Polymarket](https://github.com/QuantLet/FATED-Polymarket) | QuantLet | 7;14 | Jupyter Notebook |
| [STMS_Delta](https://github.com/QuantLet/Delta-Method) | QuantLet | 15 | Jupyter Notebook |
| [Electricity-Portfolio-Hedging](https://github.com/QuantLet/Electricity-Portfolio-Hedging) | QuantLet | 8 | Jupyter Notebook |
| [Polymarked](https://github.com/QuantLet/Polymarked) | QuantLet | 14 |  |
| [Code and Data for Reinforcement Learning in Finance: From Current Practice to Standards and Frameworks](https://github.com/MSCA-DN-Digital-Finance/WP3_eXplainable_and_Fair_AI/tree/f84806bad3edebba538633870a57ce81eaf511e5/IRP1/Code/systematic_literature_review) | Other | 1 | Python |
| [MSCA-DN-Digital-Finance/stablecoin-onchain-data: DeFi hourly datasets data-2026-02-02](https://github.com/MSCA-DN-Digital-Finance/stablecoin-onchain-data) | Other | 14 |  |
<!-- END SOFTWARE -->
