# Reusable Templates & Code Snippets for SystemC/TLM/VP Modelling

**Version:** 1.0 — July 2026  
**Standard:** Reference — Copy-paste ready, compliant with all SKILLS rules

---

## Table of Contents

1. [Bounded FIFO Template](#1-bounded-fifo-template)
2. [Object Pool Template](#2-object-pool-template)
3. [Register Bank Template](#3-register-bank-template)
4. [Scoreboard Template](#4-scoreboard-template)
5. [Round-Robin Arbiter Template](#5-round-robin-arbiter-template)
6. [TLM b\_transport Wrapper Template](#6-tlm-b_transport-wrapper-template)
7. [SC_MODULE Skeleton Template](#7-sc_module-skeleton-template)
8. [AI‑Testable SC_MODULE Template](#8-aitestable-sc_module-template)
9. [Performance Counter Template](#9-performance-counter-template)
10. [Deterministic Logger Template](#10-deterministic-logger-template)
11. [AI Test Harness Template](#11-ai-test-harness-template)
12. [FSM Template](#12-fsm-template)
13. [Usage Rules](#13-usage-rules)
14. [Glossary](#14-glossary)

---

## 1. Bounded FIFO Template

Power-of-2 depth, O(1) push/pop, no heap after construction.

```cpp
// bounded_fifo.h
#pragma once
#include <array>
#include <cstddef>
#include <systemc>

template<typename T, std::size_t DEPTH>
class BoundedFifo {
    static_assert(DEPTH > 0 && (DEPTH & (DEPTH - 1)) == 0,
                  "DEPTH must be a power of two");
public:
    BoundedFifo()  = default;
    ~BoundedFifo() = default;
    BoundedFifo(const BoundedFifo&) = delete;
    BoundedFifo& operator=(const BoundedFifo&) = delete;

    bool push(const T& v) {
        if (full()) {
            SC_REPORT_FATAL("BoundedFifo", "overflow — hardware bound exceeded");
            return false;
        }
        mem_[tail_ & MASK] = v;
        ++tail_;
        return true;
    }

    bool pop(T& out) {
        if (empty()) return false;
        out = mem_[head_ & MASK];
        ++head_;
        return true;
    }

    bool          empty()    const { return head_ == tail_; }
    bool          full()     const { return size() == DEPTH; }
    std::size_t   size()     const { return tail_ - head_; }
    std::size_t   free()     const { return DEPTH - size(); }
    static constexpr std::size_t capacity() { return DEPTH; }

    void clear() { head_ = tail_ = 0; }

    std::string dump() const {
        std::ostringstream oss;
        oss << "BoundedFifo{fill=" << size() << "/" << DEPTH << "}";
        return oss.str();
    }

private:
    static constexpr std::size_t MASK = DEPTH - 1;
    std::array<T, DEPTH> mem_{};
    std::size_t head_ = 0;
    std::size_t tail_ = 0;
};
```

---

## 2. Object Pool Template

Pre-allocated, LIFO, bounded, deterministic.

```cpp
// object_pool.h
#pragma once
#include <array>
#include <vector>
#include <cstddef>
#include <systemc>

template<typename T, std::size_t CAPACITY>
class ObjectPool {
public:
    ObjectPool() {
        free_.reserve(CAPACITY);
        for (auto& obj : pool_) free_.push_back(&obj);
    }
    ~ObjectPool() = default;
    ObjectPool(const ObjectPool&) = delete;
    ObjectPool& operator=(const ObjectPool&) = delete;

    T* acquire() {
        if (free_.empty()) {
            SC_REPORT_FATAL("ObjectPool", "pool exhausted — stimulus exceeds hardware bound");
            return nullptr;
        }
        T* p = free_.back(); free_.pop_back();
        return p;
    }

    void release(T* p) {
        sc_assert(p >= pool_.data() && p < pool_.data() + pool_.size());
        free_.push_back(p);
    }

    std::size_t available() const { return free_.size(); }
    std::size_t in_use()    const { return CAPACITY - free_.size(); }

private:
    std::array<T, CAPACITY> pool_{};
    std::vector<T*>         free_;
};
```

---

## 3. Register Bank Template

Fixed-size, bounds-checked, `dump()`-ready.

```cpp
// register_bank.h
#pragma once
#include <array>
#include <cstdint>
#include <sstream>
#include <string>
#include <systemc>

template<std::size_t N>
class RegisterBank {
public:
    RegisterBank() { regs_.fill(0); }

    uint32_t read(std::size_t idx) const {
        sc_assert(idx < N);
        return regs_[idx];
    }

    void write(std::size_t idx, uint32_t v) {
        sc_assert(idx < N);
        regs_[idx] = v;
    }

    void reset() { regs_.fill(0); }

    std::string dump() const {
        std::ostringstream oss;
        oss << "RegisterBank{";
        for (std::size_t i = 0; i < N; ++i)
            oss << " r" << i << "=0x" << std::hex << regs_[i];
        oss << "}";
        return oss.str();
    }

    static constexpr std::size_t size() { return N; }

private:
    std::array<uint32_t, N> regs_{};
};
```

---

## 4. Scoreboard Template

RAW/WAW hazard detection for out-of-order pipelines.

```cpp
// scoreboard.h
#pragma once
#include <array>
#include <cstdint>
#include <sstream>
#include <systemc>

class Scoreboard {
public:
    void mark_pending(uint8_t reg) {
        sc_assert(reg < NUM_REGS);
        pending_[reg] = true;
    }

    void mark_complete(uint8_t reg) {
        sc_assert(reg < NUM_REGS);
        pending_[reg] = false;
    }

    bool has_raw_hazard(uint8_t src_reg) const {
        sc_assert(src_reg < NUM_REGS);
        return src_reg != 0 && pending_[src_reg];
    }

    void reset() { pending_.fill(false); }

    std::string dump() const {
        std::ostringstream oss;
        oss << "Scoreboard{";
        for (uint8_t r = 0; r < NUM_REGS; ++r)
            if (pending_[r]) oss << " r" << static_cast<int>(r) << "=P";
        oss << "}";
        return oss.str();
    }

private:
    static constexpr uint8_t NUM_REGS = 32;
    std::array<bool, NUM_REGS> pending_{};
};
```

---

## 5. Round-Robin Arbiter Template

Deterministic, injectable grant latency, `dump()`-ready.

```cpp
// rr_arbiter.h
#pragma once
#include <systemc>
#include <cstdint>
#include <sstream>

class RoundRobinArbiter {
public:
    explicit RoundRobinArbiter(uint32_t n_masters, sc_time grant_latency)
        : n_(n_masters), grant_lat_(grant_latency), last_(0) {}

    sc_time request(uint32_t master_id) {
        sc_assert(master_id < n_);
        const uint32_t wait_slots =
            (master_id >= last_)
            ? (master_id - last_)
            : (n_ - last_ + master_id);
        last_ = (master_id + 1) % n_;
        return wait_slots > 0 ? sc_time(wait_slots * grant_lat_.to_double(), SC_NS) : SC_ZERO_TIME;
    }

    void reset() { last_ = 0; }

    std::string dump() const {
        std::ostringstream oss;
        oss << "RRArbiter{n=" << n_ << " last=" << last_ << "}";
        return oss.str();
    }

private:
    const uint32_t n_;
    const sc_time  grant_lat_;
    uint32_t       last_;
};
```

---

## 6. TLM b\_transport Wrapper Template

Adds bandwidth + arbitration latency. Separates performance from functional logic.

```cpp
// tlm_latency_wrapper.h
#pragma once
#include <systemc>
#include <tlm>
#include "tlm_utils/simple_target_socket.h"
#include <cstdint>
#include <sstream>

template<typename FunctionalTarget>
SC_MODULE(TlmLatencyWrapper) {
    tlm_utils::simple_target_socket<TlmLatencyWrapper> tsock{"tsock"};

    SC_HAS_PROCESS(TlmLatencyWrapper);
    TlmLatencyWrapper(sc_module_name   name,
                      FunctionalTarget& target,
                      sc_time           base_latency,
                      double            bw_bytes_per_ns,
                      sc_time           arb_latency = SC_ZERO_TIME)
        : sc_module(name)
        , target_(target)
        , base_lat_(base_latency)
        , bw_(bw_bytes_per_ns)
        , arb_lat_(arb_latency)
    {
        tsock.register_b_transport(this, &TlmLatencyWrapper::b_transport);
    }

    std::string dump_config() const {
        std::ostringstream oss;
        oss << name() << "_config{"
            << " base_ns=" << base_lat_.to_double()
            << " bw_GBps=" << bw_
            << " arb_ns="  << arb_lat_.to_double()
            << "}";
        return oss.str();
    }

private:
    FunctionalTarget& target_;
    const sc_time  base_lat_;
    const double   bw_;
    const sc_time  arb_lat_;
    uint64_t       txn_count_ = 0;

    void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
        // ① Arbitration
        delay += arb_lat_;
        // ② Base access latency
        delay += base_lat_;
        // ③ Bandwidth
        delay += sc_time(static_cast<double>(pl.get_data_length()) / bw_, SC_NS);
        // ④ Functional access
        target_.b_transport(pl, delay);
        ++txn_count_;
    }
};
```

---

## 7. SC_MODULE Skeleton Template

Minimal correct SC_MODULE with all required hooks.

```cpp
// skeleton_module.h
#pragma once
#include <systemc>
#include <cstdint>
#include <sstream>

SC_MODULE(SkeletonModule) {
    // ── Ports ──────────────────────────────────────────────────
    sc_in<bool>     clk;
    sc_in<bool>     rst_n;
    sc_in<uint32_t> data_in;
    sc_out<uint32_t> data_out;

    // ── Constructor ────────────────────────────────────────────
    SC_CTOR(SkeletonModule) {
        SC_METHOD(on_clock);
        sensitive << clk.pos() << rst_n.neg();
        dont_initialize();
    }

    // ── AI‑testability ─────────────────────────────────────────
    std::string dump_state() const {
        std::ostringstream oss;
        oss << name() << "{"
            << " reg=0x"   << std::hex << reg_
            << " cycles="  << std::dec << cycles_
            << "}";
        return oss.str();
    }

    void reset() { reg_ = 0; cycles_ = 0; }

private:
    uint32_t reg_    = 0;
    uint64_t cycles_ = 0;

    void on_clock() {
        if (!rst_n.read()) { reset(); return; }
        ++cycles_;
        reg_ = data_in.read();
        data_out.write(reg_);
    }
};
```

---

## 8. AI‑Testable SC_MODULE Template

Full template implementing the `AiTestable` interface.

```cpp
// ai_testable_module.h
#pragma once
#include <systemc>
#include <string>
#include <sstream>
#include <cstdint>

struct AiTestable {
    virtual std::string dump_state()  const = 0;
    virtual std::string dump_stats()  const = 0;
    virtual std::string dump_config() const = 0;
    virtual void        reset()             = 0;
    virtual ~AiTestable() = default;
};

SC_MODULE(AiModule), public AiTestable {
public:
    sc_in<bool>    clk;
    sc_in<bool>    rst_n;
    sc_in<uint32_t> data_in;
    sc_out<uint32_t> data_out;

    SC_HAS_PROCESS(AiModule);
    explicit AiModule(sc_module_name name, uint32_t param_a)
        : sc_module(name), param_a_(param_a) {
        SC_METHOD(on_clock);
        sensitive << clk.pos() << rst_n.neg();
        dont_initialize();
    }

    std::string dump_state() const override {
        std::ostringstream oss;
        oss << name() << "{"
            << " reg=0x"   << std::hex << reg_
            << " cycles="  << std::dec << total_cycles_
            << " stalls="  << stall_count_
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
        oss << name() << "_config{param_a=" << param_a_ << "}";
        return oss.str();
    }

    void reset() override {
        reg_          = 0;
        total_cycles_ = 0;
        stall_count_  = 0;
    }

private:
    const uint32_t param_a_;
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

## 9. Performance Counter Template

Reusable struct for transaction/latency/utilisation tracking.

```cpp
// perf_counters.h
#pragma once
#include <systemc>
#include <cstdint>
#include <sstream>

struct PerfCounters {
    uint64_t transactions   = 0;
    uint64_t read_txns      = 0;
    uint64_t write_txns     = 0;
    sc_time  total_latency  {SC_ZERO_TIME};
    sc_time  peak_latency   {SC_ZERO_TIME};
    uint64_t busy_cycles    = 0;
    uint64_t total_cycles   = 0;

    void record(tlm::tlm_command cmd, sc_time lat) {
        ++transactions;
        if (cmd == tlm::TLM_READ_COMMAND) ++read_txns;
        else                              ++write_txns;
        total_latency = sc_time(total_latency.to_double() + lat.to_double(), SC_NS);
        if (lat > peak_latency) peak_latency = lat;
    }

    void tick(bool busy) {
        ++total_cycles;
        if (busy) ++busy_cycles;
    }

    void reset() {
        transactions = read_txns = write_txns = 0;
        total_latency = peak_latency = SC_ZERO_TIME;
        busy_cycles = total_cycles = 0;
    }

    sc_time avg_latency() const {
        return transactions > 0
             ? sc_time(total_latency.to_double() / transactions, SC_NS)
             : SC_ZERO_TIME;
    }

    double utilisation() const {
        return total_cycles > 0
             ? static_cast<double>(busy_cycles) / total_cycles
             : 0.0;
    }

    std::string dump() const {
        std::ostringstream oss;
        oss << "PerfCounters{"
            << " txns="     << transactions
            << " reads="    << read_txns
            << " writes="   << write_txns
            << " avg_lat_ns="  << avg_latency().to_double()
            << " peak_lat_ns=" << peak_latency.to_double()
            << " util_pct=" << (utilisation() * 100.0)
            << "}";
        return oss.str();
    }
};
```

---

## 10. Deterministic Logger Template

`key=value` structured logging via `SC_REPORT_INFO`.

```cpp
// det_logger.h
#pragma once
#include <systemc>
#include <sstream>
#include <string>

class DeterministicLogger {
public:
    explicit DeterministicLogger(const char* module_name)
        : name_(module_name) {}

    void info(const std::string& msg) const {
        SC_REPORT_INFO(name_, msg.c_str());
    }

    /// Helper: build key=value string
    static std::string kv(std::initializer_list<std::pair<const char*, std::string>> fields) {
        std::ostringstream oss;
        bool first = true;
        for (const auto& [k, v] : fields) {
            if (!first) oss << " ";
            oss << k << "=" << v;
            first = false;
        }
        return oss.str();
    }

private:
    const char* name_;
};

// Usage:
// DeterministicLogger log_(name());
// log_.info(DeterministicLogger::kv({
//     {"op",    "READ"},
//     {"addr",  "0x1000"},
//     {"bytes", "64"},
//     {"lat_ns","12.0"},
// }));
```

---

## 11. AI Test Harness Template

Single-step cycle harness with snapshot comparison.

```cpp
// ai_harness.h
#pragma once
#include <systemc>
#include <vector>
#include <string>
#include <sstream>

template<typename Module>
class AiCycleHarness {
public:
    AiCycleHarness(Module& dut, sc_time clk_period)
        : dut_(dut), clk_period_(clk_period) {}

    void reset() { dut_.reset(); }

    // Step one clock cycle and return state snapshot
    std::string step(const typename Module::Stimulus& stim) {
        dut_.apply_stimulus(stim);
        sc_start(clk_period_);
        return dut_.dump_state();
    }

    // Run N cycles with stimuli, compare against golden snapshots
    bool run(const std::vector<typename Module::Stimulus>& stimuli,
             const std::vector<std::string>& golden)
    {
        bool pass = true;
        dut_.reset();
        for (std::size_t i = 0; i < stimuli.size(); ++i) {
            const std::string snap = step(stimuli[i]);
            if (i < golden.size() && snap != golden[i]) {
                std::ostringstream oss;
                oss << "MISMATCH cycle=" << i
                    << "\n  expected: " << golden[i]
                    << "\n  actual:   " << snap;
                SC_REPORT_ERROR("AI_HARNESS", oss.str().c_str());
                pass = false;
            }
        }
        return pass;
    }

    std::string dump_stats() const { return dut_.dump_stats(); }

private:
    Module&   dut_;
    sc_time   clk_period_;
};
```

---

## 12. FSM Template

`enum class` states, `switch` transitions, full `dump_state()`.

```cpp
// fsm_template.h
#pragma once
#include <systemc>
#include <sstream>
#include <string>
#include <cstdint>

enum class FsmState { IDLE, ACTIVE, WAIT, ERROR };

inline const char* state_name(FsmState s) {
    switch (s) {
        case FsmState::IDLE:   return "IDLE";
        case FsmState::ACTIVE: return "ACTIVE";
        case FsmState::WAIT:   return "WAIT";
        case FsmState::ERROR:  return "ERROR";
        default:               return "UNKNOWN";
    }
}

SC_MODULE(FsmModule) {
    sc_in<bool>  clk;
    sc_in<bool>  rst_n;
    sc_in<bool>  trigger;
    sc_out<bool> busy;

    SC_CTOR(FsmModule) {
        SC_METHOD(fsm_step);
        sensitive << clk.pos() << rst_n.neg();
        dont_initialize();
    }

    std::string dump_state() const {
        std::ostringstream oss;
        oss << name() << "{"
            << " state=" << state_name(state_)
            << " cycles=" << cycles_
            << "}";
        return oss.str();
    }

    void reset() { state_ = FsmState::IDLE; cycles_ = 0; }

private:
    FsmState state_  = FsmState::IDLE;
    uint64_t cycles_ = 0;

    void transition(FsmState next, const char* trigger_name) {
#ifdef AI_VERBOSE_LOG
        std::ostringstream oss;
        oss << "fsm_transition"
            << " from="    << state_name(state_)
            << " trigger=" << trigger_name
            << " to="      << state_name(next);
        SC_REPORT_INFO(name(), oss.str().c_str());
#endif
        state_ = next;
    }

    void fsm_step() {
        if (!rst_n.read()) { reset(); busy.write(false); return; }
        ++cycles_;
        switch (state_) {
            case FsmState::IDLE:
                if (trigger.read()) {
                    transition(FsmState::ACTIVE, "trigger");
                    busy.write(true);
                }
                break;
            case FsmState::ACTIVE:
                transition(FsmState::WAIT, "auto");
                break;
            case FsmState::WAIT:
                transition(FsmState::IDLE, "auto");
                busy.write(false);
                break;
            case FsmState::ERROR:
            default:
                SC_REPORT_ERROR(name(), "FSM in ERROR state");
                break;
        }
    }
};
```

---

## 13. Usage Rules

### Rule T‑01 — Templates MUST be instantiated with hardware-meaningful type parameters

```cpp
// ✅ Hardware-meaningful
BoundedFifo<FetchPacket, FETCH_QUEUE_DEPTH> fetch_queue_{};
ObjectPool<Packet, MAX_OUTSTANDING>         pkt_pool_;

// ❌ Generic/unclear
BoundedFifo<int, 16> queue_{};
```

### Rule T‑02 — Template depth/capacity parameters MUST be named `constexpr` constants

```cpp
// ✅
constexpr std::size_t FETCH_QUEUE_DEPTH = 16;
BoundedFifo<FetchPacket, FETCH_QUEUE_DEPTH> q_{};

// ❌ Magic number
BoundedFifo<FetchPacket, 16> q_{};
```

### Rule T‑03 — Templates MUST NOT use heavy metaprogramming (SFINAE, complex CRTP)

Simple `template<typename T>` and `template<typename T, std::size_t N>` only.

### Rule T‑04 — Template instantiations in hot paths MUST be fully inlineable

Prefer `std::array`-backed implementations for hot-path templates.

### Rule T‑05 — All templates MUST include `dump()` or `dump_state()` methods

---

## 14. Glossary

| Term | Definition |
|---|---|
| **Template** | C++ parameterised class or function — instantiated at compile time |
| **Pool** | Pre-allocated object store — avoids runtime `new` in simulation |
| **FIFO** | First-In First-Out bounded queue — fundamental pipeline buffer |
| **Scoreboard** | Register-state tracking table for hazard detection |
| **Arbiter** | Component that grants access to a shared resource |
| **FSM** | Finite State Machine — explicit states, transitions, outputs |
| **Harness** | Test infrastructure that drives stimulus and checks outputs |
| **AI-testable** | Module implementing `dump_state/stats/config`, `reset()`, `apply_stimulus()` |
