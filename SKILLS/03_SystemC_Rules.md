# SystemC Engineering Rules for Deterministic Hardware Modelling

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for <5‑Year Engineers  
**Prerequisite:** Read `01_Core_Philosophy.md` and `02_C++_Rules.md` first

---

## Table of Contents

1. [Philosophy Recap](#1-philosophy-recap)
2. [Module Rules](#2-module-rules)
3. [Process Rules — SC_METHOD](#3-process-rules--sc_method)
4. [Process Rules — SC_THREAD](#4-process-rules--sc_thread)
5. [Signal & Port Rules](#5-signal--port-rules)
6. [Sensitivity List Rules](#6-sensitivity-list-rules)
7. [Clock Rules](#7-clock-rules)
8. [Time Rules](#8-time-rules)
9. [Inter‑Module Communication Rules](#9-intermodule-communication-rules)
10. [Hierarchy & Binding Rules](#10-hierarchy--binding-rules)
11. [Simulation Phase Rules](#11-simulation-phase-rules)
12. [Memory & Allocation Rules](#12-memory--allocation-rules)
13. [Logging & Reporting Rules](#13-logging--reporting-rules)
14. [Error & Assertion Rules](#14-error--assertion-rules)
15. [Determinism Rules](#15-determinism-rules)
16. [AI‑Testability Rules for SystemC](#16-aitestability-rules-for-systemc)
17. [Anti‑Patterns](#17-anti-patterns)
18. [Complete Module Example — Pipeline Stage](#18-complete-module-example--pipeline-stage)
19. [Complete Module Example — Arbiter](#19-complete-module-example--arbiter)
20. [Diagram Conventions](#20-diagram-conventions)
21. [Checklist](#21-checklist)
22. [Glossary](#22-glossary)

---

## 1. Philosophy Recap

SystemC is **not** general‑purpose C++ threading. It is a **discrete‑event
simulation kernel** with cooperative coroutines.

```
Key axioms
──────────
① The SystemC kernel is single‑threaded.
② SC_METHOD runs to completion — never blocks.
③ SC_THREAD suspends only at wait() — never at OS primitives.
④ Simulation time advances only at wait() or end of delta cycle.
⑤ Determinism requires static sensitivity lists.
⑥ Shared mutable state across processes → race conditions.
```

Violating any axiom produces **non‑deterministic or undefined simulation
behaviour** — bugs that are impossible to reproduce reliably.

---

## 2. Module Rules

### Rule SC‑01 — Every module MUST inherit from `sc_module`

```cpp
// ✅ Correct
SC_MODULE(FetchStage) {
    // ...
};

// ✅ Also correct (explicit base)
class FetchStage : public sc_module {
public:
    SC_CTOR(FetchStage);
    // ...
};
```

### Rule SC‑02 — Use `SC_CTOR` or named constructor — never both

```cpp
// ✅ SC_CTOR macro (preferred for simple modules)
SC_MODULE(Counter) {
    SC_CTOR(Counter) {
        SC_METHOD(on_clock);
        sensitive << clk.pos();
    }
};

// ✅ Named constructor (required when constructor takes extra arguments)
class Cache : public sc_module {
public:
    SC_HAS_PROCESS(Cache);
    Cache(sc_module_name name, uint32_t capacity)
        : sc_module(name), capacity_(capacity) {
        SC_METHOD(on_access);
        sensitive << req_valid.pos();
    }
private:
    uint32_t capacity_;
};
```

### Rule SC‑03 — Module names MUST be unique within the simulation

```cpp
// ✅ Use string suffix for arrays
for (int i = 0; i < 4; ++i) {
    std::string n = "core_" + std::to_string(i);
    cores_[i] = std::make_unique<Core>(n.c_str(), /*params*/);
}
```

### Rule SC‑04 — All ports, signals, and submodules MUST be declared as member variables

Never allocate ports or signals on the heap dynamically during simulation.

```cpp
SC_MODULE(FetchStage) {
    // ✅ Declared as members — lifetime = module lifetime
    sc_in<bool>       clk;
    sc_in<uint64_t>   pc_in;
    sc_out<uint64_t>  pc_out;
    sc_signal<bool>   stall_internal;
    // ...
};
```

### Rule SC‑05 — No business logic in the module constructor

Constructors register processes and bind internal signals only. All
simulation logic belongs in process callbacks.

```cpp
// ✅ Constructor — registration only
SC_CTOR(FetchStage) {
    SC_METHOD(compute_next_pc);
    sensitive << pc_in << stall;

    SC_THREAD(fetch_loop);
    sensitive << clk.pos();
}

// ❌ Forbidden — simulation logic in constructor
SC_CTOR(FetchStage) {
    pc_cache.fetch(reset_vector);   // forbidden
}
```

---

## 3. Process Rules — SC_METHOD

`SC_METHOD` models **combinational logic** — it fires when inputs change and
must return immediately.

### Rule SC‑06 — SC_METHOD MUST NOT call `wait()`

Calling `wait()` inside `SC_METHOD` is a **runtime error** (`sc_error`).
It also conceptually violates the combinational model.

### Rule SC‑07 — SC_METHOD MUST NOT allocate or free heap memory

```cpp
// ❌ Forbidden inside SC_METHOD
void on_req() {
    auto* p = new Packet();   // non-deterministic allocator timing
    // ...
}
```

### Rule SC‑08 — SC_METHOD MUST NOT perform I/O

No `std::cout`, no `printf`, no file writes inside `SC_METHOD`.  
Use `SC_REPORT_INFO` with a conditional debug guard (see Rule SC‑22).

### Rule SC‑09 — SC_METHOD body MUST complete in O(1) or O(k) with small, bounded k

The method fires every delta cycle it is sensitive to. Unbounded loops
inside `SC_METHOD` stall the entire simulation.

```cpp
// ✅ Bounded loop — pipeline depth is a compile-time constant
void propagate() {
    for (std::size_t i = 0; i < PIPE_DEPTH; ++i) {
        stages_[i].propagate();
    }
}

// ❌ Forbidden — unbounded iteration
void drain_queue() {
    while (!q_.empty()) { ... }   // may run forever in delta
}
```

### Rule SC‑10 — SC_METHOD MUST write outputs only at the end

Write all outputs after all computation is complete. Never write then read
the same signal within one `SC_METHOD` invocation — the read will return
the **old** value (delta cycle semantics).

```cpp
// ✅ Correct — compute first, write last
void on_clock() {
    const bool hit  = lookup(addr_in.read());
    const bool miss = !hit;
    hit_out.write(hit);
    miss_out.write(miss);
}
```

---

## 4. Process Rules — SC_THREAD

`SC_THREAD` models **sequential hardware behaviour** — multi‑cycle
protocols, handshakes, FSMs that advance over time.

### Rule SC‑11 — SC_THREAD MUST use `wait()` to advance simulation time

```cpp
void fetch_loop() {
    while (true) {
        wait();                         // ✅ wait for clock edge
        if (stall.read()) { continue; }
        issue_fetch(pc_.read());
        wait(FETCH_LATENCY);            // ✅ advance by latency
    }
}
```

### Rule SC‑12 — SC_THREAD MUST NOT use OS blocking primitives

| Forbidden | Reason | Allowed alternative |
|---|---|---|
| `std::this_thread::sleep_for` | Bypasses simulation time | `wait(sc_time(...))` |
| `std::mutex::lock` | OS primitive — deadlocks kernel | `sc_mutex` |
| `std::condition_variable::wait` | OS blocking | `sc_event::wait()` |
| `std::future::get` | OS blocking | Model explicitly with events |

### Rule SC‑13 — SC_THREAD MUST have an infinite loop or a defined exit condition

```cpp
// ✅ Infinite loop — normal for clocked processes
void decode_loop() {
    while (true) {
        wait(clk.posedge_event());
        // ...
    }
}

// ✅ Finite with explicit termination
void init_sequence() {
    wait(RESET_DURATION);
    reset_done.write(true);
    // thread exits — do not call wait() after final work
}
```

### Rule SC‑14 — SC_THREAD MUST NOT share mutable state with SC_METHOD without explicit synchronisation

Use `sc_signal` or `sc_fifo` as the shared medium — never raw C++ member
variables read by one process and written by another.

```cpp
// ✅ Shared via sc_signal — safe, delta-cycle accurate
sc_signal<uint32_t> rob_head_;   // written by commit thread, read by issue method
```

---

## 5. Signal & Port Rules

### Rule SC‑15 — Prefer `sc_signal` for intra‑module communication

`sc_signal<T>` provides delta‑cycle update semantics and is readable by
multiple processes safely.

### Rule SC‑16 — Prefer `sc_in` / `sc_out` for inter‑module communication

Never connect two modules via raw C++ references or pointers.

### Rule SC‑17 — Use `sc_in<bool>` for single‑bit control signals, not `sc_in<int>`

```cpp
sc_in<bool>     valid;    // ✅
sc_in<int>      valid;    // ❌ — semantics unclear, wastes width
```

### Rule SC‑18 — Signal types MUST be fixed‑width integers or structs, not `double` or `float`

```cpp
sc_signal<uint64_t>   addr;     // ✅
sc_signal<double>     latency;  // ❌ — floating-point nondeterminism
```

### Rule SC‑19 — Struct payloads on signals MUST define `operator==`

SystemC calls `operator==` to detect changes. Without it, every delta
cycle fires a spurious update.

```cpp
struct Packet {
    uint64_t addr  = 0;
    uint32_t size  = 0;
    bool     valid = false;

    bool operator==(const Packet& o) const {
        return addr == o.addr && size == o.size && valid == o.valid;
    }
};
```

### Rule SC‑20 — Struct payloads on signals MUST define `operator<<` for tracing

```cpp
inline std::ostream& operator<<(std::ostream& os, const Packet& p) {
    return os << "Packet{addr=0x" << std::hex << p.addr
              << " size=" << std::dec << p.size
              << " valid=" << p.valid << "}";
}
```

---

## 6. Sensitivity List Rules

### Rule SC‑21 — Sensitivity lists MUST be static

Declare all sensitivities in the constructor. Never modify sensitivity at
runtime.

```cpp
// ✅ Static — declared once in constructor
SC_METHOD(on_req);
sensitive << req_valid << req_addr;

// ❌ Forbidden — dynamic modification
void on_req() {
    sensitive << new_signal;   // runtime modification — undefined
}
```

### Rule SC‑22 — Edge‑sensitive vs level‑sensitive MUST match hardware intent

| Hardware | Correct sensitivity |
|---|---|
| Clocked flip‑flop | `clk.pos()` — positive edge |
| Asynchronous reset | `rst_n.neg()` — negative edge |
| Combinational gate | `sensitive << a << b` — level (any change) |
| Protocol handshake | `valid.pos()` or `valid.negedge_event()` |

---

## 7. Clock Rules

### Rule SC‑23 — Use a single master clock per clock domain

```cpp
sc_clock clk("clk", sc_time(1, SC_NS));   // ✅ one master clock
```

Never instantiate multiple `sc_clock` objects for the same domain.

### Rule SC‑24 — Clock period MUST be a named constant

```cpp
// ✅
constexpr sc_time CLK_PERIOD(1, SC_NS);
sc_clock clk("clk", CLK_PERIOD);

// ❌
sc_clock clk("clk", sc_time(1, SC_NS));   // magic number — not named
```

### Rule SC‑25 — Clock domain crossings MUST use an explicit CDC model

Never pass a signal directly between two `sc_clock` domains. Use a modelled
synchroniser FIFO with the appropriate latency.

```
Clock A domain             CDC FIFO (2-cycle sync)          Clock B domain
─────────────              ───────────────────────           ─────────────
producer_thread ──────────▶  sync_in ──▶ sync_out ─────────▶ consumer_thread
                              clkA           clkB
```

---

## 8. Time Rules

### Rule SC‑26 — Use `sc_time` for all durations — never raw integers

```cpp
wait(sc_time(10, SC_NS));    // ✅
wait(10);                    // ❌ — 10 what? undefined unit
```

### Rule SC‑27 — All latency constants MUST be named `sc_time` constants

```cpp
// ✅ Named constants — documentation + reuse
constexpr sc_time CACHE_HIT_LATENCY (4,  SC_NS);
constexpr sc_time CACHE_MISS_LATENCY(80, SC_NS);
constexpr sc_time BUS_ARB_LATENCY   (2,  SC_NS);
```

### Rule SC‑28 — Never compare `sc_time` values with `==` on floating‑point backed values

Use `>=` and tolerance bands, or keep all times in integer multiples of the
clock period.

---

## 9. Inter‑Module Communication Rules

### Rule SC‑29 — Use `sc_fifo` for buffered producer‑consumer communication

```cpp
sc_fifo<Packet> fetch_to_decode{"ftd_fifo", /*depth=*/4};
```

`sc_fifo` provides built‑in blocking `read()`/`write()` with correct
simulation semantics.

### Rule SC‑30 — Use `sc_signal` for single‑cycle combinational connections

```cpp
sc_signal<uint64_t> pc_wire{"pc_wire"};
fetch.pc_out(pc_wire);
decode.pc_in(pc_wire);
```

### Rule SC‑31 — Use TLM sockets for transaction‑level communication

For any transfer that carries address, data, and control information as a
unit, use TLM‑2.0 sockets. Do not model memory‑mapped communication with
raw `sc_signal<>` buses.

### Rule SC‑32 — Never pass pointers between modules

Pass values or use TLM payloads with defined ownership semantics.

---

## 10. Hierarchy & Binding Rules

### Rule SC‑33 — All port bindings MUST occur in the parent module constructor

```cpp
SC_MODULE(Cpu) {
    FetchStage   fetch_{"fetch"};
    DecodeStage  decode_{"decode"};
    sc_signal<uint64_t> fetch_to_decode_{"f2d"};

    SC_CTOR(Cpu) {
        // ✅ All bindings in constructor
        fetch_.pc_out(fetch_to_decode_);
        decode_.pc_in(fetch_to_decode_);
    }
};
```

### Rule SC‑34 — No unbound ports at `sc_start`

Unbound ports cause a fatal simulation error. Always verify binding
completeness in a topology unit test before integrating.

---

## 11. Simulation Phase Rules

SystemC defines strict simulation phases. Code MUST respect phase
boundaries.

```
Elaboration phase   →  sc_start() not yet called
                        Module construction, port binding, process registration

Initialisation      →  sc_start(0) — all methods fire once before time=0

Simulation          →  Normal event-driven execution

End of simulation   →  sc_stop() called — end_of_simulation() callbacks
```

### Rule SC‑35 — Do not call `sc_start` before all modules are constructed

### Rule SC‑36 — Perform file open / close and trace setup in `start_of_simulation` / `end_of_simulation`

```cpp
void start_of_simulation() override {
    trace_file_ = sc_create_vcd_trace_file("trace");
    sc_trace(trace_file_, clk, "clk");
}

void end_of_simulation() override {
    sc_close_vcd_trace_file(trace_file_);
}
```

### Rule SC‑37 — Do not read port values during elaboration

Ports are not driven until simulation starts. Reading a port in the
constructor is undefined.

---

## 12. Memory & Allocation Rules

### Rule SC‑38 — No `new` / `delete` inside process callbacks

All storage used by processes must be allocated during construction and
freed in the destructor.

```cpp
// ✅ Allocate in constructor, access in process
SC_MODULE(Rob) {
    std::array<RobEntry, ROB_SIZE> entries_{};   // stack array — no heap

    SC_CTOR(Rob) {
        SC_THREAD(commit_loop);
        sensitive << clk.pos();
    }

    void commit_loop() {
        while (true) {
            wait();
            // use entries_ — no allocation
        }
    }
};
```

### Rule SC‑39 — Use `std::array` for fixed‑size hardware structures

`std::array<T, N>` has zero overhead, O(1) access, and expresses the
hardware bound in the type system.

### Rule SC‑40 — Use `std::vector` with `reserve()` for variable‑size structures, never resize during simulation

```cpp
SC_CTOR(Lsq) {
    entries_.reserve(LSQ_SIZE);   // ✅ pre-allocate in constructor
}

void on_clock() {
    entries_.push_back(e);        // ✅ only if entries_.size() < LSQ_SIZE
    // ❌ entries_.resize(...) inside process — forbidden
}
```

---

## 13. Logging & Reporting Rules

### Rule SC‑41 — Use `SC_REPORT_INFO` / `SC_REPORT_WARNING` / `SC_REPORT_ERROR` / `SC_REPORT_FATAL`

These macros attach simulation time, module name, and severity to every
message — making logs reproducible and searchable.

```cpp
// ✅ Correct
SC_REPORT_INFO(name(), "fetch stall detected");

// ❌ Forbidden
std::cout << "fetch stall\n";
```

### Rule SC‑42 — Log messages MUST include simulation time and module context

`SC_REPORT_*` macros supply time automatically. For custom messages, prefix
with `sc_time_stamp()`:

```cpp
std::ostringstream oss;
oss << "[" << sc_time_stamp() << "] " << name()
    << " pc=0x" << std::hex << pc;
SC_REPORT_INFO(name(), oss.str().c_str());
```

### Rule SC‑43 — Wrap verbose logging in `SC_DEBUG` compile guards

```cpp
#ifdef SC_DEBUG
SC_REPORT_INFO(name(), oss.str().c_str());
#endif
```

This ensures logging does not perturb timing in production simulation.

### Rule SC‑44 — Never log inside `SC_METHOD` hot paths in production builds

`SC_METHOD` fires every delta cycle it is sensitive to. Logging on every
firing inflates trace files and distorts performance measurements.

---

## 14. Error & Assertion Rules

### Rule SC‑45 — Use `SC_REPORT_FATAL` for unrecoverable model errors

```cpp
if (addr > MAX_ADDR) {
    SC_REPORT_FATAL(name(), "address out of range");
}
```

`SC_REPORT_FATAL` terminates simulation immediately with a clear message.

### Rule SC‑46 — Use `sc_assert` for model invariants

```cpp
sc_assert(rob_head_ < ROB_SIZE);
```

### Rule SC‑47 — No `assert()` from `<cassert>` — use `sc_assert`

`assert()` calls `abort()` without a SystemC stack unwind. `sc_assert`
integrates with the simulation error handler.

---

## 15. Determinism Rules

### Rule SC‑48 — Avoid delta‑cycle races

A delta‑cycle race occurs when two processes in the same delta cycle both
read and write the same signal. Resolve by:
1. Restructuring the pipeline so one process owns writes
2. Introducing an explicit `sc_signal` intermediate

### Rule SC‑49 — Iteration order over containers MUST be deterministic

```cpp
// ✅ std::map — sorted iteration
std::map<uint32_t, Module*> modules_;

// ❌ std::unordered_map — hash-dependent order
std::unordered_map<uint32_t, Module*> modules_;
```

### Rule SC‑50 — No `sc_clock` jitter in simulation unless explicitly modelling jitter

```cpp
// ❌ Forbidden unless testing CDC
sc_clock clk("clk", 1.0, 0.5, 0.0, true);   // jitter parameters
```

---

## 16. AI‑Testability Rules for SystemC

### Rule SC‑51 — Every module MUST expose a `dump_state()` method

```cpp
std::string dump_state() const {
    std::ostringstream oss;
    oss << "FetchStage{"
        << " pc=0x"  << std::hex << pc_reg_
        << " stall=" << std::dec << stall_
        << " busy="  << busy_
        << "}";
    return oss.str();
}
```

AI test harnesses call `dump_state()` to compare expected vs actual state.

### Rule SC‑52 — Every module MUST expose `reset()` and `apply_stimulus(const Stimulus&)`

This allows an AI agent to reset the model to a known state and inject
typed stimulus without coupling to simulation infrastructure.

### Rule SC‑53 — All module parameters MUST be injectable at construction time

```cpp
// ✅ Parameterised — AI can sweep configurations
Cache(sc_module_name name, uint32_t sets, uint32_t ways, uint32_t line_bytes);
```

---

## 17. Anti‑Patterns

| Anti‑Pattern | Consequence | Fix |
|---|---|---|
| `wait()` inside `SC_METHOD` | Runtime `sc_error` | Move to `SC_THREAD` |
| `new` inside process callback | Non‑deterministic timing | Pre‑allocate in constructor |
| `std::cout` in process | Unordered output, no timestamp | `SC_REPORT_INFO` |
| Raw pointer between modules | Dangling on destruction | `sc_signal` or TLM socket |
| OS `sleep()` in `SC_THREAD` | Bypasses simulation time | `wait(sc_time(...))` |
| `std::mutex` in process | OS deadlock with kernel | `sc_mutex` |
| Missing `operator==` on signal struct | Spurious delta firings | Implement `operator==` |
| Dynamic sensitivity list | Undefined simulation order | Static sensitivity only |
| Reading port in constructor | Undriven port → garbage | Read only inside processes |
| `sc_clock` with jitter (unintentional) | Non‑deterministic edge timing | Remove jitter parameters |
| Unbound port at `sc_start` | Fatal simulation error | Bind in parent constructor |
| `abort()` / `exit()` in model | No SystemC stack unwind | `SC_REPORT_FATAL` |
| Shared mutable C++ member across processes | Delta‑cycle race | `sc_signal` intermediary |

---

## 18. Complete Module Example — Pipeline Stage

This example implements a **single‑cycle pipeline register** between Fetch
and Decode. It demonstrates all rules above.

```cpp
// fetch_decode_reg.h
#pragma once
#include <systemc>
#include <cstdint>
#include <sstream>
#include "packet.h"   // defines Packet with operator== and operator<<

SC_MODULE(FetchDecodeReg) {
    // ── Ports ──────────────────────────────────────────────────
    sc_in<bool>    clk;
    sc_in<bool>    rst_n;
    sc_in<bool>    stall;      // pipeline stall signal
    sc_in<Packet>  d;          // data input (from Fetch)
    sc_out<Packet> q;          // data output (to Decode)

    // ── Constructor ────────────────────────────────────────────
    SC_CTOR(FetchDecodeReg) {
        SC_METHOD(on_clock);
        sensitive << clk.pos() << rst_n.neg();
        dont_initialize();
    }

    // ── AI‑testability ─────────────────────────────────────────
    std::string dump_state() const {
        std::ostringstream oss;
        oss << "FetchDecodeReg{q=" << q.read() << "}";
        return oss.str();
    }

private:
    void on_clock() {
        if (!rst_n.read()) {
            q.write(Packet{});           // synchronous reset
            return;
        }
        if (!stall.read()) {
            q.write(d.read());           // advance stage
        }
        // stall: hold q unchanged
    }
};
```

---

## 19. Complete Module Example — Round‑Robin Arbiter

```cpp
// rr_arbiter.h
#pragma once
#include <systemc>
#include <array>
#include <cstdint>
#include <sstream>

constexpr std::size_t N_REQ = 4;

SC_MODULE(RRArbiter) {
    // ── Ports ──────────────────────────────────────────────────
    sc_in<bool>                      clk;
    sc_in<bool>                      rst_n;
    sc_in<std::array<bool, N_REQ>>   req;   // request vector
    sc_out<int32_t>                  grant; // -1 = no grant, 0..N-1 = winner

    SC_CTOR(RRArbiter) {
        SC_METHOD(arbitrate);
        sensitive << clk.pos() << rst_n.neg();
        dont_initialize();
    }

    std::string dump_state() const {
        std::ostringstream oss;
        oss << "RRArbiter{last_grant=" << last_grant_ << "}";
        return oss.str();
    }

private:
    int32_t last_grant_ = -1;

    void arbitrate() {
        if (!rst_n.read()) {
            last_grant_ = -1;
            grant.write(-1);
            return;
        }
        const auto& r = req.read();
        // Round-robin: start search after last grant
        const int32_t start = (last_grant_ + 1) % static_cast<int32_t>(N_REQ);
        for (int32_t i = 0; i < static_cast<int32_t>(N_REQ); ++i) {
            const int32_t idx = (start + i) % static_cast<int32_t>(N_REQ);
            if (r[static_cast<std::size_t>(idx)]) {
                last_grant_ = idx;
                grant.write(idx);
                return;
            }
        }
        grant.write(-1);   // no requests
    }
};
```

---

## 20. Diagram Conventions

### 20.1 Pipeline stage diagram (ASCII)

```
         ┌───────────┐   sc_signal<Packet>   ┌────────────┐
  clk ──▶│  Fetch    │──────────────────────▶│  Decode    │
rst_n ──▶│  Stage    │  FetchDecodeReg        │  Stage     │
stall ──▶│           │◀─────────────────────▶│            │
         └───────────┘                        └────────────┘
```

### 20.2 Producer‑consumer with sc_fifo

```
  Producer                   sc_fifo<T>               Consumer
  SC_THREAD                  depth = D                SC_THREAD
  ──────────                 ──────────               ──────────
  write(pkt) ──────────────▶ [  |  |  |  ] ─────────▶ read(pkt)
              blocks if full                blocks if empty
```

### 20.3 TLM initiator‑target

```
  Initiator                  TLM Socket                 Target
  ──────────                 ──────────                 ──────
  b_transport(txn) ─────────────────────────────────▶  b_transport(txn)
                   ◀─────────────────────────────────  response_status set
```

---

## 21. Checklist

Use this checklist in every code review for SystemC modules.

### Module structure
- [ ] Inherits from `sc_module`
- [ ] Uses `SC_CTOR` or `SC_HAS_PROCESS` correctly
- [ ] All ports / signals declared as member variables
- [ ] No simulation logic in constructor

### SC_METHOD
- [ ] Does not call `wait()`
- [ ] Does not allocate heap memory
- [ ] Does not perform I/O (except `SC_REPORT` under debug guard)
- [ ] Body is O(1) or O(small constant)
- [ ] Writes outputs only after all computation

### SC_THREAD
- [ ] Uses `wait()` to advance time
- [ ] Does not use OS blocking primitives
- [ ] Has infinite loop or defined exit
- [ ] Shared state only via `sc_signal` / `sc_fifo`

### Signals & ports
- [ ] Fixed‑width integer types only
- [ ] Struct types define `operator==` and `operator<<`
- [ ] Sensitivity lists are static
- [ ] Edge sensitivity matches hardware intent

### Time & clocks
- [ ] All durations use `sc_time`
- [ ] Latency constants are named
- [ ] CDC crossings use explicit synchroniser model

### Memory
- [ ] No `new` / `delete` inside processes
- [ ] Fixed‑size structures use `std::array<T, N>`
- [ ] Variable‑size structures `reserve()` in constructor

### Logging
- [ ] `SC_REPORT_*` used exclusively
- [ ] Verbose logging under `#ifdef SC_DEBUG`
- [ ] No logging in `SC_METHOD` hot path

### Determinism
- [ ] No delta‑cycle races
- [ ] Container iteration is deterministic (`std::map`, not `std::unordered_map`)
- [ ] No unintentional clock jitter

### AI‑testability
- [ ] `dump_state()` method present
- [ ] Parameters injectable at construction
- [ ] No hidden state

---

## 22. Glossary

| Term | Definition |
|---|---|
| **SC_MODULE** | SystemC macro declaring a simulation module |
| **SC_METHOD** | Combinational process — fires on sensitivity, runs to completion |
| **SC_THREAD** | Sequential process — suspends at `wait()` |
| **sc_signal** | Typed wire with delta‑cycle update semantics |
| **sc_fifo** | Bounded FIFO channel with blocking read/write |
| **sc_clock** | Clock source generating posedge / negedge events |
| **sc_time** | Simulation time type — value + unit |
| **sc_event** | Notification primitive used by `wait()` |
| **delta cycle** | Zero‑time evaluation step within one simulation instant |
| **sensitivity list** | Set of signals/events that trigger a process |
| **elaboration** | Phase before `sc_start()` — module construction and binding |
| **CDC** | Clock Domain Crossing — signal crossing between two clock domains |
| **TLM** | Transaction Level Modelling — abstract bus protocol |
| **b_transport** | TLM blocking transport call |
| **UB** | Undefined Behaviour |
| **RAII** | Resource Acquisition Is Initialization |
