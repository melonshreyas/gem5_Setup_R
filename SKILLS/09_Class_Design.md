# Class Design Rules for Deterministic Hardware Modelling, SystemC, TLM & VP

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for SystemC/VP/Performance‑Modelling Engineers (<5‑Year)  
**Prerequisites:** `01_Core_Philosophy.md`, `02_C++_Rules.md`

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Design Philosophy](#2-design-philosophy)
3. [Single Responsibility Rule](#3-single-responsibility-rule)
4. [Encapsulation & Access Control](#4-encapsulation--access-control)
5. [Immutable State & Const Correctness](#5-immutable-state--const-correctness)
6. [Constructors, Destructors & Initialisation Patterns](#6-constructors-destructors--initialisation-patterns)
7. [Copy, Move Semantics & Ownership Rules](#7-copy-move-semantics--ownership-rules)
8. [Resource Management & RAII](#8-resource-management--raii)
9. [Interface Design & Contracts](#9-interface-design--contracts)
10. [Polymorphism & Virtual Functions](#10-polymorphism--virtual-functions)
11. [Composition vs Inheritance](#11-composition-vs-inheritance)
12. [Member Layout & Initialisation Order](#12-member-layout--initialisation-order)
13. [Thread Safety & Reentrancy Rules](#13-thread-safety--reentrancy-rules)
14. [SystemC Module Class Patterns](#14-systemc-module-class-patterns)
15. [TLM Component Class Patterns](#15-tlm-component-class-patterns)
16. [Performance‑Sensitive Class Patterns](#16-performancesensitive-class-patterns)
17. [Debugging, Introspection & Dump Interfaces](#17-debugging-introspection--dump-interfaces)
18. [Testability & Dependency Injection](#18-testability--dependency-injection)
19. [Anti‑Patterns](#19-anti-patterns)
20. [Example Class Templates](#20-example-class-templates)
21. [Checklist](#21-checklist)
22. [Glossary](#22-glossary)

---

## 1. Purpose and Scope

This document defines strict class design rules for hardware modelling code written in C++ for SystemC and TLM. Apply these rules to **all** classes used in:

- Simulation modules (`SC_MODULE` subclasses)
- TLM initiator and target classes
- VP performance model components
- Protocol adapters and bridges
- DSA hardware structures (FIFOs, caches, arbiters, state machines)
- AI test harness classes

---

## 2. Design Philosophy

| Principle | Requirement |
|---|---|
| **Determinism first** | Class behaviour must be reproducible given identical inputs and initial state |
| **Explicit ownership** | Every resource has a single, documented owner |
| **Minimal public surface** | Expose only what is necessary for correct use |
| **Immutable configuration** | Construction-time parameters are `const` after construction |
| **RAII for resources** | Memory, file handles, sockets — all tied to object lifetime |
| **No hidden side effects** | Methods must not silently mutate global or external state |
| **AI testability** | Every class exposes `dump_state()`, `reset()`, and injectable parameters |
| **Hardware mapping** | Class structure reflects hardware structure (pipeline stage, FIFO, arbiter) |

---

## 3. Single Responsibility Rule

### Rule CD‑01 — Every class MUST have a single, documented responsibility

Document it in a one-line header comment:

```cpp
/// Models a single set of an N-way set-associative cache — tag lookup and LRU eviction only.
class CacheSet { ... };

/// Annotates TLM b_transport delay with bandwidth-derived latency.
class BandwidthModel { ... };
```

### Rule CD‑02 — If a class exceeds one responsibility, split it

```
❌  CacheAndDramController  — two responsibilities → split into CacheModel + DramModel
✅  CacheModel              — tag lookup, hit/miss, LRU eviction
✅  DramModel               — RAS/CAS timing, bank scheduling, bandwidth
```

### Rule CD‑03 — Use small helper classes for parsing, formatting, and logging

Keep core hardware model classes focused on modelling. Extract helpers:

```cpp
class LatencyFormatter {
public:
    static std::string format(sc_time t) {
        std::ostringstream oss;
        oss << t.to_double() << "ns";
        return oss.str();
    }
};
```

---

## 4. Encapsulation & Access Control

### Rule CD‑04 — All data members MUST be `private`

No `public` or `protected` data members — ever.

```cpp
// ❌ Forbidden
struct Stage {
    bool     valid;   // public data
    uint64_t pc;
};

// ✅ Correct
class Stage {
public:
    bool     valid() const { return valid_; }
    uint64_t pc()    const { return pc_; }
    void     set(bool v, uint64_t p) { valid_ = v; pc_ = p; }
private:
    bool     valid_ = false;
    uint64_t pc_    = 0;
};
```

### Rule CD‑05 — Provide `const` accessors for read access

Every observable member variable gets a `const` getter. No getter for
members that do not affect external behaviour (internal counters used only
for `dump_stats()` are acceptable as read-only via `dump_stats()`).

### Rule CD‑06 — Use `friend` only for tightly coupled test helpers

```cpp
class CacheSet {
    friend class CacheSetTest;   // only for unit test — document why
    // ...
};
```

---

## 5. Immutable State & Const Correctness

### Rule CD‑07 — Configuration and metadata MUST be `const` after construction

```cpp
class BusModel {
public:
    BusModel(uint32_t width_bytes, sc_time arb_lat, double bw_bytes_per_ns)
        : width_bytes_(width_bytes)
        , arb_lat_(arb_lat)
        , bw_bytes_per_ns_(bw_bytes_per_ns) {}

private:
    const uint32_t width_bytes_;      // ✅ immutable after construction
    const sc_time  arb_lat_;
    const double   bw_bytes_per_ns_;
};
```

### Rule CD‑08 — Mark all methods that do not modify observable state as `const`

```cpp
bool     probe(uint64_t addr)   const;   // ✅ pure lookup
uint32_t set_index(uint64_t a)  const;   // ✅ pure calculation
double   hit_rate()             const;   // ✅ derived statistic
void     fill(uint64_t addr);            // mutator — NOT const
```

### Rule CD‑09 — Use `const` references for all input parameters

```cpp
// ✅
void process(const Packet& p);
void set_config(const CacheConfig& cfg);

// ❌ copies unnecessarily
void process(Packet p);
```

---

## 6. Constructors, Destructors & Initialisation Patterns

### Rule CD‑10 — Use `explicit` for all single-argument constructors

```cpp
// ✅ Prevents: Fifo f = 16; (implicit construction)
explicit Fifo(std::size_t depth);

// ❌ Allows implicit conversion
Fifo(std::size_t depth);
```

### Rule CD‑11 — Use member initialiser lists for ALL members

```cpp
// ✅ Correct — initialiser list controls order and avoids double-init
Fifo::Fifo(std::size_t depth)
    : depth_(depth)
    , head_(0)
    , tail_(0)
    , buf_(depth)   // vector allocated once, correct size
{}

// ❌ Wrong — assignment in body double-initialises
Fifo::Fifo(std::size_t depth) {
    depth_ = depth;   // default-init then assign
    buf_.resize(depth);
}
```

### Rule CD‑12 — Destructors MUST be `noexcept` and MUST NOT throw

```cpp
~CacheModel() noexcept = default;
```

### Rule CD‑13 — For SystemC modules: NO `wait()`, NO kernel calls in constructor

```cpp
// ❌ Forbidden
SC_CTOR(FetchStage) {
    wait(1, SC_NS);   // kernel call in constructor — forbidden
}

// ✅ Correct — only process registration and member init
SC_CTOR(FetchStage) {
    SC_THREAD(fetch_loop);
    sensitive << clk.pos();
}
```

### Rule CD‑14 — Avoid non-deterministic heavy work in constructors

Constructors may allocate fixed-size storage and register processes.
They must NOT perform I/O, system calls, or simulation-time queries.

---

## 7. Copy, Move Semantics & Ownership Rules

### Rule CD‑15 — Explicitly define or delete ALL six special member functions

```cpp
class Buffer {
public:
    Buffer()                           = delete;   // must provide depth
    explicit Buffer(std::size_t depth);
    Buffer(const Buffer&)              = delete;   // non-copyable
    Buffer& operator=(const Buffer&)   = delete;
    Buffer(Buffer&&)                   = default;  // movable
    Buffer& operator=(Buffer&&)        = default;
    ~Buffer()                          = default;
};
```

### Rule CD‑16 — Document ownership policy in the class header comment

```cpp
/// Owns its underlying storage. Non-copyable, movable.
/// Move transfers ownership of the storage array.
class Buffer { ... };
```

### Rule CD‑17 — For value types (small PODs), allow copy; provide `operator==`

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

---

## 8. Resource Management & RAII

### Rule CD‑18 — Use RAII for all resources

| Resource | RAII wrapper |
|---|---|
| Heap memory | `std::unique_ptr<T>` or `std::vector<T>` |
| Shared memory | `std::shared_ptr<T>` (document sharing) |
| File handles | Custom RAII wrapper with POSIX `close()` in destructor |
| VCD trace file | `end_of_simulation()` callback |

### Rule CD‑19 — No raw `new` / `delete` except inside RAII wrappers

```cpp
// ❌ Forbidden in application code
auto* p = new Packet();
delete p;

// ✅ Correct
auto p = std::make_unique<Packet>();
// automatic cleanup on scope exit
```

### Rule CD‑20 — Pre-allocate all simulation storage during construction

```cpp
class Rob {
public:
    explicit Rob(std::size_t depth) : entries_(depth) {}   // one allocation, never again
private:
    std::vector<RobEntry> entries_;   // fixed size after construction
};
```

---

## 9. Interface Design & Contracts

### Rule CD‑21 — Document preconditions and postconditions for every public method

```cpp
/// Push a packet into the FIFO.
/// @pre  !full() — caller must check before pushing
/// @post size() == old size() + 1
/// @returns true on success, false if full (caller error)
bool push(const Packet& p);
```

### Rule CD‑22 — Use `sc_assert` for internal invariants

```cpp
void fill(uint64_t addr) {
    sc_assert(addr < CAPACITY_BYTES);   // internal invariant
    // ...
}
```

### Rule CD‑23 — Use `enum class` return codes for recoverable errors in hot paths

```cpp
enum class FifoStatus { OK, FULL, EMPTY };

FifoStatus push(const Packet& p) {
    if (full()) return FifoStatus::FULL;
    // ...
    return FifoStatus::OK;
}
```

---

## 10. Polymorphism & Virtual Functions

### Rule CD‑24 — If a class is a base for polymorphism, declare `virtual ~Base() = default`

```cpp
struct ArbiterBase {
    virtual ~ArbiterBase() = default;
    virtual sc_time grant_delay(uint32_t master_id, uint32_t n_masters) = 0;
    virtual std::string policy_name() const = 0;
};
```

### Rule CD‑25 — Keep virtual function count minimal

Prefer one pure virtual method per interface. Multiple pure virtuals in
one interface indicate the interface violates the single-responsibility rule.

### Rule CD‑26 — Avoid virtual functions in `SC_METHOD` hot paths

`SC_METHOD` fires every sensitive event. Virtual dispatch per call adds
measurable overhead in large simulations. Use template or direct call instead.

```cpp
// ❌ Virtual call per clock cycle
void on_clock() { arbiter_->compute(); }

// ✅ Template — resolved at compile time
template<typename ArbPolicy>
void on_clock() { ArbPolicy::compute(state_); }
```

---

## 11. Composition vs Inheritance

### Rule CD‑27 — Prefer composition for behaviour reuse

```cpp
// ❌ Deep inheritance for reuse
class TimedBus : public Bus, public LatencyModel { ... };

// ✅ Composition
class TimedBus {
    BusModel      bus_;
    LatencyModel  latency_;
};
```

### Rule CD‑28 — Use inheritance only for true is‑a relationships

```cpp
// ✅ SC_MODULE inherits sc_module — true is-a (SystemC requirement)
SC_MODULE(FetchStage) { ... };

// ✅ AiTestable interface — true is-a (every module IS-A AiTestable)
class Cache : public sc_module, public AiTestable { ... };
```

### Rule CD‑29 — SystemC submodules MUST be composed as member variables

```cpp
class Cpu : public sc_module {
    FetchStage   fetch_{"fetch"};   // ✅ composed, lifetime = Cpu lifetime
    DecodeStage  decode_{"decode"};
    CacheModel   icache_{"icache", L1_CFG};
};
```

---

## 12. Member Layout & Initialisation Order

### Rule CD‑30 — Declare members in the order they must be initialised

C++ initialises member variables in **declaration order**, not initialiser
list order. Mismatches cause bugs.

```cpp
class CdcFifo {
    // ✅ Declared in initialisation order
    const std::size_t depth_;   // 1st
    std::vector<Packet> mem_;   // 2nd — depends on depth_
    std::size_t wr_ptr_ = 0;   // 3rd
    std::size_t rd_ptr_ = 0;   // 4th
};
```

### Rule CD‑31 — Place frequently-accessed hot members early in the struct (cache locality)

```cpp
struct RobEntry {
    // Hot: checked every cycle
    bool     valid   = false;
    bool     ready   = false;
    uint8_t  rd      = 0;
    uint32_t result  = 0;
    // Cold: checked only on commit
    uint64_t pc      = 0;
    uint32_t insn    = 0;
};
```

---

## 13. Thread Safety & Reentrancy Rules

### Rule CD‑32 — SystemC simulation is single-threaded — never use `std::mutex` in processes

### Rule CD‑33 — Mark reentrant (read-only) methods `const`

A `const` method can be safely called from multiple contexts because it
does not modify the object.

### Rule CD‑34 — Global read-only singletons MUST be fully initialised before `sc_start()`

```cpp
// ✅ Initialise before simulation starts
const NocRoutingTable& routing = NocRoutingTable::build(4, 4);
sc_start();
```

---

## 14. SystemC Module Class Patterns

### Rule CD‑35 — Module constructor: registration only

```cpp
SC_MODULE(IssueStage) {
    sc_in<bool>          clk;
    sc_in<DecodePacket>  d_in;
    sc_out<IssuePacket>  i_out;
    sc_in<bool>          stall_in;
    sc_out<bool>         stall_out;

    SC_CTOR(IssueStage) {
        SC_METHOD(on_clock);
        sensitive << clk.pos();
        dont_initialize();
    }

    std::string dump_state() const { /* ... */ }
    void reset() { /* ... */ }

private:
    Scoreboard sb_{};
    uint64_t   stall_count_ = 0;

    void on_clock();
};
```

### Rule CD‑36 — Every SC_MODULE implements `dump_state()` and `reset()`

See `07_AI_Testing_Hooks.md` for the `AiTestable` interface.

---

## 15. TLM Component Class Patterns

### Rule CD‑37 — TLM class separates transport logic and performance model

```cpp
class DramTarget : public sc_module {
    tlm_utils::simple_target_socket<DramTarget> tsock{"tsock"};

    // Performance model — injectable
    DramTimingModel timing_;

    SC_CTOR(DramTarget) {
        tsock.register_b_transport(this, &DramTarget::b_transport);
    }

private:
    void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
        timing_.annotate(pl, delay);   // ← separate performance model class
        do_transfer(pl);
        pl.set_response_status(tlm::TLM_OK_RESPONSE);
    }
};
```

### Rule CD‑38 — TLM timing model is a separate, injectable class

```cpp
class DramTimingModel {
public:
    DramTimingModel(sc_time ras, sc_time cas, double bw)
        : ras_(ras), cas_(cas), bw_(bw) {}

    void annotate(const tlm::tlm_generic_payload& pl, sc_time& delay) const {
        delay += ras_ + cas_;
        delay += sc_time(pl.get_data_length() / bw_, SC_NS);
    }

private:
    const sc_time  ras_, cas_;
    const double   bw_;
};
```

---

## 16. Performance‑Sensitive Class Patterns

### Rule CD‑39 — Pre-allocate all storage in the constructor

```cpp
class LoadStoreQueue {
public:
    explicit LoadStoreQueue(std::size_t depth) {
        entries_.reserve(depth);   // ✅ one allocation, no reallocation
    }
private:
    std::vector<LsqEntry> entries_;
};
```

### Rule CD‑40 — Use object pools for frequently allocated objects

```cpp
class PacketPool {
public:
    explicit PacketPool(std::size_t n) : pool_(n) {
        for (auto& p : pool_) free_.push_back(&p);
    }
    Packet* acquire() {
        sc_assert(!free_.empty());
        auto* p = free_.back(); free_.pop_back(); return p;
    }
    void release(Packet* p) { free_.push_back(p); }
private:
    std::vector<Packet>  pool_;
    std::vector<Packet*> free_;
};
```

### Rule CD‑41 — Use `std::array<T, N>` for hardware-bounded structures

```cpp
// ✅ Hardware depth expressed in the type — bounds checked at compile time
std::array<RobEntry, ROB_DEPTH>   rob_{};
std::array<LsqEntry, LSQ_DEPTH>   lsq_{};
std::array<PipeSlot, PIPE_DEPTH>  pipe_{};
```

---

## 17. Debugging, Introspection & Dump Interfaces

### Rule CD‑42 — Every simulation class MUST implement `dump_state() const`

```cpp
std::string dump_state() const {
    std::ostringstream oss;
    oss << name() << "{"               // ← always include module name
        // control state
        << " fsm="    << state_name(state_)
        << " stall="  << stall_
        // data state
        << " pc=0x"   << std::hex << pc_
        // queue state
        << std::dec
        << " rob="    << rob_fill_ << "/" << ROB_DEPTH
        // stats
        << " ipc="    << ipc()
        << "}";
    return oss.str();
}
```

### Rule CD‑43 — `dump_state()` MUST be `const` and side-effect free

No counters incremented, no signals written, no heap allocated inside `dump_state()`.

### Rule CD‑44 — Use `key=value` format for machine-parseability

AI test harnesses use regex to extract individual fields. Fixed field names
and fixed order are mandatory.

---

## 18. Testability & Dependency Injection

### Rule CD‑45 — Inject all collaborator objects through the constructor

```cpp
// ✅ Collaborators injected — mockable in tests
class BusModel {
public:
    BusModel(ArbiterBase& arb, LatencyModel& lat)
        : arb_(arb), lat_(lat) {}
private:
    ArbiterBase&  arb_;
    LatencyModel& lat_;
};
```

### Rule CD‑46 — Define pure abstract interfaces for all collaborators

```cpp
struct ArbiterBase {
    virtual ~ArbiterBase() = default;
    virtual sc_time grant_delay(uint32_t id) = 0;
};

struct MockArbiter : ArbiterBase {
    sc_time grant_delay(uint32_t) override { return SC_ZERO_TIME; }
};
```

### Rule CD‑47 — Provide `reset()` to restore exact power-on-reset state

```cpp
void reset() {
    state_       = FsmState::IDLE;
    pc_          = RESET_VECTOR;
    stall_       = false;
    rob_.fill({});
    lsq_.fill({});
    txn_count_   = 0;
    stall_count_ = 0;
}
```

---

## 19. Anti‑Patterns

| Anti‑Pattern | Consequence | Fix |
|---|---|---|
| Public mutable data members | Breaks encapsulation — any code can corrupt state | Make `private`, add accessors |
| Returning references to locals | UB — dangling reference | Return by value or use smart pointer |
| Implicit conversions | Silent precision loss, unexpected construction | `explicit` constructors |
| Raw `new`/`delete` in hot paths | Non-deterministic timing, leak risk | Pre-allocate or use RAII |
| Virtual functions in `SC_METHOD` | Per-cycle virtual dispatch overhead | Template polymorphism |
| Global mutable singletons | Non-resettable state, test isolation impossible | Encapsulate in module, inject |
| Non-deterministic member init order | Depends on linker order | Declare in order, use initialiser lists |
| `using namespace std` in headers | Pollutes all consumer namespaces | Explicit `std::` qualification |
| Throwing from process or transport | No SystemC unwind — simulation terminates badly | `SC_REPORT_FATAL` / status codes |
| Hidden side effects in `const` accessors | Breaks `dump_state()` purity | Never mutate in `const` methods |

---

## 20. Example Class Templates

### 20.1 Deterministic register

```cpp
class Register {
public:
    explicit Register(uint32_t init = 0) : value_(init), reset_val_(init) {}
    uint32_t read()           const { return value_; }
    void     write(uint32_t v)      { value_ = v; }
    void     reset()                { value_ = reset_val_; }
    std::string dump() const {
        std::ostringstream oss;
        oss << "reg=0x" << std::hex << value_;
        return oss.str();
    }
private:
    uint32_t value_;
    const uint32_t reset_val_;
};
```

### 20.2 Pipeline stage slot

```cpp
struct PipeSlot {
    bool     valid = false;
    uint64_t pc    = 0;
    uint32_t insn  = 0;

    void clear() { *this = PipeSlot{}; }

    std::string dump() const {
        std::ostringstream oss;
        oss << "PipeSlot{valid=" << valid
            << " pc=0x" << std::hex << pc
            << " insn=0x" << insn << "}";
        return oss.str();
    }
};
```

### 20.3 Module with injected collaborators

```cpp
class IssueWindow {
public:
    IssueWindow(std::size_t depth, ArbiterBase& arb, Scoreboard& sb)
        : depth_(depth), arb_(arb), sb_(sb) {
        slots_.reserve(depth);
    }

    bool issue(const DecodePacket& pkt) {
        if (slots_.size() >= depth_) return false;
        if (sb_.has_raw_hazard(pkt.rs1) || sb_.has_raw_hazard(pkt.rs2))
            return false;
        sb_.mark_pending(pkt.rd);
        slots_.push_back(pkt);
        return true;
    }

    std::string dump_state() const {
        std::ostringstream oss;
        oss << "IssueWindow{fill=" << slots_.size() << "/" << depth_
            << " arb=" << arb_.policy_name() << "}";
        return oss.str();
    }

    void reset() { slots_.clear(); }

private:
    const std::size_t       depth_;
    ArbiterBase&            arb_;
    Scoreboard&             sb_;
    std::vector<DecodePacket> slots_;
};
```

---

## 21. Checklist

### Responsibility & encapsulation
- [ ] Class has a single documented responsibility
- [ ] All data members are `private`
- [ ] `const` accessors provided for all observable state
- [ ] Configuration members are `const` after construction

### Construction & lifecycle
- [ ] Single-argument constructors are `explicit`
- [ ] All members initialised via member initialiser list
- [ ] All six special member functions defined or deleted
- [ ] `reset()` restores exact POR state

### Resource management
- [ ] No raw `new`/`delete` in application code
- [ ] All storage pre-allocated in constructor
- [ ] RAII wrappers used for all resources

### SystemC / TLM rules
- [ ] No `wait()` or kernel calls in constructor
- [ ] TLM timing model is a separate injectable class
- [ ] No virtual functions in `SC_METHOD` hot path

### AI testability
- [ ] `dump_state()` is `const`, side-effect free, key=value format
- [ ] All parameters injectable at construction
- [ ] `reset()` method present
- [ ] Collaborators injected — mockable

### Anti-patterns
- [ ] No implicit conversions
- [ ] No returning references to locals
- [ ] No global mutable singletons
- [ ] No `using namespace std` in headers

---

## 22. Glossary

| Term | Definition |
|---|---|
| **RAII** | Resource Acquisition Is Initialization — resource lifetime tied to object lifetime |
| **Hot path** | Code executed frequently during simulation (SC_METHOD, b_transport, tight loops) |
| **Collaborator** | A class that another class depends on — inject via constructor for testability |
| **Invariant** | A condition that must always be true for a correctly-used object |
| **Composition** | Owning another object as a member variable — preferred over inheritance for behaviour reuse |
| **Dependency injection** | Passing collaborators through constructor or method parameters — enables mocking |
| **POR state** | Power-On-Reset state — the initial state after hardware reset |
| **Value type** | A class with value semantics — copyable, comparable with `operator==` |
| **Move-only type** | A class where copy is deleted but move is defined — unique ownership |
