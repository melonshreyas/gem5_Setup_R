# Smoke Workflow for gem5

This folder contains the smoke-test workflow used to compile gem5, run a small simulation flow, and generate HTML/JSON reports for the results.

## Contents

- `jenkins_smoke.py` – main orchestration script for the workflow
- `jenkins_smoke_html.py` – HTML/JSON report generation for smoke results and history
- `send_email_report.py` – helper to send the generated history report by email as an attachment
- `chip_configuration.json` – example chip/testcase configuration used by the workflow
- `jenkins_smoke.groovy` – basic Jenkins pipeline definition for running the smoke workflow
- `test_jenkins_smoke.py` – basic smoke tests for the workflow helpers

## Workflow Overview

The workflow can:

- clone or reuse a repository checkout
- collect git metadata
- compile gem5 in `opt` or `debug` mode
- run configured smoke simulations
- write summary results to the output directory
- generate HTML and JSON reports
- optionally email the generated history HTML report

## Typical Usage

Run the workflow from the repository root:

```bash
python3 JENKINS/SMOKE/jenkins_smoke.py \
  --input-dir /Users/diya/Documents/JENKINS/SMOKE \
  --output-dir /Users/diya/Documents/JENKINS/SMOKE/SMOKE_BUILD_2 \
  --branch stable \
  --chip-configuration /Users/diya/Documents/gem5_Setup_R/JENKINS/SMOKE/chip_configuration.json \
  --compile opt
```

### Quick-start examples

1. Full run with compilation and simulation:

```bash
python3 JENKINS/SMOKE/jenkins_smoke.py \
  --input-dir /Users/diya/Documents/JENKINS/SMOKE \
  --output-dir /Users/diya/Documents/JENKINS/SMOKE/SMOKE_BUILD_2 \
  --branch stable \
  --chip-configuration /Users/diya/Documents/gem5_Setup_R/JENKINS/SMOKE/chip_configuration.json \
  --compile opt
```

2. Skip compilation and reuse the existing build:

```bash
python3 JENKINS/SMOKE/jenkins_smoke.py \
  --input-dir /Users/diya/Documents/JENKINS/SMOKE \
  --output-dir /Users/diya/Documents/JENKINS/SMOKE/SMOKE_BUILD_2 \
  --branch stable \
  --chip-configuration /Users/diya/Documents/gem5_Setup_R/JENKINS/SMOKE/chip_configuration.json \
  --skip-compilation \
  --skip_simulation
```

3. Preview the commands without executing them:

```bash
python3 JENKINS/SMOKE/jenkins_smoke.py \
  --input-dir /Users/diya/Documents/JENKINS/SMOKE \
  --output-dir /Users/diya/Documents/JENKINS/SMOKE/SMOKE_BUILD_2 \
  --branch stable \
  --chip-configuration /Users/diya/Documents/gem5_Setup_R/JENKINS/SMOKE/chip_configuration.json \
  --dry_run
```

### Useful flags

- `--skip-compilation` – skip the compile step
- `--skip_simulation` – skip simulation and still generate reports
- `--dry_run` – print the planned commands without executing them
- `--send-email` – send the generated history HTML report by email
- `--smtp-server`, `--smtp-port`, `--sender-email`, `--sender-password`, `--recipient-email`, `--email-subject` – email configuration options

## How the workflow behaves

When the workflow runs successfully, it will:

- create or reuse the requested output directory
- collect git metadata from the repository
- compile gem5 into the build tree
- run the configured chip/simulation cases
- write summary results and report files
- update the smoke history view with the latest run

If the run is interrupted or a required tool is missing, the script will usually emit a warning or error and stop at the point where the failure occurred.

## Jenkins Pipeline

A basic Jenkins pipeline script is provided in [JENKINS/SMOKE/jenkins_smoke.groovy](JENKINS/SMOKE/jenkins_smoke.groovy). It can be used in a Pipeline job with the following features:

- checks out the repository
- prepares the workspace folders
- runs the smoke workflow with configurable branch, chip, and output options
- archives the generated HTML/JSON reports
- publishes the history report as a Jenkins HTML report

To use it in Jenkins:

1. Create a new Pipeline job.
2. Set the pipeline definition to use this repository file, or copy the contents of the Groovy script into the job.
3. Run the job with the default parameters or override them to target a specific chip or mode.

Example parameter values:

- `BRANCH=stable`
- `COMPILE_TARGET=opt`
- `CHIP_NAME=CHIP_1`
- `SKIP_COMPILATION=false`
- `SKIP_SIMULATION=false`
- `DRY_RUN=false`
- `SEND_EMAIL=false`

## Email Reporting

The email helper can be used independently or through the workflow.

### Standalone usage

```bash
python3 JENKINS/SMOKE/send_email_report.py JENKINS/HISTORY/jenkins_history_smoke_results.html \
  --smtp-server smtp.gmail.com \
  --sender-email shreyassbagi@gmail.com \
  --sender-password "YOUR_GMAIL_APP_PASSWORD" \
  --recipient-email shreyassbagi@gmail.com \
  --subject "gem5 smoke report"
```

### Environment variables

The helper also supports these environment variables:

- `SMTP_SERVER`
- `SENDER_EMAIL`
- `SENDER_PASSWORD`
- `SMTP_RECIPIENTS`

## Output tree and file layout

When the workflow runs, it creates a run-specific output tree under the selected output directory. A typical layout looks like this:

```text
<output-dir>/
├── build/
│   └── ALL/
│       ├── gem5.opt
│       └── gem5.debug
├── RESULTS/
│   ├── general_results.json
│   ├── smoke_results.html
│   ├── smoke_results.json
│   ├── compilation/
│   │   ├── compile_opt.log
│   │   ├── compile_debug.log
│   │   └── results_compilation.json
│   └── simulation/
│       └── <chip-name>/
│           └── <case-name>/
│               ├── <chip>_<case>.log
│               ├── <chip>_<case>.txt
│               ├── results_simulation.json
│               └── stats.txt
└── history/
    └── smoke_history.json
```

### Important output files

- `RESULTS/general_results.json` – overall summary of git metadata, compilation status, and simulation results.
- `RESULTS/smoke_results.html` – human-readable HTML report for the current run.
- `RESULTS/smoke_results.json` – machine-readable JSON version of the run report.
- `RESULTS/compilation/compile_opt.log` or `compile_debug.log` – compilation output and build diagnostics.
- `RESULTS/compilation/results_compilation.json` – per-chip compilation status and log metadata.
- `RESULTS/simulation/<chip>/<case>/` – per-chip/per-case simulation output directories.
- `RESULTS/simulation/<chip>/<case>/<chip>_<case>.log` – simulation stdout/stderr log.
- `RESULTS/simulation/<chip>/<case>/results_simulation.json` – per-case simulation result summary.
- `RESULTS/simulation/<chip>/<case>/stats.txt` – gem5 stats file from the simulation run.

### History reports

The history report is written to:

- `JENKINS/HISTORY/jenkins_history_smoke_results.html`
- `JENKINS/HISTORY/jenkins_history_smoke_results.json`

These are updated from each successful run so recent builds can be compared over time.

## Where to inspect results

- Open the generated HTML report in a browser from the output directory.
- Review `RESULTS/general_results.json` for the full run summary.
- Check the compilation and simulation logs under `RESULTS/compilation/` and `RESULTS/simulation/`.
- Use the history HTML report in `JENKINS/HISTORY/` to compare recent smoke runs.

## Troubleshooting

- If compilation fails, inspect the logs in `RESULTS/compilation/`.
- If simulation fails, check the per-case output directories under `RESULTS/simulation/`.
- If email sending fails, confirm the SMTP server, port, and app password are correct.
- If the workflow cannot find the repository or chip config, verify the paths passed to `--input-dir` and `--chip-configuration`.

## Notes

- The workflow is designed for local or CI-style smoke validation.
- The generated reports are intended to be human-readable and easy to inspect in a browser.
- For actual email delivery, use a valid SMTP server and credentials such as a Gmail app password.
