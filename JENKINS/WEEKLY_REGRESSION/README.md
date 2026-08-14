# Weekly Regression Workflow for gem5

This folder contains the weekly regression workflow used to compile gem5, run the configured regression simulation set, and generate HTML/JSON reports for trend tracking.

## Contents

- `jenkins_weekly.py` - main orchestration script for the weekly workflow
- `jenkins_weekly_html.py` - HTML/JSON report generation for weekly results and history
- `send_email_report.py` - helper to email the generated weekly history HTML report
- `chip_configuration.json` - chip and testcase configuration used by the weekly run
- `jenkins_weekly.groovy` - Jenkins pipeline definition for weekly regression runs
- `test_jenkins_weekly.py` - basic workflow helper tests
- `docs/` - Jenkins screenshots referenced by this README

## Workflow Overview

The weekly workflow can:

- clone or reuse a repository checkout
- collect git metadata
- compile gem5 in `opt` or `debug` mode
- run configured weekly regression simulation cases
- write summary artifacts into a run output directory
- generate HTML and JSON reports
- optionally email the generated weekly history report

## Typical Usage

Run from repository root:

```bash
python3 JENKINS/WEEKLY_REGRESSION/jenkins_weekly.py \
  --input-dir /Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION \
  --output-dir /Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION/WEEKLY_BUILD_3 \
  --branch stable \
  --chip-configuration /Users/shreyas/Documents/gem5_Setup_R/JENKINS/WEEKLY_REGRESSION/chip_configuration.json \
  --compile opt
```

### Quick-start Examples

1. Full weekly run:

```bash
python3 JENKINS/WEEKLY_REGRESSION/jenkins_weekly.py \
  --input-dir /Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION \
  --output-dir /Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION/WEEKLY_BUILD_3 \
  --branch stable \
  --chip-configuration /Users/shreyas/Documents/gem5_Setup_R/JENKINS/WEEKLY_REGRESSION/chip_configuration.json \
  --compile opt
```

2. Skip compilation and simulation:

```bash
python3 JENKINS/WEEKLY_REGRESSION/jenkins_weekly.py \
  --input-dir /Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION \
  --output-dir /Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION/WEEKLY_BUILD_3 \
  --branch stable \
  --chip-configuration /Users/shreyas/Documents/gem5_Setup_R/JENKINS/WEEKLY_REGRESSION/chip_configuration.json \
  --skip-compilation \
  --skip_simulation
```

3. Dry run preview:

```bash
python3 JENKINS/WEEKLY_REGRESSION/jenkins_weekly.py \
  --input-dir /Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION \
  --output-dir /Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION/WEEKLY_BUILD_3 \
  --branch stable \
  --chip-configuration /Users/shreyas/Documents/gem5_Setup_R/JENKINS/WEEKLY_REGRESSION/chip_configuration.json \
  --dry_run
```

### Useful Flags

- `--chip-name ALL` - run all chips in configuration
- `--skip-compilation` - skip compile step
- `--skip_simulation` - skip simulation and still generate reports
- `--dry_run` - print planned commands without executing
- `--send-email` - email weekly history report

## Jenkins Pipeline

Weekly pipeline definition is in [JENKINS/WEEKLY_REGRESSION/jenkins_weekly.groovy](JENKINS/WEEKLY_REGRESSION/jenkins_weekly.groovy).

Pipeline highlights:

- checks out repository/workspace content
- discovers chip names from `chip_configuration.json`
- runs weekly workflow with selected chip and compile mode
- archives generated JSON/HTML artifacts
- publishes weekly history HTML report in Jenkins

Example parameters:

- `BRANCH=stable`
- `COMPILE_TARGET=opt`
- `CHIP_NAME=ALL`
- `SKIP_COMPILATION=false`
- `SKIP_SIMULATION=false`
- `DRY_RUN=false`

## Output Layout

Typical weekly output layout:

```text
/Users/shreyas/Documents/JENKINS/WEEKLY_REGRESSION/
└── WEEKLY_BUILD_<N>/
    ├── build/
    │   └── ALL/
    │       └── gem5.opt
    ├── RESULTS/
    │   ├── general_results.json
    │   ├── weekly_results.html
    │   ├── weekly_results.json
    │   ├── compilation/
    │   └── simulation/
    └── ...
```

History report files:

- `/Users/shreyas/Documents/JENKINS/HISTORY/WEEKLY_REGRESSION/jenkins_history_weekly_results.html`
- `/Users/shreyas/Documents/JENKINS/HISTORY/WEEKLY_REGRESSION/jenkins_history_weekly_results.json`
- `/Users/shreyas/Documents/JENKINS/HISTORY/WEEKLY_REGRESSION/history_results.json`

## Golden Comparison

Each completed weekly build also runs `JENKINS/compare_golden_results.py` against the per-chip baselines in `/Users/shreyas/Documents/JENKINS/HISTORY/GOLDEN/WEEKLY_REGRESSION/`.

The comparison allows a maximum 5% numeric deviation and writes the following table-oriented reports under `WEEKLY_BUILD_<N>/RESULTS/golden_comparison/`:

- `golden_comparison.html` - visual table of testcase, metric, golden value, actual value, signed deviation, tolerance, and status
- `golden_comparison.csv` - spreadsheet-friendly result table
- `golden_comparison.json` - detailed machine-readable result data

Statuses include `PASS`, `FAIL`, `MISSING_ACTUAL`, and `NO_BASELINE`. Add known-good values under each chip JSON's `golden_values` object to activate comparisons.

## Jenkins Screenshots

### Weekly Report View

![Weekly history report table view](docs/jenkins_results_tree_2.png)

### Weekly Run Details Snapshot

![Weekly run details and table](docs/jenkins_results_tree.png)

### Weekly Folder in JENKINS Root

![Weekly output directory listing](docs/jenkins_smoke_directories.png)

### Jenkins New Item for Weekly Job

![Create weekly job from Jenkins New Item](docs/jenkins_new_item_weekly.png)

### Pipeline Stage View

![Jenkins pipeline stage view](docs/jenkins_stage_view.png)

## Notes

- This README mirrors the SMOKE documentation style with weekly-specific scripts and paths.
- If you add newer screenshots, place them in `JENKINS/WEEKLY_REGRESSION/docs/` and update image links in this file.

## Purpose

This automation is intended to streamline recurring regression activities, reduce repetitive manual steps, and provide a consistent record of each run. It is a practical engineering workflow for improving repeatability, traceability, and validation; it is not intended to make judgments about individuals, teams, or organizations.

## Industry Practice

Build automation, CI/CD pipelines, regression execution, environment checks, revision tracking, and release validation are standard support processes used across software, hardware, firmware, verification, modeling, validation, and release-engineering teams. Jenkins or an equivalent automation platform is general engineering infrastructure rather than a domain-specific activity, and this workflow follows that common pattern to reduce repeated manual work around weekly regression. Its use should remain within the user's authorized access and applicable company security, confidentiality, and information-handling policies; the workflow is routine engineering support and does not change an engineer's core technical responsibilities.

Participation in these activities is not intended to limit a person to release automation, CI/CD, or support work. Engineers who develop and maintain such workflows can also contribute to broader technical areas, including modeling, microarchitecture, performance analysis, SystemC/C++, verification, and system-level engineering, according to their role, interests, skills, and authorized opportunities. Support infrastructure is one part of an engineering contribution, not a definition or restriction of a person's capabilities.

## Logging and Traceability

Each run may record operational details such as the Jenkins build number, Git branch, commit ID, commit author, compile target, stage results, runtime, simulation logs, statistics, and output paths. These details make it easier to reproduce a result, identify technical bottlenecks, understand recurring failures, and improve the workflow.

This information is intended for engineering traceability and process improvement only. It is not intended for micromanagement, surveillance, personal criticism, or evaluation of individuals. Conclusions should be based on technical evidence and run context, not isolated metadata such as a commit author or build duration.
