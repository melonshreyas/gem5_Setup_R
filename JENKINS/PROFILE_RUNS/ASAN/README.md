# Smoke Workflow for gem5

## Purpose

This automation is intended to streamline recurring profile-run activities, reduce repetitive manual steps, and provide a consistent record of each run. It is a practical engineering workflow for improving repeatability, traceability, and validation; it is not intended to make judgments about individuals, teams, or organizations.

## Industry Practice

Build automation, CI/CD pipelines, regression execution, environment checks, revision tracking, and release validation are standard support processes used across software, hardware, firmware, verification, modeling, validation, and release-engineering teams. Jenkins or an equivalent automation platform is general engineering infrastructure rather than a domain-specific activity, and this workflow follows that common pattern to reduce repeated manual work around ASAN validation. Its use should remain within the user's authorized access and applicable company security, confidentiality, and information-handling policies; the workflow is routine engineering support and does not change an engineer's core technical responsibilities.

Participation in these activities is not intended to limit a person to release automation, CI/CD, or support work. Engineers who develop and maintain such workflows can also contribute to broader technical areas, including modeling, microarchitecture, performance analysis, SystemC/C++, verification, and system-level engineering, according to their role, interests, skills, and authorized opportunities. Support infrastructure is one part of an engineering contribution, not a definition or restriction of a person's capabilities.

## Logging and Traceability

Each run may record operational details such as the Jenkins build number, Git branch, commit ID, commit author, compile target, stage results, runtime, simulation logs, statistics, and output paths. These details make it easier to reproduce a result, identify technical bottlenecks, understand recurring failures, and improve the workflow.

This information is intended for engineering traceability and process improvement only. It is not intended for micromanagement, surveillance, personal criticism, or evaluation of individuals. Conclusions should be based on technical evidence and run context, not isolated metadata such as a commit author or build duration.

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

## Reusing the Pipeline for a New Jenkins Job

One of the biggest advantages of the `jenkins_smoke.groovy` pipeline is that it is completely parameterised. This means you can create a brand-new Jenkins job for a different workflow (for example `WEEKLY_REGRESSION` or `PROFILE_RUNS`) by simply duplicating the existing `SMOKE` job and changing the parameters — **no Groovy edits required**.

### How to duplicate a Jenkins pipeline

![Duplicate an existing Jenkins Pipeline](docs/jenkins_duplicate_pipeline.png)

Jenkins makes this very easy through its **"Duplicate an existing Item"** option on the New Item page:

1. Go to `http://localhost:8080/view/all/newJob`.
2. Enter the new job name (for example `WEEKLY_REGRESSION`).
3. At the bottom of the page, select **"Duplicate an existing Item"** and type `SMOKE` in the copy-from field.
4. Click **OK**.
5. In the new job's configuration, update only the parameters that differ (for example `CHIP_NAME`, `OUTPUT_DIR`, or the pipeline trigger schedule).
6. Click **Save**.

The new job will inherit the full pipeline script, all parameters, the build discard policy, and the report publishing configuration. The same `jenkins_smoke.py` script and `chip_configuration.json` can be reused unchanged, or pointed at a different configuration file for the new workflow.

This approach ensures that any future improvements to the core pipeline (such as new report formats, better logging, or email support) can be rolled out to all derived jobs simply by updating the shared script.

## Jenkins Integration in Action

The screenshots below show the smoke workflow running end-to-end inside Jenkins, the output directory layout it produces, and how to reuse the pipeline for new jobs.

### Jenkins Stage View — Build History

![Jenkins Stage View](docs/jenkins_stage_view.png)

The Jenkins Stage View shows all pipeline stages for each build:

- **Checkout** — clones or updates the repository in the Jenkins workspace.
- **Prepare Environment** — creates the output directory and updates Git submodules.
- **Run Smoke Workflow** — compiles gem5 and runs all configured chip/simulation cases. This is the longest stage (~30 minutes for a full build and simulation run).
- **Declarative: Post Actions** — archives the HTML and JSON report artifacts.

Build `#10` (green) completed successfully in roughly 3 hours 45 minutes end-to-end. Earlier builds (`#5`–`#9`) show failed runs that were used to iterate on the pipeline configuration.

---

### Output Directory Structure — JENKINS Folder

![JENKINS directory layout](docs/jenkins_smoke_directories.png)

The JENKINS output tree on disk after several successful and in-progress builds. The top-level layout looks like:

```text
~/Documents/JENKINS/
├── HISTORY/                         ← accumulated history across all runs
│   ├── history_results.json
│   ├── history_results_format.json
│   ├── jenkins_history_smoke_results.html
│   └── jenkins_history_smoke_results.json
├── SMOKE/                           ← all smoke build outputs
│   ├── SMOKE_BUILD_1/
│   ├── SMOKE_BUILD_2/
│   ├── SMOKE_BUILD_3/
│   ├── SMOKE_BUILD_6/
│   ├── SMOKE_BUILD_9/
│   ├── SMOKE_BUILD_10/
│   └── ...
├── PROFILE_RUNS/
└── WEEKLY_REGRESSION/
```

---

### Build Output — SMOKE_BUILD_10 Contents

![SMOKE_BUILD_10 directory contents](docs/jenkins_smoke_build_contents.png)

Inside a completed build output directory (`SMOKE_BUILD_10`), the full gem5 repository checkout is present alongside the `RESULTS/` folder:

```text
SMOKE_BUILD_10/
├── SConstruct
├── src/
├── build/
├── materials/
├── WORKLOAD/
├── JENKINS/
└── RESULTS/
```

The repository is cloned once per build into the build-numbered directory so each run is fully isolated and reproducible.

---

### RESULTS Tree — Compilation and Simulation Outputs

![RESULTS tree from SMOKE_BUILD_10](docs/jenkins_results_tree.png)

The `RESULTS/` folder inside a completed build contains all compilation and simulation outputs:

```text
RESULTS/
├── compilation/
│   ├── CHIP_1/
│   │   ├── compile.log
│   │   └── results_compilation.json
│   └── compile_opt.log
├── general_results.json
└── simulation/
    └── CHIP_1/
        ├── smoke_test_cache_materials/
        │   ├── citations.bib
        │   ├── config.ini
        │   ├── config.json
        │   ├── simerr.txt
        │   ├── simout.txt
        │   ├── simulation.log
        │   └── stats.txt
        ├── smoke_test_cores_materials/
        ├── smoke_test_full_system_materials/
        └── smoke_test_memory_materials/
```

Each simulation case gets its own subdirectory with the full gem5 output including `stats.txt`, `simout.txt`, and `simerr.txt`.

---

> **Note for screenshots:** Save each image to `JENKINS/SMOKE/docs/` using the filenames referenced above (`jenkins_stage_view.png`, `jenkins_smoke_directories.png`, `jenkins_smoke_build_contents.png`, `jenkins_results_tree.png`, `jenkins_duplicate_pipeline.png`) so they render correctly in GitHub and any Markdown viewer.
