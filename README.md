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
533 software record(s).

| Software | Category | IRP | Language |
| --- | --- | --- | --- |
| [TSFM causal analysis](https://github.com/MSCA-DN-Digital-Finance/tsfm_causal_analysis) | Paper replication software | 1 | Python;Jupyter Notebook;PowerShell |
| [Psychological-diagnostics](https://github.com/QuantLet/Psychological-diagnostics) | QuantLet | 7 | R |
| [MANDATORY! Has to be the same as the Quantlet file, without file type ending, e.g. R,py,...](https://github.com/QuantLet/Styleguide-and-FAQ) | QuantLet | 7 |  |
| [MVAghadatail](https://github.com/QuantLet/Collaboration_Example_MVAghadatail) | QuantLet | 7 | R |
| [MVAghdis](https://github.com/QuantLet/Collaboration_Example_MVAghdis) | QuantLet | 7 | R |
| [MVAlaplacedis](https://github.com/QuantLet/Collaboration_Example_MVAlaplacedis) | QuantLet | 7 | R |
| [New-change-keywords](https://github.com/QuantLet/New-change-keywords) | QuantLet | 7 |  |
| [tu_dresden_mva2](https://github.com/QuantLet/tu_dresden_mva2) | QuantLet | 7 | R |
| [FRM](https://github.com/QuantLet/FRM) | QuantLet | 7 | R |
| [TXT](https://github.com/QuantLet/TXT) | QuantLet | 7 | Python |
| [DYTEC](https://github.com/QuantLet/DYTEC) | QuantLet | 7 | R |
| [MMSTAT](https://github.com/QuantLet/MMSTAT) | QuantLet | 7 | R |
| [MSM](https://github.com/QuantLet/MSM) | QuantLet | 7;12;13 | Jupyter Notebook |
| [FASTEC-with-Expectiles](https://github.com/QuantLet/FASTEC-with-Expectiles) | QuantLet | 7 | R |
| [TEDAS](https://github.com/QuantLet/TEDAS) | QuantLet | 7 | MATLAB |
| [Local_Quantile_Regression](https://github.com/QuantLet/Local_Quantile_Regression) | QuantLet | 7 | R |
| [MTS](https://github.com/QuantLet/MTS) | QuantLet | 7 | R |
| [TimeVaryingPenalization](https://github.com/QuantLet/TimeVaryingPenalization) | QuantLet | 7 | R |
| [lCARE-BTU-HUB](https://github.com/QuantLet/lCARE-BTU-HUB) | QuantLet | 7 | MATLAB |
| [SRM](https://github.com/QuantLet/SRM) | QuantLet | 7 | R |
| [TSARMARJMCMC](https://github.com/QuantLet/RJMCMC) | QuantLet | 7 | MATLAB |
| [XFG3](https://github.com/QuantLet/XFG3) | QuantLet | 7 | R |
| [SPA](https://github.com/QuantLet/SPA) | QuantLet | 7 | R |
| [SMS2](https://github.com/QuantLet/SMS2) | QuantLet | 7 | R |
| [SFE_class_2015](https://github.com/QuantLet/SFE_class_2015) | QuantLet | 7;12;15 | Jupyter Notebook |
| [TENET](https://github.com/QuantLet/TENET) | QuantLet | 7 | R |
| [ADM](https://github.com/QuantLet/ADM) | QuantLet | 7 | MATLAB |
| [FPCA](https://github.com/QuantLet/FPCA) | QuantLet | 7 | MATLAB |
| [Q-Problems](https://github.com/QuantLet/Q-Problems) | QuantLet | 7 | R |
| [Time-varying-HAC](https://github.com/QuantLet/Time-varying-HAC) | QuantLet | 7 | R |
| [COP-Estimation-Misspec](https://github.com/QuantLet/COP-Estimation-Misspec) | QuantLet | 7 | R |
| [VolLinkages](https://github.com/QuantLet/VolLinkages) | QuantLet | 7 | R |
| [LETF-Moneyness](https://github.com/QuantLet/LETF-Moneyness) | QuantLet | 7 | R |
| [XFG3-Temp_old](https://github.com/QuantLet/XFG3-Temp_old) | QuantLet | 7 | R |
| [Balanced_Quantile_Predictive_Regression](https://github.com/QuantLet/Balanced_Quantile_Predictive_Regression) | QuantLet | 7 | R |
| [Disaster](https://github.com/QuantLet/Disaster) | QuantLet | 7 | MATLAB |
| [AdaptivePenalizedMacroFactor](https://github.com/QuantLet/Adaptive_Penalized_Macro_Factors) | QuantLet | 7 | MATLAB |
| [BCS](https://github.com/QuantLet/BCS) | QuantLet | 7 | R |
| [collection_unsorted](https://github.com/QuantLet/collection_unsorted) | QuantLet | 7 | MATLAB |
| [vcExp](https://github.com/QuantLet/vcExp) | QuantLet | 7 | MATLAB |
| [plotting](https://github.com/QuantLet/plotting) | QuantLet | 7 | R |
| [TEDAS_TAU_SPINE](https://github.com/QuantLet/TEDAS_TAU_SPINE) | QuantLet | 7 | MATLAB |
| [MCAR](https://github.com/QuantLet/MCAR) | QuantLet | 7 | R |
| [DataExpo2013_QuachSymanzikForsgren](https://github.com/QuantLet/QuachSymanzikForsgren) | QuantLet | 7 | Portugol |
| [TERES_EVT](https://github.com/QuantLet/CRIX---TERES-EVT) | QuantLet | 7 | R |
| [VWAP](https://github.com/QuantLet/VWAP) | QuantLet | 7 | R |
| [NIC_class_2015](https://github.com/QuantLet/NIC_class_2015) | QuantLet | 7 | R |
| [COP](https://github.com/QuantLet/COP) | QuantLet | 7 | R |
| [SFM2-SS16-ToDo](https://github.com/QuantLet/SFM2-SS16-ToDo) | QuantLet | 7;11 | Jupyter Notebook |
| [NAR](https://github.com/QuantLet/NAR) | QuantLet | 7 | R |
| [XFG-SS16](https://github.com/QuantLet/XFG-SS16) | QuantLet | 7 |  |
| [SFE_merge_TB](https://github.com/QuantLet/SFE_merge_TB) | QuantLet | 7 | R |
| [SMS](https://github.com/QuantLet/SMS) | QuantLet | 7 | R |
| [MuPoMo](https://github.com/QuantLet/MuPoMo) | QuantLet | 7 | R |
| [CMB](https://github.com/QuantLet/CMB) | QuantLet | 7 | CoffeeScript |
| [MVA-ToDo](https://github.com/QuantLet/MVA-ToDo) | QuantLet | 7 | MATLAB |
| [GeoCopula](https://github.com/QuantLet/GeoCopula) | QuantLet | 7 | R |
| [TERES](https://github.com/QuantLet/TERES) | QuantLet | 7 | R |
| [japanesetwitter](https://github.com/QuantLet/japanesetwitter) | QuantLet | 7 | R |
| [ARR](https://github.com/QuantLet/ARR) | QuantLet | 7 | R |
| [Stable](https://github.com/QuantLet/Stable) | QuantLet | 7 | MATLAB |
| [EIV_UCS](https://github.com/QuantLet/EIV_UCS) | QuantLet | 7 | R |
| [VFAR](https://github.com/QuantLet/VFAR) | QuantLet | 7 | MATLAB |
| [varuca](https://github.com/QuantLet/varuca) | QuantLet | 7 | R |
| [EconCrix](https://github.com/QuantLet/EconCrix) | QuantLet | 7 | R |
| [Data-adaptive-PCA](https://github.com/QuantLet/Data-adaptive-PCA) | QuantLet | 7 | R |
| [PCA-in-an-Asymmetric-Norm](https://github.com/QuantLet/PCA-in-an-Asymmetric-Norm) | QuantLet | 7 | R |
| [MVA-Plotly](https://github.com/QuantLet/MVA-Plotly) | QuantLet | 7 | R |
| [Plotly](https://github.com/QuantLet/Plotly) | QuantLet | 7 | HTML |
| [SCRIX](https://github.com/QuantLet/SCRIX) | QuantLet | 7 | R |
| [Face-Recognition](https://github.com/QuantLet/Face-Recognition) | QuantLet | 7 | R |
| [XFG-ToDo](https://github.com/QuantLet/XFG-ToDo) | QuantLet | 7 | R |
| [MSE-ToDO](https://github.com/QuantLet/MSE-ToDO) | QuantLet | 7 | R |
| [IC](https://github.com/QuantLet/IC) | QuantLet | 7 | R |
| [Stochastic_processes](https://github.com/QuantLet/Stochastic_processes) | QuantLet | 7 | R |
| [big_data_analysis](https://github.com/QuantLet/big_data_analysis) | QuantLet | 7 | R |
| [Git2Q3-Collaboration](https://github.com/QuantLet/Git2Q3-Collaboration) | QuantLet | 7 |  |
| [forceNetwork](https://github.com/QuantLet/forceNetwork) | QuantLet | 7 | HTML |
| [DEDA-Bitcoin](https://github.com/QuantLet/DEDA-Bitcoin) | QuantLet | 7 | R |
| [gaplmsbk](https://github.com/QuantLet/gaplmsbk) | QuantLet | 7 | R |
| [CCS](https://github.com/QuantLet/CCS) | QuantLet | 7 | R |
| [CCNMGQR](https://github.com/QuantLet/CCNMGQR) | QuantLet | 7 | R |
| [q_awc](https://github.com/QuantLet/q_awc) | QuantLet | 7 | Python |
| [MediaNews](https://github.com/QuantLet/MediaNews) | QuantLet | 7 | R |
| [STF-ToDo](https://github.com/QuantLet/STF-ToDo) | QuantLet | 7 | MATLAB |
| [MSE](https://github.com/QuantLet/MSE) | QuantLet | 7 | R |
| [MHE](https://github.com/QuantLet/MHE) | QuantLet | 7 | MATLAB |
| [FPCA_Electricity](https://github.com/QuantLet/FPCA_Electricity) | QuantLet | 7 | R |
| [XFG](https://github.com/QuantLet/XFG) | QuantLet | 7 | R |
| [electricitypriceforecasting](https://github.com/QuantLet/electricitypriceforecasting) | QuantLet | 7 | MATLAB |
| [CRC](https://github.com/QuantLet/CRC) | QuantLet | 7 | R |
| [Topic Modeling](https://github.com/QuantLet/Topic-Modeling) | QuantLet | 7 | MATLAB |
| [STF](https://github.com/QuantLet/STF) | QuantLet | 7 | R |
| [D3Genesis](https://github.com/QuantLet/D3Genesis) | QuantLet | 7 | HTML |
| [SFE](https://github.com/QuantLet/SFE) | QuantLet | 7;14;15 | R |
| [Q3D3LSA](https://github.com/QuantLet/Q3D3LSA) | QuantLet | 7 | R |
| [SMS-ToDo](https://github.com/QuantLet/SMS-ToDo) | QuantLet | 7 |  |
| [MVA](https://github.com/QuantLet/MVA) | QuantLet | 7;8 | Jupyter Notebook |
| [sim_estim_ms_skewtt_factorcop](https://github.com/QuantLet/Copula) | QuantLet | 7 | MATLAB |
| [SIM](https://github.com/QuantLet/SIM) | QuantLet | 7 | R |
| [SFS-ToDo](https://github.com/QuantLet/SFS-ToDo) | QuantLet | 7 | MATLAB |
| [exgb](https://github.com/QuantLet/exgb) | QuantLet | 7 | Python |
| [pricing_kernels_and_implied_volatility](https://github.com/QuantLet/pricing_kernels_and_implied_volatility) | QuantLet | 7 | R |
| [SFS](https://github.com/QuantLet/SFS) | QuantLet | 7 | R |
| [MRS-ToDo](https://github.com/QuantLet/MRS-ToDo) | QuantLet | 7 |  |
| [MSR_R](https://github.com/QuantLet/MSR_R) | QuantLet | 7 | MATLAB |
| [choroImmi](https://github.com/QuantLet/choroImmi) | QuantLet | 7 | JavaScript |
| [SPM](https://github.com/QuantLet/SPM) | QuantLet | 7 | Jupyter Notebook |
| [topic-models](https://github.com/QuantLet/topic-models) | QuantLet | 7 | Python |
| [SFE_class_2016](https://github.com/QuantLet/SFE_class_2016) | QuantLet | 7 | R |
| [BetaBoost](https://github.com/QuantLet/BetaBoost) | QuantLet | 7 | Python |
| [DDINetwork](https://github.com/QuantLet/DDINetwork) | QuantLet | 7 | MATLAB |
| [Clustering_Validation_Pipeline](https://github.com/QuantLet/Clustering_Validation_Pipeline) | QuantLet | 7 | R |
| [SDA](https://github.com/QuantLet/SDA) | QuantLet | 7 | R |
| [M_MEM](https://github.com/QuantLet/M_MEM) | QuantLet | 7 | MATLAB |
| [Factor_copula_systemic](https://github.com/QuantLet/Factor_copula_systemic) | QuantLet | 7 | R |
| [LIBRO](https://github.com/QuantLet/LIBRO) | QuantLet | 7 | R |
| [Kelly](https://github.com/QuantLet/Kelly) | QuantLet | 7 | MATLAB |
| [SPL](https://github.com/QuantLet/SPL) | QuantLet | 7 | R |
| [nutrition_changes_south_korea](https://github.com/QuantLet/nutrition_changes_south_korea) | QuantLet | 7 | R |
| [RGoogleAnalytics](https://github.com/QuantLet/RGoogleAnalytics) | QuantLet | 7 | R |
| [Q-Kolleg](https://github.com/QuantLet/Q-Kolleg) | QuantLet | 7 | R |
| [SIFI](https://github.com/QuantLet/SIFI) | QuantLet | 7 | MATLAB |
| [INET](https://github.com/QuantLet/INET) | QuantLet | 7 | R |
| [METISNET](https://github.com/QuantLet/METISNET) | QuantLet | 7 | R |
| [VWAP](https://github.com/QuantLet/VWAP_Germany) | QuantLet | 7 | R |
| [Tukey](https://github.com/QuantLet/Tukey) | QuantLet | 7 | Jupyter Notebook |
| [GPLM](https://github.com/QuantLet/GPLM) | QuantLet | 7 | R |
| [Q3](https://github.com/QuantLet/Q3) | QuantLet | 7 | R |
| [BCS-1](https://github.com/QuantLet/BCS-1) | QuantLet | 7 | R |
| [DAIIkmeansEM](https://github.com/QuantLet/DAIIkmeansEM) | QuantLet | 7 | R |
| [PGFP](https://github.com/QuantLet/PGFP) | QuantLet | 7 | R |
| [HFHD](https://github.com/QuantLet/HFHD) | QuantLet | 7 | R |
| [Regulatory_Complexity_Germany](https://github.com/QuantLet/Regulatory_Complexity_Germany) | QuantLet | 7 | R |
| [DEDA_Class_2017](https://github.com/QuantLet/DEDA_Class_2017) | QuantLet | 7 | Python |
| [forecastSNSTSexamples](https://github.com/QuantLet/forecastSNSTSexamples) | QuantLet | 7 | R |
| [FVC](https://github.com/QuantLet/FVC) | QuantLet | 7 | R |
| [RegimeSwitching](https://github.com/QuantLet/RegimeSwitching) | QuantLet | 7 | R |
| [HARRV](https://github.com/QuantLet/HARRV) | QuantLet | 7 | R |
| [Dynamics-of-Tail-Event-Curves](https://github.com/QuantLet/Dynamics-of-Tail-Event-Curves) | QuantLet | 7 | R |
| [CRIXdeeplearning](https://github.com/QuantLet/CRIXdeeplearning) | QuantLet | 7 | Python |
| [Cointegration](https://github.com/QuantLet/Cointegration) | QuantLet | 7 | MATLAB |
| [CrixToDate](https://github.com/QuantLet/CrixToDate) | QuantLet | 7 | R |
| [SFE_class_2017](https://github.com/QuantLet/SFE_class_2017) | QuantLet | 7 | Jupyter Notebook |
| [SVR_GARCH_KDE](https://github.com/QuantLet/SVR_GARCH_KDE) | QuantLet | 7 | R |
| [CoVaR](https://github.com/QuantLet/CoVaR) | QuantLet | 7 | R |
| [FCVAR](https://github.com/QuantLet/FCVAR) | QuantLet | 7 | R |
| [DMF](https://github.com/QuantLet/DMF) | QuantLet | 7 | R |
| [pdf_to_text](https://github.com/QuantLet/pdf_to_text) | QuantLet | 7 | Python |
| [OI_Crypto](https://github.com/QuantLet/OI_Crypto) | QuantLet | 7 | R |
| [CascadeLDA](https://github.com/QuantLet/LDA_thesis) | QuantLet | 7 | Python |
| [SRMC](https://github.com/QuantLet/SRMC) | QuantLet | 7 | R |
| [SPL_class_WS1617](https://github.com/QuantLet/SPL_class_WS1617) | QuantLet | 7 | R |
| [SPL_class_SS17](https://github.com/QuantLet/SPL_class_SS17) | QuantLet | 7 | R |
| [Ms_Th_Predict_Poll_From_Emotions](https://github.com/QuantLet/Ms_Th_Predict_Poll_From_Emotions) | QuantLet | 7 | Jupyter Notebook |
| [Improving_Crime_Counts](https://github.com/QuantLet/Improving_Crime_Counts) | QuantLet | 7 | R |
| [SVCJ_crix](https://github.com/QuantLet/SVCJ) | QuantLet | 7 | MATLAB |
| [DEDA_Class_SS2018](https://github.com/QuantLet/DEDA_Class_SS2018) | QuantLet | 7 | Jupyter Notebook |
| [PAM](https://github.com/QuantLet/PAM) | QuantLet | 7 | R |
| [VCRIX](https://github.com/QuantLet/VCRIX) | QuantLet | 7 | R |
| [elephant_wiggle_trunk](https://github.com/QuantLet/FittingElephant) | QuantLet | 7 | Jupyter Notebook |
| [CCP](https://github.com/QuantLet/CCP) | QuantLet | 7 | MATLAB |
| [UCC](https://github.com/QuantLet/UCC) | QuantLet | 7 | Jupyter Notebook |
| [NetworkCASC](https://github.com/QuantLet/NetworkCASC) | QuantLet | 7 | R |
| [LASSO_Time_Space](https://github.com/QuantLet/LASSO_Time_Space) | QuantLet | 7 | R |
| [Spatial_Functional_PCA](https://github.com/QuantLet/Spatial_Functional_PCA) | QuantLet | 7 | R |
| [RiskProfilePortfolio](https://github.com/QuantLet/RiskProfilePortfolio) | QuantLet | 7 | MATLAB |
| [GrangerCausalityTestInQuantile_Simulation](https://github.com/QuantLet/GrangerCausalityTestInQuantile) | QuantLet | 7 | R |
| [DataGenerationForCausalInference](https://github.com/QuantLet/DataGenerationForCausalInference) | QuantLet | 7 | R |
| [CRIX_tedas](https://github.com/QuantLet/CRIX_tedas) | QuantLet | 7 | R |
| [Quantlet_Extraction_Evaluation_Visualisation](https://github.com/QuantLet/Quantlet) | QuantLet | 7 | Python |
| [Localizing_Multivariate_CAViaR](https://github.com/QuantLet/mvcaviar) | QuantLet | 7 | Python |
| [NNQR](https://github.com/QuantLet/NNQR) | QuantLet | 7 | R |
| [MnistDeepLearning](https://github.com/QuantLet/mnistDeepLearning) | QuantLet | 7 | Python |
| [DEDA_SVM](https://github.com/QuantLet/DEDA_SVM) | QuantLet | 7 | Python |
| [SVCJOptionApp](https://github.com/QuantLet/SVCJOptionApp) | QuantLet | 7 | R |
| [BLEM](https://github.com/QuantLet/BLEM) | QuantLet | 7 | R |
| [DistributionalForecasts](https://github.com/QuantLet/DistributionalForecasts.jl) | QuantLet | 7 | Julia |
| [RINFIN](https://github.com/QuantLet/RINFIN) | QuantLet | 7 | R |
| [GMMvb](https://github.com/QuantLet/GMMvb) | QuantLet | 7 | Python |
| [DEDA_Class_2018_StGallen](https://github.com/QuantLet/DEDA_Class_2018_StGallen) | QuantLet | 7 | Python |
| [ICA](https://github.com/QuantLet/ICA) | QuantLet | 7 | R |
| [TalesSentimentTails](https://github.com/QuantLet/TalesSentimentTails) | QuantLet | 7 | R |
| [DEDA_RandForest](https://github.com/QuantLet/DEDA_RandForest) | QuantLet | 7 | Jupyter Notebook |
| [quantile_coherency_replication_pack](https://github.com/QuantLet/quantile_coherency_replication) | QuantLet | 7 | R |
| [PCA-SVM](https://github.com/QuantLet/PCA-SVM) | QuantLet | 7 | R |
| [USC](https://github.com/QuantLet/USC) | QuantLet | 7 | Jupyter Notebook |
| [GMMcluster](https://github.com/QuantLet/GMMcluster) | QuantLet | 7 | Python |
| [SFM_Class_2018_Merton](https://github.com/QuantLet/SFM_Class_2018_Merton) | QuantLet | 7 | R |
| [PP_CPP_Simulation](https://github.com/QuantLet/PP-CPP) | QuantLet | 7 | R |
| [HClustering](https://github.com/QuantLet/HClustering) | QuantLet | 7 | Jupyter Notebook |
| [opp_comp_abalone_analysis](https://github.com/QuantLet/opp_comp_abalone) | QuantLet | 7 | Python |
| [RVOL](https://github.com/QuantLet/RVOL) | QuantLet | 7 | Python |
| [SFEbitreeKO](https://github.com/QuantLet/SFEbitreeKO) | QuantLet | 7 | R |
| [SFM_Class_2018_smart_contracts](https://github.com/QuantLet/SFM_Class_2018_smart_contracts) | QuantLet | 7 | Jupyter Notebook |
| [QNN](https://github.com/QuantLet/QNN) | QuantLet | 7 | R |
| [DEDA_Class_2018WS](https://github.com/QuantLet/DEDA_Class_2018WS) | QuantLet | 7 | HTML |
| [LDA-DTM](https://github.com/QuantLet/LDA-DTM) | QuantLet | 7 | Python |
| [SCG_Scagnostics](https://github.com/QuantLet/SCG_Scagnostics) | QuantLet | 7 | Jupyter Notebook |
| [DeepLearning](https://github.com/QuantLet/DeepLearning) | QuantLet | 7;12 | Jupyter Notebook |
| [VIX](https://github.com/QuantLet/VIX) | QuantLet | 7 | R |
| [ssmmatlab](https://github.com/QuantLet/ssmmatlab) | QuantLet | 7 | MATLAB |
| [awcd](https://github.com/QuantLet/awcd) | QuantLet | 7 | Python |
| [DT_AlphaShape](https://github.com/QuantLet/DT_AlphaShape) | QuantLet | 7 | Jupyter Notebook |
| [ZHAW_FX](https://github.com/QuantLet/ZHAW_FX) | QuantLet | 7 | R |
| [LMVCAViaR](https://github.com/QuantLet/LMVCAViaR) | QuantLet | 7 | MATLAB |
| [Genus_proximum_cryptos](https://github.com/QuantLet/Genus_proximum_cryptos) | QuantLet | 7 | R |
| [RCVJ_Forecasting](https://github.com/QuantLet/RCVJ_Forecasting) | QuantLet | 7 | Python |
| [UYCTReur](https://github.com/QuantLet/UYCTR) | QuantLet | 7 | R |
| [Stat_fin_markets](https://github.com/QuantLet/Stat_fin_markets) | QuantLet | 7 | Jupyter Notebook |
| [SIEVE_application](https://github.com/QuantLet/SIEVE) | QuantLet | 7 |  |
| [Quantlet_Grading](https://github.com/QuantLet/Quantlet_Evaluation) | QuantLet | 7 | Python |
| [ONSM](https://github.com/QuantLet/ONSM) | QuantLet | 7 | Python |
| [XFG_2019SS](https://github.com/QuantLet/XFG_2019SS) | QuantLet | 7 | R |
| [SL_Klagenfurt_2019](https://github.com/QuantLet/SL_Klagenfurt_2019) | QuantLet | 7 | Python |
| [DCA_comparison](https://github.com/QuantLet/DCA_comparison) | QuantLet | 7 | Python |
| [thesis-reinforcement-learning](https://github.com/QuantLet/thesis-reinforcement-learning) | QuantLet | 7 | Python |
| [SoNIC](https://github.com/QuantLet/SoNIC) | QuantLet | 7 | Python |
| [PythonTsa_call_functions](https://github.com/QuantLet/STSM) | QuantLet | 7 | Python |
| [MailProcessingTime](https://github.com/QuantLet/MailProcessingTime) | QuantLet | 7 | Python |
| [SFM_Merton](https://github.com/QuantLet/Hedge) | QuantLet | 7 |  |
| [MLvsGARCH](https://github.com/QuantLet/MLvsGARCH) | QuantLet | 7 | Jupyter Notebook |
| [CCID](https://github.com/QuantLet/CCID) | QuantLet | 7 | R |
| [DEDA_Class_2019SS](https://github.com/QuantLet/DEDA_Class_2019SS) | QuantLet | 7 | Python |
| [NextUnicorn](https://github.com/QuantLet/NextUnicorn) | QuantLet | 7 |  |
| [CRIX_cointegration](https://github.com/QuantLet/CRIX_Cointegration) | QuantLet | 7 | R |
| [HedgingCrix_models_paths](https://github.com/QuantLet/HedgingCRIX) | QuantLet | 7 | Jupyter Notebook |
| [SVCJ_MC](https://github.com/QuantLet/SVCJ_MC) | QuantLet | 7 | Jupyter Notebook |
| [SVCJ_MC](https://github.com/QuantLet/SVCJ_MC-1) | QuantLet | 7 | Jupyter Notebook |
| [EMAIS](https://github.com/QuantLet/EMAIS) | QuantLet | 7 | R |
| [DEDA_class2019_SYSU](https://github.com/QuantLet/DEDA_class2019_SYSU) | QuantLet | 7 | Python |
| [CGBRP](https://github.com/QuantLet/CGBRP) | QuantLet | 7 | MATLAB |
| [CryptoDynamics](https://github.com/QuantLet/CryptoDynamics) | QuantLet | 7 | R |
| [UTSE](https://github.com/QuantLet/UTSER) | QuantLet | 7 | R |
| [DEDA_Class_2019WS](https://github.com/QuantLet/DEDA_Class_2019WS) | QuantLet | 7 | HTML |
| [DigitalEconomyDecisionAnalytics](https://github.com/QuantLet/DigitalEconomyDecisionAnalytics) | QuantLet | 7;8 | HTML |
| [BERT](https://github.com/QuantLet/BERT) | QuantLet | 7 | Jupyter Notebook |
| [SDA_2019_St_Gallen](https://github.com/QuantLet/SDA_2019_St_Gallen) | QuantLet | 7 | HTML |
| [Tenure_Satisfaction](https://github.com/QuantLet/Tenure_Satisfaction) | QuantLet | 7 | R |
| [DR_GATES](https://github.com/QuantLet/DR_GATES) | QuantLet | 7 | R |
| [simulations](https://github.com/QuantLet/CPAsimulations) | QuantLet | 7 | R |
| [CPAoutsample](https://github.com/QuantLet/CPAoutsample) | QuantLet | 7 | R |
| [CPAinsample](https://github.com/QuantLet/CPAinsample) | QuantLet | 7 | R |
| [SFM_Class_2019WS](https://github.com/QuantLet/SFM_Class_2019WS) | QuantLet | 7 | HTML |
| [DEDA_mergers_acquisitions_energy](https://github.com/QuantLet/DEDA_mergers_acquisitions_energy) | QuantLet | 7 | R |
| [InterSwap](https://github.com/QuantLet/SDC) | QuantLet | 7 | Solidity |
| [Regulatory-risk-cryptocurrency](https://github.com/QuantLet/Regulatory-risk-cryptocurrency) | QuantLet | 7 | Python |
| [Scaling_Sierpinski](https://github.com/QuantLet/Scaling_Sierpinski) | QuantLet | 7 | MATLAB |
| [TVP-VAR-Estimation-Workshop](https://github.com/QuantLet/TVP-VAR-Estimation-Workshop) | QuantLet | 7 | MATLAB |
| [SFE_class_2019](https://github.com/QuantLet/SFE_class_2019) | QuantLet | 7 | Python |
| [SC](https://github.com/QuantLet/SC) | QuantLet | 7 | Jupyter Notebook |
| [LLE](https://github.com/QuantLet/LLE) | QuantLet | 7 | Jupyter Notebook |
| [RND_calibration](https://github.com/QuantLet/RND_calibration) | QuantLet | 7 | R |
| [LOBDeepPP](https://github.com/QuantLet/LOBDeepPP) | QuantLet | 7 | Python |
| [Financial Report Analysis BERT W2V GLOVE](https://github.com/QuantLet/Financial-Report-Analysis-BERT-W2V-GLOVE) | QuantLet | 7 | Jupyter Notebook |
| [SL_Klagenfurt_2020](https://github.com/QuantLet/SL_Klagenfurt_2020) | QuantLet | 7 | Jupyter Notebook |
| [CoinGeckoCrawler](https://github.com/QuantLet/CoinGeckoCrawler) | QuantLet | 7 | Python |
| [AdaBoost_P2PL](https://github.com/QuantLet/AdaBoost_P2PL) | QuantLet | 7 | Jupyter Notebook |
| [Financial Report Analysis BERT W2V GLOVE](https://github.com/QuantLet/BERT_financialReportAnalysis) | QuantLet | 7 | Jupyter Notebook |
| [DEDA_class_2020SS](https://github.com/QuantLet/DEDA_class_2020SS) | QuantLet | 7 | Jupyter Notebook |
| [GANTimeSeries](https://github.com/QuantLet/GANTimeSeries) | QuantLet | 7 | Python |
| [plot_crypto_ts](https://github.com/QuantLet/plot_crypto_ts) | QuantLet | 7 | R |
| [pHacking](https://github.com/QuantLet/pHacking) | QuantLet | 7 | R |
| [AOBDL_code](https://github.com/QuantLet/AOBDL_code) | QuantLet | 7 | Jupyter Notebook |
| [Alpha_shapes](https://github.com/QuantLet/alpha_shapes) | QuantLet | 7 | R |
| [loadcrix](https://github.com/QuantLet/loadcrix) | QuantLet | 7 | Jupyter Notebook |
| [KEC](https://github.com/QuantLet/KEC) | QuantLet | 7 | Jupyter Notebook |
| [alphashape_animation](https://github.com/QuantLet/alphashape_animation) | QuantLet | 7 | Jupyter Notebook |
| [GRF](https://github.com/QuantLet/GRF) | QuantLet | 7 | R |
| [SCC_wo_salt_factory](https://github.com/QuantLet/SCC) | QuantLet | 7 | Solidity |
| [loadbtc](https://github.com/QuantLet/LoadBTC) | QuantLet | 7 | Jupyter Notebook |
| [CSC_Dapps](https://github.com/QuantLet/CSC_Dapps) | QuantLet | 7 | Jupyter Notebook |
| [DynamicNets.jl](https://github.com/QuantLet/DynamicNets.jl) | QuantLet | 7 | Julia |
| [waveletcojumps](https://github.com/QuantLet/waveletcojumps) | QuantLet | 7 | HTML |
| [sam2N](https://github.com/QuantLet/sam2N) | QuantLet | 7 | MATLAB |
| [sam](https://github.com/QuantLet/sam) | QuantLet | 7 | MATLAB |
| [frequencyConnectedness](https://github.com/QuantLet/frequencyConnectedness) | QuantLet | 7 | R |
| [quantspec](https://github.com/QuantLet/quantspec) | QuantLet | 7 | R |
| [PQRreturns](https://github.com/QuantLet/PQRreturns) | QuantLet | 7 | R |
| [sinus_animation](https://github.com/QuantLet/sinus_animation) | QuantLet | 7 | Python |
| [CRIXcoin](https://github.com/QuantLet/CRIXStablecoin) | QuantLet | 7 | Solidity |
| [DynamicNets](https://github.com/QuantLet/DynamicNets) | QuantLet | 7 | MATLAB |
| [statsintro_python](https://github.com/QuantLet/statsintro_python) | QuantLet | 7 | HTML |
| [data_driven_controlling](https://github.com/QuantLet/data_driven_controlling) | QuantLet | 7 | Jupyter Notebook |
| [Automated-Cryptocurrency-Portfolios](https://github.com/QuantLet/Automated-Cryptocurrency-Portfolios) | QuantLet | 7 | Python |
| [SDA_2020_Giessen](https://github.com/QuantLet/SDA_2020_Giessen) | QuantLet | 7 | Jupyter Notebook |
| [SDA_2020_NCTU](https://github.com/QuantLet/SDA_2020_NCTU) | QuantLet | 7 | Jupyter Notebook |
| [Spatial_Analysis](https://github.com/QuantLet/Spatial_Analysis) | QuantLet | 7 | Jupyter Notebook |
| [JumpDetectR](https://github.com/QuantLet/JumpDetectR) | QuantLet | 7 | R |
| [SDA_2020_St_Gallen](https://github.com/QuantLet/SDA_2020_St_Gallen) | QuantLet | 7 | Jupyter Notebook |
| [Blockchain_mechanism](https://github.com/QuantLet/Blockchain_mechanism) | QuantLet | 7 | Jupyter Notebook |
| [SurrogateModel](https://github.com/QuantLet/SurrogateModel) | QuantLet | 7 | MATLAB |
| [BitcoinPricingKernels](https://github.com/QuantLet/BitcoinPricingKernels) | QuantLet | 7 | Python |
| [CardSpentplot](https://github.com/QuantLet/CardSpentplot) | QuantLet | 7 | R |
| [Anomaly-Detection](https://github.com/QuantLet/Anomaly-Detection) | QuantLet | 7 | Python |
| [TENET portfolio](https://github.com/QuantLet/Tenet_portfolio) | QuantLet | 7 | R |
| [FRM-EM-paper](https://github.com/QuantLet/FRM-EM-paper) | QuantLet | 7 | Python |
| [Pink_Noise](https://github.com/QuantLet/Pink_Noise) | QuantLet | 7 | Jupyter Notebook |
| [Meta_learner-for-Causal-ML](https://github.com/QuantLet/Meta_learner-for-Causal-ML) | QuantLet | 7 | R |
| [SVCJrw](https://github.com/QuantLet/SVCJrw) | QuantLet | 7 | R |
| [CBR-FRD](https://github.com/QuantLet/CBR-FRD) | QuantLet | 7 | Python |
| [MANDATORY! Has to be the same as the Quantlet file, without file type ending, e.g. R,py,...](https://github.com/QuantLet/SDA_2021_NUS) | QuantLet | 7 | Jupyter Notebook |
| [FRM_Expectile](https://github.com/QuantLet/FRM_Expectile) | QuantLet | 7 | R |
| [UMAP_sim_ts](https://github.com/QuantLet/Dimension-Reduction-Techniques) | QuantLet | 7 | Jupyter Notebook |
| [MANDATORY! Has to be the same as the Quantlet file, without file type ending, e.g. R,py,...](https://github.com/QuantLet/DEDA-SoSe2021) | QuantLet | 7 | Jupyter Notebook |
| [KF_modelres](https://github.com/QuantLet/KF_modelres) | QuantLet | 7 | R |
| [MANDATORY! Has to be the same as the Quantlet file, without file type ending, e.g. R,py,...](https://github.com/QuantLet/Example_quantlet) | QuantLet | 7 | Python |
| [UMAP](https://github.com/QuantLet/UMAP) | QuantLet | 7 | Jupyter Notebook |
| [localpoly](https://github.com/QuantLet/localpoly) | QuantLet | 7 | Python |
| [pricing_kernel_uniform_confidence_bands](https://github.com/QuantLet/pricing_kernel_uniform_confidence_bands) | QuantLet | 7 | R |
| [PAC_CV_GCV](https://github.com/QuantLet/PAC_CV_GCV) | QuantLet | 7 | Jupyter Notebook |
| [evaluation_indices](https://github.com/QuantLet/evaluation_indices) | QuantLet | 7 | R |
| [CRIXForecastApp](https://github.com/QuantLet/CRIXForecastApp) | QuantLet | 7 | R |
| [Projected_IFE](https://github.com/QuantLet/Projected_IFE) | QuantLet | 7 | R |
| [1d_GAN](https://github.com/QuantLet/1d_GAN) | QuantLet | 7 | Jupyter Notebook |
| [Metis-Shapley](https://github.com/QuantLet/Metis-Shapley) | QuantLet | 7 | Jupyter Notebook |
| [Outcome-adaptive-Random-Forest](https://github.com/QuantLet/Outcome-adaptive-Random-Forest) | QuantLet | 7 | R |
| [Supervised-Randomization](https://github.com/QuantLet/Supervised-Randomization) | QuantLet | 7 | R |
| [BitcoinOptionTrading](https://github.com/QuantLet/BitcoinOptionTrading) | QuantLet | 7 | Python |
| [FRM_Quantlet_China](https://github.com/QuantLet/FRM_Quantlet_China) | QuantLet | 7 | MATLAB |
| [RobustM](https://github.com/QuantLet/RobustM) | QuantLet | 7 | R |
| [VAR_Example](https://github.com/QuantLet/VAR_Example) | QuantLet | 7 | Jupyter Notebook |
| [VAR_Metis](https://github.com/QuantLet/VAR_Metis) | QuantLet | 7 | Jupyter Notebook |
| [NetworksofNews_CrossSectionalReturns](https://github.com/QuantLet/NetworksofNews_CrossSectionalReturns) | QuantLet | 7 | Python |
| [GAN_TS_stacking](https://github.com/QuantLet/GAN_TS_stacking) | QuantLet | 7 | Jupyter Notebook |
| [statsintro-python-2e](https://github.com/QuantLet/statsintro-python-2e) | QuantLet | 7 | Jupyter Notebook |
| [Cryptocurrencies_and_Stablecoins](https://github.com/QuantLet/Cryptocurrencies-and-Stablecoins-a-high-frequency-analysis) | QuantLet | 7 | Scala |
| [DEDA_Class_2021WS](https://github.com/QuantLet/DEDA_Class_2021WS) | QuantLet | 7 |  |
| [EmbeddingPortfolio](https://github.com/QuantLet/EmbeddingPortfolio) | QuantLet | 7 | Jupyter Notebook |
| [SDA_2021_St_Gallen](https://github.com/QuantLet/SDA_2021_St_Gallen) | QuantLet | 7 | Jupyter Notebook |
| [COVID_Risk_Narratives](https://github.com/QuantLet/COVID_Risk_Narratives_for_DFIN) | QuantLet | 7 | Jupyter Notebook |
| [indices_ccVStrad](https://github.com/QuantLet/indices_ccVStrad) | QuantLet | 7 | R |
| [Hedging Effectiveness Plots](https://github.com/QuantLet/Hedging-Effectiveness-Plots) | QuantLet | 7 | HTML |
| [Portfolio_Diversification_Risk_Clustering](https://github.com/QuantLet/Portfolio_Diversification_Risk_Clustering) | QuantLet | 7 | Jupyter Notebook |
| [hedging_cc](https://github.com/QuantLet/hedging_cc) | QuantLet | 7 | Jupyter Notebook |
| [EPF](https://github.com/QuantLet/EPF) | QuantLet | 7 | Jupyter Notebook |
| [CBR-BK](https://github.com/QuantLet/CBR_BK) | QuantLet | 7 | Python |
| [Quantlets as NFT](https://github.com/QuantLet/quantinar_nft) | QuantLet | 7 | Python |
| [SDA_2021_HeartFailure](https://github.com/QuantLet/SDA_2021_HeartFailure) | QuantLet | 7 | Jupyter Notebook |
| [ChristmasTree](https://github.com/QuantLet/ChristmasTree) | QuantLet | 7 | Python |
| [DEDA_class_WS21](https://github.com/QuantLet/DEDA_class_WS21) | QuantLet | 7 | R |
| [pyTSA](https://github.com/QuantLet/pyTSA) | QuantLet | 7 | Python |
| [CP2P](https://github.com/QuantLet/CP2P) | QuantLet | 7 | Jupyter Notebook |
| [SFM_Rough_Rice_Futures_Price](https://github.com/QuantLet/21-SFM1-TS-Project-Xingjia-Wang) | QuantLet | 7 | Jupyter Notebook |
| [SGX_reports](https://github.com/QuantLet/SGX_reports) | QuantLet | 7 | Python |
| [Word-cloud-Search-engine-optimisation](https://github.com/QuantLet/Word-cloud-Search-engine-optimisation-) | QuantLet | 7 | Jupyter Notebook |
| [Metis_GMM](https://github.com/QuantLet/Metis_GMM) | QuantLet | 7 | R |
| [Metis_MST](https://github.com/QuantLet/Metis_MST) | QuantLet | 7 | Jupyter Notebook |
| [py-RobustM](https://github.com/QuantLet/py-RobustM) | QuantLet | 7 | Python |
| [Encode-the-Qode](https://github.com/QuantLet/Encode-the-Qode) | QuantLet | 7 | Jupyter Notebook |
| [Markowitz Portfolio](https://github.com/QuantLet/Network-Structure-Portfolio) | QuantLet | 7 | R |
| [p2pInterestRate](https://github.com/QuantLet/p2pInterestRate) | QuantLet | 7 | Jupyter Notebook |
| [network_BTC_exchanges](https://github.com/QuantLet/network_BTC_exchanges) | QuantLet | 7 | R |
| [CRIX_ETF](https://github.com/QuantLet/CRIX_ETF) | QuantLet | 7 | R |
| [SMLSM](https://github.com/QuantLet/SMLSM) | QuantLet | 7 | Python |
| [UStatistics](https://github.com/QuantLet/UStatistics) | QuantLet | 7 | Jupyter Notebook |
| [DEIS](https://github.com/QuantLet/RoboAdvisors) | QuantLet | 7 | Python |
| [BitcoinOptions](https://github.com/QuantLet/BitcoinOptions) | QuantLet | 7 | Python |
| [Solidity-Lottery](https://github.com/QuantLet/Solidity-Lottery) | QuantLet | 7 | Solidity |
| [DEDA_2022_NYCU](https://github.com/QuantLet/DEDA_2022_NYCU) | QuantLet | 7;8 | Jupyter Notebook |
| [Deribit_inverse_BTC_options](https://github.com/QuantLet/Deribit_inverse_BTC_options) | QuantLet | 7 | MATLAB |
| [hf.econometrics](https://github.com/QuantLet/hf.econometrics) | QuantLet | 7 | R |
| [Network-portfolio](https://github.com/QuantLet/Network-portfolio) | QuantLet | 7 | R |
| [fit_IV_DEJD](https://github.com/QuantLet/fit_IV_DEJD) | QuantLet | 7 | Jupyter Notebook |
| [IV_implied_fair_premium_curves](https://github.com/QuantLet/IV_implied_fair_premium_curves) | QuantLet | 7 | Jupyter Notebook |
| [Quantinar-Staking-Simulation](https://github.com/QuantLet/Quantinar-Staking-Simulation) | QuantLet | 7 | Python |
| [Shapley_Smoothing](https://github.com/QuantLet/Shapley_Smoothing) | QuantLet | 7 | Jupyter Notebook |
| [DAI_digital_art_index](https://github.com/QuantLet/DAI_digital_art_index) | QuantLet | 7 | Jupyter Notebook |
| [SDA_2022_St_Gallen](https://github.com/QuantLet/SDA_2022_St_Gallen) | QuantLet | 7 | Python |
| [Deribit_inverse_BTC_options_hedging](https://github.com/QuantLet/Deribit_inverse_BTC_options_hedging) | QuantLet | 7 | Jupyter Notebook |
| [quantinar-keycloak-theme](https://github.com/QuantLet/quantinar-keycloak-theme) | QuantLet | 7 | FreeMarker |
| [QuantinarRep](https://github.com/QuantLet/quantinar-rep) | QuantLet | 7 | Python |
| [Hedging-Cryptos-with-Bitcoin-Futures](https://github.com/QuantLet/Hedging-Cryptos-with-Bitcoin-Futures) | QuantLet | 7 | HTML |
| [Pricing_kernel_crypto](https://github.com/QuantLet/Pricing_kernel_crypto) | QuantLet | 7 |  |
| [alpha_t-RIM](https://github.com/QuantLet/alpha_t-RIM) | QuantLet | 7 | Jupyter Notebook |
| [CACrypto](https://github.com/QuantLet/CACrypto) | QuantLet | 7 | Jupyter Notebook |
| [Multifractal_Models_in_Finance](https://github.com/QuantLet/Multifractal_Models_in_Finance) | QuantLet | 7 | Jupyter Notebook |
| [HAND](https://github.com/QuantLet/HAND) | QuantLet | 7 | Jupyter Notebook |
| [PyIntro](https://github.com/QuantLet/PyIntro) | QuantLet | 7 | Jupyter Notebook |
| [DEDA_class_SoSe2023](https://github.com/QuantLet/DEDA_class_SoSe2023) | QuantLet | 7 | Jupyter Notebook |
| [Robust_M_CC](https://github.com/QuantLet/Robust_M_CC) | QuantLet | 7 | R |
| [CryptoVolumeForecasting](https://github.com/QuantLet/CryptoVolumeForecasting) | QuantLet | 7 | Python |
| [SRMforDA](https://github.com/QuantLet/SRMforDA) | QuantLet | 7 | R |
| [Spectral_Risk_Measure_SRM_METIS](https://github.com/QuantLet/Spectral_Risk_Measure_SRM_METIS) | QuantLet | 7 | Jupyter Notebook |
| [MPF-Electricity](https://github.com/QuantLet/MPF-Electricity) | QuantLet | 7 | Jupyter Notebook |
| [Ethereum-Energy-Consumption](https://github.com/QuantLet/Ethereum-Energy-Consumption) | QuantLet | 7 |  |
| [Metcalfes-Law-and-Cryptocurrencies](https://github.com/QuantLet/Metcalfes-Law-and-Cryptocurrencies) | QuantLet | 7 | Jupyter Notebook |
| [osppaa_2021](https://github.com/QuantLet/osppaa_2021) | QuantLet | 7 | R |
| [csaamoe_2021](https://github.com/QuantLet/csaamoe_2021) | QuantLet | 7 | Python |
| [msic-dasoq_2019](https://github.com/QuantLet/msic-dasoq_2019) | QuantLet | 7 | R |
| [catvom_2021](https://github.com/QuantLet/catvom_2021) | QuantLet | 7 | TeX |
| [Math-Stat-Chap01-prob](https://github.com/QuantLet/Math-Stat-Chap01-prob) | QuantLet | 7 | Jupyter Notebook |
| [FRM_RO](https://github.com/QuantLet/FRM_RO) | QuantLet | 7 | HTML |
| [VizTech](https://github.com/QuantLet/VizTech) | QuantLet | 7 | Jupyter Notebook |
| [HawkesProcesses](https://github.com/QuantLet/HawkesProcesses) | QuantLet | 7 | Jupyter Notebook |
| [Stochvolmodels](https://github.com/QuantLet/Stochvolmodels) | QuantLet | 7 | Jupyter Notebook |
| [TDFA](https://github.com/QuantLet/TDFA) | QuantLet | 7 | R |
| [IDA](https://github.com/QuantLet/IDA) | QuantLet | 7 | Jupyter Notebook |
| [Chinese-Word-Cloud](https://github.com/QuantLet/Chinese-Word-Cloud) | QuantLet | 7 | Python |
| [PAV-Pool-Adjacent-Violator](https://github.com/QuantLet/PAV-Pool-Adjacent-Violator) | QuantLet | 7 | Jupyter Notebook |
| [FRM-Taiwan](https://github.com/QuantLet/FRM-Taiwan) | QuantLet | 7;8 | Jupyter Notebook |
| [Emoji-Embedding-For-Finance](https://github.com/QuantLet/Emoji-Embedding-For-Finance) | QuantLet | 7 | Jupyter Notebook |
| [CSBD_Project](https://github.com/QuantLet/CSBD_Project) | QuantLet | 7 | HTML |
| [SDA_2023_Rental_Prices](https://github.com/QuantLet/SDA_2023_Rental_Prices) | QuantLet | 7 | Python |
| [20231215-Moc-Far-Stat-Arbitrage-LSTM-US-Tech](https://github.com/QuantLet/20231215-Moc-Far-Stat-Arbitrage-LSTM-US-Tech) | QuantLet | 7 | Jupyter Notebook |
| [TY_TreasuryYield](https://github.com/QuantLet/TY_TreasuryYield) | QuantLet | 7 | Python |
| [Covid-RO](https://github.com/QuantLet/Covid-RO) | QuantLet | 7 | Jupyter Notebook |
| [Data-Science-math-less-Digital-Society](https://github.com/QuantLet/Data-Science-math-less-Digital-Society) | QuantLet | 7 | HTML |
| [np_var_mis](https://github.com/QuantLet/np_var_mis) | QuantLet | 7 | Jupyter Notebook |
| [FRM_Quantlet_Crypto](https://github.com/QuantLet/FRM_Quantlet_Crypto) | QuantLet | 7 | R |
| [Industrial-Picture-Classification-via-SVM](https://github.com/QuantLet/Industrial-Picture-Classification-via-SVM) | QuantLet | 7 | Jupyter Notebook |
| [HJP](https://github.com/QuantLet/HJP) | QuantLet | 7 | Jupyter Notebook |
| [QReg_engel_curve](https://github.com/QuantLet/QReg_engel_curve) | QuantLet | 7 | Python |
| [BoostExamples](https://github.com/QuantLet/BoostExamples) | QuantLet | 7 | Jupyter Notebook |
| [Recommendation-System](https://github.com/QuantLet/Recommendation-System) | QuantLet | 7 | Jupyter Notebook |
| [Cross-Section-and-Panel-Data-H](https://github.com/QuantLet/Cross-Section-and-Panel-Data-H) | QuantLet | 7 | Jupyter Notebook |
| [BigDataIndex](https://github.com/QuantLet/BigDataIndex) | QuantLet | 7 | Jupyter Notebook |
| [EM_Algorithm](https://github.com/QuantLet/EM_Algorithm) | QuantLet | 7 | R |
| [Rough Volatility with Correlated Jumps](https://github.com/QuantLet/rough_vola_hawkes) | QuantLet | 7 | Python |
| [DEDA_2024_NYCU](https://github.com/QuantLet/DEDA_2024_NYCU) | QuantLet | 7;8 | Python |
| [PricingKernelBspline](https://github.com/QuantLet/PricingKernelBspline) | QuantLet | 7 | Jupyter Notebook |
| [Metcalfe_Law_and_LPPL_Crypto](https://github.com/QuantLet/Metcalfe_Law_and_LPPL_Crypto) | QuantLet | 7;15 | Jupyter Notebook |
| [LLM-Examples](https://github.com/QuantLet/LLM-Examples) | QuantLet | 7 | Jupyter Notebook |
| [CCIndexRisk](https://github.com/QuantLet/CCIndexRisk) | QuantLet | 7 | R |
| [Herding](https://github.com/QuantLet/Herding) | QuantLet | 7 | HTML |
| [pylpa](https://github.com/QuantLet/pylpa) | QuantLet | 7 | Python |
| [DEDA_word_embeddings_BERT_examples](https://github.com/QuantLet/DEDA_word_embeddings_BERT_examples) | QuantLet | 7 | Jupyter Notebook |
| [sent-vol-network](https://github.com/QuantLet/sent-vol-network) | QuantLet | 7 | R |
| [EM-App-CPI](https://github.com/QuantLet/EM-App-CPI) | QuantLet | 7 | R |
| [DigitalFinance](https://github.com/QuantLet/DigitalFinance) | QuantLet | 7 | Jupyter Notebook |
| [DEDA_class_SoSe2024](https://github.com/QuantLet/DEDA_class_SoSe2024) | QuantLet | 7 | Jupyter Notebook |
| [CBECopBTCETH](https://github.com/QuantLet/CBECopBTCETH) | QuantLet | 7 | R |
| [2024-XAI-Intro](https://github.com/QuantLet/2024-XAI-Intro) | QuantLet | 7 | Jupyter Notebook |
| [quantinar_recommender](https://github.com/QuantLet/quantinar_recommender) | QuantLet | 7 | Python |
| [Bayesian_Statistics](https://github.com/QuantLet/Bayesian_Statistics) | QuantLet | 7 | Jupyter Notebook |
| [BitMood](https://github.com/QuantLet/BitMood) | QuantLet | 7 | Jupyter Notebook |
| [Bootstrap](https://github.com/QuantLet/Bootstrap) | QuantLet | 7 | R |
| [PricingKernel_NonMonotone](https://github.com/QuantLet/PricingKernel_NonMonotone) | QuantLet | 7 | Python |
| [Meta_Learning_Monitoring_Source_Code](https://github.com/QuantLet/Meta_Learning_Monitoring_Source_Code) | QuantLet | 7 | Jupyter Notebook |
| [Energy Price Modelling A comparative Evaluation of Four Generations of Forecasting Methods](https://github.com/QuantLet/AI4EFin) | QuantLet | 7 | Jupyter Notebook |
| [DEDA Course - Group 3 Homework: Capturing the Baijiu(白酒) Industry Landscape](https://github.com/QuantLet/DEDA_2024_fdu_g3final) | QuantLet | 7 | Python |
| [DEDA_Final_Project_DEDA_Fudan_Group2](https://github.com/QuantLet/-DEDA2024_FUDAN_Group2_Final-Project) | QuantLet | 7 | Python |
| [HashRecommendation](https://github.com/QuantLet/HashRecommendation) | QuantLet | 7 | Jupyter Notebook |
| [ATSSB-Applied-Time-Series-Solutions-Book](https://github.com/QuantLet/ATSSB-Applied-Time-Series-Solutions-Book) | QuantLet | 7 | Jupyter Notebook |
| [Crypto_Currency_Returns](https://github.com/QuantLet/Crypto_Currency_Returns) | QuantLet | 7;8 | Jupyter Notebook |
| [ETH_Event_Study](https://github.com/QuantLet/ETH_Event_Study) | QuantLet | 7 | R |
| [LLM4Forecasting](https://github.com/QuantLet/LLM4Forecasting) | QuantLet | 7;12 | Jupyter Notebook |
| [LLM-Risk](https://github.com/QuantLet/LLM_Risk) | QuantLet | 7 | Jupyter Notebook |
| [timeseries](https://github.com/QuantLet/timeseries) | QuantLet | 7 | Jupyter Notebook |
| [02_analyses_parallel](https://github.com/QuantLet/convergence) | QuantLet | 7 | R |
| [SOM](https://github.com/QuantLet/SOM) | QuantLet | 7 | Jupyter Notebook |
| [Quantlet_The_Code_Snippet_Knowledge_Platform](https://github.com/QuantLet/Quantlet_The_Code_Snippet_Knowledge_Platform) | QuantLet | 7 | Python |
| [Dogecoin and Speculative Bubbles: A Study Using LPPL and Sentiment Analysis](https://github.com/QuantLet/Dogecoin-and-Speculative-Bubbles) | QuantLet | 7 | Jupyter Notebook |
| [crypto_loan_plots](https://github.com/QuantLet/crypto_loan_plots) | QuantLet | 7 | Jupyter Notebook |
| [Volatility Jumps and Pricing Kernel Features: A Study Comparing the Classical and CDI Estimation Method](https://github.com/QuantLet/Volatility-Jumps-and-Pricing-Kernel-Features) | QuantLet | 7 | Jupyter Notebook |
| [Hierarchical Loan forecasting : A study of End-to-End coherent models](https://github.com/QuantLet/Hierarchical-Loan-Forecasting) | QuantLet | 7;14 | Jupyter Notebook |
| [Decomposing-Stock-Factors](https://github.com/QuantLet/Decomposing-Stock-Factors) | QuantLet | 7;15 | Jupyter Notebook |
| [CentralBank2StockMarket](https://github.com/QuantLet/CentralBank2StockMarket) | QuantLet | 7;12 | Jupyter Notebook |
| [Energy_Stock_Market](https://github.com/QuantLet/Energy_Stock_Market) | QuantLet | 7 | Jupyter Notebook |
| [sent-spillover](https://github.com/QuantLet/sent-spillover) | QuantLet | 7 |  |
| [Fraud Detection](https://github.com/QuantLet/Fraud-Detection-Demo) | QuantLet | 7;8 | Jupyter Notebook |
| [AIAdoptionEU](https://github.com/QuantLet/AIAdoptionEU) | QuantLet | 7 | Jupyter Notebook |
| [Econometrics_R](https://github.com/QuantLet/Econometrics_R) | QuantLet | 7 | R |
| [RO_Electricity_Forecasting](https://github.com/QuantLet/RO_Electricity_Forecasting) | QuantLet | 7 | Python |
| [WP3_eXplainable_and_Fair_AI](https://github.com/QuantLet/WP3_eXplainable_and_Fair_AI) | QuantLet | 1;12;17 |  |
| [Courses](https://github.com/QuantLet/Courses) | QuantLet | 1;7;8;9;11;12;13;14 | Jupyter Notebook |
| [Marginal Effect for ordinal data](https://github.com/QuantLet/Data-reduction) | QuantLet | 7 | R |
| [GRU](https://github.com/QuantLet/GRU) | QuantLet | 7;12 | Jupyter Notebook |
| [QNAR_RS](https://github.com/QuantLet/QNAR_RS) | QuantLet | 7 | Jupyter Notebook |
| [Explainable AI for Electricity Price Anomaly Detection](https://github.com/QuantLet/Explainable-AI-for-Electricity-Price-Anomaly-Detection) | QuantLet | 7 | Jupyter Notebook |
| [Multi-objective Explainable AI for Romanian Electricity Price Analysis](https://github.com/QuantLet/Multi_objective_XAI_Romanian_Electricity_Price_Analysis) | QuantLet | 7 | Jupyter Notebook |
| [DEDA_2025_CUEB](https://github.com/QuantLet/DEDA_2025_CUEB) | QuantLet | 7;8 | Jupyter Notebook |
| [Stable_Distribution](https://github.com/QuantLet/Stable_Distribution) | QuantLet | 7;12 | Jupyter Notebook |
| [SDexamples](https://github.com/QuantLet/SDexamples) | QuantLet | 7 | Jupyter Notebook |
| [Proper Scoring Rules](https://github.com/QuantLet/Proper-Scoring-Rules) | QuantLet | 7;14 | Jupyter Notebook |
| [Quantile_Treatment](https://github.com/QuantLet/QuantileRegression_Treatment) | QuantLet | 7 | R |
| [QuantLet_NLP_Introduction](https://github.com/QuantLet/QuantLet_NLP_Introduction) | QuantLet | 7 | Jupyter Notebook |
| [Empirical-Mode-Decomposition](https://github.com/QuantLet/Empirical-Mode-Decomposition) | QuantLet | 7 | Jupyter Notebook |
| [AR_sim_p](https://github.com/QuantLet/AR_sim_p) | QuantLet | 7 | Python |
| [LPA_AR](https://github.com/QuantLet/LPA_AR) | QuantLet | 7 | Jupyter Notebook |
| [SHAP_AR](https://github.com/QuantLet/SHAP_AR) | QuantLet | 7 | Jupyter Notebook |
| [FRM_Stable_Coins](https://github.com/QuantLet/FRM_Stable_Coins) | QuantLet | 7 | R |
| [LPA_LSTM](https://github.com/QuantLet/LPA_LSTM) | QuantLet | 7 | Jupyter Notebook |
| [LLMs-for-BTC-TS](https://github.com/QuantLet/LLMs-for-BTC-TS) | QuantLet | 7;14 | Jupyter Notebook |
| [SHAP_LSTM](https://github.com/QuantLet/SHAP_LSTM) | QuantLet | 7 | Jupyter Notebook |
| [Crypto_Zombies](https://github.com/QuantLet/Crypto_Zombies) | QuantLet | 7 | R |
| [2025_HTW_ESG_Portfolio_Optimization](https://github.com/QuantLet/ESG-Portfolio-Optimization) | QuantLet | 7;8;12 | Jupyter Notebook |
| [AdaptiveWIN-SHAP](https://github.com/QuantLet/AdaptiveWIN-SHAP) | QuantLet | 7 | Python |
| [BCN-Seminar](https://github.com/QuantLet/BCN-Seminar) | QuantLet | 7 | Python |
| [Hierarchical Time Series : A geometric approach](https://github.com/QuantLet/HTS_visualization) | QuantLet | 7;14 | Jupyter Notebook |
| [Insider trading Financial Forensics](https://github.com/QuantLet/Insider-Trading-Prediction) | QuantLet | 7 | Jupyter Notebook |
| [CARDI](https://github.com/QuantLet/CARDI) | QuantLet | 7 | R |
| [neural-networks-introduction](https://github.com/QuantLet/neural-networks-introduction) | QuantLet | 7 | Python |
| [Whitepaper_CC_Indices](https://github.com/QuantLet/Whitepaper_CC_Indices) | QuantLet | 7 | Python |
| [A_New_EMD_Approach](https://github.com/QuantLet/A_New_EMD_Approach) | QuantLet | 7;8 | Jupyter Notebook |
| [OnlineMonitoring_FunctionalTS_ARSN](https://github.com/QuantLet/OnlineMonitoring_FunctionalTS_ARSN) | QuantLet | 7 | R |
| [01 FINDER-LLM](https://github.com/QuantLet/FINDER-LLM) | QuantLet | 7;8;12 | Jupyter Notebook |
| [fulvio-PhD](https://github.com/QuantLet/fulvio-PhD) | QuantLet | 13 |  |
| [Onchain Insights](https://github.com/QuantLet/onchain-insights) | QuantLet | 7;8;14 | Jupyter Notebook |
| [EMQA](https://github.com/QuantLet/EMQA) | QuantLet | 7 | Jupyter Notebook |
| [TSA](https://github.com/QuantLet/TSA) | QuantLet | 7 | Jupyter Notebook |
| [Energy Demand ETH](https://github.com/QuantLet/Energy_Demand_ETH) | QuantLet | 7 | Python |
| [A counterfactual analysis of Romania’s 2024 energy crisis](https://github.com/QuantLet/Counterfactual-analysis-Romania-energy-crisis) | QuantLet | 7 | Jupyter Notebook |
| [Multi-horizon explainability in Romania's energy price forecasting](https://github.com/QuantLet/Multi-horizon-explainability-in-Romania-s-energy-price-forecasting) | QuantLet | 7 | Jupyter Notebook |
| [Explainable AI-based early warning system for electricity price spikes: evidence from the Romanian market](https://github.com/QuantLet/Explainable-AI-based-early-warning-system-for-electricity-price-spikes) | QuantLet | 7 | Jupyter Notebook |
| [BCN-XMU-course2026](https://github.com/QuantLet/BCN-XMU-course2026) | QuantLet | 7 | Jupyter Notebook |
| [Transparent-Movie](https://github.com/QuantLet/Transparent-Movie-Instruction) | QuantLet | 7;8 | Jupyter Notebook |
| [NN_DL](https://github.com/QuantLet/NN_DL) | QuantLet | 7 | Jupyter Notebook |
| [AI_Listening2CB](https://github.com/QuantLet/AI_Listening2CB) | QuantLet | 12 | Jupyter Notebook |
| [Network_Centrality](https://github.com/QuantLet/Network_Centrality) | QuantLet | 7;14 | Jupyter Notebook |
| [TSFM_VaR_CEE](https://github.com/QuantLet/TSFM_VaR_CEE) | QuantLet | 7;8 | Jupyter Notebook |
| [DEDA-HUB-Quantlets](https://github.com/QuantLet/DEDA-HUB-Quantlets) | QuantLet | 7 | Jupyter Notebook |
| [XAI_beyond_SHAP](https://github.com/QuantLet/XAI_beyond_SHAP) | QuantLet | 14 |  |
| [Spline EMD vs. IRMF Test](https://github.com/QuantLet/Spline-EMD-vs.-IRMF-Test) | QuantLet | 7 | Python |
| [IDA Team](https://github.com/QuantLet/IDA_Team) | QuantLet | 7 | Python |
| [DEDAcryptoBasket](https://github.com/QuantLet/Crypto-index-coding-eamples) | QuantLet | 7 | Jupyter Notebook |
| [GNN_XAI_Stability](https://github.com/QuantLet/GNN_XAI_Stability) | QuantLet | 7 | Python |
| [DEDAcryptoBasket](https://github.com/QuantLet/Crypto-index-coding-examples) | QuantLet | 7 | Jupyter Notebook |
| [IDA_FRMspillover](https://github.com/QuantLet/SPARC_FRMspillover) | QuantLet | 7 | Python |
| [IDA_localising](https://github.com/QuantLet/SPARC_localising) | QuantLet | 7 | Python |
| [USGDPGrowth](https://github.com/QuantLet/ATSSB_-USGDPGrowth) | QuantLet | 7 | Python |
| [MSR](https://github.com/QuantLet/MSR) | QuantLet | 7 | Jupyter Notebook |
| [SYNCRISK](https://github.com/QuantLet/SYNCRISK) | QuantLet | 7 | Python |
| [CBDC](https://github.com/QuantLet/CBDC) | QuantLet | 7 | Jupyter Notebook |
| [Redispatch_ML_Forecasting](https://github.com/QuantLet/redispatch-ml-forecasting) | QuantLet | 7 | Jupyter Notebook |
| [IRMF-Intrinsic-Robust-Multiscale-Filtering](https://github.com/QuantLet/IRMF-Intrinsic-Robust-Multiscale-Filtering) | QuantLet | 7 | Python |
| [FATED-Polymarket](https://github.com/QuantLet/FATED-Polymarket) | QuantLet | 7;14 | Jupyter Notebook |
| [STMS_Delta](https://github.com/QuantLet/Delta-Method) | QuantLet | 7;15 | Jupyter Notebook |
| [Electricity-Portfolio-Hedging](https://github.com/QuantLet/Electricity-Portfolio-Hedging) | QuantLet | 8 | Jupyter Notebook |
| [AlphaLuck](https://github.com/QuantLet/AlphaLuck) | QuantLet | 7 | Python |
| [Polymarked](https://github.com/QuantLet/Polymarked) | QuantLet | 14 |  |
| [Code and Data for Reinforcement Learning in Finance: From Current Practice to Standards and Frameworks](https://github.com/MSCA-DN-Digital-Finance/WP3_eXplainable_and_Fair_AI/tree/f84806bad3edebba538633870a57ce81eaf511e5/IRP1/Code/systematic_literature_review) | Other | 1 | Python |
| [MSCA-DN-Digital-Finance/stablecoin-onchain-data: DeFi hourly datasets data-2026-02-02](https://github.com/MSCA-DN-Digital-Finance/stablecoin-onchain-data) | Other | 14 |  |
<!-- END SOFTWARE -->
