# SWaT Report Generator
The SWaT (Secure Water Treatment) Report Generator is used to securely view large datasets detailing incident logs by producing simple and condensed diagrams directly from the data.

> The application is intentionally small. The CI/CD pipeline is the focus of this project, and the report generator exists to give the pipeline something real to test, build, scan, and deploy.

## Application Overview
[![CI](https://github.com/cdmarian21/swat-report-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/cdmarian21/swat-report-generator/actions/workflows/ci.yml)
[![Build](https://github.com/cdmarian21/swat-report-generator/actions/workflows/build.yml/badge.svg)](https://github.com/cdmarian21/swat-report-generator/actions/workflows/build.yml)
[![Deploy](https://github.com/cdmarian21/swat-report-generator/actions/workflows/deploy.yml/badge.svg)](https://github.com/cdmarian21/swat-report-generator/actions/workflows/deploy.yml)

**[Live report →](https://cdmarian21.github.io/swat-report-generator/)**

The generator reads a SWaT historian CSV and produces a static HTML report, with no external assets. 

For each labeled attack it shows:

- an **attack timeline** with start/end times,
- the **primary sensor/actuator targets**,
- an **attack-type category** — *Sensor Spoofing*, *Valve Manipulation*, or *Pump Override*, and
- **behavior during the attack window vs. the normal baseline** (mean, min, max, and percent deviation, with significant anomalies or deviations flagged).

**About the dataset:** SWaT (Secure Water Treatment) is an ICS testbed created by iTrust, SUTD. This dataset (SWaT.A12, Mar 2026) is an 8-hour run sampled once per second with 28,861 rows × 87 columns detailing the six water treatment process stages (P1–P6). The first 4 hours are normal operation, and the second 4 hours contain **11 labeled cyberattacks** with known timestamps and targets. Each column name encodes its type: .Pv = sensor reading, .Status = actuator state, .Speed = pump speed, _STATE = process state, .Alarm = alarm state.

**Why the real dataset isn't in this repo:** The full CSV is sensitive operational ICS data, licensed by iTrust, and too large for source control. Committing it to a public repo would breach the license and leak operational data. Instead, a seeded mock-data generator produces a mock data in the form of a CSV for CI and the public demo, while the real file is swapped in locally (see [Instructions to Run](#instructions-to-run)). The .gitignore enforces this, so the dataset can never be committed by accident.

## Repository Layout

```
swat-report-generator/
├── src/
│   ├── attacks.py             # the 11-attack catalogue (domain model)
│   ├── schema.py              # 87-column schema + type classifier
│   ├── generate_mock_data.py  # synthetic CSV (same dimensions as real CSV)
│   └── generate_report.py     # CSV -> self-contained HTML report
├── data/                      # real/mock CSV lives here (gitignored)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml             # SAST + dependency audit
│   │   ├── build.yml          # build, scan, SBOM, push to GHCR
│   │   └── deploy.yml         # generate report, publish to Pages
│   └── dependabot.yml         # dependency updates (pip, actions, docker)
├── Dockerfile                 # multi-stage, non-root, patched base
├── requirements.txt           # single pinned runtime dependency (pandas)
└── README.md
```

## Pipeline Details

Workflow steps: test (on every change) -> build a scanned artifact (on merge) -> publish (on version tag). Each workflow declares the necessary permissions to fulfill its task, granting the token of only the scope that the job needs (least privilege).

### CI — ci.yml
**Trigger:** every push/pull request to main
**Permissions:** contents: read

| Step | Why it exists |
|------|---------------|
| Checkout + set up Python 3.12 | Exists to prepare the runner |
| pytest | runs unit + smoke tests so a broken app fails CI, not only insecure code |
| bandit -r src --severity-level high | catches insecure Python source code and fails the job on a high severity faults (SAST) |
| pip-audit -r requirements.txt | fails the job if a dependency has a known vulnerability (SCA) |

Nothing reaches main without passing both states.

### Build — build.yml
**Trigger:** push (merge) to main
**Permissions:** contents: read, packages: write

| Step | Why it exists |
|------|---------------|
| docker build (multi-stage) | Produces the runtime image |
| **Trivy** image scan | Scans the image + OS for CVEs; fails the build on any fixable high/critical faults |
| **Syft** SBOM | Generates an SPDX SBOM documenting all components (build artifact) |
| Log in + push to **GHCR** | Publishes the image (tagged with the commit SHA and latest) |

The scan runs before the push, so a failing scan means nothing is published to GH.

### Deploy — deploy.yml
**Trigger:** a version tag (`v*.*.*`)
**Permissions:** contents: read, packages: read, pages: write, id-token: write

| Step | Why it exists |
|------|---------------|
| Log in + pull image from GHCR (by commit SHA) | Retrieve the exact image built for this release commit |
| Run the container | The container's default command generates the report |
| Copy, Upload, Deploy | Publishes the HTML to GitHub Pages |

The image is pulled by commit SHA (not latest), so a release deploys exactly the artifact built for that commit. id-token: write lets the Pages deployment authenticate via OIDC, and deployment to the github-pages environment is restricted to release tags.

## Instructions to Run

### Locally (Python)

```bash
git clone https://github.com/cdmarian21/swat-report-generator.git
cd swat-report-generator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Generate mock data, then the report:
python src/generate_mock_data.py --output data/mock_swat.csv --seed 42
python src/generate_report.py --input data/mock_swat.csv --output output/report.html
# open output/report.html in a browser
```

### With Docker

```bash
docker build -t swat-report .
docker run --name swat swat-report
docker cp swat:/app/output/report.html ./report.html
docker rm swat
```

### Swapping in the real dataset

Because the mock data has the same schema, the same code runs on the real file:

```bash
# Drop the real CSV into data/ (it is gitignored and never committed), then:
python src/generate_report.py --input data/dataset.csv --output output/report.html
```

The real CSV's columns must match src/schema.py. 
The timestamp parser has a flexible format, so if the real file's timestamp format differs, adjust the it in generate_report.py.

## Security Reasoning

The pipeline applies defense in depth: independent controls at each layer, so a gap in one is covered by another.
Each tool was specifically chosen for this context:

| Layer | Control | Why it fits here |
|-------|---------|------------------|
| Source code | **Bandit** (SAST) | Bandit is the standard Python SAST. It catches insecure source code before anything is built |
| Dependencies | **pip-audit** (SCA) | One runtime dependency is deliberately shipped; pip-audit guards it (and any future additions) against known CVEs |
| Image + OS | **Trivy** | Catches OS-level CVEs the language scanners can't see (where most container risk lives) |
| Transparency | **Syft SBOM** | Documents every component for supply chain visibility (you have to know what you have to secure it) |
| Blast radius | **Least-privilege** | Each workflow's token is scoped to only what it needs (damage control) |
| Data handling | **No secrets** | Sensitive ICS data and secrets stay out of the repo entirely (default CI runs on synthetic data) |

**Two important decisions:**
- **Trivy gates on *fixable* HIGH/CRITICAL only (--ignore-unfixed).** Slim base images carry some CVEs with no inherent fix; failing on those would make the control permanently red and meaningless. So, we instead patch the base image at build time (apt-get upgrade) and fail only on vulnerabilities we can act on.
- **Reproducible/minimal images.** The Dockerfile is multi-stage (build tooling never ships), runs as a **non-root user**, uses a pinned slim base, and the sole Python dependency is exact-pinned for reproducible, scannable builds.

## Repository Security Settings

Workflow permissions: blocks limit what each run can do, but the *enforcement* that nothing reaches main without passing CI comes from repository settings. This repo uses:

- **Branch protection on main** — require a pull request, require the **CI** status check to pass before merging, and block direct pushes. Because build.yml triggers on merge to main, requiring CI before merge means only CI-passed code is ever built or deployed.
- **Restricted release tags** — limit who can create `v*.*.*` tags, since a tag is what triggers a deploy.
- **Secret scanning + push protection** — GitHub-native, to catch committed credentials before they land.
- **Environment + package scoping** — the github-pages environment is restricted to release tags, and the GHCR package is published for distribution.


## Attribution

SWaT dataset (SWaT.A12, Mar 2026) courtesy of iTrust, Centre for Research in Cyber Security, Singapore University of Technology and Design.
Source: https://itrust.sutd.edu.sg/itrust-labs_datasets/ — Goh, J., Adepu, S., Junejo, K. N., & Mathur, A.
