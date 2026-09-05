# Strict TLM‑2.0 Engineering Rules, Patterns, Diagrams & VP Modelling Techniques

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for SystemC/VP/Performance‑Modelling Engineers (<5‑Year)  
**Prerequisites:** `01_Core_Philosophy.md`, `02_C++_Rules.md`, `03_SystemC_Rules.md`

---

## Table of Contents

1. [Philosophy of TLM‑2.0](#1-philosophy-of-tlm20)
2. [TLM‑2.0 Core Rules](#2-tlm20-core-rules)
3. [Sockets & Payload Rules](#3-sockets--payload-rules)
4. [b\_transport Rules](#4-b_transport-rules)
5. [nb\_transport\_fw / nb\_transport\_bw Rules](#5-nb_transport_fw--nb_transport_bw-rules)
6. [Timing Annotation Rules](#6-timing-annotation-rules)
7. [Protocol Rules](#7-protocol-rules)
8. [Memory Manager Rules](#8-memory-manager-rules)
9. [VP Performance Modelling Patterns](#9-vp-performance-modelling-patterns)
10. [TLM‑2.0 Hardware Diagrams](#10-tlm20-hardware-diagrams)
11. [Complete Initiator Example](#11-complete-initiator-example)
12. [Complete Target Example](#12-complete-target-example)
13. [Complete Router / Interconnect Example](#13-complete-router--interconnect-example)
14. [AI‑Testability Hooks](#14-aitestability-hooks)
15. [TLM Anti‑Patterns](#15-tlm-anti-patterns)
16. [TLM Templates Reference](#16-tlm-templates-reference)
17. [Checklist](#17-checklist)
18. [Glossary](#18-glossary)

---

## 1. Philosophy of TLM‑2.0

> **TLM‑2.0 is not a software API. It is a hardware transaction protocol
> embedded in SystemC.**

Every TLM transaction models a real bus transfer — with address decoding,
arbitration, latency, and bandwidth constraints. Code that treats
`b_transport` as a function call without timing annotation is **wrong** —
it silently collapses all memory latency to zero and produces invalid
performance estimates.

### Core axioms

```
① Every transaction has a timing annotation — no exceptions.
② Payload ownership is explicit — initiator allocates, initiator frees.
③ b_transport is deterministic — same payload → same effect, always.
④ No dynamic allocation in transport hot paths.
⑤ No exceptions anywhere in the TLM stack.
⑥ No custom protocol phases — use the standard 4‑phase handshake.
⑦ Bandwidth, latency, and arbitration are modelled explicitly.
⑧ AI testing requires stable, typed, logged state at module boundaries.
```

---

## 2. TLM‑2.0 Core Rules

### Rule TLM‑01 — All TLM behaviour MUST be deterministic

```cpp
// ❌ Forbidden — non-deterministic delay
delay += sc_time(rand() % 10, SC_NS);

// ✅ Correct — deterministic, parameter-driven
delay += sc_time(static_cast<double>(size_bytes) / bandwidth_bytes_per_ns, SC_NS);
```

### Rule TLM‑02 — No dynamic allocation in transport hot paths

Payload objects MUST be pre-allocated before `sc_start()` or managed by a
memory manager (see §8). Never `new` inside `b_transport`,
`nb_transport_fw`, or `nb_transport_bw`.

```cpp
// ❌ Forbidden
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    auto* buf = new uint8_t[pl.get_data_length()];   // heap alloc on hot path
    // ...
}

// ✅ Correct — stack buffer, bounded size
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    uint8_t buf[MAX_TRANSFER_BYTES];
    std::memcpy(buf, pl.get_data_ptr(), pl.get_data_length());
    // ...
}
```

### Rule TLM‑03 — No exceptions in the TLM stack

```cpp
// ❌ Forbidden
if (addr > MAX_ADDR) throw std::out_of_range("bad addr");

// ✅ Correct — use TLM response status
if (addr > MAX_ADDR) {
    pl.set_response_status(tlm::TLM_ADDRESS_ERROR_RESPONSE);
    return;
}
```

### Rule TLM‑04 — No logging inside critical transport paths in production builds

```cpp
// ❌ Forbidden in production
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    SC_REPORT_INFO(name(), "b_transport called");   // fires every transaction
}

// ✅ Correct — debug guard
void b_transport(tlm_payload_t& pl, sc_time& delay) {
#ifdef TLM_DEBUG
    std::ostringstream oss;
    oss << "b_transport addr=0x" << std::hex << pl.get_address();
    SC_REPORT_INFO(name(), oss.str().c_str());
#endif
    // ...
}
```

### Rule TLM‑05 — No polymorphic payload extensions unless explicitly documented

Undocumented extensions create hidden inter-module coupling that breaks
determinism and AI testability.

### Rule TLM‑06 — Response status MUST always be set before returning from b\_transport

```cpp
// ❌ Forbidden — response status left at default (TLM_INCOMPLETE_RESPONSE)
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    do_access(pl);
    // forgot pl.set_response_status(...)
}

// ✅ Correct
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    if (!do_access(pl)) {
        pl.set_response_status(tlm::TLM_GENERIC_ERROR_RESPONSE);
        return;
    }
    pl.set_response_status(tlm::TLM_OK_RESPONSE);
}
```

---

## 3. Sockets & Payload Rules

### Rule TLM‑07 — Use `tlm_utils::simple_initiator_socket` and `tlm_utils::simple_target_socket`

Raw `tlm::tlm_initiator_socket` requires manual callback binding. The
`tlm_utils` wrappers handle this correctly and are the standard.

```cpp
#include "tlm_utils/simple_initiator_socket.h"
#include "tlm_utils/simple_target_socket.h"

SC_MODULE(Master) {
    tlm_utils::simple_initiator_socket<Master> isock{"isock"};
    // ...
};

SC_MODULE(Slave) {
    tlm_utils::simple_target_socket<Slave> tsock{"tsock"};
    SC_CTOR(Slave) {
        tsock.register_b_transport(this, &Slave::b_transport);
    }
    // ...
};
```

### Rule TLM‑08 — Payload MUST be reused across transactions — never heap-allocated per call

```cpp
// ❌ Forbidden — new payload every transaction
void run() {
    while (true) {
        wait(clk.posedge_event());
        auto* pl = new tlm::tlm_generic_payload();   // leaks, non-deterministic
        isock->b_transport(*pl, delay_);
    }
}

// ✅ Correct — single reused payload, reset between uses
tlm::tlm_generic_payload pl_;   // member variable

void run() {
    while (true) {
        wait(clk.posedge_event());
        pl_.set_command(tlm::TLM_READ_COMMAND);
        pl_.set_address(addr_);
        pl_.set_data_ptr(buf_);
        pl_.set_data_length(sizeof(buf_));
        pl_.set_byte_enable_ptr(nullptr);
        pl_.set_streaming_width(sizeof(buf_));
        pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
        isock->b_transport(pl_, delay_);
    }
}
```

### Rule TLM‑09 — Payload MUST be fully initialised before every transport call

All seven mandatory fields must be set:

| Field | Setter | Must set? |
|---|---|---|
| Command | `set_command()` | ✅ |
| Address | `set_address()` | ✅ |
| Data pointer | `set_data_ptr()` | ✅ |
| Data length | `set_data_length()` | ✅ |
| Byte enable pointer | `set_byte_enable_ptr()` | ✅ (`nullptr` if unused) |
| Streaming width | `set_streaming_width()` | ✅ (= data_length for non-streaming) |
| Response status | `set_response_status(TLM_INCOMPLETE_RESPONSE)` | ✅ (reset before each call) |

### Rule TLM‑10 — Data buffer pointer MUST point to valid storage for the entire transport call

```cpp
// ❌ Forbidden — pointer to local that goes out of scope inside b_transport
{
    uint8_t buf[64];
    pl_.set_data_ptr(buf);
    isock->b_transport(pl_, delay_);
}
// buf destroyed here — target may have retained the pointer

// ✅ Correct — member array outlives the transport call
std::array<uint8_t, MAX_TRANSFER_BYTES> buf_{};
```

### Rule TLM‑11 — Targets MUST NOT store the payload data pointer beyond the transport call

```cpp
// ❌ Forbidden — storing pointer past return
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    saved_ptr_ = pl.get_data_ptr();   // dangling after return
}

// ✅ Correct — copy data immediately
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    std::memcpy(mem_.data() + pl.get_address(), pl.get_data_ptr(),
                pl.get_data_length());
}
```

---

## 4. b\_transport Rules

`b_transport` is a **blocking** call. The initiator suspends until the
target returns. The target models the entire transaction latency via
`delay` accumulation.

### Rule TLM‑12 — b\_transport MUST annotate timing via `delay`

```cpp
// ❌ Forbidden — zero latency model
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    mem_[pl.get_address()] = *pl.get_data_ptr();
    // delay untouched — zero latency, invalid performance model
}

// ✅ Correct — latency reflected
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    const uint32_t bytes = pl.get_data_length();
    delay += ACCESS_LATENCY + sc_time(bytes / BW_BYTES_PER_NS, SC_NS);
    std::memcpy(mem_.data() + pl.get_address(),
                pl.get_data_ptr(), bytes);
    pl.set_response_status(tlm::TLM_OK_RESPONSE);
}
```

### Rule TLM‑13 — b\_transport MUST be reentrant-safe

If the same target can receive concurrent calls (multi-initiator router),
all state modifications must be guarded by explicit arbitration, not
implicit assumptions.

### Rule TLM‑14 — b\_transport MUST NOT call `sc_start` or kernel-advancing functions

`b_transport` runs inside the initiator's simulation thread. Calling
`sc_start` from within it is undefined.

### Rule TLM‑15 — After b\_transport returns, initiator MUST check response status

```cpp
isock->b_transport(pl_, delay_);
if (pl_.get_response_status() != tlm::TLM_OK_RESPONSE) {
    SC_REPORT_ERROR(name(), "transaction failed");
}
```

---

## 5. nb\_transport\_fw / nb\_transport\_bw Rules

Non-blocking transport models the **4-phase handshake** used in
cycle-accurate timing models and loosely-timed protocols.

### Standard 4-phase protocol

```
Initiator                               Target
─────────                               ──────
nb_transport_fw(BEGIN_REQ)  ──────────▶
                            ◀──────────  nb_transport_bw(END_REQ)
nb_transport_fw(BEGIN_RESP) ──────────▶  [or target calls nb_transport_bw(BEGIN_RESP)]
                            ◀──────────  nb_transport_bw(END_RESP)
```

### Rule TLM‑16 — nb\_transport\_fw MUST be non-blocking — no `wait()` inside

```cpp
// ❌ Forbidden
tlm_sync_enum nb_transport_fw(tlm_payload_t& pl, tlm_phase& ph, sc_time& d) {
    wait(ACCESS_LATENCY);   // blocks — forbidden in nb_transport
    // ...
}
```

### Rule TLM‑17 — nb\_transport\_fw MUST return a valid `tlm_sync_enum`

| Return value | Meaning |
|---|---|
| `TLM_ACCEPTED` | Phase accepted; target will call bw later |
| `TLM_UPDATED` | Phase updated by target; check `phase` argument |
| `TLM_COMPLETED` | Transaction complete in this call |

### Rule TLM‑18 — nb\_transport\_bw MUST NOT block

Same rule as `nb_transport_fw` — it runs in the target's context and must
return immediately.

### Rule TLM‑19 — No custom protocol phases

```cpp
// ❌ Forbidden
tlm::tlm_phase MY_CUSTOM_PHASE = 10;

// ✅ Only standard phases
tlm::BEGIN_REQ, tlm::END_REQ, tlm::BEGIN_RESP, tlm::END_RESP
```

### Rule TLM‑20 — nb\_transport implementations MUST handle all four phases

Unhandled phases cause silent protocol bugs. Use a `switch` with an
explicit `default` that reports an error.

```cpp
tlm_sync_enum nb_transport_fw(tlm_payload_t& pl, tlm_phase& ph, sc_time& d) {
    switch (ph) {
        case tlm::BEGIN_REQ:  /* ... */ return tlm::TLM_ACCEPTED;
        case tlm::END_RESP:   /* ... */ return tlm::TLM_COMPLETED;
        default:
            SC_REPORT_ERROR(name(), "unexpected TLM phase");
            return tlm::TLM_ACCEPTED;
    }
}
```

---

## 6. Timing Annotation Rules

### Rule TLM‑21 — Timing annotation MUST be cumulative — always `+=`, never `=`

```cpp
// ❌ Forbidden — overwrites upstream latency accumulated by initiator
delay = sc_time(10, SC_NS);

// ✅ Correct — adds target's contribution to the running total
delay += sc_time(10, SC_NS);
```

### Rule TLM‑22 — Timing MUST be monotonic — never subtract from `delay`

```cpp
// ❌ Forbidden
delay -= sc_time(5, SC_NS);
```

### Rule TLM‑23 — Bandwidth latency MUST be derived from transfer size

```cpp
// ❌ Forbidden — fixed latency ignores transfer size
delay += sc_time(10, SC_NS);

// ✅ Correct
constexpr double BW_BYTES_PER_NS = 8.0;   // 8 GB/s bus
delay += sc_time(static_cast<double>(pl.get_data_length()) / BW_BYTES_PER_NS, SC_NS);
```

### Rule TLM‑24 — Arbitration latency MUST be added when a shared resource is claimed

```cpp
// ✅ Arbiter adds its delay before memory latency
delay += arbiter_.request(requester_id_);
delay += ACCESS_LATENCY;
```

### Rule TLM‑25 — All latency constants MUST be named `sc_time` constants

```cpp
// ✅ Named, documented
constexpr sc_time SRAM_LATENCY    (2,  SC_NS);
constexpr sc_time DRAM_LATENCY    (80, SC_NS);
constexpr sc_time BUS_ARB_LATENCY (1,  SC_NS);
```

---

## 7. Protocol Rules

### Rule TLM‑26 — Every b\_transport call is a complete, atomic transaction

From the model's perspective, a `b_transport` call represents one hardware
transaction — read or write — with a start address, byte count, and
completion status.

### Rule TLM‑27 — Burst transfers MUST be modelled as a single b\_transport call with correct `data_length`

```cpp
// ✅ 64-byte cache-line fill as single transaction
pl_.set_data_length(CACHE_LINE_BYTES);
pl_.set_streaming_width(CACHE_LINE_BYTES);
delay += sc_time(CACHE_LINE_BYTES / BW_BYTES_PER_NS, SC_NS);
```

### Rule TLM‑28 — READ command MUST fill `data_ptr` on return; WRITE command MUST consume `data_ptr` in target

```cpp
// Read target — fills buffer
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    if (pl.get_command() == tlm::TLM_READ_COMMAND) {
        std::memcpy(pl.get_data_ptr(),
                    mem_.data() + pl.get_address(),
                    pl.get_data_length());
    } else {
        std::memcpy(mem_.data() + pl.get_address(),
                    pl.get_data_ptr(),
                    pl.get_data_length());
    }
    delay += ACCESS_LATENCY;
    pl.set_response_status(tlm::TLM_OK_RESPONSE);
}
```

### Rule TLM‑29 — Address decoding MUST be performed in the router/interconnect, not in leaf targets

Leaf targets receive pre-decoded, offset-adjusted addresses. This mirrors
real hardware where the interconnect strips the base address.

---

## 8. Memory Manager Rules

When a model creates many short-lived transactions (e.g. DMA engines),
using a **memory manager** avoids heap fragmentation.

### Rule TLM‑30 — Use `tlm::tlm_mm_interface` for pooled payload management

```cpp
class PayloadPool : public tlm::tlm_mm_interface {
public:
    tlm::tlm_generic_payload* allocate() {
        if (!pool_.empty()) {
            auto* p = pool_.back();
            pool_.pop_back();
            return p;
        }
        return new tlm::tlm_generic_payload(this);
    }

    void free(tlm::tlm_generic_payload* p) override {
        p->reset();
        pool_.push_back(p);
    }

private:
    std::vector<tlm::tlm_generic_payload*> pool_;
};
```

### Rule TLM‑31 — Memory manager pool MUST be pre-populated during elaboration

```cpp
PayloadPool pool_;

SC_CTOR(DmaEngine) {
    // Pre-populate during construction — not during simulation
    for (int i = 0; i < MAX_OUTSTANDING; ++i) {
        pool_.free(new tlm::tlm_generic_payload(&pool_));
    }
}
```

### Rule TLM‑32 — `acquire()` / `release()` reference counts MUST be balanced

```cpp
auto* pl = pool_.allocate();
pl->acquire();
isock->b_transport(*pl, delay_);
pl->release();   // returns to pool when ref count reaches zero
```

---

## 9. VP Performance Modelling Patterns

These patterns compose inside `b_transport` to build accurate performance
models. Apply them in the order shown.

### 9.1 Latency accumulation pattern

```cpp
// Apply base access latency
delay += SRAM_LATENCY;
```

### 9.2 Bandwidth throttling pattern

```cpp
// Add transfer time based on bus width
const uint32_t bytes = pl.get_data_length();
delay += sc_time(static_cast<double>(bytes) / BW_BYTES_PER_NS, SC_NS);
```

### 9.3 Arbitration delay pattern

```cpp
// Add round-robin arbitration overhead
delay += arbiter_.compute_grant_delay(requester_id_);
```

### 9.4 Queuing delay pattern

```cpp
// Model a finite-depth request queue
const uint32_t q_depth = req_queue_.size();
delay += sc_time(q_depth * QUEUE_ENTRY_LATENCY_NS, SC_NS);
```

### 9.5 Pipeline stall pattern

```cpp
// Data hazard: stall until dependency clears
if (hazard_detected_) {
    delay += static_cast<double>(stall_cycles_) * CLK_PERIOD;
}
```

### 9.6 Cache miss penalty pattern

```cpp
// Tag lookup miss → DRAM penalty
if (!tag_hit(pl.get_address())) {
    delay += DRAM_LATENCY;
} else {
    delay += CACHE_HIT_LATENCY;
}
```

### 9.7 NoC hop delay pattern

```cpp
// Each router hop adds a fixed latency
const uint32_t hops = noc_.route(src_id_, dst_id_).hop_count();
delay += hops * NOC_HOP_LATENCY;
```

### 9.8 Burst coalescing pattern

```cpp
// Multiple small transfers coalesced into one bus transaction
const uint32_t bus_transactions =
    (total_bytes + BUS_WIDTH_BYTES - 1) / BUS_WIDTH_BYTES;
delay += bus_transactions * BUS_CYCLE_TIME;
```

### 9.9 Composing patterns — full memory subsystem example

```cpp
void b_transport(tlm_payload_t& pl, sc_time& delay) {
    // ① Arbitration
    delay += arbiter_.compute_grant_delay(id_);

    // ② Cache lookup
    const bool hit = cache_.lookup(pl.get_address());
    if (!hit) {
        // ③ DRAM bandwidth + latency
        const uint32_t bytes = pl.get_data_length();
        delay += DRAM_LATENCY;
        delay += sc_time(static_cast<double>(bytes) / DRAM_BW_BYTES_PER_NS, SC_NS);
        cache_.fill(pl.get_address(), pl.get_data_ptr(), bytes);
    } else {
        delay += CACHE_HIT_LATENCY;
    }

    // ④ Read/write operation
    if (pl.get_command() == tlm::TLM_READ_COMMAND) {
        cache_.read(pl.get_address(), pl.get_data_ptr(), pl.get_data_length());
    } else {
        cache_.write(pl.get_address(), pl.get_data_ptr(), pl.get_data_length());
    }

    pl.set_response_status(tlm::TLM_OK_RESPONSE);
}
```

---

## 10. TLM‑2.0 Hardware Diagrams

### 10.1 Single initiator → single target

```
  Initiator (Master)                         Target (Slave / Memory)
  ──────────────────                         ───────────────────────
  simple_initiator_socket<Master>  ─────────▶  simple_target_socket<Slave>
                                   b_transport(pl, delay)
                                   ◀─────────  pl.response_status = TLM_OK
```

### 10.2 TLM 4-phase non-blocking handshake

```
  Time ──────────────────────────────────────────────────────────────▶

  Initiator  ──BEGIN_REQ──▶                   ──BEGIN_RESP──▶
                            ◀──END_REQ──                    ◀──END_RESP──
  Target                                ──BEGIN_RESP──▶

  delay annotations:
     BEGIN_REQ  → END_REQ   : cmd decode + arbitration latency
     END_REQ    → BEGIN_RESP : memory access latency + bandwidth
     BEGIN_RESP → END_RESP   : data return + bus latency
```

### 10.3 Multi-master router interconnect

```
  Master 0 ──isock──┐                        ┌──tsock── Slave 0 (0x0000–0x0FFF)
  Master 1 ──isock──┤    ┌────────────┐      ├──tsock── Slave 1 (0x1000–0x1FFF)
  Master 2 ──isock──┼───▶│   Router   │──────┤
  Master 3 ──isock──┘    │ (address   │      └──tsock── Slave 2 (0x2000–0x2FFF)
                         │  decode +  │
                         │  arbitrate)│
                         └────────────┘
                         RR arbiter — adds arb_delay per winner
                         Address decode — strips base, routes to target
```

### 10.4 TLM timing budget breakdown

```
  Total delay = arb_delay + queue_delay + access_latency + bw_delay

  arb_delay    ── time waiting for bus grant
  queue_delay  ── time waiting for request queue slot
  access_latency ─ base memory/cache latency
  bw_delay     ── bytes / bandwidth_bytes_per_ns
```

### 10.5 Pipeline + TLM integration

```
  ┌──────────┐  sc_fifo<Req>  ┌──────────────┐  TLM b_transport  ┌──────────┐
  │  Issue   │ ──────────────▶│  Load/Store  │ ─────────────────▶│  Cache   │
  │  Stage   │                │  Unit        │                    │  Model   │
  └──────────┘                └──────────────┘ ◀─────────────────└──────────┘
                                                response + delay
```

---

## 11. Complete Initiator Example

```cpp
// tlm_initiator.h
#pragma once
#include <systemc>
#include <tlm>
#include "tlm_utils/simple_initiator_socket.h"
#include <array>
#include <cstdint>
#include <sstream>

constexpr uint32_t TRANSFER_BYTES  = 64;
constexpr sc_time  ISSUE_PERIOD    (1, SC_NS);

SC_MODULE(TlmInitiator) {
    // ── Ports ──────────────────────────────────────────────────
    sc_in<bool> clk;
    sc_in<bool> rst_n;

    // ── TLM socket ─────────────────────────────────────────────
    tlm_utils::simple_initiator_socket<TlmInitiator> isock{"isock"};

    // ── Constructor ────────────────────────────────────────────
    SC_CTOR(TlmInitiator) {
        SC_THREAD(run);
        sensitive << clk.pos();

        // Pre-initialise reused payload fields that never change
        pl_.set_byte_enable_ptr(nullptr);
        pl_.set_streaming_width(TRANSFER_BYTES);
        pl_.set_data_ptr(buf_.data());
        pl_.set_data_length(TRANSFER_BYTES);
    }

    // ── AI‑testability ─────────────────────────────────────────
    std::string dump_state() const {
        std::ostringstream oss;
        oss << "TlmInitiator{addr=0x" << std::hex << current_addr_
            << " total_ns=" << std::dec << total_delay_.to_double() << "}";
        return oss.str();
    }

private:
    tlm::tlm_generic_payload       pl_{};
    std::array<uint8_t, TRANSFER_BYTES> buf_{};
    sc_time                        delay_{SC_ZERO_TIME};
    sc_time                        total_delay_{SC_ZERO_TIME};
    uint64_t                       current_addr_ = 0;

    void run() {
        wait();   // skip reset
        while (true) {
            wait(clk.posedge_event());
            if (!rst_n.read()) { current_addr_ = 0; continue; }

            // ── Set per-transaction fields ──────────────────────
            pl_.set_command(tlm::TLM_READ_COMMAND);
            pl_.set_address(current_addr_);
            pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
            delay_ = SC_ZERO_TIME;

            // ── Issue transaction ───────────────────────────────
            isock->b_transport(pl_, delay_);

            // ── Check response ──────────────────────────────────
            if (pl_.get_response_status() != tlm::TLM_OK_RESPONSE) {
                SC_REPORT_ERROR(name(), "TLM transaction error");
                continue;
            }

            total_delay_ += delay_;
            current_addr_ += TRANSFER_BYTES;

#ifdef TLM_DEBUG
            std::ostringstream oss;
            oss << "read addr=0x" << std::hex << (current_addr_ - TRANSFER_BYTES)
                << " delay=" << delay_.to_double() << "ns";
            SC_REPORT_INFO(name(), oss.str().c_str());
#endif
        }
    }
};
```

---

## 12. Complete Target Example

```cpp
// tlm_memory.h
#pragma once
#include <systemc>
#include <tlm>
#include "tlm_utils/simple_target_socket.h"
#include <array>
#include <cstdint>
#include <cstring>
#include <sstream>

constexpr uint32_t MEM_SIZE_BYTES  = 65536;
constexpr sc_time  MEM_RD_LATENCY  (10, SC_NS);
constexpr sc_time  MEM_WR_LATENCY  ( 8, SC_NS);
constexpr double   MEM_BW_BYTES_PER_NS = 8.0;   // 8 GB/s

SC_MODULE(TlmMemory) {
    // ── TLM socket ─────────────────────────────────────────────
    tlm_utils::simple_target_socket<TlmMemory> tsock{"tsock"};

    SC_CTOR(TlmMemory) {
        tsock.register_b_transport(this, &TlmMemory::b_transport);
        mem_.fill(0);
    }

    std::string dump_state() const {
        std::ostringstream oss;
        oss << "TlmMemory{accesses=" << access_count_ << "}";
        return oss.str();
    }

private:
    std::array<uint8_t, MEM_SIZE_BYTES> mem_{};
    uint64_t access_count_ = 0;

    void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
        const uint64_t addr  = pl.get_address();
        const uint32_t bytes = pl.get_data_length();
        uint8_t* const dptr  = pl.get_data_ptr();

        // ── Bounds check ────────────────────────────────────────
        if (addr + bytes > MEM_SIZE_BYTES) {
            pl.set_response_status(tlm::TLM_ADDRESS_ERROR_RESPONSE);
            return;
        }

        // ── Latency: base + bandwidth ───────────────────────────
        const sc_time base = (pl.get_command() == tlm::TLM_READ_COMMAND)
                           ? MEM_RD_LATENCY : MEM_WR_LATENCY;
        delay += base;
        delay += sc_time(static_cast<double>(bytes) / MEM_BW_BYTES_PER_NS, SC_NS);

        // ── Data transfer ───────────────────────────────────────
        if (pl.get_command() == tlm::TLM_READ_COMMAND) {
            std::memcpy(dptr, mem_.data() + addr, bytes);
        } else {
            std::memcpy(mem_.data() + addr, dptr, bytes);
        }

        pl.set_response_status(tlm::TLM_OK_RESPONSE);
        ++access_count_;
    }
};
```

---

## 13. Complete Router / Interconnect Example

```cpp
// tlm_router.h
#pragma once
#include <systemc>
#include <tlm>
#include "tlm_utils/simple_initiator_socket.h"
#include "tlm_utils/simple_target_socket.h"
#include <array>
#include <cstdint>

// Address map — two slaves
constexpr uint64_t SLAVE0_BASE = 0x0000'0000ULL;
constexpr uint64_t SLAVE0_SIZE = 0x0001'0000ULL;   // 64 KB
constexpr uint64_t SLAVE1_BASE = 0x0001'0000ULL;
constexpr uint64_t SLAVE1_SIZE = 0x0001'0000ULL;   // 64 KB

constexpr sc_time  ROUTER_DECODE_LATENCY(1, SC_NS);

SC_MODULE(TlmRouter) {
    // ── Upstream (from masters) ─────────────────────────────────
    tlm_utils::simple_target_socket<TlmRouter> tsock{"tsock"};

    // ── Downstream (to slaves) ─────────────────────────────────
    tlm_utils::simple_initiator_socket<TlmRouter> isock0{"isock0"};
    tlm_utils::simple_initiator_socket<TlmRouter> isock1{"isock1"};

    SC_CTOR(TlmRouter) {
        tsock.register_b_transport(this, &TlmRouter::b_transport);
    }

private:
    void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
        const uint64_t addr = pl.get_address();

        // ── Address decode latency ──────────────────────────────
        delay += ROUTER_DECODE_LATENCY;

        // ── Route to correct slave, strip base address ──────────
        if (addr >= SLAVE0_BASE && addr < SLAVE0_BASE + SLAVE0_SIZE) {
            pl.set_address(addr - SLAVE0_BASE);
            isock0->b_transport(pl, delay);
            pl.set_address(addr);   // restore original address
        } else if (addr >= SLAVE1_BASE && addr < SLAVE1_BASE + SLAVE1_SIZE) {
            pl.set_address(addr - SLAVE1_BASE);
            isock1->b_transport(pl, delay);
            pl.set_address(addr);
        } else {
            pl.set_response_status(tlm::TLM_ADDRESS_ERROR_RESPONSE);
        }
    }
};
```

---

## 14. AI‑Testability Hooks

### Rule TLM‑33 — Every TLM module MUST expose `dump_state() const`

```cpp
std::string dump_state() const {
    std::ostringstream oss;
    oss << "TlmMemory{"
        << " accesses=" << access_count_
        << " last_addr=0x" << std::hex << last_addr_
        << "}";
    return oss.str();
}
```

### Rule TLM‑34 — Bandwidth and latency parameters MUST be injectable at construction time

```cpp
// ✅ AI can sweep across configurations
TlmMemory(sc_module_name name,
          sc_time rd_latency,
          sc_time wr_latency,
          double  bw_bytes_per_ns);
```

### Rule TLM‑35 — All timing constants MUST be observable via getters

```cpp
sc_time read_latency()   const { return rd_latency_; }
sc_time write_latency()  const { return wr_latency_; }
double  bandwidth()      const { return bw_bytes_per_ns_; }
```

### Rule TLM‑36 — Log format MUST be stable and machine-parseable

```cpp
// ✅ Key=value format — parseable by AI test harness
oss << "op=READ addr=0x" << std::hex << addr
    << " bytes=" << std::dec << bytes
    << " delay_ns=" << delay.to_double();
```

---

## 15. TLM Anti‑Patterns

| Anti‑Pattern | Consequence | Correct approach |
|---|---|---|
| `new payload` inside `b_transport` | Heap fragmentation, non-deterministic timing | Reuse member payload or use memory manager |
| `delay = 0` (zero latency) | Invalid performance model — collapses all latency | Always annotate with latency + bandwidth |
| `delay = value` (not `+=`) | Overwrites upstream latency | Always use `+=` |
| Storing `data_ptr` beyond transport call | Dangling pointer — UB | Copy data immediately inside `b_transport` |
| `throw` inside transport | Terminates simulation without cleanup | Set `TLM_GENERIC_ERROR_RESPONSE` |
| `SC_REPORT_INFO` on every transaction | Dominates simulation runtime | Guard with `#ifdef TLM_DEBUG` |
| Custom protocol phases | Breaks interoperability | Use only `BEGIN/END_REQ/RESP` |
| Missing response status | Initiator receives `TLM_INCOMPLETE_RESPONSE` — silent bug | Always `set_response_status` before return |
| `rand()` in timing | Non-deterministic simulation | Use fixed, parameter-driven latency |
| `unordered_map` for address decode | Non-deterministic routing order | `std::map` or explicit if/else chain |
| `wait()` inside `nb_transport_fw` | Runtime crash — nb must be non-blocking | Move blocking logic to `SC_THREAD` |
| Multi-master writes to same signal | Delta-cycle race | Route through router with arbitration |

---

## 16. TLM Templates Reference

### 16.1 Minimal b\_transport target

```cpp
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
    const uint64_t addr  = pl.get_address();
    const uint32_t bytes = pl.get_data_length();

    if (addr + bytes > CAPACITY) {
        pl.set_response_status(tlm::TLM_ADDRESS_ERROR_RESPONSE);
        return;
    }

    delay += BASE_LATENCY;
    delay += sc_time(static_cast<double>(bytes) / BW_BYTES_PER_NS, SC_NS);

    if (pl.get_command() == tlm::TLM_READ_COMMAND) {
        std::memcpy(pl.get_data_ptr(), storage_.data() + addr, bytes);
    } else {
        std::memcpy(storage_.data() + addr, pl.get_data_ptr(), bytes);
    }

    pl.set_response_status(tlm::TLM_OK_RESPONSE);
}
```

### 16.2 nb\_transport\_fw — initiator side

```cpp
tlm::tlm_sync_enum nb_transport_fw(tlm::tlm_generic_payload& pl,
                                   tlm::tlm_phase& phase,
                                   sc_time& delay) {
    switch (phase) {
        case tlm::BEGIN_REQ:
            delay += CMD_DECODE_LATENCY;
            phase = tlm::END_REQ;
            return tlm::TLM_UPDATED;

        case tlm::END_RESP:
            resp_event_.notify(delay);
            return tlm::TLM_COMPLETED;

        default:
            SC_REPORT_ERROR(name(), "unexpected phase in nb_transport_fw");
            return tlm::TLM_ACCEPTED;
    }
}
```

### 16.3 nb\_transport\_bw — target side

```cpp
tlm::tlm_sync_enum nb_transport_bw(tlm::tlm_generic_payload& pl,
                                   tlm::tlm_phase& phase,
                                   sc_time& delay) {
    switch (phase) {
        case tlm::BEGIN_RESP:
            delay += RESP_LATENCY;
            phase = tlm::END_RESP;
            return tlm::TLM_UPDATED;

        default:
            SC_REPORT_ERROR(name(), "unexpected phase in nb_transport_bw");
            return tlm::TLM_ACCEPTED;
    }
}
```

### 16.4 Complete initiator transaction loop

```cpp
void run() {
    while (true) {
        wait(clk.posedge_event());

        pl_.set_command(tlm::TLM_READ_COMMAND);
        pl_.set_address(addr_);
        pl_.set_data_ptr(buf_.data());
        pl_.set_data_length(BUF_SIZE);
        pl_.set_byte_enable_ptr(nullptr);
        pl_.set_streaming_width(BUF_SIZE);
        pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);

        sc_time delay = SC_ZERO_TIME;
        isock->b_transport(pl_, delay);

        sc_assert(pl_.get_response_status() == tlm::TLM_OK_RESPONSE);

        addr_ += BUF_SIZE;
    }
}
```

---

## 17. Checklist

Use in every TLM module code review.

### Payload
- [ ] No `new tlm_generic_payload` inside transport calls
- [ ] All seven mandatory fields set before every transport call
- [ ] Response status reset to `TLM_INCOMPLETE_RESPONSE` before each call
- [ ] Response status set to `TLM_OK_RESPONSE` or error code before return
- [ ] Data pointer points to storage valid for entire transport call duration
- [ ] Target does not store `data_ptr` beyond transport call

### Timing
- [ ] `delay +=` used (not `delay =`)
- [ ] Base access latency applied
- [ ] Bandwidth latency derived from transfer size
- [ ] Arbitration latency added when applicable
- [ ] All latency values are named `sc_time` constants

### Protocol
- [ ] Only standard phases used (`BEGIN/END_REQ/RESP`)
- [ ] `nb_transport_fw` / `nb_transport_bw` contain no `wait()`
- [ ] All four phases handled in `nb_transport` switch
- [ ] Address decoding in router, not in leaf target
- [ ] Base address stripped before forwarding to leaf target

### Error handling
- [ ] No `throw` anywhere in TLM stack
- [ ] Bounds check before every memory access
- [ ] Initiator checks response status after every `b_transport` call

### AI‑testability
- [ ] `dump_state()` method present
- [ ] Bandwidth and latency parameters injectable at construction
- [ ] Log format is key=value, machine-parseable
- [ ] No `unordered_map` for routing tables

---

## 18. Glossary

| Term | Definition |
|---|---|
| **TLM‑2.0** | OSCI Transaction Level Modelling standard, version 2.0 |
| **b\_transport** | Blocking transport — initiator blocks until target returns |
| **nb\_transport\_fw** | Non-blocking forward transport — initiator → target, must not block |
| **nb\_transport\_bw** | Non-blocking backward transport — target → initiator, must not block |
| **tlm\_generic\_payload** | Standard TLM payload struct — carries command, address, data |
| **tlm\_phase** | Protocol phase — `BEGIN_REQ`, `END_REQ`, `BEGIN_RESP`, `END_RESP` |
| **tlm\_sync\_enum** | Return value of nb_transport — `TLM_ACCEPTED`, `TLM_UPDATED`, `TLM_COMPLETED` |
| **simple\_initiator\_socket** | `tlm_utils` wrapper — handles callback registration automatically |
| **simple\_target\_socket** | `tlm_utils` wrapper — `register_b_transport` binds the callback |
| **timing annotation** | The `sc_time& delay` parameter — accumulates transaction latency |
| **memory manager** | `tlm_mm_interface` implementation — pools payload objects |
| **bandwidth** | Bytes transferred per nanosecond on the modelled bus |
| **arbitration latency** | Time a requester waits to win a shared resource grant |
| **address decode** | Mapping a system address to a target slave + local offset |
| **burst** | Single TLM transaction carrying multiple bytes (data_length > bus_width) |
| **VP** | Virtual Prototype — full-system SystemC/TLM simulation |
| **UB** | Undefined Behaviour |
