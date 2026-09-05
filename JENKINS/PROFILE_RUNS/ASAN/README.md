# gem5 ASAN Profile Workflow

This job builds gem5 with AddressSanitizer, runs the configured simulations, and stores sanitizer logs and reports separately from SMOKE and PERF runs.

## Files

- `jenkins_asan.py`: ASAN orchestration, compilation, simulation, and history update.
- `jenkins_asan_html.py`: current-run and history report generation.
- `jenkins_asan.groovy`: Jenkins Pipeline definition.
- `chip_configuration.json`: chip and testcase definitions.
- `test_jenkins_asan.py`: focused workflow tests.

## Local Run

From the repository root:

```bash
python3 JENKINS/PROFILE_RUNS/ASAN/jenkins_asan.py \
  --input-dir /Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/ASAN \
  --output-dir /Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/ASAN/ASAN_BUILD_1 \
  --branch stable \
  --chip-configuration JENKINS/PROFILE_RUNS/ASAN/chip_configuration.json \
  --compile opt \
  --chip-name ALL
```

The compiler command is `scons build/ALL/gem5.opt --sanitize=address -j16` for an opt build, or `scons build/ALL/gem5.debug --sanitize=address` for a debug build. ASAN builds are always recompiled so an ordinary cached gem5 binary cannot be mistaken for an instrumented binary.

Preview the commands without compiling or simulating:

```bash
python3 JENKINS/PROFILE_RUNS/ASAN/jenkins_asan.py \
  --output-dir /tmp/gem5-asan-dry-run \
  --branch stable \
  --chip-configuration JENKINS/PROFILE_RUNS/ASAN/chip_configuration.json \
  --compile opt \
  --chip-name CHIP_1 \
  --dry_run
```

Useful options include `--compile debug`, `--chip-name CHIP_1`, `--skip-compilation`, `--skip_simulation`, `--verbose`, and `--send-email`.

## Jenkins Setup

Create a Pipeline job using `JENKINS/PROFILE_RUNS/ASAN/jenkins_asan.groovy` from SCM. The pipeline accepts `BRANCH`, `INPUT_DIR`, `OUTPUT_DIR`, `CHIP_CONFIGURATION`, `COMPILE_TARGET`, `CHIP_NAME`, `SKIP_COMPILATION`, `SKIP_SIMULATION`, `DRY_RUN`, and `SEND_EMAIL`.

Each simulation uses `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1:abort_on_error=1:symbolize=1:log_path=<case>/asan.log` so sanitizer failures stop the simulation, produce symbolized output, and remain in the captured logs. It publishes only ASAN artifacts.

## Output Layout

```text
ASAN_BUILD_<n>/
├── build/ALL/gem5.opt or gem5.debug
└── RESULTS/
    ├── asan_results.html
    ├── asan_results.json
    ├── general_results.json
    ├── compilation/
    │   ├── compile_opt_asan.log or compile_debug_asan.log
    │   └── results_compilation.json
    └── simulation/<chip>/<case>/
        ├── simulation.log
        ├── asan.log.*
        ├── stats.txt
        └── results_simulation.json
```

Persistent history is written under `/Users/diya/Documents/JENKINS/HISTORY/PROFILE_RUNS/ASAN/`:

- `history_results.json`
- `jenkins_history_asan_results.html`
- `jenkins_history_asan_results.json`
- `asan_report.css`

## Validation

Run the focused tests with:

```bash
python3 -m unittest discover -s JENKINS/PROFILE_RUNS/ASAN -p 'test_*.py'
```
