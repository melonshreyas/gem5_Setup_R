# Code Review Checklists for C++, SystemC, TLM, VP, Memory Safety & AI‑Testability

**Version:** 1.0 — July 2026  
**Standard:** Mandatory — Every PR must pass the relevant checklists before merge

---

## How to Use

1. Identify which categories apply to the PR (C++, SystemC, TLM, VP, Memory, AI).
2. Work through each checklist item. Mark ✅ pass, ❌ fail, or N/A.
3. A PR may not merge if any item is marked ❌.
4. Cite the rule number (e.g. *C‑09*, *SC‑07*, *TLM‑12*) when raising a review comment.

---

## 1. General C++ Checklist

- [ ] Headers have `#pragma once` or `#ifndef` include guards
- [ ] No `using namespace std;` in any header
- [ ] Only required headers included — no `<bits/stdc++.h>`
- [ ] Fixed-width integer types used (`uint32_t`, `int64_t`) where appropriate
- [ ] Const-correctness applied throughout — all read-only methods are `const`
- [ ] No implicit conversions — single-argument constructors are `explicit`
- [ ] All six special member functions explicitly defined or deleted
- [ ] No raw owning pointers — `unique_ptr` / `shared_ptr` used for ownership
- [ ] No `new`/`delete` in hot paths — pools or pre-allocated storage used
- [ ] No exceptions in SystemC/TLM kernel paths
- [ ] `dump_state()` implemented for every simulation class
- [ ] All functions ≤ 40 lines
- [ ] No `using namespace std;` in `.cpp` files at file scope

---

## 2. SystemC Checklist

- [ ] `SC_METHOD` does not call `wait()` — confirmed no blocking
- [ ] `SC_METHOD` does not allocate heap memory
- [ ] `SC_METHOD` does not perform I/O (except `SC_REPORT` under `#ifdef` guard)
- [ ] `SC_METHOD` body is O(1) or O(small constant) — no unbounded loops
- [ ] `SC_THREAD` loops contain `wait()` — no infinite busy-spin
- [ ] `SC_THREAD` does not call OS blocking primitives (`sleep`, `mutex::lock`)
- [ ] Sensitivity lists are static — no runtime modification
- [ ] Edge/level sensitivity matches hardware intent
- [ ] No OS time used — `sc_time` and `sc_time_stamp()` exclusively
- [ ] No global mutable state accessible across modules
- [ ] Module constructors do not call kernel functions or `wait()`
- [ ] All ports, signals, and submodules declared as member variables
- [ ] Unbound ports: verified all ports bound before `sc_start()`
- [ ] `start_of_simulation()` / `end_of_simulation()` used for file/trace setup
- [ ] No `std::cout` or `printf` — `SC_REPORT_*` used exclusively

---

## 3. TLM Checklist

- [ ] `b_transport` uses `delay +=` (not `delay =`) — cumulative annotation
- [ ] `b_transport` adds base latency, bandwidth latency, and arbitration latency
- [ ] All seven payload fields set before every `b_transport` call
- [ ] Response status reset to `TLM_INCOMPLETE_RESPONSE` before each call
- [ ] Response status set to `TLM_OK_RESPONSE` or error code before return
- [ ] Initiator checks response status after every `b_transport` call
- [ ] Payload data pointer valid for entire duration of transport call
- [ ] Target does not store `data_ptr` beyond transport call scope
- [ ] No `new` / `delete` inside `b_transport`
- [ ] No `throw` anywhere in TLM stack — error via `TLM_GENERIC_ERROR_RESPONSE`
- [ ] No `wait()` inside `nb_transport_fw` or `nb_transport_bw`
- [ ] All four TLM phases handled in `nb_transport` switch with `default` error case
- [ ] Only standard phases used (`BEGIN/END_REQ/RESP`) — no custom phases
- [ ] Address decoding in router, not in leaf target
- [ ] All latency values are named `sc_time` constants

---

## 4. VP Performance Modelling Checklist

- [ ] Latency decomposed: arbitration + queueing + access + bandwidth contributions separate
- [ ] Bandwidth latency derived from `data_length / bw_bytes_per_ns` — not a fixed constant
- [ ] Bus width declared as a named `constexpr` constant
- [ ] Every shared resource has an explicit arbiter model
- [ ] Arbitration latency added before resource access latency
- [ ] Every queue has a declared hardware-depth bound constant
- [ ] Queue overflow triggers `SC_REPORT_FATAL` — not silent drop
- [ ] Backpressure propagates upstream via stall signal
- [ ] Cache hierarchy levels have distinct latency constants
- [ ] DRAM latency decomposed: RAS + CAS + bandwidth (not a single magic number)
- [ ] NoC routing uses explicit hop count from routing table
- [ ] Performance counters collected: transactions, total latency, peak latency
- [ ] Hit rate tracked for cache models
- [ ] Bus utilisation tracked
- [ ] Stats reported only in `end_of_simulation()` — not mid-simulation
- [ ] Initiator calls `wait(delay)` after every `b_transport` call

---

## 5. Memory Safety Checklist

- [ ] No `new`/`delete` in `SC_METHOD` or `b_transport`
- [ ] Pools pre-allocated in constructor and bounded by hardware constant
- [ ] Pool overflow triggers `SC_REPORT_FATAL`
- [ ] No dangling references returned from any function
- [ ] No references to locals stored across `wait()` boundaries
- [ ] Smart pointers used for all heap ownership
- [ ] `std::array<T,N>` used for fixed-size hardware structures
- [ ] `std::vector::reserve()` called in constructor for variable-size structures
- [ ] No `resize()` during simulation
- [ ] TLM payload data buffer is stack or pre-allocated member storage
- [ ] Target does not store payload `data_ptr` beyond transport call
- [ ] AddressSanitizer / LeakSanitizer enabled in CI pipeline

---

## 6. AI‑Testability Checklist

- [ ] Module implements `dump_state()` — `const`, side-effect free, `key=value` format
- [ ] Module implements `dump_stats()` — transactions, latency, hit rate, utilisation
- [ ] Module implements `dump_config()` — all construction-time parameters visible
- [ ] Module implements `reset()` — restores exact power-on-reset state
- [ ] All parameters injectable at construction time
- [ ] Typed `apply_stimulus()` method present
- [ ] `Stimulus` struct is serialisable and deserialisable
- [ ] No `static` local variables in process callbacks
- [ ] No `rand()`, `random_device`, OS time, or wall clock
- [ ] No `std::unordered_map` or `std::unordered_set` in observable state
- [ ] FP rounding mode fixed in `before_end_of_elaboration()`
- [ ] Log format is `key=value`, fixed field order
- [ ] FSM transitions log old state, trigger, and new state
- [ ] Verbose logging guarded by `#ifdef AI_VERBOSE_LOG`
- [ ] Golden reference model exists for the module
- [ ] `reset_stats()` available independently of `reset()`

---

## 7. Class Design Checklist

- [ ] Class has a single documented responsibility (one-line header comment)
- [ ] All data members are `private`
- [ ] All read methods are `const`
- [ ] Configuration/metadata members are `const` after construction
- [ ] Single-argument constructors are `explicit`
- [ ] All members initialised via member initialiser list
- [ ] All six special member functions defined or deleted
- [ ] Collaborators injected through constructor — no hardcoded dependencies
- [ ] `dump_state()`, `dump_stats()`, `dump_config()` implemented
- [ ] No global mutable singletons
- [ ] Composition used over deep inheritance

---

## 8. Operator Overloading Checklist

- [ ] `operator<<` returns `std::ostream&` by reference
- [ ] `operator<<` is side-effect free on serialised object
- [ ] `operator<<` uses `key=value` format
- [ ] `operator==` and `operator!=` defined together
- [ ] All `sc_signal<T>` payloads define `operator==` and `operator<<`
- [ ] All conversion operators are `explicit`
- [ ] `operator[]` bounds-checks in debug builds
- [ ] No overloading of `&&`, `||`, `,`
- [ ] No allocation or I/O inside any operator

---

## 9. DSA Hardware Patterns Checklist

- [ ] Structure uses hardware name, not algorithm name
- [ ] Depth/capacity is a named `constexpr` constant
- [ ] Overflow triggers `SC_REPORT_FATAL`
- [ ] No `std::unordered_map` or `std::unordered_set`
- [ ] Lookup/query functions are `const` and pure
- [ ] FSM states are `enum class` — not raw integers
- [ ] All four FSM transitions handled with `default` error case

---

## 10. Merge Criteria

A PR MUST satisfy **all** of the following before merge:

| Criterion | Required |
|---|---|
| All relevant checklists pass (no ❌ items) | ✅ mandatory |
| CI green: unit tests, static analysis, sanitizers | ✅ mandatory |
| Peer review: at least one approver (not the author) | ✅ mandatory |
| Design doc or diagram updated if structure changed | ✅ mandatory |
| `dump_state()` output verified unchanged for existing golden tests | ✅ if AI tests exist |
| `SKILLS/README.md` index updated if new skill file added | ✅ if applicable |

---

## 11. Quick Reference — Rule Numbers

| Rule | File | Key rule |
|---|---|---|
| C‑01 to C‑42 | `02_C++_Rules.md` | C++ language rules |
| SC‑01 to SC‑53 | `03_SystemC_Rules.md` | SystemC process and module rules |
| TLM‑01 to TLM‑43 | `04_TLM2_Patterns.md` | TLM payload, timing, and protocol rules |
| VP‑01 to VP‑54 | `05_VP_Performance_Modelling.md` | Latency, bandwidth, queueing, cache rules |
| DSA‑01 to DSA‑05 | `06_DSA_Hardware_Patterns.md` | Hardware-aligned DSA rules |
| AI‑01 to AI‑53 | `07_AI_Testing_Hooks.md` | AI testability, logging, golden reference |
| DIAG‑01 to DIAG‑10 | `08_Hardware_Diagrams.md` | Diagram drawing and mapping rules |
| CD‑01 to CD‑47 | `09_Class_Design.md` | Class design, RAII, interface rules |
| M‑01 to M‑31 | `10_Memory_Safety.md` | Memory ownership, pool, lifetime rules |
| O‑01 to O‑24 | `11_Operator_Overloading.md` | Operator rules |
