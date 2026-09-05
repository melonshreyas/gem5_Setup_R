# Strict VP Performance Modelling Rules, Patterns, Diagrams & SystemC/TLM Integration

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for SystemC/VP/Performance‑Modelling Engineers (<5‑Year)  
**Prerequisites:** `01_Core_Philosophy.md`, `02_C++_Rules.md`, `03_SystemC_Rules.md`, `04_TLM2_Patterns.md`

---

## Table of Contents

1. [Philosophy of VP Performance Modelling](#1-philosophy-of-vp-performance-modelling)
2. [Determinism Rules](#2-determinism-rules)
3. [Latency Modelling Rules](#3-latency-modelling-rules)
4. [Bandwidth Modelling Rules](#4-bandwidth-modelling-rules)
5. [Arbitration Modelling Rules](#5-arbitration-modelling-rules)
6. [Queueing Theory Rules](#6-queueing-theory-rules)
7. [Pipeline Modelling Rules](#7-pipeline-modelling-rules)
8. [Cache & Memory Hierarchy Modelling Rules](#8-cache--memory-hierarchy-modelling-rules)
9. [NoC & Interconnect Modelling Rules](#9-noc--interconnect-modelling-rules)
10. [DMA & Burst Modelling Rules](#10-dma--burst-modelling-rules)
11. [Clock Domain Crossing Modelling Rules](#11-clock-domain-crossing-modelling-rules)
12. [TLM‑2.0 Integration Rules](#12-tlm20-integration-rules)
13. [SystemC Integration Rules](#13-systemc-integration-rules)
14. [Performance Measurement & Statistics](#14-performance-measurement--statistics)
15. [AI‑Testability Hooks](#15-aitestability-hooks)
16. [Hardware Diagrams](#16-hardware-diagrams)
17. [Complete Examples](#17-complete-examples)
18. [VP Anti‑Patterns](#18-vp-anti-patterns)
19. [VP Templates Reference](#19-vp-templates-reference)
20. [Checklist](#20-checklist)
21. [Glossary](#21-glossary)

---

## 1. Philosophy of VP Performance Modelling

> **VP performance modelling is not functional modelling.  
> It is quantitative, architectural, timing-accurate simulation.**

Functional models answer: *does the hardware produce the correct result?*  
Performance models answer: *how long does it take, why, and where is the bottleneck?*

A performance model that produces correct outputs but with zero or magic latency
is **wrong**. It is useless for architecture exploration, bandwidth sizing,
bottleneck analysis, and power estimation.

### The five pillars of correct performance modelling

| Pillar | What it means | What breaks without it |
|---|---|---|
| **Latency** | Every operation takes N cycles | All events collapsed to zero time |
| **Bandwidth** | Every channel carries B bytes/ns | Bus saturation invisible |
| **Arbitration** | Shared resources have contention | Multi-master conflicts hidden |
| **Queueing** | Bounded buffers cause backpressure | Pipeline stalls invisible |
| **Hierarchy** | Cache, memory, NoC each have different latency | All accesses appear identical |

### Core axioms

```
① Every delay annotation is += (cumulative), never = (overwrite).
② Every latency is a named sc_time constant, never a magic number.
③ Every bandwidth model derives delay from transfer size.
④ Every arbitration adds its grant latency before resource access.
⑤ Every queue has a declared hardware depth — overflow is a model error.
⑥ Performance statistics are collected deterministically — same run → same numbers.
⑦ AI testing requires injectable parameters and stable state dumps.
```

---

## 2. Determinism Rules

### Rule VP‑01 — Performance models MUST be deterministic

Every simulation run with identical stimulus must produce identical cycle counts,
latency distributions, and throughput numbers.

```cpp
// ❌ Forbidden — non-deterministic delay
delay += sc_time(rand() % 10, SC_NS);

// ✅ Correct — deterministic, parameter-driven
delay += sc_time(static_cast<double>(bytes) / bw_bytes_per_ns_, SC_NS);
```

### Rule VP‑02 — All performance parameters MUST be named constants or constructor-injected values

```cpp
// ❌ Forbidden — magic number, not traceable
delay += sc_time(42, SC_NS);

// ✅ Correct — named constant, traceable to hardware spec
constexpr sc_time DRAM_ROW_ACTIVATE_LATENCY(35, SC_NS);
delay += DRAM_ROW_ACTIVATE_LATENCY;
```

### Rule VP‑03 — No floating-point nondeterminism in timing calculations

```cpp
// ✅ Lock rounding mode at model construction
#include <cfenv>
fesetround(FE_TONEAREST);

// ✅ Use integer arithmetic where possible
const uint64_t cycles = (bytes + BUS_WIDTH_BYTES - 1) / BUS_WIDTH_BYTES;
delay += cycles * CLK_PERIOD;
```

### Rule VP‑04 — No non-deterministic containers in performance models

| Forbidden | Reason | Alternative |
|---|---|---|
| `std::unordered_map` | Hash-dependent iteration order | `std::map` |
| `std::unordered_set` | Hash-dependent order | `std::set` |
| `std::priority_queue` with equal-priority items and no tiebreak | Non-deterministic order | Add sequence number as tiebreak |

---

## 3. Latency Modelling Rules

### Rule VP‑05 — Latency MUST be decomposed into its hardware components

A single `delay +=` with a magic number hides the architecture. Decompose
every latency into its constituent parts:

```
Total latency = arb_latency
              + queue_latency
              + pipeline_latency
              + cache_latency   (hit or miss path)
              + memory_latency  (if miss)
              + noc_latency     (if remote)
              + bandwidth_latency
```

### Rule VP‑06 — Latency MUST be monotonic — always `+=`, never `-=`

```cpp
// ❌ Forbidden — negative latency contribution
delay -= sc_time(5, SC_NS);

// ✅ Correct — only additions
delay += sc_time(5, SC_NS);
```

### Rule VP‑07 — All latency constants MUST be named `sc_time` values with hardware-aligned names

```cpp
// ✅ Correct — names match hardware spec terminology
constexpr sc_time L1_HIT_LATENCY      ( 4, SC_NS);
constexpr sc_time L2_HIT_LATENCY      (12, SC_NS);
constexpr sc_time L3_HIT_LATENCY      (40, SC_NS);
constexpr sc_time DRAM_CAS_LATENCY    (14, SC_NS);
constexpr sc_time DRAM_RAS_LATENCY    (35, SC_NS);
constexpr sc_time NOC_HOP_LATENCY     ( 3, SC_NS);
constexpr sc_time BUS_ARB_LATENCY     ( 1, SC_NS);
constexpr sc_time CDC_SYNC_LATENCY    ( 2, SC_NS);
constexpr sc_time PIPELINE_FILL_CYCLES( 5, SC_NS);
```

### Rule VP‑08 — Read and write latencies MUST be modelled separately

Most memory technologies have asymmetric read/write timing.

```cpp
const sc_time access_lat = (pl.get_command() == tlm::TLM_READ_COMMAND)
                          ? SRAM_READ_LATENCY
                          : SRAM_WRITE_LATENCY;
delay += access_lat;
```

### Rule VP‑09 — First-access vs subsequent-access latency MUST be distinguished for pipelined buses

```cpp
// First word latency + streaming latency for burst
delay += FIRST_WORD_LATENCY;
delay += (burst_words - 1) * SUBSEQUENT_WORD_LATENCY;
```

---

## 4. Bandwidth Modelling Rules

### Rule VP‑10 — Bandwidth latency MUST be derived from actual transfer size

```cpp
// ❌ Forbidden — fixed latency ignores bytes transferred
delay += sc_time(10, SC_NS);

// ✅ Correct — proportional to transfer size
constexpr double BUS_BW_BYTES_PER_NS = 16.0;   // 16 GB/s
delay += sc_time(static_cast<double>(pl.get_data_length()) / BUS_BW_BYTES_PER_NS,
                 SC_NS);
```

### Rule VP‑11 — Bus width MUST be an explicit compile-time constant

```cpp
constexpr uint32_t AXI_BUS_WIDTH_BYTES = 64;   // 512-bit AXI4 bus
constexpr uint32_t DDR_BUS_WIDTH_BYTES = 8;    // 64-bit DDR4 data bus

// Cycles to transfer N bytes across a bus
inline uint32_t bus_cycles(uint32_t bytes, uint32_t bus_width) {
    return (bytes + bus_width - 1) / bus_width;
}
```

### Rule VP‑12 — Burst efficiency MUST be modelled separately from single-beat efficiency

A burst of 64 bytes on a 16-byte bus is 4 beats, but only 1 arbitration.
Model them independently:

```cpp
const uint32_t beats = bus_cycles(bytes, BUS_WIDTH_BYTES);
delay += BUS_ARB_LATENCY;                            // one arbitration
delay += beats * BUS_BEAT_LATENCY;                   // N beats of data
```

### Rule VP‑13 — Bandwidth must be peak, not sustained — model contention separately

Peak bandwidth is the raw bus capacity. Sustained bandwidth is reduced by:
- Multi-master contention (arbitration overhead)
- Protocol overhead (header beats, turnaround cycles)
- Bank conflicts (DRAM)

Model each source of reduction explicitly.

---

## 5. Arbitration Modelling Rules

### Rule VP‑14 — Every shared resource MUST have an explicit arbiter model

```cpp
class RoundRobinArbiter {
public:
    explicit RoundRobinArbiter(uint32_t n_masters, sc_time grant_latency)
        : n_(n_masters), grant_lat_(grant_latency), last_(0) {}

    sc_time request(uint32_t master_id) {
        // Compute wait cycles based on round-robin position
        const uint32_t wait_slots = (master_id >= last_)
            ? (master_id - last_)
            : (n_ - last_ + master_id);
        last_ = (master_id + 1) % n_;
        return wait_slots * grant_lat_;
    }

private:
    uint32_t n_;
    sc_time  grant_lat_;
    uint32_t last_;
};
```

### Rule VP‑15 — Arbitration policy MUST be one of the defined hardware policies

| Policy | Class to use | Use case |
|---|---|---|
| Round-robin | `RoundRobinArbiter` | Fair multi-master bus |
| Fixed priority | `PriorityArbiter` | Real-time + best-effort |
| Weighted fair | `WFQArbiter` | QoS-differentiated NoC |
| Time-division | `TDMArbiter` | Predictable WCET |

### Rule VP‑16 — Arbitration latency MUST be added before resource access latency

```cpp
// ✅ Correct order: arbitrate → access
delay += arbiter_.request(master_id_);
delay += SRAM_READ_LATENCY;
delay += sc_time(static_cast<double>(bytes) / BW_BYTES_PER_NS, SC_NS);
```

### Rule VP‑17 — Arbitration winner state MUST be deterministic

Round-robin position, priority table, and weight assignments must produce
the same winner sequence for the same input request pattern, every run.

---

## 6. Queueing Theory Rules

### Rule VP‑18 — Every pipeline stage is a bounded queue — model the bound

```cpp
constexpr std::size_t FETCH_QUEUE_DEPTH  = 16;
constexpr std::size_t DECODE_QUEUE_DEPTH =  8;
constexpr std::size_t LSQ_DEPTH          = 56;
constexpr std::size_t ROB_DEPTH          = 192;
constexpr std::size_t STORE_BUF_DEPTH    = 56;
```

### Rule VP‑19 — Queue backpressure MUST stall the upstream stage

```cpp
void issue_stage() {
    while (true) {
        wait(clk.posedge_event());
        if (decode_queue_.num_free() == 0) {
            stall_out_.write(true);   // ✅ explicit backpressure
            continue;
        }
        stall_out_.write(false);
        decode_queue_.write(fetch_packet_);
    }
}
```

### Rule VP‑20 — Queueing delay formula MUST reflect Little's Law when applicable

For steady-state average latency through a queue:

```
W = L / λ

W  = average wait time
L  = average number of items in system (queue depth at steady state)
λ  = arrival rate (transactions per ns)
```

Model this as:
```cpp
const double occupancy  = static_cast<double>(q_.size()) / Q_DEPTH;
const sc_time q_delay   = occupancy * MAX_QUEUE_WAIT;
delay += q_delay;
```

### Rule VP‑21 — Queue overflow MUST be a fatal model error, not a silent drop

```cpp
if (fifo_.num_free() == 0) {
    SC_REPORT_FATAL(name(), "queue overflow — model error: producer too fast");
}
fifo_.write(pkt);
```

---

## 7. Pipeline Modelling Rules

### Rule VP‑22 — Every pipeline stage MUST be a named struct

```cpp
struct FetchPacket  { uint64_t pc; bool valid = false; };
struct DecodePacket { uint64_t pc; uint32_t insn; bool valid = false; };
struct IssuePacket  { uint64_t pc; uint32_t insn; uint8_t rd; bool valid = false; };
```

### Rule VP‑23 — Pipeline depth MUST be a compile-time constant

```cpp
constexpr std::size_t PIPE_DEPTH = 5;
std::array<PipeStage, PIPE_DEPTH> pipe_{};
```

### Rule VP‑24 — Pipeline throughput = 1 / max_stage_latency (when no stalls)

Each stage must complete within one clock period. If any stage takes longer,
that stage is the throughput bottleneck. Document which stage is the critical
path.

```cpp
// ✅ Document critical path in comment
// Critical path: EXECUTE stage (ALU + forwarding) = 0.9 * CLK_PERIOD
constexpr sc_time EXECUTE_LATENCY(sc_time(0.9, SC_NS));
```

### Rule VP‑25 — Pipeline stalls MUST be counted and logged

```cpp
uint64_t stall_cycles_   = 0;
uint64_t total_cycles_   = 0;
uint64_t insns_retired_  = 0;

void commit() {
    ++total_cycles_;
    if (data_hazard_) {
        ++stall_cycles_;
        return;
    }
    ++insns_retired_;
}

double ipc() const {
    return total_cycles_ > 0
         ? static_cast<double>(insns_retired_) / total_cycles_
         : 0.0;
}
```

### Rule VP‑26 — Hazard detection MUST be explicit

```cpp
enum class HazardType { NONE, RAW, WAR, WAW, STRUCTURAL, CONTROL };

HazardType detect_hazard(const IssuePacket& a, const IssuePacket& b) {
    if (a.rd != 0 && a.rd == b.rs1) return HazardType::RAW;
    if (a.rd != 0 && a.rd == b.rs2) return HazardType::RAW;
    return HazardType::NONE;
}
```

---

## 8. Cache & Memory Hierarchy Modelling Rules

### Rule VP‑27 — Cache hierarchy levels MUST be individually modelled with distinct latencies

```cpp
struct CacheLevelConfig {
    uint32_t sets;
    uint32_t ways;
    uint32_t line_bytes;
    sc_time  hit_latency;
    sc_time  miss_penalty;   // latency to fill from next level
};

constexpr CacheLevelConfig L1_CFG  = {64,   4, 64, L1_HIT_LATENCY,  L2_HIT_LATENCY};
constexpr CacheLevelConfig L2_CFG  = {512,  8, 64, L2_HIT_LATENCY,  L3_HIT_LATENCY};
constexpr CacheLevelConfig L3_CFG  = {4096, 16, 64, L3_HIT_LATENCY, DRAM_CAS_LATENCY};
```

### Rule VP‑28 — Cache tag lookup MUST be a pure function

```cpp
// ✅ Pure, AI-testable
bool probe(uint64_t addr) const {
    const uint32_t set  = (addr >> offset_bits_) & set_mask_;
    const uint64_t tag  = addr >> (offset_bits_ + index_bits_);
    for (uint32_t w = 0; w < ways_; ++w) {
        if (tags_[set][w] == tag && valid_[set][w]) return true;
    }
    return false;
}
```

### Rule VP‑29 — Cache miss path MUST model fill latency from the correct next level

```cpp
sc_time access(uint64_t addr, sc_time& delay) {
    if (probe(addr)) {
        delay += hit_latency_;
        ++hit_count_;
        return hit_latency_;
    }
    // Miss — stall and fill from next level
    delay += miss_penalty_;
    fill(addr);
    ++miss_count_;
    return miss_penalty_;
}
```

### Rule VP‑30 — Write policy (write-back / write-through) MUST be explicitly selected

```cpp
enum class WritePolicy { WRITE_BACK, WRITE_THROUGH };
```

Write-through adds an additional write latency on every store. Write-back
generates dirty evictions with eviction latency.

### Rule VP‑31 — DRAM latency MUST decompose into row activation + CAS + transfer

```cpp
// DRAM open-page model
sc_time dram_latency(bool row_hit, uint32_t bytes) {
    const sc_time row_part = row_hit ? SC_ZERO_TIME : DRAM_RAS_LATENCY;
    const sc_time cas_part = DRAM_CAS_LATENCY;
    const sc_time bw_part  = sc_time(static_cast<double>(bytes) / DRAM_BW_BYTES_PER_NS, SC_NS);
    return row_part + cas_part + bw_part;
}
```

---

## 9. NoC & Interconnect Modelling Rules

### Rule VP‑32 — NoC topology MUST be declared as an explicit routing table

```cpp
enum class NocTopology { MESH_2D, TORUS_2D, RING, CROSSBAR, TREE };

struct NocConfig {
    NocTopology topology;
    uint32_t    rows;
    uint32_t    cols;
    sc_time     hop_latency;
    uint32_t    link_width_bytes;
    double      link_bw_bytes_per_ns;
};
```

### Rule VP‑33 — Hop count MUST be computed from source and destination node IDs

```cpp
// 2D mesh Manhattan distance routing
uint32_t hop_count(uint32_t src, uint32_t dst, uint32_t cols) {
    const uint32_t sx = src % cols,  sy = src / cols;
    const uint32_t dx = dst % cols,  dy = dst / cols;
    return std::abs(static_cast<int32_t>(sx) - static_cast<int32_t>(dx))
         + std::abs(static_cast<int32_t>(sy) - static_cast<int32_t>(dy));
}
```

### Rule VP‑34 — NoC congestion MUST be modelled as an occupancy factor

```cpp
// Congestion model: extra latency proportional to link utilisation
const double util  = link_busy_cycles_ / static_cast<double>(total_cycles_);
const sc_time cong = sc_time(util * NOC_HOP_LATENCY.to_double(), SC_NS);
delay += hops * (NOC_HOP_LATENCY + cong);
```

### Rule VP‑35 — NoC router arbitration MUST be modelled explicitly

Each router node is a shared resource. Packets from multiple input ports
contending for the same output port must queue and be arbitrated.

---

## 10. DMA & Burst Modelling Rules

### Rule VP‑36 — DMA engine MUST model: descriptor fetch → arbitration → burst → completion interrupt

```
DMA lifecycle
─────────────
① Fetch descriptor from memory (latency: DRAM_LATENCY)
② Request bus arbitration (latency: arb_delay)
③ Issue burst transaction (latency: burst_bytes / BW_BYTES_PER_NS)
④ Notify CPU via interrupt (latency: IRQ_DELIVERY_LATENCY)
```

### Rule VP‑37 — Burst size MUST be bounded by hardware limits

```cpp
constexpr uint32_t AXI_MAX_BURST_BYTES = 4096;   // AXI4 burst limit

if (transfer_bytes > AXI_MAX_BURST_BYTES) {
    SC_REPORT_FATAL(name(), "DMA burst exceeds AXI4 maximum");
}
```

### Rule VP‑38 — DMA throughput calculation MUST account for descriptor overhead

```cpp
// Total DMA time = descriptor_fetch + arb + burst + interrupt
const sc_time dma_total = DESCRIPTOR_FETCH_LATENCY
                        + arbiter_.request(dma_id_)
                        + sc_time(static_cast<double>(bytes) / DMA_BW_BYTES_PER_NS, SC_NS)
                        + IRQ_DELIVERY_LATENCY;
```

---

## 11. Clock Domain Crossing Modelling Rules

### Rule VP‑39 — CDC must be modelled as an explicit synchroniser FIFO module

Never pass a signal directly between two `sc_clock` domains. Use a named
`CdcFifo` module that models the synchroniser latency.

```cpp
SC_MODULE(CdcFifo) {
    sc_in<bool>   clk_src;
    sc_in<bool>   clk_dst;
    sc_in<Packet> data_in;
    sc_out<Packet> data_out;

    SC_CTOR(CdcFifo) {
        SC_THREAD(transfer_loop);
        sensitive << clk_dst.pos();
    }

private:
    static constexpr uint32_t SYNC_STAGES = 2;

    void transfer_loop() {
        while (true) {
            wait(clk_dst.posedge_event());
            // Model 2-FF synchroniser: 2 dst clock cycles latency
            wait(SYNC_STAGES - 1);
            data_out.write(data_in.read());
        }
    }
};
```

### Rule VP‑40 — CDC latency MUST reflect synchroniser depth and destination clock period

```cpp
const sc_time cdc_latency = SYNC_STAGES * DST_CLK_PERIOD;
delay += cdc_latency;
```

### Rule VP‑41 — Metastability window MUST NOT be modelled as randomness

Metastability is resolved by the synchroniser. Model it as a fixed worst-case
latency, not a probabilistic event.

---

## 12. TLM‑2.0 Integration Rules

### Rule VP‑42 — All VP performance contributions MUST flow through `b_transport` delay annotation

The `sc_time& delay` parameter is the single accumulation point for all
performance effects. Never model latency outside of it (e.g. via `wait()`
inside `b_transport`).

```cpp
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
    // ✅ All latency contributions here
    delay += arbiter_.request(id_);
    delay += cache_.access(pl.get_address());
    delay += sc_time(static_cast<double>(pl.get_data_length()) / BW_BYTES_PER_NS, SC_NS);
    pl.set_response_status(tlm::TLM_OK_RESPONSE);
}
```

### Rule VP‑43 — TLM timing annotation MUST be consistent with SystemC time advance

After `b_transport` returns, the initiator MUST call `wait(delay)` to advance
simulation time. Without this, the delay is computed but never consumed.

```cpp
// ✅ Initiator consumes the annotated delay
sc_time delay = SC_ZERO_TIME;
isock->b_transport(pl_, delay);
wait(delay);                     // advance simulation clock
```

---

## 13. SystemC Integration Rules

### Rule VP‑44 — Performance statistics MUST be updated inside the process owning the relevant state

```cpp
// ✅ Correct — statistics updated where state is authoritative
void commit_thread() {
    while (true) {
        wait(clk.posedge_event());
        if (rob_head_valid_) {
            ++insns_retired_;
        }
    }
}
```

### Rule VP‑45 — Performance counters MUST be read via `const` getters — never exposed as public members

```cpp
// ✅
uint64_t insns_retired() const { return insns_retired_; }
uint64_t stall_cycles()  const { return stall_cycles_; }
double   ipc()           const {
    return total_cycles_ > 0
         ? static_cast<double>(insns_retired_) / total_cycles_
         : 0.0;
}
```

### Rule VP‑46 — Performance reporting MUST happen in `end_of_simulation()`

```cpp
void end_of_simulation() override {
    std::ostringstream oss;
    oss << name()
        << " insns_retired=" << insns_retired_
        << " total_cycles="  << total_cycles_
        << " stall_cycles="  << stall_cycles_
        << " ipc="           << ipc()
        << " hit_rate="      << cache_.hit_rate();
    SC_REPORT_INFO(name(), oss.str().c_str());
}
```

---

## 14. Performance Measurement & Statistics

### Rule VP‑47 — Every model MUST collect at minimum: transaction count, total latency, and peak latency

```cpp
struct PerfCounters {
    uint64_t transactions   = 0;
    sc_time  total_latency  {SC_ZERO_TIME};
    sc_time  peak_latency   {SC_ZERO_TIME};

    void record(sc_time lat) {
        ++transactions;
        total_latency += lat;
        if (lat > peak_latency) peak_latency = lat;
    }

    sc_time avg_latency() const {
        return transactions > 0
             ? sc_time(total_latency.to_double() / transactions, SC_NS)
             : SC_ZERO_TIME;
    }
};
```

### Rule VP‑48 — Cache models MUST report hit rate

```cpp
double hit_rate() const {
    const uint64_t total = hit_count_ + miss_count_;
    return total > 0 ? static_cast<double>(hit_count_) / total : 0.0;
}
```

### Rule VP‑49 — Bus models MUST report utilisation

```cpp
double utilisation() const {
    return total_cycles_ > 0
         ? static_cast<double>(busy_cycles_) / total_cycles_
         : 0.0;
}
```

### Rule VP‑50 — Pipeline models MUST report IPC and stall breakdown

```cpp
void print_stats() const {
    SC_REPORT_INFO(name(),
        (std::ostringstream{}
            << "IPC=" << ipc()
            << " stall_pct=" << (100.0 * stall_cycles_ / total_cycles_)
            << "% raw_hazards=" << raw_hazard_count_
            << " struct_hazards=" << struct_hazard_count_).str().c_str());
}
```

---

## 15. AI‑Testability Hooks

### Rule VP‑51 — All performance model parameters MUST be injectable at construction time

```cpp
// ✅ AI can sweep: latency × bandwidth × arbitration policy
MemorySubsystem(sc_module_name name,
                CacheLevelConfig l1,
                CacheLevelConfig l2,
                sc_time          dram_latency,
                double           dram_bw_bytes_per_ns,
                ArbPolicy        policy);
```

### Rule VP‑52 — Every model MUST expose `dump_state()` and `dump_stats()`

```cpp
std::string dump_state() const {
    std::ostringstream oss;
    oss << name() << "{"
        << " pending_reqs=" << pending_
        << " queue_depth="  << q_.size()
        << "}";
    return oss.str();
}

std::string dump_stats() const {
    std::ostringstream oss;
    oss << name() << "{"
        << " txns="     << perf_.transactions
        << " avg_lat="  << perf_.avg_latency()
        << " peak_lat=" << perf_.peak_latency
        << " hit_rate=" << cache_.hit_rate()
        << " util="     << bus_.utilisation()
        << "}";
    return oss.str();
}
```

### Rule VP‑53 — Log format MUST be key=value for machine parseability

```cpp
// ✅ AI harness can regex-extract individual fields
oss << "op=READ"
    << " addr=0x"   << std::hex << addr
    << " bytes="    << std::dec << bytes
    << " lat_ns="   << lat.to_double()
    << " hit="      << (hit ? "true" : "false");
```

### Rule VP‑54 — Stimulus must be injectable without modifying module internals

Provide a typed `Stimulus` struct and an `apply_stimulus()` method:

```cpp
struct MemStimulus {
    tlm::tlm_command cmd;
    uint64_t         addr;
    uint32_t         bytes;
};

void apply_stimulus(const MemStimulus& s) {
    pl_.set_command(s.cmd);
    pl_.set_address(s.addr);
    pl_.set_data_length(s.bytes);
    pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
    sc_time delay = SC_ZERO_TIME;
    isock->b_transport(pl_, delay);
    wait(delay);
}
```

---

## 16. Hardware Diagrams

### 16.1 Full memory hierarchy latency stack

```
  CPU Request
      │
      ▼
  ┌─────────┐  hit (4 ns)
  │   L1$   │────────────────────────────────────────────▶ Response
  └────┬────┘
       │ miss
       ▼
  ┌─────────┐  hit (12 ns)
  │   L2$   │────────────────────────────────────────────▶ Response
  └────┬────┘
       │ miss
       ▼
  ┌─────────┐  hit (40 ns)
  │   L3$   │────────────────────────────────────────────▶ Response
  └────┬────┘
       │ miss
       ▼
  ┌─────────────────────────────┐
  │  Memory Controller          │  RAS(35ns) + CAS(14ns) + BW
  │  DRAM Row Activate + CAS    │────────────────────────────▶ Response
  └─────────────────────────────┘
```

### 16.2 TLM delay accumulation — memory subsystem

```
  b_transport called with delay = 0 ns

  ① += BUS_ARB_LATENCY          →  delay =  1 ns
  ② += L1 probe (miss)          →  delay =  5 ns   (1 + 4)
  ③ += L2 probe (miss)          →  delay = 17 ns   (5 + 12)
  ④ += DRAM_RAS_LATENCY         →  delay = 52 ns   (17 + 35)
  ⑤ += DRAM_CAS_LATENCY         →  delay = 66 ns   (52 + 14)
  ⑥ += BW (64B / 8 GB/s)        →  delay = 74 ns   (66 + 8)

  b_transport returns; initiator calls wait(74 ns)
```

### 16.3 5-stage pipeline with stall

```
  Cycle  │  1      2      3      4      5      6      7
  ───────┼──────────────────────────────────────────────
  Fetch  │  I1     I2     I3     ─(s)─  I4     I5     I6
  Decode │         I1     I2     ─(s)─  I3     I4     I5
  Issue  │                I1     ─(s)─  I2     I3     I4
  Exec   │                       I1     ─(s)─  I2     I3
  WB     │                              I1     ─(s)─  I2

  (s) = RAW stall — I1 result not yet written when I2 reads it
  Stall inserts a bubble in cycle 4 — all stages hold or flush.
```

### 16.4 Round-robin arbiter timing

```
  Cycle:   1    2    3    4    5    6    7
           │    │    │    │    │    │    │
  M0 req:  ████      ████      ████
  M1 req:       ████      ████      ████
  M2 req:  ████ ████           ████

  Grant:   M0   M1   M2   M1   M0   M1   M2
           ▲         ▲              ▲
           first     second         third M0 grant
           M0 wait=0 M0 wait=2 cycles (RR position)
```

### 16.5 2D mesh NoC routing (4×4)

```
  (0,0)──(1,0)──(2,0)──(3,0)
    │      │      │      │
  (0,1)──(1,1)──(2,1)──(3,1)
    │      │      │      │
  (0,2)──(1,2)──(2,2)──(3,2)
    │      │      │      │
  (0,3)──(1,3)──(2,3)──(3,3)

  Route (0,0) → (3,2):
    X hops: 3  (right along row 0)
    Y hops: 2  (down to row 2)
    Total:  5 hops × NOC_HOP_LATENCY (3 ns) = 15 ns
```

### 16.6 DMA engine lifecycle diagram

```
  CPU writes descriptor
        │
        ▼
  ┌─────────────┐  ① Descriptor fetch (DRAM_LATENCY)
  │  DMA Engine │──────────────────────────────────────┐
  └──────┬──────┘                                       │
         │ ② Arbitration request (arb_delay)             │
         ▼                                               │
  ┌─────────────┐  ③ Burst transfer (bytes / BW_BPS)   │
  │  Bus Fabric │──────────────────────────────────────▶│
  └──────┬──────┘                                       │
         │ ④ Completion interrupt (IRQ_LATENCY)          │
         ▼                                               ▼
       CPU                                          Memory
```

---

## 17. Complete Examples

### 17.1 Complete cache model

```cpp
// simple_cache.h
#pragma once
#include <systemc>
#include <tlm>
#include "tlm_utils/simple_target_socket.h"
#include <array>
#include <vector>
#include <cstdint>
#include <sstream>

constexpr uint32_t C_SETS       = 64;
constexpr uint32_t C_WAYS       = 4;
constexpr uint32_t C_LINE_BYTES = 64;
constexpr sc_time  C_HIT_LAT   (4,  SC_NS);
constexpr sc_time  C_MISS_PEN  (80, SC_NS);   // fetches from next level

SC_MODULE(SimpleCache) {
    tlm_utils::simple_target_socket<SimpleCache> tsock{"tsock"};
    tlm_utils::simple_initiator_socket<SimpleCache> next_level{"next_level"};

    SC_CTOR(SimpleCache) {
        tsock.register_b_transport(this, &SimpleCache::b_transport);
        tags_.assign(C_SETS, std::vector<uint64_t>(C_WAYS, INVALID_TAG));
        valid_.assign(C_SETS, std::vector<bool>(C_WAYS, false));
        lru_.assign(C_SETS, std::vector<uint32_t>(C_WAYS, 0));
    }

    std::string dump_stats() const {
        std::ostringstream oss;
        oss << name()
            << " hits=" << hits_ << " misses=" << misses_
            << " hit_rate=" << hit_rate();
        return oss.str();
    }

    double hit_rate() const {
        const uint64_t t = hits_ + misses_;
        return t > 0 ? static_cast<double>(hits_) / t : 0.0;
    }

private:
    static constexpr uint64_t INVALID_TAG = ~0ULL;
    std::vector<std::vector<uint64_t>> tags_;
    std::vector<std::vector<bool>>     valid_;
    std::vector<std::vector<uint32_t>> lru_;
    uint64_t hits_   = 0;
    uint64_t misses_ = 0;

    uint32_t set_index(uint64_t addr) const {
        return (addr / C_LINE_BYTES) % C_SETS;
    }
    uint64_t tag_of(uint64_t addr) const {
        return addr / (C_LINE_BYTES * C_SETS);
    }
    uint64_t align(uint64_t addr) const {
        return addr & ~static_cast<uint64_t>(C_LINE_BYTES - 1);
    }

    bool probe(uint64_t addr) const {
        const uint32_t s = set_index(addr);
        const uint64_t t = tag_of(addr);
        for (uint32_t w = 0; w < C_WAYS; ++w) {
            if (valid_[s][w] && tags_[s][w] == t) return true;
        }
        return false;
    }

    void install(uint64_t addr) {
        const uint32_t s = set_index(addr);
        const uint64_t t = tag_of(addr);
        // LRU eviction: find way with max lru counter
        uint32_t evict = 0;
        for (uint32_t w = 1; w < C_WAYS; ++w)
            if (lru_[s][w] > lru_[s][evict]) evict = w;
        tags_[s][evict]  = t;
        valid_[s][evict] = true;
        // Update LRU
        for (uint32_t w = 0; w < C_WAYS; ++w) ++lru_[s][w];
        lru_[s][evict] = 0;
    }

    void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
        const uint64_t addr  = pl.get_address();
        const uint32_t bytes = pl.get_data_length();

        if (probe(addr)) {
            delay += C_HIT_LAT;
            ++hits_;
        } else {
            // Miss — fill from next level
            delay += C_MISS_PEN;
            tlm::tlm_generic_payload fill_pl;
            uint8_t fill_buf[C_LINE_BYTES] = {};
            fill_pl.set_command(tlm::TLM_READ_COMMAND);
            fill_pl.set_address(align(addr));
            fill_pl.set_data_ptr(fill_buf);
            fill_pl.set_data_length(C_LINE_BYTES);
            fill_pl.set_byte_enable_ptr(nullptr);
            fill_pl.set_streaming_width(C_LINE_BYTES);
            fill_pl.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);
            next_level->b_transport(fill_pl, delay);
            install(addr);
            ++misses_;
        }

        // Forward to underlying memory (next_level handles actual data)
        pl.set_response_status(tlm::TLM_OK_RESPONSE);
        (void)bytes;
    }
};
```

### 17.2 Complete performance counter module

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

    void record_txn(tlm::tlm_command cmd, sc_time lat) {
        ++transactions;
        if (cmd == tlm::TLM_READ_COMMAND) ++read_txns;
        else                              ++write_txns;
        total_latency += lat;
        if (lat > peak_latency) peak_latency = lat;
    }

    void tick(bool busy) {
        ++total_cycles;
        if (busy) ++busy_cycles;
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
        oss << "txns="     << transactions
            << " reads="   << read_txns
            << " writes="  << write_txns
            << " avg_lat=" << avg_latency().to_double() << "ns"
            << " peak_lat="<< peak_latency.to_double()  << "ns"
            << " util="    << (utilisation() * 100.0)   << "%";
        return oss.str();
    }
};
```

---

## 18. VP Anti‑Patterns

| Anti‑Pattern | Consequence | Correct Approach |
|---|---|---|
| `delay = 0` everywhere | All latency collapsed — invalid perf model | Annotate every transaction |
| `delay = X` (overwrite) | Upstream latency lost | Always `delay +=` |
| Magic number latencies | Untraceable, unmaintainable | Named `sc_time` constants |
| Random delays or misses | Non-deterministic simulation | Fixed, parameter-driven values |
| No arbitration model | Multi-master contention invisible | Explicit arbiter per shared resource |
| Unbounded queues | Backpressure invisible | Bounded queues with stall/fatal on overflow |
| All cache levels same latency | Hierarchy invisible | Distinct `sc_time` per level |
| DRAM as single fixed latency | Row/bank effects invisible | RAS + CAS + BW decomposition |
| No performance counters | Can't measure bottlenecks | Collect txns, latency, hit rate, utilisation |
| `std::unordered_map` for routing | Non-deterministic traversal | `std::map` or explicit decode chain |
| Stats reported mid-simulation | Partial data — misleading | Report only in `end_of_simulation()` |
| `wait()` inside `b_transport` | Mixes blocking and annotated-delay models | All latency via `delay +=`, never `wait()` inside transport |
| Missing `wait(delay)` after `b_transport` | Delay computed but time never advances | Initiator MUST call `wait(delay)` after transport call |

---

## 19. VP Templates Reference

### 19.1 Full b\_transport performance chain

```cpp
void b_transport(tlm::tlm_generic_payload& pl, sc_time& delay) {
    const uint64_t addr  = pl.get_address();
    const uint32_t bytes = pl.get_data_length();

    // ① Arbitration
    delay += arbiter_.request(id_);

    // ② Cache lookup
    if (!cache_.probe(addr)) {
        // ③ DRAM: RAS + CAS + bandwidth
        delay += DRAM_RAS_LATENCY;
        delay += DRAM_CAS_LATENCY;
        delay += sc_time(static_cast<double>(C_LINE_BYTES) / DRAM_BW_BYTES_PER_NS, SC_NS);
        cache_.install(addr);
        ++miss_count_;
    } else {
        delay += CACHE_HIT_LATENCY;
        ++hit_count_;
    }

    // ④ Bus bandwidth for requested transfer
    delay += sc_time(static_cast<double>(bytes) / BUS_BW_BYTES_PER_NS, SC_NS);

    // ⑤ Data transfer
    do_transfer(pl);

    // ⑥ Record statistics
    perf_.record_txn(pl.get_command(),
                     delay - initial_delay_);   // delta since entry

    pl.set_response_status(tlm::TLM_OK_RESPONSE);
}
```

### 19.2 Initiator transaction + time advance

```cpp
void issue_read(uint64_t addr, uint32_t bytes) {
    pl_.set_command(tlm::TLM_READ_COMMAND);
    pl_.set_address(addr);
    pl_.set_data_ptr(buf_.data());
    pl_.set_data_length(bytes);
    pl_.set_byte_enable_ptr(nullptr);
    pl_.set_streaming_width(bytes);
    pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);

    sc_time delay = SC_ZERO_TIME;
    isock->b_transport(pl_, delay);

    sc_assert(pl_.get_response_status() == tlm::TLM_OK_RESPONSE);
    wait(delay);   // ✅ advance simulation time by accumulated latency
}
```

### 19.3 Pipeline stage with backpressure

```cpp
void execute_stage() {
    while (true) {
        wait(clk.posedge_event());

        // Check output queue space
        if (wb_queue_.num_free() == 0) {
            ++stall_cycles_;
            stall_out_.write(true);
            continue;
        }
        stall_out_.write(false);

        if (!issue_queue_.num_available()) continue;

        IssuePacket pkt = issue_queue_.read();
        // ... execute ...
        wb_queue_.write(result);
        ++insns_executed_;
    }
}
```

---

## 20. Checklist

Use in every VP performance model code review.

### Latency
- [ ] Every `b_transport` uses `delay +=` (not `delay =`)
- [ ] All latency values are named `sc_time` constants
- [ ] Read and write latencies are separate constants
- [ ] DRAM latency decomposed: RAS + CAS + bandwidth

### Bandwidth
- [ ] Bandwidth delay derived from `data_length / bw_bytes_per_ns`
- [ ] Bus width declared as compile-time constant
- [ ] Burst treated as single arbitration + N beat latencies

### Arbitration
- [ ] Every shared resource has an explicit arbiter instance
- [ ] Arbitration latency added before access latency
- [ ] Arbiter policy (RR / priority / WFQ) explicitly named

### Queueing
- [ ] Every queue has a declared hardware depth constant
- [ ] Queue overflow triggers `SC_REPORT_FATAL` (not silent drop)
- [ ] Backpressure propagates to upstream stage via stall signal

### Cache
- [ ] Each hierarchy level has distinct latency constants
- [ ] Tag lookup is a pure function
- [ ] Miss path fills from next level with correct latency
- [ ] Hit rate counter present

### Performance counters
- [ ] Transaction count, total latency, peak latency collected
- [ ] Bus utilisation tracked
- [ ] IPC and stall breakdown tracked (pipeline models)
- [ ] Stats reported only in `end_of_simulation()`

### TLM integration
- [ ] Initiator calls `wait(delay)` after every `b_transport`
- [ ] No `wait()` inside `b_transport` body
- [ ] Response status checked after every `b_transport` call

### AI‑testability
- [ ] All parameters injectable at construction
- [ ] `dump_state()` and `dump_stats()` present
- [ ] Log format is key=value

---

## 21. Glossary

| Term | Definition |
|---|---|
| **Latency** | Time from request issue to response available |
| **Bandwidth** | Maximum data rate of a channel (bytes/ns) |
| **Throughput** | Actual sustained data rate under load |
| **Arbitration** | Process of granting a shared resource to one of N requesters |
| **Backpressure** | Signal from a downstream stage to stall an upstream stage |
| **IPC** | Instructions Per Cycle — pipeline throughput metric |
| **CPI** | Cycles Per Instruction — inverse of IPC |
| **RAW hazard** | Read-After-Write data dependency causing a pipeline stall |
| **Cache hit** | Requested data found in cache — served at hit_latency |
| **Cache miss** | Data not in cache — must fetch from next level |
| **Miss penalty** | Additional latency incurred on a cache miss |
| **RAS latency** | Row Address Strobe — DRAM row activation time |
| **CAS latency** | Column Address Strobe — DRAM column access time |
| **NoC** | Network‑on‑Chip — on-die packet-switched interconnect |
| **Hop** | One router traversal in a NoC path |
| **DMA** | Direct Memory Access — hardware block that moves data without CPU |
| **CDC** | Clock Domain Crossing — signal transition between two clock domains |
| **Metastability** | Transient undefined state when a flip-flop samples a changing input |
| **Little's Law** | L = λW — queue length = arrival rate × wait time |
| **VP** | Virtual Prototype — full-system TLM simulation |
| **TLM** | Transaction Level Modelling |
| **WCET** | Worst-Case Execution Time |
