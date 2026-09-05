# AI Black‑Box Testing Hooks, Deterministic Logging, Structural Testability & Simulation‑Safe Instrumentation

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for SystemC/VP/Performance‑Modelling Engineers (<5‑Year)  
**Prerequisites:** `01_Core_Philosophy.md`, `02_C++_Rules.md`, `03_SystemC_Rules.md`, `04_TLM2_Patterns.md`, `05_VP_Performance_Modelling.md`, `06_DSA_Hardware_Patterns.md`

---

## Table of Contents

1. [Philosophy of AI‑Testability](#1-philosophy-of-aitestability)
2. [Determinism Rules](#2-determinism-rules)
3. [Structural Testability Rules](#3-structural-testability-rules)
4. [Logging Rules](#4-logging-rules)
5. [State Visibility Rules](#5-state-visibility-rules)
6. [Pure Function Rules](#6-pure-function-rules)
7. [Container Determinism Rules](#7-container-determinism-rules)
8. [Floating‑Point Determinism Rules](#8-floatingpoint-determinism-rules)
9. [SystemC AI‑Testability Rules](#9-systemc-aitestability-rules)
10. [TLM‑2.0 AI‑Testability Rules](#10-tlm20-aitestability-rules)
11. [VP Performance Modelling AI‑Testability Rules](#11-vp-performance-modelling-aitestability-rules)
12. [Stimulus Injection Rules](#12-stimulus-injection-rules)
13. [Golden Reference Rules](#13-golden-reference-rules)
14. [Hardware Diagrams — AI Instrumentation Points](#14-hardware-diagrams--ai-instrumentation-points)
15. [AI Test Harness Patterns](#15-ai-test-harness-patterns)
16. [AI‑Friendly Module Templates](#16-aifriendly-module-templates)
17. [Complete AI‑Testable Module Example](#17-complete-aitable-module-example)
18. [Anti‑Patterns](#18-anti-patterns)
19. [Checklist](#19-checklist)
20. [Glossary](#20-glossary)

---

## 1. Philosophy of AI‑Testability

> **AI cannot test what it cannot observe.  
> AI cannot validate what it cannot predict.  
> AI cannot reproduce what is not deterministic.**

An AI test agent operates as a **black-box stimulus generator and output
checker**. It drives typed inputs into a module interface, observes typed
outputs and state dumps, and compares them against a golden reference.
This only works if every module in the simulation satisfies six properties:

| Property | Requirement |
|---|---|
| **Deterministic** | Same inputs → same outputs, every run, every machine |
| **Observable** | All state visible via `dump_state()` / getters / structured log |
| **Predictable** | Output is a pure function of inputs and visible state |
| **Reproducible** | Test can be re-run from a serialised state snapshot |
| **Bounded** | All containers and queues have hardware-derived capacity limits |
| **Injectable** | All parameters and stimulus can be applied without modifying internals |

### Why standard C++ testing is insufficient for hardware models

| Dimension | Unit test (gtest) | AI black-box test |
|---|---|---|
| Stimulus coverage | Manually authored | AI-generated, space-exploring |
| State observation | Explicit assertions | Full state dump comparison |
| Reproducibility | Fixed test cases | Requires determinism guarantee |
| Regression detection | Known cases only | Detects unknown regressions |
| Parameter sweep | Manual | AI sweeps config space |

### The AI‑testability contract

Every module MUST honour this contract:

```cpp
// ① Construct with injectable parameters
Module m("name", param_a, param_b);

// ② Reset to known state
m.reset();

// ③ Apply typed stimulus
m.apply_stimulus(stim);

// ④ Advance simulation
sc_start(N, SC_NS);

// ⑤ Observe full state
const std::string snap = m.dump_state();

// ⑥ Observe statistics
const std::string stats = m.dump_stats();

// ⑦ Compare against golden reference
assert(snap == golden_snap);
```

---

## 2. Determinism Rules

### Rule AI‑01 — All behaviour MUST be deterministic across runs and machines

```cpp
// ❌ Forbidden — non-deterministic sources
rand();
std::random_device{}();
std::chrono::system_clock::now();
gettimeofday();
getpid();
std::this_thread::get_id();

// ✅ Allowed — deterministic alternatives
// Seeded PRNG with fixed seed if randomness is structurally needed:
std::mt19937 rng(FIXED_SEED_42);
```

### Rule AI‑02 — Same stimulus sequence MUST produce identical state snapshots

```cpp
// ✅ Reproducibility test pattern
Module a("a", cfg), b("b", cfg);
apply_same_stimulus(a);
apply_same_stimulus(b);
assert(a.dump_state() == b.dump_state());   // must be identical
```

### Rule AI‑03 — No hidden static local state

```cpp
// ❌ Forbidden — persists across test runs
void issue(Packet p) {
    static uint32_t seq_num = 0;   // hidden, non-resettable
    p.id = seq_num++;
}

// ✅ Correct — state in module member, resettable
uint32_t seq_num_ = 0;
void issue(Packet p) { p.id = seq_num_++; }
void reset()        { seq_num_ = 0; }
```

### Rule AI‑04 — No global mutable state outside the simulation kernel

```cpp
// ❌ Forbidden
int g_transaction_count = 0;

// ✅ Correct — per-module, resettable
class MemController : public sc_module {
    uint64_t txn_count_ = 0;   // owned by this module
public:
    uint64_t txn_count() const { return txn_count_; }
    void     reset_stats()     { txn_count_ = 0; }
};
```

### Rule AI‑05 — Simulation time MUST be the only time source

```cpp
// ❌ Forbidden
auto t = std::chrono::steady_clock::now();   // wall time — non-deterministic

// ✅ Correct
sc_time t = sc_time_stamp();   // simulation time — deterministic
```

---

## 3. Structural Testability Rules

### Rule AI‑06 — Every module MUST implement the AI‑testability interface

```cpp
class AiTestable {
public:
    virtual ~AiTestable() = default;

    // Serialise full module state to a stable string
    virtual std::string dump_state() const = 0;

    // Serialise performance statistics
    virtual std::string dump_stats() const = 0;

    // Reset to power-on-reset state
    virtual void reset() = 0;
};
```

Every `SC_MODULE` in the VP MUST inherit from (or implement) `AiTestable`.

### Rule AI‑07 — All parameters MUST be injectable at construction time

```cpp
// ❌ Forbidden — hardcoded parameters
SC_MODULE(Cache) {
    static constexpr uint32_t SETS = 64;   // can't vary for AI sweep
};

// ✅ Correct — injected parameters
class Cache : public sc_module {
public:
    SC_HAS_PROCESS(Cache);
    Cache(sc_module_name name, uint32_t sets, uint32_t ways, sc_time hit_lat)
        : sc_module(name), sets_(sets), ways_(ways), hit_lat_(hit_lat) {}
private:
    uint32_t sets_;
    uint32_t ways_;
    sc_time  hit_lat_;
};
```

### Rule AI‑08 — Every module MUST expose typed getters for all observable state

```cpp
// ✅ One getter per observable quantity — AI can query individually
uint64_t pc()          const { return pc_; }
bool     stalled()     const { return stall_; }
uint32_t rob_entries() const { return rob_.size(); }
double   hit_rate()    const { return cache_.hit_rate(); }
```

### Rule AI‑09 — Stimulus MUST be applied through typed `apply_stimulus()` — never via direct member access

```cpp
struct FetchStimulus {
    uint64_t pc;
    bool     reset;
    bool     stall;
};

void apply_stimulus(const FetchStimulus& s) {
    if (s.reset) { reset(); return; }
    stall_.write(s.stall);
    pc_in_.write(s.pc);
}
```

---

## 4. Logging Rules

### Rule AI‑10 — All log output MUST use `SC_REPORT_INFO` — never `std::cout` or `printf`

`SC_REPORT_*` attaches simulation time and module name to every message.
These are essential for AI post-processing of log files.

```cpp
// ❌ Forbidden — unordered, no timestamp, no module name
std::cout << "cache miss addr=0x" << addr << "\n";
printf("miss\n");

// ✅ Correct
std::ostringstream oss;
oss << "op=MISS addr=0x" << std::hex << addr
    << " lat_ns=" << CACHE_MISS_PENALTY.to_double();
SC_REPORT_INFO(name(), oss.str().c_str());
```

### Rule AI‑11 — Log format MUST be `key=value` — machine-parseable

```
✅  op=READ  addr=0x0000_1000  bytes=64  lat_ns=12.0  hit=true
✅  op=WRITE addr=0x0000_2000  bytes=4   lat_ns=8.0   hit=false
✅  state=IDLE  pc=0x0000_0000  stall=false  rob_fill=0

❌  "cache miss at address 4096"          — not parseable
❌  "read 64 bytes, took 12 nanoseconds"  — not parseable
```

### Rule AI‑12 — Log fields MUST be in consistent order across all calls from the same site

```cpp
// ✅ Fixed field order — AI can regex-extract field N reliably
oss << "cycle="  << cycle_
    << " op="    << (write ? "WRITE" : "READ")
    << " addr=0x" << std::hex << addr
    << " bytes=" << std::dec << bytes
    << " lat_ns=" << lat;
```

### Rule AI‑13 — Verbose logs MUST be guarded by a compile-time flag

```cpp
#ifdef AI_VERBOSE_LOG
    std::ostringstream oss;
    oss << "state=" << dump_state();
    SC_REPORT_INFO(name(), oss.str().c_str());
#endif
```

This prevents log noise from perturbing timing in production simulation
while keeping full visibility available for AI test runs.

### Rule AI‑14 — Every state transition MUST log the old state, trigger, and new state

```cpp
// ✅ FSM transition log — fully reconstructable from log
void transition(FsmState next, const char* trigger) {
    std::ostringstream oss;
    oss << "fsm_transition"
        << " from=" << state_name(state_)
        << " trigger=" << trigger
        << " to=" << state_name(next);
    SC_REPORT_INFO(name(), oss.str().c_str());
    state_ = next;
}
```

---

## 5. State Visibility Rules

### Rule AI‑15 — `dump_state()` MUST serialise ALL member variables that affect output

```cpp
std::string dump_state() const {
    std::ostringstream oss;
    oss << name() << "{"
        // ── Control state ─────────────────────────────────────
        << " fsm="      << state_name(state_)
        << " stall="    << stall_
        << " rst_n="    << rst_n_
        // ── Data state ────────────────────────────────────────
        << " pc=0x"     << std::hex << pc_
        << " insn=0x"   << insn_
        // ── Queue state ───────────────────────────────────────
        << std::dec
        << " rob_fill=" << rob_.size()  << "/" << ROB_DEPTH
        << " lsq_fill=" << lsq_.size()  << "/" << LSQ_DEPTH
        // ── Performance state ─────────────────────────────────
        << " cycles="   << total_cycles_
        << " stalls="   << stall_cycles_
        << "}";
    return oss.str();
}
```

### Rule AI‑16 — `dump_state()` output MUST be deterministic — same state → same string

The string MUST NOT include wall-clock time, pointers, or any value that
varies between runs.

```cpp
// ❌ Forbidden in dump_state()
oss << " ptr=" << reinterpret_cast<uintptr_t>(buf_);   // pointer value varies
oss << " wall_ns=" << get_wall_time_ns();               // wall time varies
```

### Rule AI‑17 — State snapshots MUST be comparable with `==`

```cpp
// ✅ AI test pattern — snapshot comparison
const std::string before = m.dump_state();
m.apply_stimulus(stim);
sc_start(1, SC_NS);
const std::string after = m.dump_state();

if (after == before && stim.should_change_state) {
    SC_REPORT_ERROR("AI_TEST", "state did not change when expected");
}
```

### Rule AI‑18 — Submodule state MUST be included in parent's `dump_state()`

```cpp
std::string dump_state() const {
    std::ostringstream oss;
    oss << "Cpu{"
        << " fetch="  << fetch_.dump_state()
        << " decode=" << decode_.dump_state()
        << " cache="  << cache_.dump_state()
        << "}";
    return oss.str();
}
```

---

## 6. Pure Function Rules

### Rule AI‑19 — All lookup / decode / compute functions MUST be `const` pure functions

```cpp
// ✅ Pure — same inputs → same output, no side effects
uint32_t set_index(uint64_t addr)  const { return (addr >> offset_bits_) & set_mask_; }
uint64_t tag_of   (uint64_t addr)  const { return addr >> (offset_bits_ + index_bits_); }
bool     probe    (uint64_t addr)  const;
uint32_t hop_count(uint32_t s, uint32_t d) const;

// ❌ Forbidden — modifies state inside const function
uint32_t set_index(uint64_t addr) const {
    ++probe_count_;   // hidden side effect
    return (addr >> offset_bits_) & set_mask_;
}
```

### Rule AI‑20 — Const functions MUST NOT access global or static mutable state

```cpp
// ❌ Forbidden
uint32_t decode(uint32_t insn) const {
    return insn ^ global_xor_mask;   // global state — non-deterministic
}
```

### Rule AI‑21 — Functions with side effects MUST be clearly named as mutators

```cpp
// ✅ Clear naming — mutators are not const
void record_access(uint64_t addr);    // mutates hit_count_ — not const
void fill(uint64_t addr);             // mutates tag array — not const
bool probe(uint64_t addr) const;      // pure lookup — const
```

---

## 7. Container Determinism Rules

### Rule AI‑22 — Use `std::map` and `std::set` — never `std::unordered_map` or `std::unordered_set`

| Container | Iteration order | AI safe? |
|---|---|---|
| `std::map<K,V>` | Sorted by key — deterministic | ✅ |
| `std::set<K>` | Sorted — deterministic | ✅ |
| `std::vector<T>` | Insertion order — deterministic | ✅ |
| `std::array<T,N>` | Index order — deterministic | ✅ |
| `std::unordered_map<K,V>` | Hash-dependent — **non-deterministic** | ❌ |
| `std::unordered_set<K>` | Hash-dependent — **non-deterministic** | ❌ |
| `std::priority_queue<T>` | Heap order — may vary on equal keys | ⚠️ add sequence-number tiebreak |

### Rule AI‑23 — When `std::priority_queue` is required, add a sequence number tiebreak

```cpp
struct PqEntry {
    sc_time  priority;
    uint64_t seq;      // insertion order tiebreak
    Packet   pkt;

    bool operator>(const PqEntry& o) const {
        if (priority != o.priority) return priority > o.priority;
        return seq > o.seq;   // deterministic tiebreak
    }
};
```

### Rule AI‑24 — Container iteration in `dump_state()` MUST always produce the same order

```cpp
// ✅ std::map iterates in key order — deterministic dump
for (const auto& [addr, entry] : pending_map_) {
    oss << " [0x" << std::hex << addr << "=" << entry.status << "]";
}
```

---

## 8. Floating‑Point Determinism Rules

### Rule AI‑25 — Fix the floating-point rounding mode at simulation start

```cpp
#include <cfenv>

void before_end_of_elaboration() override {
    if (fesetround(FE_TONEAREST) != 0) {
        SC_REPORT_FATAL(name(), "failed to set FP rounding mode");
    }
}
```

### Rule AI‑26 — No floating-point arithmetic in `dump_state()` or state comparisons

```cpp
// ❌ Forbidden — FP comparison in dump breaks AI snapshot equality
oss << " hit_rate=" << (hit_count_ / static_cast<double>(total_count_));

// ✅ Correct — dump raw integer counts; let AI compute ratio
oss << " hits=" << hit_count_ << " total=" << total_count_;
```

### Rule AI‑27 — Latency calculations using FP MUST be followed by explicit rounding

```cpp
// ✅ Round to nearest nanosecond to avoid platform-specific FP drift
const double raw_ns = static_cast<double>(bytes) / bw_bytes_per_ns_;
const double rounded_ns = std::round(raw_ns * 1000.0) / 1000.0;   // 1 ps resolution
delay += sc_time(rounded_ns, SC_NS);
```

### Rule AI‑28 — Never compare two `sc_time` values derived from FP arithmetic with `==`

```cpp
// ❌ Fragile — FP-derived sc_time equality is platform-dependent
if (delay == sc_time(10.0, SC_NS)) { ... }

// ✅ Correct — compare with tolerance or use integer multiples of CLK_PERIOD
if (delay >= sc_time(9.999, SC_NS) && delay <= sc_time(10.001, SC_NS)) { ... }
// Or better: keep all times as integer multiples of CLK_PERIOD
const uint32_t cycles = 10;
delay += cycles * CLK_PERIOD;
```

---

## 9. SystemC AI‑Testability Rules

### Rule AI‑29 — SC_METHOD MUST NOT contain hidden local static state

```cpp
// ❌ Forbidden
void on_clock() {
    static uint32_t event_id = 0;   // hidden, non-resettable
    ++event_id;
}

// ✅ Correct — member variable, resettable
uint32_t event_id_ = 0;
void on_clock() { ++event_id_; }
void reset()    { event_id_ = 0; }
```

### Rule AI‑30 — Every SC_THREAD state transition MUST be observable via `dump_state()`

The FSM state of every `SC_THREAD` is a member variable. Its value at
any simulation instant is returned by `dump_state()`.

### Rule AI‑31 — Module reset MUST restore the exact same state as power-on-reset

```cpp
void reset() {
    state_       = FsmState::IDLE;
    pc_          = RESET_VECTOR;
    stall_       = false;
    rob_head_    = 0;
    rob_tail_    = 0;
    txn_count_   = 0;
    stall_count_ = 0;
    rob_.fill({});
}
```

### Rule AI‑32 — AI test harness MUST be able to single-step the simulation

```cpp
// ✅ Step harness — observe state after every cycle
for (uint32_t i = 0; i < N_CYCLES; ++i) {
    sc_start(CLK_PERIOD);
    const std::string snap = module_.dump_state();
    log_snapshot(i, snap);
    if (snap != golden_[i]) {
        report_divergence(i, golden_[i], snap);
    }
}
```

---

## 10. TLM‑2.0 AI‑Testability Rules

### Rule AI‑33 — Every TLM target MUST log the transaction before and after processing

```cpp
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
#ifdef AI_VERBOSE_LOG
    {
        std::ostringstream oss;
        oss << "txn_start"
            << " op="    << (pl.get_command() == tlm::TLM_READ_COMMAND ? "READ" : "WRITE")
            << " addr=0x" << std::hex << pl.get_address()
            << " bytes=" << std::dec << pl.get_data_length();
        SC_REPORT_INFO(name(), oss.str().c_str());
    }
#endif

    // ... perform transaction ...

#ifdef AI_VERBOSE_LOG
    {
        std::ostringstream oss;
        oss << "txn_end"
            << " status=" << pl.get_response_string()
            << " delay_ns=" << delay.to_double();
        SC_REPORT_INFO(name(), oss.str().c_str());
    }
#endif
}
```

### Rule AI‑34 — TLM payload fields MUST be fully observable

AI must be able to verify the entire payload state:

```cpp
std::string dump_payload(const tlm::tlm_generic_payload& pl) {
    std::ostringstream oss;
    oss << "Payload{"
        << " cmd="    << (pl.get_command() == tlm::TLM_READ_COMMAND ? "R" : "W")
        << " addr=0x" << std::hex << pl.get_address()
        << " bytes="  << std::dec << pl.get_data_length()
        << " status=" << pl.get_response_string()
        << "}";
    return oss.str();
}
```

### Rule AI‑35 — All TLM module parameters MUST be observable via `dump_config()`

```cpp
std::string dump_config() const {
    std::ostringstream oss;
    oss << name() << "_config{"
        << " rd_lat_ns=" << rd_latency_.to_double()
        << " wr_lat_ns=" << wr_latency_.to_double()
        << " bw_GBps="   << bw_bytes_per_ns_
        << " capacity="  << capacity_bytes_
        << "}";
    return oss.str();
}
```

---

## 11. VP Performance Modelling AI‑Testability Rules

### Rule AI‑36 — Performance parameters MUST be sweepable

```cpp
// ✅ AI can instantiate with any combination
MemSubsystem mem("mem",
    /*l1_sets=*/64,    /*l1_ways=*/4,
    /*l2_sets=*/512,   /*l2_ways=*/8,
    /*dram_lat=*/sc_time(80, SC_NS),
    /*dram_bw=*/8.0,
    /*arb_policy=*/ArbPolicy::ROUND_ROBIN);
```

### Rule AI‑37 — Statistics MUST be independently resettable without restarting simulation

```cpp
void reset_stats() {
    perf_.transactions  = 0;
    perf_.total_latency = SC_ZERO_TIME;
    perf_.peak_latency  = SC_ZERO_TIME;
    hit_count_  = 0;
    miss_count_ = 0;
    busy_cycles_ = 0;
}
```

This allows AI to measure throughput in isolated windows (warm-up phase
excluded from measurement).

### Rule AI‑38 — Performance counters MUST be checkpointable and restorable

```cpp
struct PerfSnapshot {
    uint64_t transactions;
    double   total_latency_ns;
    double   peak_latency_ns;
    uint64_t hit_count;
    uint64_t miss_count;

    std::string serialise() const {
        std::ostringstream oss;
        oss << "txns="    << transactions
            << " tot_ns=" << total_latency_ns
            << " peak_ns="<< peak_latency_ns
            << " hits="   << hit_count
            << " misses=" << miss_count;
        return oss.str();
    }
};

PerfSnapshot checkpoint() const {
    return { perf_.transactions,
             perf_.total_latency.to_double(),
             perf_.peak_latency.to_double(),
             hit_count_, miss_count_ };
}
```

---

## 12. Stimulus Injection Rules

### Rule AI‑39 — Every module MUST accept stimulus through a typed `Stimulus` struct

```cpp
struct CacheStimulus {
    tlm::tlm_command cmd;
    uint64_t         addr;
    uint32_t         bytes;
    bool             flush;   // optional control: flush all lines
};

void apply_stimulus(const CacheStimulus& s) {
    if (s.flush) { flush_all(); return; }
    pl_.set_command(s.cmd);
    pl_.set_address(s.addr);
    pl_.set_data_length(s.bytes);
    pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
    sc_time delay = SC_ZERO_TIME;
    isock->b_transport(pl_, delay);
    wait(delay);
}
```

### Rule AI‑40 — Stimulus structs MUST be serialisable and deserialisable

```cpp
std::string CacheStimulus::serialise() const {
    std::ostringstream oss;
    oss << "cmd=" << (cmd == tlm::TLM_READ_COMMAND ? "R" : "W")
        << " addr=0x" << std::hex << addr
        << " bytes="  << std::dec << bytes
        << " flush="  << flush;
    return oss.str();
}

CacheStimulus CacheStimulus::deserialise(const std::string& s) {
    CacheStimulus st{};
    // ... parse key=value pairs ...
    return st;
}
```

### Rule AI‑41 — AI test harness MUST be able to replay a stimulus sequence from a log file

```cpp
void replay_from_log(const std::string& log_path, AiTestable& module) {
    std::ifstream f(log_path);
    std::string line;
    while (std::getline(f, line)) {
        const auto stim = CacheStimulus::deserialise(line);
        module.apply_stimulus(stim);
        sc_start(CLK_PERIOD);
    }
}
```

---

## 13. Golden Reference Rules

### Rule AI‑42 — Every testable module MUST have a golden reference model

The golden reference is a minimal, provably-correct C++ model of the
expected behaviour. It needs no timing model — only functional correctness.

```cpp
// Golden reference — pure C++, no SystemC, no TLM
class GoldenCache {
public:
    GoldenCache(uint32_t sets, uint32_t ways, uint32_t line_bytes)
        : sets_(sets), ways_(ways), line_bytes_(line_bytes),
          tags_(sets, std::vector<uint64_t>(ways, INVALID)),
          valid_(sets, std::vector<bool>(ways, false)) {}

    bool probe(uint64_t addr) const {
        const uint32_t s = set(addr);
        const uint64_t t = tag(addr);
        for (uint32_t w = 0; w < ways_; ++w)
            if (valid_[s][w] && tags_[s][w] == t) return true;
        return false;
    }

    void fill(uint64_t addr) {
        const uint32_t s = set(addr);
        const uint64_t t = tag(addr);
        // Find invalid way, else evict way 0 (simplified)
        for (uint32_t w = 0; w < ways_; ++w) {
            if (!valid_[s][w]) { tags_[s][w] = t; valid_[s][w] = true; return; }
        }
        tags_[s][0] = t;   // evict
    }

private:
    static constexpr uint64_t INVALID = ~0ULL;
    uint32_t sets_, ways_, line_bytes_;
    std::vector<std::vector<uint64_t>> tags_;
    std::vector<std::vector<bool>>     valid_;

    uint32_t set(uint64_t a) const { return (a / line_bytes_) % sets_; }
    uint64_t tag(uint64_t a) const { return a / (line_bytes_ * sets_); }
};
```

### Rule AI‑43 — AI test MUST compare VP model output against golden reference output

```cpp
void run_cache_ai_test(uint32_t sets, uint32_t ways, uint32_t line_bytes,
                       const std::vector<CacheStimulus>& stimuli)
{
    GoldenCache golden(sets, ways, line_bytes);
    VpCache     vp("vp", sets, ways, line_bytes,
                   L1_HIT_LATENCY, L2_HIT_LATENCY);

    for (const auto& s : stimuli) {
        const bool golden_hit = golden.probe(s.addr);
        vp.apply_stimulus(s);
        sc_start(CLK_PERIOD);

        // Compare functional result
        const bool vp_hit = vp.last_hit();
        if (vp_hit != golden_hit) {
            std::ostringstream oss;
            oss << "MISMATCH stim=" << s.serialise()
                << " golden_hit=" << golden_hit
                << " vp_hit=" << vp_hit;
            SC_REPORT_ERROR("AI_TEST", oss.str().c_str());
        }

        // Update golden after comparison
        if (!golden_hit) golden.fill(s.addr);
    }
}
```

---

## 14. Hardware Diagrams — AI Instrumentation Points

### 14.1 AI observation points in a 5-stage pipeline

```
  ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐
  │  FETCH   │──────▶│  DECODE  │──────▶│  ISSUE   │──────▶│ EXECUTE  │──────▶│   WB     │
  └──────────┘  FIFO └──────────┘  FIFO └──────────┘  FIFO └──────────┘  FIFO └──────────┘
       │                 │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼                 ▼
  ① dump_state()   ② dump_state()   ③ dump_state()   ④ dump_state()   ⑤ dump_state()
    pc, valid        insn, valid       rd, rs1, rs2      result           commit_pc

  AI harness observes all 5 dumps after every clock cycle.
  FIFO occupancy also visible via dump_state() at each stage boundary.
```

### 14.2 AI observation points in a TLM memory subsystem

```
  AI Initiator
  ────────────
  apply_stimulus(stim) ──▶  [dump_config() before run]
                            ┌─────────┐
                            │ Arbiter │──▶ grant_delay logged: "arb_grant master=N delay=X"
                            └────┬────┘
                                 ▼
                            ┌─────────┐
                            │  L1 $   │──▶ hit/miss logged: "op=PROBE hit=true/false"
                            └────┬────┘
                                 │ (miss only)
                                 ▼
                            ┌─────────┐
                            │  DRAM   │──▶ access logged: "op=DRAM_READ delay_ns=94"
                            └─────────┘
  AI reads dump_stats() after run:
  "txns=N avg_lat=X peak_lat=Y hit_rate=Z util=W"
```

### 14.3 AI stimulus → observe → compare loop

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  AI Test Harness                                                │
  │                                                                 │
  │  ① Generate stimulus sequence (or load from log)               │
  │  ② apply_stimulus(stim) on VP module                           │
  │  ③ sc_start(CLK_PERIOD)                                        │
  │  ④ snap_vp     = vp_module.dump_state()                        │
  │  ⑤ snap_golden = golden_model.step(stim)                       │
  │  ⑥ assert snap_vp == snap_golden (functional)                  │
  │  ⑦ assert perf within tolerance (timing)                       │
  │  ⑧ Log divergence with full state dump if mismatch             │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 15. AI Test Harness Patterns

### 15.1 Single-step cycle harness

```cpp
template<typename Module>
void run_cycle_harness(Module& dut,
                       const std::vector<typename Module::Stimulus>& stimuli,
                       const std::vector<std::string>& golden_snaps)
{
    sc_assert(stimuli.size() == golden_snaps.size());
    dut.reset();

    for (std::size_t i = 0; i < stimuli.size(); ++i) {
        dut.apply_stimulus(stimuli[i]);
        sc_start(CLK_PERIOD);

        const std::string snap = dut.dump_state();
        if (snap != golden_snaps[i]) {
            std::ostringstream oss;
            oss << "CYCLE " << i << " MISMATCH\n"
                << "  expected: " << golden_snaps[i] << "\n"
                << "  actual:   " << snap;
            SC_REPORT_ERROR("AI_HARNESS", oss.str().c_str());
        }
    }
}
```

### 15.2 Parameter sweep harness

```cpp
struct SweepResult {
    uint32_t    rob_depth;
    uint32_t    cache_sets;
    double      ipc;
    double      hit_rate;
    sc_time     avg_latency;
};

std::vector<SweepResult> sweep_cache_rob(
    const std::vector<uint32_t>& rob_depths,
    const std::vector<uint32_t>& cache_sets,
    const std::vector<CacheStimulus>& workload)
{
    std::vector<SweepResult> results;
    for (uint32_t rob : rob_depths) {
        for (uint32_t sets : cache_sets) {
            VpCore core("core", rob, sets, /*ways=*/4);
            core.reset();
            for (const auto& s : workload) {
                core.apply_stimulus(s);
                sc_start(CLK_PERIOD);
            }
            results.push_back({rob, sets,
                               core.ipc(), core.hit_rate(),
                               core.avg_latency()});
        }
    }
    return results;
}
```

### 15.3 Regression harness — replay and compare

```cpp
void regression_test(const std::string& golden_log_path, AiTestable& dut) {
    std::ifstream f(golden_log_path);
    std::string line;
    uint32_t cycle = 0;
    while (std::getline(f, line)) {
        if (line.substr(0, 5) == "snap:") {
            const std::string expected = line.substr(5);
            const std::string actual   = dut.dump_state();
            if (actual != expected) {
                std::ostringstream oss;
                oss << "REGRESSION at cycle " << cycle
                    << "\n  expected: " << expected
                    << "\n  actual:   " << actual;
                SC_REPORT_ERROR("REGRESSION", oss.str().c_str());
            }
        } else if (line.substr(0, 5) == "stim:") {
            // deserialise and apply stimulus
        }
        sc_start(CLK_PERIOD);
        ++cycle;
    }
}
```

### 15.4 Fuzz harness — random but seeded stimulus

```cpp
void fuzz_harness(AiTestable& dut, uint32_t seed, uint32_t n_cycles) {
    std::mt19937 rng(seed);   // fixed seed — reproducible
    dut.reset();

    for (uint32_t i = 0; i < n_cycles; ++i) {
        CacheStimulus s;
        s.cmd   = (rng() & 1) ? tlm::TLM_READ_COMMAND : tlm::TLM_WRITE_COMMAND;
        s.addr  = (rng() % 256) * CACHE_LINE_BYTES;
        s.bytes = CACHE_LINE_BYTES;
        s.flush = false;

        dut.apply_stimulus(s);
        sc_start(CLK_PERIOD);

        // Log every cycle for post-hoc analysis
        SC_REPORT_INFO("FUZZ",
            (std::to_string(i) + " " + dut.dump_state()).c_str());
    }
}
```

---

## 16. AI‑Friendly Module Templates

### 16.1 Full AI‑testable SC_MODULE template

```cpp
// ai_testable_module.h
#pragma once
#include <systemc>
#include <string>
#include <sstream>
#include <cstdint>

// Base interface — every module implements this
struct AiTestable {
    virtual std::string dump_state() const = 0;
    virtual std::string dump_stats() const = 0;
    virtual std::string dump_config() const = 0;
    virtual void        reset() = 0;
    virtual ~AiTestable() = default;
};

// Template: replace placeholders with real hardware logic
SC_MODULE(AiModule), public AiTestable {
public:
    // ── Ports ──────────────────────────────────────────────────
    sc_in<bool>    clk;
    sc_in<bool>    rst_n;
    sc_in<uint32_t> data_in;
    sc_out<uint32_t> data_out;

    // ── Constructor ────────────────────────────────────────────
    SC_HAS_PROCESS(AiModule);
    explicit AiModule(sc_module_name name, uint32_t param_a)
        : sc_module(name), param_a_(param_a) {
        SC_METHOD(on_clock);
        sensitive << clk.pos() << rst_n.neg();
        dont_initialize();
    }

    // ── AI‑testability interface ────────────────────────────────
    std::string dump_state() const override {
        std::ostringstream oss;
        oss << name() << "{"
            << " reg=0x"    << std::hex << reg_
            << " cycles="   << std::dec << total_cycles_
            << " stalls="   << stall_count_
            << "}";
        return oss.str();
    }

    std::string dump_stats() const override {
        std::ostringstream oss;
        oss << name() << "_stats{"
            << " total_cycles=" << total_cycles_
            << " stalls="       << stall_count_
            << "}";
        return oss.str();
    }

    std::string dump_config() const override {
        std::ostringstream oss;
        oss << name() << "_config{"
            << " param_a=" << param_a_
            << "}";
        return oss.str();
    }

    void reset() override {
        reg_          = 0;
        total_cycles_ = 0;
        stall_count_  = 0;
    }

private:
    uint32_t param_a_;
    uint32_t reg_          = 0;
    uint64_t total_cycles_ = 0;
    uint64_t stall_count_  = 0;

    void on_clock() {
        if (!rst_n.read()) { reset(); return; }
        ++total_cycles_;
        reg_ = data_in.read();
        data_out.write(reg_);
    }
};
```

---

## 17. Complete AI‑Testable Module Example

A complete, fully AI-testable cache module demonstrating all rules above.

```cpp
// ai_cache.h
#pragma once
#include <systemc>
#include <tlm>
#include "tlm_utils/simple_target_socket.h"
#include <array>
#include <vector>
#include <sstream>
#include <cstdint>
#include <cstring>
#include <cfenv>

constexpr uint32_t AC_SETS       = 64;
constexpr uint32_t AC_WAYS       = 4;
constexpr uint32_t AC_LINE_BYTES = 64;
constexpr sc_time  AC_HIT_LAT   (4,  SC_NS);
constexpr sc_time  AC_MISS_PEN  (80, SC_NS);
constexpr double   AC_BW_BYTES_PER_NS = 8.0;

struct CacheStimulus {
    tlm::tlm_command cmd   = tlm::TLM_READ_COMMAND;
    uint64_t         addr  = 0;
    uint32_t         bytes = AC_LINE_BYTES;
    bool             flush = false;

    std::string serialise() const {
        std::ostringstream oss;
        oss << "cmd=" << (cmd == tlm::TLM_READ_COMMAND ? "R" : "W")
            << " addr=0x" << std::hex << addr
            << " bytes="  << std::dec << bytes
            << " flush="  << flush;
        return oss.str();
    }
};

SC_MODULE(AiCache) {
    tlm_utils::simple_target_socket<AiCache> tsock{"tsock"};

    SC_HAS_PROCESS(AiCache);
    AiCache(sc_module_name name,
            uint32_t sets, uint32_t ways, uint32_t line_bytes,
            sc_time hit_lat, sc_time miss_pen, double bw_bytes_per_ns)
        : sc_module(name)
        , sets_(sets), ways_(ways), line_bytes_(line_bytes)
        , hit_lat_(hit_lat), miss_pen_(miss_pen)
        , bw_(bw_bytes_per_ns)
    {
        fesetround(FE_TONEAREST);
        tsock.register_b_transport(this, &AiCache::b_transport);
        tags_.assign(sets_, std::vector<uint64_t>(ways_, INVALID_TAG));
        valid_.assign(sets_, std::vector<bool>(ways_, false));
    }

    // ── AI‑testability ─────────────────────────────────────────
    std::string dump_state() const {
        std::ostringstream oss;
        oss << name() << "{"
            << " sets=" << sets_ << " ways=" << ways_
            << " hits=" << hits_ << " misses=" << misses_
            << "}";
        return oss.str();
    }

    std::string dump_stats() const {
        std::ostringstream oss;
        oss << name() << "_stats{"
            << " hits="     << hits_
            << " misses="   << misses_
            << " hit_rate=" << hit_rate()
            << " avg_lat_ns=" << avg_lat_ns()
            << "}";
        return oss.str();
    }

    std::string dump_config() const {
        std::ostringstream oss;
        oss << name() << "_config{"
            << " sets="         << sets_
            << " ways="         << ways_
            << " line_bytes="   << line_bytes_
            << " hit_lat_ns="   << hit_lat_.to_double()
            << " miss_pen_ns="  << miss_pen_.to_double()
            << " bw_GBps="      << bw_
            << "}";
        return oss.str();
    }

    void reset() {
        for (auto& row : tags_)  std::fill(row.begin(), row.end(), INVALID_TAG);
        for (auto& row : valid_) std::fill(row.begin(), row.end(), false);
        hits_ = misses_ = 0;
        total_lat_ns_ = 0.0;
        last_hit_ = false;
    }

    double hit_rate() const {
        const uint64_t t = hits_ + misses_;
        return t > 0 ? static_cast<double>(hits_) / t : 0.0;
    }

    double avg_lat_ns() const {
        const uint64_t t = hits_ + misses_;
        return t > 0 ? total_lat_ns_ / t : 0.0;
    }

    bool last_hit() const { return last_hit_; }

private:
    static constexpr uint64_t INVALID_TAG = ~0ULL;

    uint32_t sets_, ways_, line_bytes_;
    sc_time  hit_lat_, miss_pen_;
    double   bw_;

    std::vector<std::vector<uint64_t>> tags_;
    std::vector<std::vector<bool>>     valid_;

    uint64_t hits_ = 0, misses_ = 0;
    double   total_lat_ns_ = 0.0;
    bool     last_hit_ = false;

    uint32_t set_idx(uint64_t a) const { return (a / line_bytes_) % sets_; }
    uint64_t tag_of (uint64_t a) const { return a / (static_cast<uint64_t>(line_bytes_) * sets_); }

    bool probe(uint64_t addr) const {
        const uint32_t s = set_idx(addr);
        const uint64_t t = tag_of(addr);
        for (uint32_t w = 0; w < ways_; ++w)
            if (valid_[s][w] && tags_[s][w] == t) return true;
        return false;
    }

    void install(uint64_t addr) {
        const uint32_t s = set_idx(addr);
        const uint64_t t = tag_of(addr);
        for (uint32_t w = 0; w < ways_; ++w) {
            if (!valid_[s][w]) { tags_[s][w] = t; valid_[s][w] = true; return; }
        }
        tags_[s][0] = t;   // LRU simplified: evict way 0
    }

    void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
        const uint64_t addr  = pl.get_address();
        const uint32_t bytes = pl.get_data_length();

        last_hit_ = probe(addr);
        sc_time contrib;

        if (last_hit_) {
            contrib = hit_lat_;
            ++hits_;
        } else {
            contrib = miss_pen_;
            contrib += sc_time(std::round(static_cast<double>(bytes) / bw_ * 1000.0) / 1000.0, SC_NS);
            install(addr);
            ++misses_;
        }

        delay += contrib;
        total_lat_ns_ += contrib.to_double();

#ifdef AI_VERBOSE_LOG
        std::ostringstream oss;
        oss << "op=" << (pl.get_command() == tlm::TLM_READ_COMMAND ? "READ" : "WRITE")
            << " addr=0x" << std::hex << addr
            << " bytes=" << std::dec << bytes
            << " hit=" << last_hit_
            << " contrib_ns=" << contrib.to_double();
        SC_REPORT_INFO(name(), oss.str().c_str());
#endif

        pl.set_response_status(tlm::TLM_OK_RESPONSE);
    }
};
```

---

## 18. Anti‑Patterns

| Anti‑Pattern | AI testing consequence | Fix |
|---|---|---|
| `static` local variables in process | Non-resettable hidden state — test isolation impossible | Move to module member with `reset()` |
| No `dump_state()` | AI cannot observe module — black box | Implement full `dump_state()` |
| `std::cout` logging | Unordered output, no timestamp — unparseable | `SC_REPORT_INFO` with key=value |
| Free-form log strings | AI cannot parse field values | `key=value` format, fixed field order |
| Hardcoded parameters | AI cannot sweep configuration space | Constructor-injected parameters |
| FP in dump strings | Snapshot comparison fails across platforms | Dump raw integer counts only |
| No `reset()` method | Cannot isolate test runs | Explicit `reset()` restoring POR state |
| No golden reference | No correctness baseline | `GoldenCache` / `GoldenFsm` reference model |
| `std::unordered_map` in state dump | Non-deterministic field order | `std::map` for deterministic iteration |
| Pointer values in dump | Differ every run — comparison always fails | Never include pointers in `dump_state()` |
| Wall time in log | Non-deterministic — regression comparison breaks | Use `sc_time_stamp()` only |
| No stats reset | Cannot measure warm-up vs steady-state separately | `reset_stats()` separate from `reset()` |

---

## 19. Checklist

Use in every AI-testable module code review.

### Determinism
- [ ] No `rand()`, `random_device`, OS time, or wall clock
- [ ] No `static` local variables in process callbacks
- [ ] No global mutable state
- [ ] FP rounding mode fixed in `before_end_of_elaboration()`

### Structural testability
- [ ] Inherits or implements `AiTestable` interface
- [ ] All parameters injectable at construction
- [ ] Typed `apply_stimulus()` method present
- [ ] `reset()` restores exact POR state

### State visibility
- [ ] `dump_state()` serialises ALL output-affecting member variables
- [ ] No pointer values, wall time, or platform-specific values in dump
- [ ] Submodule states included in parent `dump_state()`
- [ ] `dump_config()` exposes all configuration parameters

### Logging
- [ ] All logs use `SC_REPORT_INFO` / `SC_REPORT_*`
- [ ] Log format is `key=value`, fixed field order
- [ ] Verbose logs guarded by `#ifdef AI_VERBOSE_LOG`
- [ ] FSM transitions log old state, trigger, and new state

### Pure functions
- [ ] All lookup/decode/compute functions are `const`
- [ ] No side effects in `const` functions
- [ ] Mutators clearly named and not `const`

### Container determinism
- [ ] `std::map` / `std::set` used — no `unordered_*`
- [ ] `std::priority_queue` has sequence-number tiebreak if used

### Golden reference
- [ ] Golden reference model exists for every VP module
- [ ] AI test compares VP output vs golden output
- [ ] Divergence logged with full state dump

### Statistics
- [ ] Transaction count, total latency, peak latency collected
- [ ] `reset_stats()` available separately from `reset()`
- [ ] Stats observable via `dump_stats()`

---

## 20. Glossary

| Term | Definition |
|---|---|
| **AI black-box testing** | AI agent drives typed stimulus into module interfaces and validates outputs without knowing internal implementation |
| **Determinism** | Same inputs + same state → same outputs, every run, every machine |
| **dump\_state()** | Method returning a stable, complete string serialisation of all module state |
| **dump\_stats()** | Method returning performance counters (txns, latency, hit rate, utilisation) |
| **dump\_config()** | Method returning the module's construction-time parameters |
| **AiTestable** | Base interface — `dump_state()`, `dump_stats()`, `dump_config()`, `reset()` |
| **apply\_stimulus()** | Typed method to inject a `Stimulus` struct into a module |
| **Stimulus struct** | Typed, serialisable data structure encoding one test input |
| **Golden reference** | Minimal, provably-correct C++ model used to generate expected outputs |
| **Snapshot comparison** | `assert(vp.dump_state() == golden.dump_state())` |
| **key=value log** | Machine-parseable log format — AI can regex-extract any field |
| **POR state** | Power-On-Reset state — the exact state after hardware reset |
| **reset\_stats()** | Clears performance counters without resetting functional state |
| **Checkpoint** | Serialised performance counter snapshot for interval measurement |
| **Fuzz harness** | Seeded PRNG-driven stimulus — reproducible random coverage |
| **Regression harness** | Replays a golden stimulus log and compares state snapshots |
| **Parameter sweep** | AI instantiates the module with varying config and measures output |
| **FE\_TONEAREST** | IEEE 754 round-to-nearest mode — deterministic FP rounding |
| **SC\_REPORT\_INFO** | SystemC structured reporting — attaches time and module name |
| **SC\_ZERO\_TIME** | `sc_time(0, SC_NS)` — zero simulation time |
