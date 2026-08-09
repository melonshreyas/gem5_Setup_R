# Smoke Workflow for gem5

This folder contains the smoke-test workflow used to compile gem5, run a small simulation flow, and generate HTML/JSON reports for the results.

## Contents

- `jenkins_smoke.py` – main orchestration script for the workflow
- `jenkins_smoke_html.py` – HTML/JSON report generation for smoke results and history
- `send_email_report.py` – helper to send the generated history report by email as an attachment
- `chip_configuration.json` – example chip/testcase configuration used by the workflow
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

## Output Files

When the workflow runs, it writes reports and result files into the selected output directory, typically under:

- `RESULTS/general_results.json`
- `RESULTS/smoke_results.html`
- `RESULTS/smoke_results.json`
- `RESULTS/compilation/`
- `RESULTS/simulation/`

The history report is written to:

- `JENKINS/HISTORY/jenkins_history_smoke_results.html`
- `JENKINS/HISTORY/jenkins_history_smoke_results.json`

## Where to inspect results

- Open the generated HTML report in a browser from the output directory.
- Review the summary JSON for machine-readable data.
- Check the compilation and simulation log files in the `RESULTS/compilation` and `RESULTS/simulation` folders.
- Use the history HTML report to compare recent runs over time.

## Troubleshooting

- If compilation fails, inspect the logs in `RESULTS/compilation/`.
- If simulation fails, check the per-case output directories under `RESULTS/simulation/`.
- If email sending fails, confirm the SMTP server, port, and app password are correct.
- If the workflow cannot find the repository or chip config, verify the paths passed to `--input-dir` and `--chip-configuration`.

## Notes

- The workflow is designed for local or CI-style smoke validation.
- The generated reports are intended to be human-readable and easy to inspect in a browser.
- For actual email delivery, use a valid SMTP server and credentials such as a Gmail app password.
