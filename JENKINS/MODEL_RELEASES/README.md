# Model Releases

This directory contains a dedicated Jenkins flow for creating validated gem5 model releases. It is independent of the SMOKE and WEEKLY_REGRESSION jobs, although it reuses the existing `chip_configuration.json` testcase definitions.

The release flow performs source checkout, compilation, selected simulations, manifest creation, HTML report generation, optional email delivery, and Jenkins artifact archiving.

## Purpose

This automation is intended to streamline recurring model-release activities, reduce repetitive manual steps, and provide a consistent record of each release. It is a practical engineering workflow for improving repeatability, traceability, and validation; it is not intended to make judgments about individuals, teams, or organizations.

## Industry Practice

Build automation, CI/CD pipelines, regression execution, environment checks, revision tracking, and release validation are standard support processes used across software, hardware, firmware, verification, modeling, validation, and release-engineering teams. Jenkins or an equivalent automation platform is general engineering infrastructure rather than a domain-specific activity, and this workflow follows that common pattern to reduce repeated manual work around model releases. Its use should remain within the user’s authorized access and applicable company security, confidentiality, and information-handling policies; the workflow itself is intended as routine release support and does not change an engineer’s core technical responsibilities.

Participation in these activities is not intended to limit a person to release automation, CI/CD, or support work. Engineers who develop and maintain such workflows can also contribute to their broader technical areas, including modeling, microarchitecture, performance analysis, SystemC/C++, verification, and system-level engineering, according to their role, interests, skills, and authorized opportunities. Support infrastructure is one part of an engineering contribution, not a definition or restriction of a person’s capabilities.

## Logging and Traceability

Each release may record operational details such as the Jenkins build number, model unit, generated version, Git branch, commit ID, commit author, compile target, stage results, runtime, simulation logs, and output paths. These details make it easier to reproduce a result, identify technical bottlenecks, understand recurring failures, and improve the workflow.

This information is intended for engineering traceability and process improvement only. It is not intended for micromanagement, surveillance, personal criticism, or evaluation of individuals. Conclusions should be based on the technical evidence and context of the run, not on isolated metadata such as a commit author or build duration.

## Files

- `jenkins_model_release.groovy` - Jenkins declarative pipeline and parameters
- `model_release.py` - release orchestration, validation, automatic version creation, clone, compile, and simulation
- `model_release_html.py` - standalone HTML report generator
- `model_release_email.py` - standalone SMTP/email adapter
- `release_manifest.json` - optional template/example metadata file
- `README.md` - this operating guide

## Release Storage

The authoritative release location is:

```text
/Users/diya/Documents/JENKINS/HISTORY/MODEL_RELEASES/
```

Each model unit gets one persistent folder. Each run creates the next numbered version inside that unit folder:

```text
MODEL_RELEASES/
├── IFU/
│   ├── IFU_1/
│   └── IFU_2/
├── L1_DCACHE/
│   └── L1_DCACHE_1/
└── LSU/
    └── LSU_1/
```

The unit folder is reused. Version folders are immutable: an existing non-empty generated version is never overwritten.

## Model Unit Names

The Jenkins dropdown and Python validator use these exact POWER9-oriented names:

```text
IFU
BPU
IDU
DISPATCH_UNIT
RENAME_UNIT
ISSUE_QUEUE
COMPLETION_UNIT
FXU
ALU
FPU
VSX
CRU
LSU
EA_GENERATION
L1_ICACHE
L1_DCACHE
L2_CACHE
DTLB
PREFETCH_ENGINE
MEMORY_CONTROLLER
COHERENCE_ENGINE
NEST_INTERCONNECT
PCIe_CONTROLLER
CAPI_INTERFACE
NVLINK_INTERFACE
SMT_SCHEDULER
```

For example, selecting `IFU` automatically creates `IFU_1`, then `IFU_2` on the next release.

## Jenkins Parameters

### Required parameters

- `MODEL_UNIT_NAME` - selected POWER9 unit from the dropdown
- `BRANCH` - Git branch to clone, normally `stable`
- `SUMMARY` - release summary text
- `FIXES` - fixes and changes included in the release
- `REPO_URL` - source repository URL

The pipeline stops in `CHECK_REQUIRED_INPUTS` if any required value is empty.

### Build and selection parameters

- `COMPILE_TARGET` - `opt` or `debug`
- `CHIP_NAME` - `ALL`, `CHIP_1`, `CHIP_2`, or `CHIP_3`
- `TESTCASE` - `ALL` or a comma-separated list of testcase names
- `CHIP_CONFIGURATION` - optional path; defaults to `JENKINS/SMOKE/chip_configuration.json`

### Email parameters

- `SEND_EMAIL` - disabled by default
- `SMTP_SERVER`
- `SENDER_EMAIL`
- `SENDER_PASSWORD`
- `RECIPIENT_EMAILS` - comma-separated addresses

Email credentials should be supplied through Jenkins credentials/environment configuration where possible. Do not commit passwords or app passwords to the repository.

## Chip and Testcase Selection

The default configuration is:

```text
/Users/diya/Documents/gem5_Setup_R/JENKINS/SMOKE/chip_configuration.json
```

Available chips in the current configuration:

```text
CHIP_1
CHIP_2
CHIP_3
```

`CHIP_NAME=ALL` selects every configured chip. A comma-separated selection such as `CHIP_1,CHIP_3` selects only those chips.

The current testcase names are:

```text
smoke_test_cores_materials
smoke_test_cache_materials
smoke_test_memory_materials
smoke_test_full_system_materials
```

`TESTCASE=ALL` selects all testcases for each selected chip. A targeted value such as `smoke_test_cache_materials` runs only that case. Unknown chips or testcases block the release before compilation.

## Pipeline Stages

```text
CHECK_REQUIRED_INPUTS
	|
	v
CHECKOUT_SOURCE
	|
	v
PREPARE_RELEASE_DIRECTORY
	|
	v
CLONE_RELEASE_SOURCE
	|
	v
COLLECT_RELEASE_METADATA
	|
	v
VALIDATE_RELEASE_MANIFEST
	|
	v
ARCHIVE_RELEASE_ARTIFACTS
```

`CHECK_REQUIRED_INPUTS` validates required fields. `CHECKOUT_SOURCE` checks out the pipeline repository. `PREPARE_RELEASE_DIRECTORY` creates the history root and verifies Python. `COLLECT_RELEASE_METADATA` creates the next version, clones the source, compiles gem5, runs selected simulations, writes metadata, generates HTML, and optionally sends email. The final stages validate and archive the release artifacts.

## Version Directory Contents

A completed release looks like:

```text
/Users/diya/Documents/JENKINS/HISTORY/MODEL_RELEASES/IFU/IFU_1/
├── clone.log
├── source/
│   ├── src/
│   ├── configs/
│   ├── build/ALL/gem5.opt
│   └── ...
├── RESULTS/
│   ├── compilation/compile_opt.log
│   └── simulation/
│       └── CHIP_1/
│           ├── smoke_test_cores_materials/
│           │   ├── simulation.log
│           │   ├── stats.txt
│           │   ├── simout.txt
│           │   └── simerr.txt
│           └── smoke_test_cache_materials/
├── release_manifest.json
├── RELEASE_NOTES.md
└── release_report.html
```

## Compilation and Simulation

The compile target maps to:

```text
COMPILE_TARGET=opt   -> build/ALL/gem5.opt
COMPILE_TARGET=debug -> build/ALL/gem5.debug
```

The compile command runs from the cloned source directory:

```text
scons build/ALL/gem5.opt -j20 --ignore-style --install-hooks
```

Each selected chip and testcase receives a separate output directory:

```text
<VERSION>/RESULTS/simulation/CHIP_1/smoke_test_cache_materials/
```

The manifest records status, return code, runtime, command, output directory, and `stats.txt` path for every case. A missing simulation script is recorded as `SKIP` with a reason.

## Generated Metadata

`release_manifest.json` records the generated release name/version, model unit, branch, source commit, summary, fixes, source path, selected chips, testcase filter, compile target/log, and per-chip/per-testcase simulation results.

`RELEASE_NOTES.md` contains the release title, version, model unit, branch, summary, and fixes.

## Separate HTML Report

`model_release_html.py` creates the unit/version-specific report:

```text
<VERSION>/release_report.html
```

Its table contains:

- `CHIP_NAME`
- `TESTCASE`
- `STATUS`
- `RETURN_CODE`
- `RUNTIME_SECONDS`
- `STATS_FILE`

Status cells are visually distinguished for pass, fail, and skip results.

## Separate Email Module

`model_release_email.py` is responsible only for email delivery. It delegates SMTP behavior to the existing SMOKE email helper and attaches `release_report.html`.

Email is sent only when `SEND_EMAIL=true`.

Do not place real credentials in shell history, source files, or Git. Prefer Jenkins credentials/environment configuration.

## Direct Command Example

```bash
cd /Users/diya/Documents/gem5_Setup_R
python3 JENKINS/MODEL_RELEASES/model_release.py \
  --model-unit-name IFU \
  --branch stable \
  --summary "IFU model release validation" \
  --fixes "Initial validated release" \
  --chip-name CHIP_1 \
  --testcase smoke_test_cores_materials \
  --compile opt
```

The command automatically creates the next available IFU version.

## Dry Run

Use `--dry-run` to inspect the complete release plan without changing the release history or running external commands. Dry-run mode:

- loads the selected chip configuration JSON
- applies the default `CHIP_NAME=ALL`, `TESTCASE=ALL`, and `COMPILE_TARGET=opt` values when they are not overridden
- calculates the next unit-prefixed version, such as `IFU_1`
- lists the planned Git clone, SCons compile, and per-chip/per-testcase simulation commands
- does not create the real unit/version release directory
- does not clone, compile, simulate, send email, or write a release manifest

Example:

```bash
python3 JENKINS/MODEL_RELEASES/model_release.py \
  --model-unit-name IFU \
  --branch stable \
  --summary "Dry-run release plan" \
  --fixes "No source changes; command validation only" \
  --chip-name CHIP_1 \
  --testcase smoke_test_cache_materials \
  --compile opt \
  --dry-run
```

The preview files are written in the repository working directory:

```text
model_release_dry_run/
├── dry_run_manifest.json
└── dry_run.log
```

The terminal prints the same commands and records them in the JSON/log preview. This makes it possible to review paths, defaults, chip selection, testcase selection, and command construction before starting a real release.

## Basic Validation Tests

Run checks without cloning or compiling:

```bash
cd /Users/diya/Documents/gem5_Setup_R
python3 -m py_compile \
  JENKINS/MODEL_RELEASES/model_release.py \
  JENKINS/MODEL_RELEASES/model_release_html.py \
  JENKINS/MODEL_RELEASES/model_release_email.py
python3 JENKINS/MODEL_RELEASES/model_release.py --help
```

Automatic version logic can be tested safely with a temporary directory:

```python
from pathlib import Path
import tempfile
import model_release

with tempfile.TemporaryDirectory() as root:
    unit = Path(root) / "IFU"
    unit.mkdir()
    (unit / "IFU_1").mkdir()
    assert model_release.next_release_version(unit, "IFU") == "IFU_2"
```

## Blocking Rules

The release is blocked when:

- a required Jenkins field is empty
- the model unit is not in the approved POWER9 list
- a selected chip does not exist
- a selected testcase does not exist
- source cloning fails
- compilation fails or the expected binary is missing
- a generated version unexpectedly already contains files
- manifest/report validation fails
- explicitly requested email delivery fails

The release flow never overwrites an existing version.

## Current Path Convention

The current local MacBook setup intentionally uses `/Users/diya`:

```text
/Users/diya/Documents/JENKINS/HISTORY/MODEL_RELEASES
/Users/diya/Documents/gem5_Setup_R/JENKINS/SMOKE/chip_configuration.json
```

## Development Support

The release workflow and documentation were developed and reviewed with support from GitHub Copilot and IBM BoB AI. These tools were used for code navigation, implementation assistance, parser/report design, documentation drafting, and validation planning. The repository behavior, paths, commands, and release decisions remain owned by the project developer and should be verified with local tests and Jenkins runs.

