# gem5 PERF Profile Workflow

This job runs gem5 simulations for performance-oriented profiling and stores outputs separately from SMOKE and ASAN.

## Files

- `jenkins_perf.py`: PERF orchestration, checkout, compilation, simulation, and history update.
- `jenkins_perf_html.py`: PERF current-run and history report generation.
- `jenkins_perf.groovy`: Jenkins Pipeline definition.
- `chip_configuration.json`: chip and testcase definitions.
- `test_jenkins_perf.py`: focused workflow tests.

## Paths

- Run output: `/Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/PERF/`
- History and reports: `/Users/diya/Documents/JENKINS/HISTORY/PROFILE_RUNS/PROFILE/PERF/`

## Local Run

From the repository root:

```bash
python3 JENKINS/PROFILE_RUNS/PERF/jenkins_perf.py \
  --input-dir /Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/PERF \
  --output-dir /Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/PERF/PERF_BUILD_1 \
  --branch stable \
  --chip-configuration JENKINS/PROFILE_RUNS/PERF/chip_configuration.json \
  --compile opt \
  --chip-name CHIP_1
```

Preview the commands without compiling or simulating:

```bash
python3 JENKINS/PROFILE_RUNS/PERF/jenkins_perf.py \
  --output-dir /tmp/gem5-perf-dry-run \
  --branch stable \
  --chip-configuration JENKINS/PROFILE_RUNS/PERF/chip_configuration.json \
  --compile opt \
  --chip-name CHIP_1 \
  --dry_run
```

Useful options include `--compile debug`, `--chip-name ALL`, `--skip-compilation`, `--skip_simulation`, `--verbose`, `--lsf 1`, and `--send-email`.

Enable Linux `perf` call-stack recording explicitly with:

```bash
python3 JENKINS/PROFILE_RUNS/PERF/jenkins_perf.py \
  --input-dir /Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/PERF \
  --output-dir /Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/PERF/PERF_BUILD_1 \
  --branch stable \
  --chip-configuration JENKINS/PROFILE_RUNS/PERF/chip_configuration.json \
  --compile opt \
  --chip-name CHIP_1 \
  --perf-record \
  --perf-frequency 999 \
  --perf-call-graph dwarf
```

This wraps each gem5 invocation as:

```bash
perf record -F 999 -g -- build/ALL/gem5.opt <gem5-arguments>
```

Inspect the recorded call graph with:

```bash
perf report --call-graph
```

For a DWARF-unwound profile, use `--perf-call-graph dwarf` on a Linux host.
The wrapper is disabled by default because macOS does not provide Linux `perf`.

## Jenkins Setup

Create a Pipeline job using `JENKINS/PROFILE_RUNS/PERF/jenkins_perf.groovy` from SCM. The pipeline checks out `stable`, runs the PERF workflow, archives PERF artifacts, and publishes the PERF history report.

The job accepts `BRANCH`, `INPUT_DIR`, `OUTPUT_DIR`, `CHIP_CONFIGURATION`, `COMPILE_TARGET`, `CHIP_NAME`, `SKIP_COMPILATION`, `SKIP_SIMULATION`, `DRY_RUN`, and `SEND_EMAIL`.

## Output Layout

```text
PERF_BUILD_<n>/
├── build/ALL/gem5.opt or gem5.debug
└── RESULTS/
    ├── perf_results.html
    ├── perf_results.json
    ├── general_results.json
    ├── compilation/
    │   ├── compile_opt.log or compile_debug.log
    │   └── results_compilation.json
    └── simulation/<chip>/<case>/
        ├── simulation.log
        ├── stats.txt
        └── results_simulation.json
```

Persistent history is written under `/Users/diya/Documents/JENKINS/HISTORY/PROFILE_RUNS/PROFILE/PERF/`:

- `history_results.json`
- `jenkins_history_perf_results.html`
- `jenkins_history_perf_results.json`
- `perf_report.css`

## Validation

```bash
python3 -m unittest discover -s JENKINS/PROFILE_RUNS/PERF -p 'test_*.py'
```

This PERF workflow does not assume Linux `perf` is installed. On macOS, use it to collect repeatable gem5 performance runs and statistics; run Linux `perf` separately on a Linux host when hardware sampling is required.

On macOS, do not type `perf` directly in zsh: shell correction may replace it
with `/usr/bin/gperf`, which is a perfect-hash generator rather than a profiler.
The PERF runner rejects `--perf-record` when Linux `perf` is unavailable instead
of invoking the wrong executable. Use a Linux VM, Linux host, or remote Linux
machine for the `perf record` workflow.
