# Anti‑Patterns in Hardware Modelling, SystemC, TLM & VP Code

**Version:** 1.0 — July 2026  
**Standard:** Mandatory — These patterns are forbidden in all production simulation code

---

## Table of Contents

1. [C++ Anti‑Patterns](#1-c-anti-patterns)
2. [SystemC Anti‑Patterns](#2-systemc-anti-patterns)
3. [TLM Anti‑Patterns](#3-tlm-anti-patterns)
4. [VP Performance Modelling Anti‑Patterns](#4-vp-performance-modelling-anti-patterns)
5. [Memory Safety Anti‑Patterns](#5-memory-safety-anti-patterns)
6. [AI‑Testability Anti‑Patterns](#6-aitestability-anti-patterns)
7. [DSA Anti‑Patterns](#7-dsa-anti-patterns)
8. [Operator Overloading Anti‑Patterns](#8-operator-overloading-anti-patterns)
9. [Summary Table](#9-summary-table)
10. [Glossary](#10-glossary)

---

## 1. C++ Anti‑Patterns

### AP‑C01 — Hidden Global State

**Description:** Global mutable variables used across modules without explicit ownership.

```cpp
// ❌ Forbidden
int g_transaction_count = 0;   // modified by multiple modules
```

**Why bad:** Breaks determinism. Tests become order-dependent. State is non-resettable.  
**Fix:** Encapsulate state in the owning module as a member variable with `reset()`.

---

### AP‑C02 — Implicit Conversions

**Description:** Non-explicit single-argument constructors allow silent construction.

```cpp
// ❌ Forbidden
Packet p = 10;   // implicit construction from int — silent
```

**Why bad:** Silent precision loss, unexpected construction, hard to detect in code review.  
**Fix:** `explicit Packet(uint32_t size);`

---

### AP‑C03 — Returning References to Locals

**Description:** Returning a reference or pointer to a stack variable.

```cpp
// ❌ UB — dangling reference
const int& get() { int x = 10; return x; }
```

**Why bad:** Undefined behaviour — function returns address of destroyed stack frame.  
**Fix:** Return by value, or use a member variable / `unique_ptr`.

---

### AP‑C04 — Using `using namespace std;` in Headers

**Description:** Namespace pollution that affects all consumers of the header.

```cpp
// ❌ Forbidden in headers
using namespace std;
```

**Why bad:** All files that include this header inherit the namespace, causing name collisions.  
**Fix:** Always use `std::string`, `std::vector`, etc. explicitly.

---

### AP‑C05 — Magic Number Literals

**Description:** Numeric literals with no named constant.

```cpp
// ❌ Forbidden — what is 192? 35? 14?
delay += sc_time(35 + 14, SC_NS);
if (rob_fill > 192) { ... }
```

**Why bad:** Untraceable to hardware spec. Changes require grep instead of single rename.  
**Fix:** `constexpr sc_time DRAM_LATENCY(49, SC_NS);` and `constexpr uint32_t ROB_DEPTH = 192;`

---

### AP‑C06 — Overuse of Macros

**Description:** Complex multi-line macros replacing functions.

```cpp
// ❌ Forbidden
#define COMPUTE_DELAY(s, b) ((s) / (b))   // hides types, breaks debugger
```

**Why bad:** Macros bypass type-checking, break debuggers, and can't be overloaded.  
**Fix:** `inline constexpr sc_time compute_delay(uint32_t size, double bw) { ... }`

---

### AP‑C07 — Deep Inheritance for Behaviour Reuse

**Description:** Long inheritance chains to share code between hardware models.

```cpp
// ❌ Forbidden
class MemController : public Arbiter, public Scheduler, public BandwidthModel { ... };
```

**Why bad:** Fragile. Base class changes break all derived classes. Diamond inheritance risk.  
**Fix:** Composition — `MemController` *has-a* `Arbiter`, *has-a* `BandwidthModel`.

---

## 2. SystemC Anti‑Patterns

### AP‑SC01 — Blocking Inside SC_METHOD

**Description:** Calling `wait()` inside an `SC_METHOD`.

```cpp
// ❌ Runtime error
SC_METHOD(on_clock);
void on_clock() { wait(1, SC_NS); }   // SC_ERROR at runtime
```

**Why bad:** `SC_METHOD` is a combinational process — it must return immediately.  
**Fix:** Move sequential logic to `SC_THREAD`.

---

### AP‑SC02 — Dynamic Allocation Inside SC_METHOD

```cpp
// ❌ Forbidden
void on_clock() { auto* p = new Packet(); ... delete p; }
```

**Why bad:** Non-deterministic allocator timing. Potential leaks if process re-enters.  
**Fix:** Pre-allocate in constructor; use pool in process.

---

### AP‑SC03 — Logging Inside SC_METHOD Hot Path

```cpp
// ❌ Forbidden in production SC_METHOD
void on_clock() { SC_REPORT_INFO(name(), "clock fired"); }
```

**Why bad:** Fires every delta cycle — inflates logs and perturbs timing measurement.  
**Fix:** Guard with `#ifdef SC_DEBUG`.

---

### AP‑SC04 — OS Sleep Inside SC_THREAD

```cpp
// ❌ Forbidden
void run() { while(true) { std::this_thread::sleep_for(std::chrono::nanoseconds(1)); } }
```

**Why bad:** Bypasses the SystemC simulation kernel. OS sleep ≠ simulation time.  
**Fix:** `wait(sc_time(1, SC_NS));`

---

### AP‑SC05 — Reading Port Values in the Constructor

```cpp
// ❌ UB — port not driven during elaboration
SC_CTOR(Unit) { if (cfg_port.read()) { ... } }   // undriven port → garbage
```

**Why bad:** Ports are only driven after simulation starts.  
**Fix:** Read ports inside process callbacks, not in constructors.

---

### AP‑SC06 — Missing `operator==` on `sc_signal` Payload

**Description:** Struct used as `sc_signal<T>` without `operator==`.

**Why bad:** SystemC calls `operator==` to detect changes. Missing `operator==` → spurious delta firings every cycle, inflating simulation time.  
**Fix:** Always define `operator==` (and `operator<<`) for signal payload structs.

---

### AP‑SC07 — Dynamic Sensitivity Lists

```cpp
// ❌ Forbidden — runtime sensitivity modification
void on_req() { sensitive << new_signal; }
```

**Why bad:** Unpredictable scheduling order; not supported by all SystemC implementations.  
**Fix:** Declare all sensitivities statically in the constructor.

---

## 3. TLM Anti‑Patterns

### AP‑TLM01 — Zero-Latency `b_transport`

```cpp
// ❌ Invalid performance model
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    do_access(pl);
    // delay left at 0 — all latency silently collapsed
}
```

**Why bad:** Produces invalid performance estimates. Every access appears instantaneous.  
**Fix:** Always annotate: `delay += ACCESS_LATENCY + BW_LATENCY;`

---

### AP‑TLM02 — `delay = X` (Overwrite Instead of Accumulate)

```cpp
// ❌ Forbidden — overwrites upstream latency
delay = sc_time(10, SC_NS);
```

**Why bad:** Discards any latency accumulated by the router or initiator.  
**Fix:** `delay += sc_time(10, SC_NS);`

---

### AP‑TLM03 — Heap Allocation Inside `b_transport`

```cpp
// ❌ Forbidden
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    auto* buf = new uint8_t[pl.get_data_length()];
    // ...
    delete[] buf;
}
```

**Why bad:** Non-deterministic allocator timing; leak risk on early return.  
**Fix:** Stack buffer or pre-allocated member array.

---

### AP‑TLM04 — Missing Response Status

```cpp
// ❌ Forbidden — response left as TLM_INCOMPLETE_RESPONSE
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    do_access(pl);
    // forgot pl.set_response_status(TLM_OK_RESPONSE)
}
```

**Why bad:** Initiator receives `TLM_INCOMPLETE_RESPONSE` — silent functional bug.  
**Fix:** Always set response status before returning.

---

### AP‑TLM05 — `throw` Inside Transport

```cpp
// ❌ Forbidden
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    if (addr > MAX_ADDR) throw std::out_of_range("bad addr");
}
```

**Why bad:** Terminates simulation without SystemC cleanup.  
**Fix:** `pl.set_response_status(tlm::TLM_ADDRESS_ERROR_RESPONSE); return;`

---

### AP‑TLM06 — Storing `data_ptr` Beyond Transport Call

```cpp
// ❌ Forbidden
uint8_t* saved_ = nullptr;
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    saved_ = pl.get_data_ptr();   // dangling after return
}
```

**Why bad:** `data_ptr` points to initiator's buffer — invalid after `b_transport` returns.  
**Fix:** `std::memcpy(local_buf_.data(), pl.get_data_ptr(), pl.get_data_length());`

---

## 4. VP Performance Modelling Anti‑Patterns

### AP‑VP01 — Random Delays

```cpp
// ❌ Forbidden
delay += sc_time(rand() % 10, SC_NS);
```

**Why bad:** Non-deterministic simulation. Different runs → different results.  
**Fix:** Fixed, parameter-driven latency constants.

---

### AP‑VP02 — Unbounded Queues

```cpp
// ❌ Forbidden — queue grows forever
while (req_available()) queue_.push_back(pop_req());
```

**Why bad:** Models infinite buffering — hides backpressure and stall behaviour.  
**Fix:** `constexpr std::size_t Q_DEPTH = 32;` and overflow → `SC_REPORT_FATAL`.

---

### AP‑VP03 — All Cache Levels Same Latency

```cpp
// ❌ Forbidden — wrong
delay += CACHE_LATENCY;   // same for L1, L2, L3, DRAM
```

**Why bad:** Hierarchy invisible. All accesses appear identical.  
**Fix:** Distinct `sc_time` constant per cache level.

---

### AP‑VP04 — DRAM as Single Fixed Latency

```cpp
// ❌ Wrong — ignores RAS, row hit/miss, bandwidth
delay += sc_time(80, SC_NS);
```

**Why bad:** Hides DRAM scheduling effects; open-page vs closed-page indistinguishable.  
**Fix:** `delay += DRAM_RAS_LATENCY + DRAM_CAS_LATENCY + BW_LATENCY;`

---

### AP‑VP05 — Stats Reported Mid-Simulation

```cpp
// ❌ Wrong — partial data
SC_METHOD(print_stats);
sensitive << clk.pos();
void print_stats() { SC_REPORT_INFO(name(), dump_stats().c_str()); }
```

**Why bad:** Partial statistics mid-run are misleading and confusing.  
**Fix:** Report only in `end_of_simulation()`.

---

## 5. Memory Safety Anti‑Patterns

### AP‑M01 — `new`/`delete` in Hot Paths

**Already covered in TLM and SystemC sections.** The rule is universal:
no dynamic allocation during simulation.

### AP‑M02 — Unbounded Container Growth

```cpp
// ❌ Forbidden — grows without bound
void on_req() { log_.push_back(req); }   // log_ never cleared
```

**Why bad:** OOM, non-deterministic timing from vector reallocations.  
**Fix:** Bounded ring buffer or log eviction at fixed depth.

### AP‑M03 — Non-Deterministic Initialisation Order of Globals

```cpp
// ❌ Forbidden — init order across TUs is unspecified
// file_a.cpp: int g_a = 10;
// file_b.cpp: int g_b = g_a * 2;   // g_a may not be init yet
```

**Why bad:** C++ does not guarantee init order across translation units.  
**Fix:** Use local static with `[[nodiscard]]` accessor; or initialise in `sc_main` before `sc_start`.

---

## 6. AI‑Testability Anti‑Patterns

### AP‑AI01 — No `dump_state()`

**Why bad:** AI cannot observe module — it is opaque to the test harness.  
**Fix:** Every simulation class implements `dump_state() const`.

### AP‑AI02 — Pointer Values in `dump_state()`

```cpp
// ❌ Forbidden — pointer values differ every run
oss << " buf_ptr=" << reinterpret_cast<uintptr_t>(buf_);
```

**Why bad:** `dump_state()` output differs between runs — snapshot comparison always fails.  
**Fix:** Never include addresses, pointers, or wall time in `dump_state()`.

### AP‑AI03 — Free-Form Log Strings

```cpp
// ❌ AI cannot parse
SC_REPORT_INFO("CACHE", "missed on address 4096 after 12 nanoseconds");
```

**Why bad:** AI regex cannot reliably extract fields.  
**Fix:** `"op=MISS addr=0x1000 lat_ns=12.0"` — `key=value` format.

### AP‑AI04 — Hardcoded Parameters

```cpp
// ❌ Forbidden — AI cannot sweep ROB size
SC_MODULE(Core) { static constexpr uint32_t ROB_DEPTH = 192; };
```

**Why bad:** AI needs to vary parameters to explore architecture space.  
**Fix:** Constructor-injected parameter.

### AP‑AI05 — No `reset()` Method

**Why bad:** Test isolation impossible — previous test's state contaminates next test.  
**Fix:** Explicit `reset()` restoring POR state.

---

## 7. DSA Anti‑Patterns

### AP‑DSA01 — Naming Hardware Structures After DSA Algorithms

```cpp
// ❌ Forbidden — obscures hardware intent
class SlidingWindow { ... };   // what hardware does this model?

// ✅ Correct
class IssueWindow { ... };
class ReorderBuffer { ... };
```

### AP‑DSA02 — Unbounded DSA Container Used for Hardware Structure

```cpp
// ❌ Forbidden — models infinite instruction window
std::queue<Instruction> rob_;   // no depth limit
```

**Fix:** `std::array<RobEntry, ROB_DEPTH>` with explicit overflow check.

### AP‑DSA03 — `std::list` for Hardware FIFO

**Why bad:** Poor cache locality. Every element allocation is separate. Iteration is random-access-unfriendly.  
**Fix:** Ring buffer with power-of-2 depth and index masking.

---

## 8. Operator Overloading Anti‑Patterns

### AP‑O01 — Implicit Conversion Operator

```cpp
// ❌ Forbidden
class Addr { operator uint64_t() const { return v_; } };   // implicit
Addr a(0x1000);
uint64_t x = a;   // silent — no cast visible
```

**Fix:** `explicit operator uint64_t() const { return v_; }`

### AP‑O02 — `operator<<` That Mutates the Object

```cpp
// ❌ Forbidden — const correctness violation
std::ostream& operator<<(std::ostream& os, Packet& p) {   // non-const ref
    ++p.log_count_;   // mutation inside stream operator
    return os << p.addr;
}
```

**Fix:** `operator<<` must take `const Packet&`.

### AP‑O03 — Overloading `&&`, `||`, `,`

**Why bad:** Overloading these operators removes short-circuit evaluation and sequencing guarantees.

---

## 9. Summary Table

| # | Anti‑Pattern | Category | Fix |
|---|---|---|---|
| AP‑C01 | Hidden global state | C++ | Encapsulate in module |
| AP‑C02 | Implicit conversions | C++ | `explicit` constructors |
| AP‑C03 | Returning refs to locals | C++ | Return by value |
| AP‑C04 | `using namespace std` in headers | C++ | Explicit `std::` |
| AP‑C05 | Magic number literals | C++ | Named `constexpr` constants |
| AP‑SC01 | Blocking `SC_METHOD` | SystemC | Move to `SC_THREAD` |
| AP‑SC02 | Allocation in `SC_METHOD` | SystemC | Pre-allocate / pool |
| AP‑SC06 | Missing `operator==` on signal payload | SystemC | Define `operator==` |
| AP‑TLM01 | Zero-latency `b_transport` | TLM | Always annotate delay |
| AP‑TLM02 | `delay =` instead of `delay +=` | TLM | Always `+=` |
| AP‑TLM04 | Missing response status | TLM | Set before return |
| AP‑TLM05 | `throw` in transport | TLM | Use response status codes |
| AP‑VP01 | Random delays | VP | Fixed latency constants |
| AP‑VP02 | Unbounded queues | VP | `SC_REPORT_FATAL` on overflow |
| AP‑M02 | Unbounded container growth | Memory | Bounded ring buffer |
| AP‑AI01 | No `dump_state()` | AI | Implement full dump |
| AP‑AI02 | Pointers in dump | AI | Never include addresses |
| AP‑DSA01 | Algorithm names for HW | DSA | Use hardware names |
| AP‑O01 | Implicit conversion operator | Operators | `explicit` |

---

## 10. Glossary

| Term | Definition |
|---|---|
| **Anti-pattern** | A recurring solution that seems reasonable but causes problems in practice |
| **Hot path** | Code executed frequently during simulation (SC_METHOD, b_transport, tight loops) |
| **Determinism** | Same inputs + initial state → same outputs, every run |
| **POR state** | Power-On-Reset state — the initial state after hardware reset |
| **Spurious delta firing** | An `SC_METHOD` firing due to missing `operator==` even though signal value did not change |
