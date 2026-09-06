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

The compiler command is `scons build/ALL/gem5.opt --sanitize=address -j16 --ignore-style --install-hooks` for an opt build, or `scons build/ALL/gem5.debug --sanitize=address --ignore-style --install-hooks` for a debug build. ASAN builds are always recompiled so an ordinary cached gem5 binary cannot be mistaken for an instrumented binary.

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

Each simulation uses `ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:symbolize=1:log_path=<case>/asan.log` so sanitizer failures stop the simulation, produce symbolized output, and remain in the captured logs. It publishes only ASAN artifacts.

## ASAN Evidence

The workflow was validated with an explicit, opt-in native probe. The probe is
enabled only when `GEM5_ASAN_TRIGGER=1` is set; ordinary simulations do not
execute it.

```bash
GEM5_ASAN_TRIGGER=1 \
ASAN_OPTIONS='halt_on_error=1:abort_on_error=1:symbolize=1:log_path=/Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/ASAN/ASAN_BUILD_1/RESULTS/simulation/CHIP_1/smoke_test_cores_materials/asan.log' \
/Users/diya/Documents/gem5_Setup_R/build/ALL/gem5.opt \
  --outdir=/Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/ASAN/ASAN_BUILD_1/RESULTS/simulation/CHIP_1/smoke_test_cores_materials \
  --redirect-stdout \
  --redirect-stderr \
  /Users/diya/Documents/gem5_Setup_R/materials/02-Using-gem5/04-cores/cores.py
```

The captured terminal evidence reported:

```text
==89943==ERROR: AddressSanitizer: heap-use-after-free on address 0x6020000085b0
READ of size 4 at 0x6020000085b0 thread T0
```

The report was written to:

```text
/Users/diya/Documents/JENKINS/PROFILE_RUNS/PERF_RUN/ASAN/ASAN_BUILD_1/RESULTS/simulation/CHIP_1/smoke_test_cores_materials/asan.log.89943
```

On macOS, the terminal may also show `atos failed to symbolize address` warnings
when the binary or source symbol paths are not available to the system symbolizer.
The ASAN detection itself is still confirmed by the `heap-use-after-free` and
`READ of size 4` lines.

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
