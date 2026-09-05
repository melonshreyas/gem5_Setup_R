# Memory Safety Rules, Patterns & Checks for Deterministic SystemC/TLM/VP Modelling

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for All Engineers (<5‑Year)  
**Prerequisites:** `01_Core_Philosophy.md`, `02_C++_Rules.md`, `09_Class_Design.md`

---

## Table of Contents

1. [Memory Safety Philosophy](#1-memory-safety-philosophy)
2. [Ownership & Lifetime Rules](#2-ownership--lifetime-rules)
3. [Smart Pointer Usage Rules](#3-smart-pointer-usage-rules)
4. [Stack vs Heap Rules](#4-stack-vs-heap-rules)
5. [Pools & Preallocation Patterns](#5-pools--preallocation-patterns)
6. [Buffer & Array Rules](#6-buffer--array-rules)
7. [Zero-Copy & Payload Rules](#7-zero-copy--payload-rules)
8. [Avoiding Dangling References](#8-avoiding-dangling-references)
9. [Memory Safety in SystemC Processes](#9-memory-safety-in-systemc-processes)
10. [Memory Safety in TLM Handlers](#10-memory-safety-in-tlm-handlers)
11. [Deterministic Allocation Policy](#11-deterministic-allocation-policy)
12. [Leak Detection & Tooling](#12-leak-detection--tooling)
13. [Complete Examples](#13-complete-examples)
14. [Checklist](#14-checklist)
15. [Glossary](#15-glossary)

---

## 1. Memory Safety Philosophy

| Principle | Requirement |
|---|---|
| **Deterministic lifetime** | Every object's lifetime must be explicit and reproducible |
| **Single owner** | Ownership must be obvious from type and API |
| **No hidden allocations** | No `new`/`malloc` in hot simulation paths |
| **Value semantics preferred** | Stack variables by default; heap only when justified |
| **RAII for all resources** | Lifetime tied to object scope |

---

## 2. Ownership & Lifetime Rules

### Rule M‑01 — Every heap resource MUST have a single owning object

```cpp
// ✅ Unique ownership — clear, RAII
auto buf = std::make_unique<uint8_t[]>(SIZE);

// ❌ Ambiguous ownership — who deletes?
uint8_t* raw = new uint8_t[SIZE];
```

### Rule M‑02 — Document ownership in header comments when nontrivial

```cpp
/// Owns the storage array. Non-copyable, movable.
/// Callers receive non-owning raw pointers valid only during b_transport.
class PayloadBuffer { ... };
```

### Rule M‑03 — No global mutable ownership

Global objects that own heap memory must be fully initialised before `sc_start()` and read-only thereafter.

### Rule M‑04 — Ownership transfers MUST be explicit — use move semantics, never implicit copy

```cpp
// ✅ Explicit transfer
auto dst = std::move(src);   // src is now empty — transfer is visible

// ❌ Implicit copy hides ownership
auto dst = src;              // is this a copy or a transfer?
```

---

## 3. Smart Pointer Usage Rules

### Rule M‑05 — Prefer `std::unique_ptr` for exclusive ownership

```cpp
// ✅ One owner — no overhead
std::unique_ptr<CacheSet[]> sets_ = std::make_unique<CacheSet[]>(num_sets_);
```

### Rule M‑06 — Use `std::shared_ptr` only when shared ownership is required — document why

```cpp
// ✅ Shared ownership — multiple modules share the routing table
std::shared_ptr<const NocRoutingTable> routing_;
// Documented: routing table built once, shared read-only across all routers
```

### Rule M‑07 — Use `std::weak_ptr` to break `shared_ptr` cycles

### Rule M‑08 — Raw pointers (`T*`) are for non-owning observers only

```cpp
// ✅ Non-owning observer — does not delete
void process(const Packet* pkt);   // caller retains ownership

// ❌ Owning raw pointer — forbidden
Packet* owned = new Packet();
```

### Rule M‑09 — No `new`/`delete` in hot paths — use pools or pre-allocated storage

---

## 4. Stack vs Heap Rules

### Rule M‑10 — Prefer stack (automatic) allocation for small, short-lived objects

```cpp
// ✅ Stack — automatic lifetime, zero allocation cost
uint8_t buf[CACHE_LINE_BYTES];
Packet  pkt{};
```

### Rule M‑11 — Use heap only when justified

| Justification | Example |
|---|---|
| Object too large for stack | `std::vector<uint8_t>` of 64 MB |
| Lifetime exceeds scope | Module member owned across `wait()` calls |
| Polymorphic object | `std::unique_ptr<ArbiterBase>` |

### Rule M‑12 — Never return pointers or references to stack objects

```cpp
// ❌ UB — stack frame destroyed on return
const uint8_t* get_buf() {
    uint8_t buf[64];
    return buf;   // dangling
}
```

---

## 5. Pools & Preallocation Patterns

### Rule M‑13 — Use object pools for frequently allocated objects

```cpp
template<typename T, std::size_t CAPACITY>
class ObjectPool {
public:
    ObjectPool() {
        pool_.resize(CAPACITY);
        for (auto& obj : pool_) free_.push_back(&obj);
    }

    T* acquire() {
        sc_assert(!free_.empty());
        auto* p = free_.back(); free_.pop_back();
        return p;
    }

    void release(T* p) {
        sc_assert(p >= pool_.data() && p < pool_.data() + pool_.size());
        free_.push_back(p);
    }

    std::size_t available() const { return free_.size(); }

private:
    std::vector<T>   pool_;
    std::vector<T*>  free_;
};
```

### Rule M‑14 — Pools MUST be bounded and pre-populated during elaboration

```cpp
SC_CTOR(DmaEngine) {
    // ✅ Pre-populate before simulation starts
    for (std::size_t i = 0; i < MAX_OUTSTANDING; ++i)
        pkt_pool_.acquire(); // force pre-allocation; release back immediately
    // Alternatively: pool is sized at construction (see Rule M‑13 above)
}
```

### Rule M‑15 — Pool overflow MUST trigger `SC_REPORT_FATAL`

```cpp
T* acquire() {
    if (free_.empty()) {
        SC_REPORT_FATAL("POOL", "pool exhausted — stimulus exceeds hardware bound");
    }
    return free_.back(); free_.pop_back();
}
```

### Rule M‑16 — Pool allocation order MUST be deterministic (LIFO stack = `std::vector`)

`std::vector` as the free list gives deterministic LIFO order. This ensures
the same object is reused in the same pattern for identical stimulus sequences.

---

## 6. Buffer & Array Rules

### Rule M‑17 — Use `std::array<T, N>` for fixed-size hardware structures

```cpp
// ✅ Hardware bound in the type — stack-allocated, zero overhead
std::array<RobEntry,   ROB_DEPTH>  rob_{};
std::array<uint8_t,    CACHE_LINE_BYTES> line_buf_{};
```

### Rule M‑18 — Use `std::vector` with `reserve()` for variable-size structures

```cpp
// ✅ One allocation in constructor, no reallocation during simulation
class Lsq {
public:
    explicit Lsq(std::size_t depth) { entries_.reserve(depth); }
private:
    std::vector<LsqEntry> entries_;
};
```

### Rule M‑19 — Use `.at()` in debug builds for bounds-checked access

```cpp
#ifdef NDEBUG
    return arr_[idx];
#else
    return arr_.at(idx);   // throws std::out_of_range — caught in test
#endif
```

### Rule M‑20 — Never `resize()` a container during simulation hot paths

---

## 7. Zero-Copy & Payload Rules

### Rule M‑21 — Zero-copy is allowed only with explicit lifetime documentation

```cpp
/// @param data_ptr  Non-owning pointer. Caller must ensure buffer
///                  remains valid until b_transport returns.
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay);
```

### Rule M‑22 — TLM payload data buffer MUST be stack or pre-allocated member storage

```cpp
// ✅ Member buffer — lifetime = module lifetime
std::array<uint8_t, MAX_TRANSFER_BYTES> data_buf_{};

void run() {
    pl_.set_data_ptr(data_buf_.data());   // always valid
    pl_.set_data_length(transfer_bytes_);
    isock->b_transport(pl_, delay_);
}
```

### Rule M‑23 — Targets MUST NOT store the payload `data_ptr` beyond the transport call

```cpp
// ❌ Forbidden — dangling after b_transport returns
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
    saved_ptr_ = pl.get_data_ptr();   // dangling after return
}

// ✅ Correct — copy immediately
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
    std::memcpy(mem_.data() + pl.get_address(),
                pl.get_data_ptr(), pl.get_data_length());
}
```

---

## 8. Avoiding Dangling References

### Rule M‑24 — Never return a reference or pointer to a local variable

```cpp
// ❌ UB
const Packet& get_pkt() {
    Packet p{};
    return p;   // dangling
}

// ✅ Return by value
Packet get_pkt() { return Packet{}; }
```

### Rule M‑25 — When storing references, ensure the referent outlives the reference

```cpp
// ✅ Lifetime documented: arbiter_ must outlive BusModel
class BusModel {
public:
    explicit BusModel(ArbiterBase& arb) : arb_(arb) {}
    // arb_ is a reference — caller is responsible for keeping arbiter alive
private:
    ArbiterBase& arb_;
};
```

### Rule M‑26 — Never store references across `wait()` calls in `SC_THREAD`

Between two `wait()` calls, the simulation may advance and the referenced
object's state may be inconsistent. Copy the value before `wait()`, or
use member variables.

---

## 9. Memory Safety in SystemC Processes

### Rule M‑27 — No `new` / `delete` / `malloc` / `free` inside `SC_METHOD`

```cpp
// ❌ Forbidden
void on_clock() {
    auto* pkt = new Packet();   // allocation in SC_METHOD
    process(pkt);
    delete pkt;
}

// ✅ Correct — pre-allocated pool
void on_clock() {
    Packet* pkt = pool_.acquire();
    sc_assert(pkt != nullptr);
    process(pkt);
    pool_.release(pkt);
}
```

### Rule M‑28 — Avoid heap allocation in `SC_THREAD` hot loops; use pools

```cpp
// ✅ Pool allocated in constructor, reused in loop
void dma_loop() {
    while (true) {
        wait(clk.posedge_event());
        Packet* desc = desc_pool_.acquire();
        fetch_descriptor(desc);
        // ... process ...
        desc_pool_.release(desc);
    }
}
```

### Rule M‑29 — Do not store pointers to local stack variables across `wait()` boundaries

---

## 10. Memory Safety in TLM Handlers

### Rule M‑30 — `b_transport` MUST NOT heap-allocate buffers for payload data

```cpp
// ❌ Forbidden
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
    auto buf = std::make_unique<uint8_t[]>(pl.get_data_length());   // heap in hot path
    std::memcpy(buf.get(), mem_.data() + pl.get_address(), pl.get_data_length());
    // ...
}

// ✅ Correct — stack buffer (bounded by MAX_TRANSFER_BYTES)
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
    sc_assert(pl.get_data_length() <= MAX_TRANSFER_BYTES);
    uint8_t buf[MAX_TRANSFER_BYTES];
    std::memcpy(buf, mem_.data() + pl.get_address(), pl.get_data_length());
    // ...
}
```

### Rule M‑31 — Reuse payload objects across transactions

```cpp
// ✅ Reuse member payload — reset fields before each call
tlm::tlm_generic_payload pl_;

void issue_read(uint64_t addr, uint32_t bytes) {
    pl_.set_command(tlm::TLM_READ_COMMAND);
    pl_.set_address(addr);
    pl_.set_data_ptr(buf_.data());
    pl_.set_data_length(bytes);
    pl_.set_byte_enable_ptr(nullptr);
    pl_.set_streaming_width(bytes);
    pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
    // ...
}
```

---

## 11. Deterministic Allocation Policy

### Policy M‑P1 — All dynamic allocations MUST occur during deterministic initialisation phases

Allocate in: module constructor, `before_end_of_elaboration()`, pool pre-population.  
Never allocate in: `SC_METHOD`, `b_transport`, simulation hot loops.

### Policy M‑P2 — Hot paths MUST use pre-allocated resources

Every allocation needed during simulation must already exist in a pool or
pre-allocated container.

### Policy M‑P3 — Memory allocation must be bounded

No container may grow unboundedly during simulation. Every container has a
declared maximum size matching the hardware specification.

---

## 12. Leak Detection & Tooling

### Development builds

Enable memory sanitizers in all non-production builds:

```bash
# AddressSanitizer + LeakSanitizer
g++ -fsanitize=address,leak -g -O1 ...

# Valgrind (alternative)
valgrind --leak-check=full --error-exitcode=1 ./sim
```

### Static analysis

```bash
# clang-tidy: catches ownership and lifetime issues
clang-tidy --checks='clang-analyzer-cplusplus*,modernize-*' ...

# cppcheck
cppcheck --enable=all --std=c++17 src/
```

### Deterministic allocation counter

In debug builds, wrap the allocator to assert zero net allocations during steady-state simulation:

```cpp
#ifdef DEBUG_ALLOC
std::atomic<int64_t> g_alloc_delta{0};
void* operator new(std::size_t n) {
    ++g_alloc_delta;
    return std::malloc(n);
}
void operator delete(void* p) noexcept {
    --g_alloc_delta;
    std::free(p);
}
// After warm-up: sc_assert(g_alloc_delta == 0);
#endif
```

---

## 13. Complete Examples

### 13.1 Pool-based packet processing

```cpp
constexpr std::size_t MAX_PKTS = 32;

SC_MODULE(PacketProcessor) {
    SC_CTOR(PacketProcessor)
        : pool_(MAX_PKTS) {
        SC_METHOD(on_pkt);
        sensitive << pkt_valid.pos();
    }

private:
    ObjectPool<Packet, MAX_PKTS> pool_;

    void on_pkt() {
        Packet* p = pool_.acquire();
        *p = pkt_in.read();
        process(*p);
        pool_.release(p);
    }
};
```

### 13.2 Pre-allocated TLM initiator

```cpp
SC_MODULE(TlmMaster) {
    tlm_utils::simple_initiator_socket<TlmMaster> isock{"isock"};

    SC_CTOR(TlmMaster) {
        // Pre-initialise reused fields
        pl_.set_byte_enable_ptr(nullptr);
        pl_.set_streaming_width(BUF_SIZE);
        pl_.set_data_ptr(buf_.data());
        pl_.set_data_length(BUF_SIZE);

        SC_THREAD(run);
        sensitive << clk.pos();
    }

private:
    tlm::tlm_generic_payload        pl_{};
    std::array<uint8_t, BUF_SIZE>   buf_{};

    void run() {
        while (true) {
            wait();
            pl_.set_command(tlm::TLM_READ_COMMAND);
            pl_.set_address(addr_);
            pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
            sc_time delay = SC_ZERO_TIME;
            isock->b_transport(pl_, delay);
            sc_assert(pl_.get_response_status() == tlm::TLM_OK_RESPONSE);
            wait(delay);
            addr_ += BUF_SIZE;
        }
    }

    static constexpr uint32_t BUF_SIZE = 64;
    uint64_t addr_ = 0;
};
```

---

## 14. Checklist

- [ ] No `new`/`delete` in `SC_METHOD` or `b_transport`
- [ ] Pools pre-allocated in constructor and bounded
- [ ] No dangling references returned from any function
- [ ] All heap resources managed by `unique_ptr`, `shared_ptr`, or pool
- [ ] `std::array<T,N>` used for fixed-size hardware structures
- [ ] `std::vector::reserve()` called in constructor for variable-size structures
- [ ] No `resize()` during simulation
- [ ] TLM payload data buffer is stack or pre-allocated member storage
- [ ] Targets do not store `data_ptr` beyond transport call scope
- [ ] AddressSanitizer / LeakSanitizer enabled in CI
- [ ] No pointers to locals returned or stored across `wait()` boundaries
- [ ] Pool overflow triggers `SC_REPORT_FATAL`

---

## 15. Glossary

| Term | Definition |
|---|---|
| **RAII** | Resource Acquisition Is Initialization — object destructor releases resource |
| **Pool** | Pre-allocated set of objects reused across simulation to avoid runtime `new` |
| **Zero-copy** | Passing a buffer pointer without copying the data — requires careful lifetime management |
| **Hot path** | Code executed frequently during simulation: `SC_METHOD`, `b_transport`, tight loops |
| **Dangling reference/pointer** | Reference or pointer to an object whose lifetime has ended — UB |
| **Automatic storage** | Stack-allocated variable — lifetime tied to its enclosing scope |
| **Owning pointer** | Pointer responsible for deleting its target |
| **Non-owning pointer** | Pointer that observes but does not own — `T*` in this codebase |
| **AddressSanitizer** | Compiler instrumentation that detects memory errors at runtime |
| **LeakSanitizer** | Compiler instrumentation that detects memory leaks at program exit |
