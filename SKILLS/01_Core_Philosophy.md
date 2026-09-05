# Core Philosophy for Deterministic Hardware Modelling & SystemC/VP Engineering

**Version:** 1.0 — July 2026  
**Standard:** Mandatory  
**Audience:** All engineers — <5‑year engineers must read before writing any model code

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Determinism First](#2-determinism-first)
3. [Predictability Over Cleverness](#3-predictability-over-cleverness)
4. [Hardware‑Aligned Thinking](#4-hardwarealigned-thinking)
5. [Simulation Is Not Software Execution](#5-simulation-is-not-software-execution)
6. [AI‑Testability Philosophy](#6-aitestability-philosophy)
7. [SystemC Philosophy](#7-systemc-philosophy)
8. [TLM‑2.0 Philosophy](#8-tlm20-philosophy)
9. [VP Performance Modelling Philosophy](#9-vp-performance-modelling-philosophy)
10. [DSA Philosophy for Hardware](#10-dsa-philosophy-for-hardware)
11. [Code Review Philosophy](#11-code-review-philosophy)
12. [Summary](#12-summary)

---

## 1. Purpose

This document defines the core philosophy behind deterministic, safe, and
predictable modelling code for:

- Virtual Prototyping (VP)
- SystemC / TLM‑2.0
- Performance Modelling
- Front‑End Silicon Architecture
- ESL Modelling
- AI‑assisted black‑box testing

It establishes the **mindset** required for engineers to write code that is:

| Property | Why it matters |
|---|---|
| **Deterministic** | Reproducible bugs, reproducible regressions |
| **Hardware‑aligned** | Model reflects silicon — not software patterns |
| **AI‑testable** | AI stimulus generators need pure, stateless interfaces |
| **Maintainable** | Next engineer must understand it without author context |
| **Predictable** | O‑complexity and timing must be known at design time |
| **Safe** | No UB, no leaks, no dangling references |

---

## 2. Determinism First

> **Hardware is deterministic. Your modelling code must be too.**

Every simulation run with identical stimulus must produce identical results —
cycle counts, transaction logs, state traces, and output values.

### Non‑negotiable rules

| Rule | Forbidden pattern | Allowed alternative |
|---|---|---|
| No randomness | `rand()`, `mt19937` without fixed seed | Fixed seed + documented seed parameter |
| No FP nondeterminism | `double` arithmetic without rounding control | Integer arithmetic; fixed rounding mode |
| No non‑deterministic containers | `unordered_map` iteration | `std::map` or `unordered_map` with fixed hash + sorted output |
| No global mutable state | `static int counter` | State encapsulated in the owning module |
| No OS time | `gettimeofday()`, `std::chrono::now()` | `sc_time_stamp()` |
| No concurrency races | Shared variable between `SC_THREAD`s | Explicit channel or `sc_signal` |
| No UB | Signed overflow, out‑of‑bounds, null deref | Asserts, bounds checks, `std::array` |

---

## 3. Predictability Over Cleverness

> **Clever code is dangerous in modelling.**

A one‑liner that saves 10 characters but hides the latency model is worse
than 5 explicit lines that make the pipeline stage obvious.

### Prefer explicit over implicit

```
✅  Explicit state machines
✅  Explicit pipeline stage structs
✅  Explicit latency constants (named, not magic numbers)
✅  Explicit bandwidth limits
✅  Explicit arbitration logic
✅  Explicit ownership (RAII, unique_ptr)
✅  Explicit lifetime (stack > heap)
```

### Avoid

```
❌  Hidden state transitions inside operator overloads
❌  Implicit integer promotion hiding bus-width truncation
❌  Template metaprogramming that obscures pipeline structure
❌  "One‑liner clever hacks" — if it needs a comment to explain the trick,
    the trick is wrong
❌  Overloaded operators that have timing side effects
```

---

## 4. Hardware‑Aligned Thinking

Software engineers think in **functions and data structures**.  
Hardware engineers think in **physical structures and time**.

### The hardware mental model

```
Pipelines        — stages with latency and throughput
FIFOs            — bounded queues with backpressure
State machines   — explicit, enumerated, drawn before coded
Arbiters         — fair or priority, never implicit
Latency          — every operation takes N cycles
Bandwidth        — every channel has a peak rate
Hazards          — RAW, WAR, WAW — explicit detection
Stalls           — normal, not an error condition
Clock domains    — crossing requires synchronisers
Memory hierarchy — L1/L2/L3/DRAM — each has latency + bandwidth
NoC topology     — mesh, ring, crossbar — routing is explicit
```

### Rule: model structure mirrors silicon

If the RTL has a 4-stage pipeline, the model has 4 named pipeline stage
structs. If the silicon has a 4-deep store buffer, the model has a
`std::array<StoreEntry, 4>`. The code is documentation of the hardware.

---

## 5. Simulation Is Not Software Execution

These two mental models are **incompatible**. Never mix them.

| Dimension | Simulation (SystemC) | Software execution |
|---|---|---|
| Scheduling | Event‑driven, deterministic | OS‑scheduled, non‑deterministic |
| Time | `sc_time` — discrete, explicit | Wall clock — continuous, opaque |
| Threads | Cooperative coroutines (SC_THREAD) | Preemptive OS threads |
| Order | Defined by sensitivity lists | Defined by OS scheduler |
| Side effects | Must be confined to `delta` | Can span arbitrary time |
| Blocking | Only inside `SC_THREAD` with `wait()` | Anywhere |

### Consequences

- **Never** call `std::this_thread::sleep_for` in a SystemC model.
- **Never** use `std::mutex` inside simulation processes.
- **Never** rely on destructor order across modules — use `end_of_simulation`.
- **Never** read OS wall time to make simulation decisions.

---

## 6. AI‑Testability Philosophy

AI black‑box testing drives stimulus into model interfaces and checks
outputs. This only works if the model exposes **pure, stateless, typed
interfaces**.

### 6.1 Pure functions

```cpp
// ✅ AI-testable — pure function
uint32_t compute_tag(uint64_t addr, uint32_t index_bits, uint32_t offset_bits) const;

// ❌ Not AI-testable — reads hidden global state
uint32_t compute_tag(uint64_t addr) const;   // uses g_cache_config internally
```

### 6.2 Deterministic logging

```cpp
// ✅ Correct — deterministic, SC_REPORT route
std::ostringstream oss;
oss << "[FETCH] pc=0x" << std::hex << pc << " cycle=" << std::dec << cycle;
SC_REPORT_INFO("FETCH", oss.str().c_str());

// ❌ Forbidden — bypasses SystemC time-stamp
std::cout << "pc=" << pc << "\n";
```

### 6.3 No hidden state

Every piece of state that affects output **must** be:
- A named member variable
- Accessible via a `const` getter
- Visible in the model's state dump

### 6.4 No non‑deterministic containers

`std::unordered_map` iterates in hash-dependent order. AI test comparisons
of state dumps will be flaky.  Use `std::map`.

### 6.5 Fixed floating‑point rounding

```cpp
// At module construction — lock rounding mode
fesetround(FE_TONEAREST);
```

---

## 7. SystemC Philosophy

> **SystemC is not C++. It is a hardware description language embedded in C++.**

Treat SystemC constructs with the same discipline as RTL coding rules.

### 7.1 SC_METHOD — combinational process

```
✅  Reads inputs (sc_in / sc_signal)
✅  Computes outputs combinationally
✅  Writes outputs (sc_out / sc_signal)
✅  Returns immediately

❌  Calls wait()          — compile error, but conceptually forbidden
❌  Allocates memory      — non-deterministic timing
❌  Performs file I/O     — side effects outside simulation
❌  Modifies shared state — race condition across delta cycles
```

### 7.2 SC_THREAD — sequential process

```
✅  Uses wait() for time advance and event synchronisation
✅  Implements multi-cycle protocols (handshakes, burst transfers)
✅  Maintains local state across wait() calls

❌  Calls OS sleep()           — bypasses simulation time
❌  Allocates on hot path      — timing perturbation
❌  Relies on thread-local storage — non-portable, non-deterministic
```

### 7.3 Sensitivity lists — must be static and deterministic

```cpp
// ✅ Static sensitivity — safe
SC_METHOD(on_clock);
sensitive << clk.pos();

// ❌ Dynamic sensitivity inside process body — forbidden
// (changes the sensitivity set at runtime — unpredictable)
```

### 7.4 Time — use sc_time, never OS time

```cpp
sc_time latency(10, SC_NS);   // ✅
wait(latency);                // ✅

// ❌ Forbidden
std::this_thread::sleep_for(std::chrono::nanoseconds(10));
```

---

## 8. TLM‑2.0 Philosophy

> **TLM is a hardware transaction protocol — not a software RPC.**

### Core rules

| Rule | Rationale |
|---|---|
| `b_transport` must be deterministic | Same payload → same effect, every call |
| No exceptions in `b_transport` | Use `tlm_response_status` codes |
| No dynamic allocation on hot path | Non‑deterministic timing |
| No logging in critical TLM paths | Use `#ifdef DEBUG_TLM` guards |
| No polymorphic payload extensions unless documented | Hidden dependencies break AI testing |
| `timing_annotation` must be set | Omitting it silently collapses latency |

### Transaction lifecycle ownership

```
Initiator allocates payload    →  initiator owns it
Initiator calls b_transport    →  target borrows it (must not store pointer)
b_transport returns            →  initiator resumes ownership
Initiator calls mm->free()     →  memory manager reclaims
```

Never store a reference to a TLM payload beyond the scope of the transport call.

---

## 9. VP Performance Modelling Philosophy

> **Performance modelling is not functional modelling.**

Functional models answer: *does the hardware produce the correct result?*  
Performance models answer: *how long does it take, and why?*

### 9.1 Latency is a first‑class citizen

Every operation **must** have an explicit latency:
```cpp
constexpr sc_time L1_HIT_LATENCY  (4,  SC_NS);
constexpr sc_time L2_HIT_LATENCY  (12, SC_NS);
constexpr sc_time DRAM_LATENCY    (80, SC_NS);
```

### 9.2 Bandwidth is a first‑class citizen

Every channel **must** have an explicit bandwidth model:
```cpp
constexpr uint32_t BUS_WIDTH_BYTES    = 64;
constexpr uint32_t BUS_FREQ_MHZ       = 800;
constexpr double   BUS_PEAK_GB_S      = (BUS_WIDTH_BYTES * BUS_FREQ_MHZ * 1e6) / 1e9;
```

### 9.3 Arbitration is a first‑class citizen

Shared resources **must** have explicit arbitration:
```cpp
enum class ArbPolicy { ROUND_ROBIN, FIXED_PRIORITY, WEIGHTED_FAIR };
```

### 9.4 Queues are everywhere

Every pipeline stage is a **bounded queue**. Model the bound explicitly:
```cpp
constexpr std::size_t ROB_SIZE      = 192;
constexpr std::size_t STORE_BUFFER  = 56;
constexpr std::size_t FETCH_QUEUE   = 16;
```

### 9.5 Stalls are normal

A stall is not an error — it is the model detecting a structural or data
hazard. Log stalls deterministically and account for them in throughput
calculations.

---

## 10. DSA Philosophy for Hardware

Classic DSA patterns map directly to hardware structures. Use the hardware
name, not the algorithm name, in code.

| DSA Pattern | Hardware Analogue | Use In Model |
|---|---|---|
| Sliding window | Pipeline window / ROB | Issue window, in‑flight tracking |
| Two‑pointer | Dual‑port memory access | Load/store unit pairs |
| Fast/slow pointer | Clock domain crossing | CDC FIFO read/write pointers |
| Merge intervals | Bus grant merging | Burst arbitration |
| Monotonic stack | Dependency chain | RAW hazard detection |
| BFS | Shortest path in NoC | Routing table generation |
| DFS | Dependency graph walk | Hazard resolution |
| Topological sort | Pipeline ordering | Stage scheduling |
| Union‑Find | Connectivity | Network topology modelling |
| Segment tree | Range queries | MMU region / TLB range lookup |

**Rule:** When implementing one of these patterns in a model, use the
hardware terminology in class/method names. Never name a hardware structure
`SlidingWindow` — name it `IssueWindow` or `ReorderBuffer`.

---

## 11. Code Review Philosophy

Every code review for model code **must** explicitly check all of the
following categories. Reviewers sign off on each:

| Category | Key question |
|---|---|
| **Determinism** | Can two runs with the same stimulus produce different results? |
| **Safety** | Any UB, dangling refs, out‑of‑bounds, leaks? |
| **Testability** | Can AI/unit tests drive and observe this code? |
| **Hardware alignment** | Does structure mirror silicon? Are latencies named constants? |
| **SystemC correctness** | SC_METHOD / SC_THREAD rules obeyed? |
| **TLM correctness** | Payload ownership correct? Response status set? |
| **Performance modelling** | Latency, bandwidth, queue bounds all explicit? |
| **AI‑testability** | Pure functions? No hidden state? Deterministic log? |

A review that approves code without checking all categories is **incomplete**.

---

## 12. Summary

| Pillar | One‑line rule |
|---|---|
| Determinism | Same stimulus → same result, always |
| Predictability | Explicit > clever |
| Hardware alignment | Code mirrors silicon structure |
| Simulation discipline | SystemC is not C++ threading |
| AI‑testability | Pure functions, no hidden state |
| TLM discipline | Transactions are hardware protocol, not RPC |
| Performance modelling | Latency, bandwidth, and queues are first‑class |
| DSA for hardware | Use hardware names for hardware patterns |
| Code review | All eight categories, every review |

The remaining files in the `SKILLS/` directory define the concrete rules
that implement this philosophy:

| File | Content |
|---|---|
| `02_C++_Rules.md` | C++ language rules |
| `03_SystemC_Rules.md` | SystemC process, signal, and module rules |
| `04_TLM2_Patterns.md` | TLM‑2.0 initiator/target patterns |
| `05_VP_Performance_Modelling.md` | Latency, bandwidth, and arbitration modelling |
| `06_DSA_Hardware_Patterns.md` | DSA adapted for hardware structures |
| `07_AI_Testing_Hooks.md` | AI‑testable interface design |
| `08_Hardware_Diagrams.md` | ASCII/Mermaid diagram conventions |
| `12_Review_Checklists.md` | Per‑category review checklists |
| `13_AntiPatterns.md` | What never to do and why |
| `15_Glossary.md` | Definitions for all terms used |
