# Hardware Architecture Diagrams for SystemC, TLM‑2.0, VP Performance Modelling & AI‑Testable Simulation

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for SystemC/VP/Performance‑Modelling Engineers (<5‑Year)  
**Prerequisites:** `01_Core_Philosophy.md` through `07_AI_Testing_Hooks.md`

---

## Table of Contents

1. [Philosophy of Hardware Diagrams](#1-philosophy-of-hardware-diagrams)
2. [Pipeline Diagrams](#2-pipeline-diagrams)
3. [FIFO & Queue Diagrams](#3-fifo--queue-diagrams)
4. [Cache Hierarchy Diagrams](#4-cache-hierarchy-diagrams)
5. [Memory Controller & DRAM Diagrams](#5-memory-controller--dram-diagrams)
6. [MMU & Address Decode Diagrams](#6-mmu--address-decode-diagrams)
7. [NoC & Interconnect Diagrams](#7-noc--interconnect-diagrams)
8. [Bus & Arbitration Diagrams](#8-bus--arbitration-diagrams)
9. [DMA Engine Diagrams](#9-dma-engine-diagrams)
10. [Clock Domain Crossing Diagrams](#10-clock-domain-crossing-diagrams)
11. [Register File Diagrams](#11-register-file-diagrams)
12. [TLM‑2.0 Mapping Diagrams](#12-tlm20-mapping-diagrams)
13. [VP Performance Modelling Diagrams](#13-vp-performance-modelling-diagrams)
14. [AI‑Testability Instrumentation Diagrams](#14-aitestability-instrumentation-diagrams)
15. [Diagram Drawing Rules](#15-diagram-drawing-rules)
16. [Anti‑Patterns](#16-anti-patterns)
17. [Glossary](#17-glossary)

---

## 1. Philosophy of Hardware Diagrams

> **A diagram that cannot be traced to code is documentation debt.  
> Every box must map to a module. Every arrow must map to a signal or transaction.**

### Rules for all diagrams

| Rule | Requirement |
|---|---|
| **DIAG‑01** | Every box maps to a named `SC_MODULE`, struct, or class |
| **DIAG‑02** | Every arrow maps to an `sc_signal`, `sc_fifo`, or TLM socket |
| **DIAG‑03** | Every latency annotation maps to a named `sc_time` constant |
| **DIAG‑04** | Every queue depth maps to a named `constexpr std::size_t` |
| **DIAG‑05** | Diagrams must be reproducible — no random layouts |
| **DIAG‑06** | AI observation points must be marked with ① ② ③ |

---

## 2. Pipeline Diagrams

### 2.1 Basic 5-stage in-order pipeline

```
  Cycle  │  1      2      3      4      5      6      7      8
  ───────┼──────────────────────────────────────────────────────
  Fetch  │  [I1]   [I2]   [I3]   [I4]   [I5]   [I6]   [I7]   [I8]
  Decode │          [I1]   [I2]   [I3]   [I4]   [I5]   [I6]   [I7]
  Issue  │                 [I1]   [I2]   [I3]   [I4]   [I5]   [I6]
  Execute│                        [I1]   [I2]   [I3]   [I4]   [I5]
  WB     │                               [I1]   [I2]   [I3]   [I4]

  Pipeline fill latency = 5 cycles (PIPE_DEPTH × CLK_PERIOD)
  Steady-state throughput = 1 instruction per cycle (IPC = 1.0)
```

**SystemC mapping:**
```cpp
// Stage registers — one per boundary
sc_signal<FetchPacket>   f2d{"f2d"};
sc_signal<DecodePacket>  d2i{"d2i"};
sc_signal<IssuePacket>   i2e{"i2e"};
sc_signal<ExecPacket>    e2w{"e2w"};

// Latency constant
constexpr sc_time PIPELINE_FILL = 5 * CLK_PERIOD;
```

---

### 2.2 Pipeline with RAW stall

```
  Cycle  │  1      2      3      4(s)   5      6      7
  ───────┼───────────────────────────────────────────────
  Fetch  │  [I1]   [I2]   [I3]   ──s──  [I4]   [I5]   [I6]
  Decode │          [I1]   [I2]   ──s──  [I3]   [I4]   [I5]
  Issue  │                 [I1]   ──s──  [I2]   [I3]   [I4]
  Execute│                        [I1]   ──s──  [I2]   [I3]
  WB     │                               [I1]   ──s──  [I2]

  (s) = bubble inserted by RAW hazard: I2 reads r1 before I1 writes r1
  Cost = 1 stall cycle per RAW hazard
```

**VP performance integration:**
```cpp
if (scoreboard_.has_raw_hazard(insn.rs1) || scoreboard_.has_raw_hazard(insn.rs2)) {
    ++stall_cycles_;
    delay += CLK_PERIOD;
    return;
}
```

---

### 2.3 Superscalar pipeline (2-wide issue)

```
  ┌──────────┐   2 instr/cycle   ┌──────────┐
  │  Fetch   │──────────────────▶│  Decode  │
  │ (2-wide) │                   │ (2-wide) │
  └──────────┘                   └────┬─────┘
                                       │ 2 instr
                                  ┌────▼─────┐
                                  │  Issue   │  OoO window: ROB_DEPTH entries
                                  │  (OoO)   │
                                  └────┬─────┘
                                       │
                      ┌────────────────┼────────────────┐
                      ▼                ▼                 ▼
                 ┌─────────┐     ┌─────────┐      ┌─────────┐
                 │  Int EU │     │  FP EU  │      │  Mem EU │
                 └────┬────┘     └────┬────┘      └────┬────┘
                      └──────────────┴──────────────────┘
                                      │
                                 ┌────▼─────┐
                                 │  Commit  │  In-order, ROB head
                                 └──────────┘
```

---

### 2.4 Pipeline inter-stage FIFO depths

```
  Stage boundary      FIFO name        Hardware depth   sc_fifo depth
  ──────────────────  ───────────────  ───────────────  ─────────────
  Fetch → Decode      fetch_queue_     16 instructions  16
  Decode → Issue      decode_queue_    8 instructions   8
  Issue → Execute     issue_queue_     4 micro-ops      4
  Execute → WB        exec_queue_      4 results        4
  WB → Commit (ROB)   rob_             192 entries      192
```

---

## 3. FIFO & Queue Diagrams

### 3.1 Bounded ring buffer

```
  Index:  0    1    2    3    4    5    6    7
          ┌────┬────┬────┬────┬────┬────┬────┬────┐
  Data:   │    │    │ D2 │ D3 │ D4 │    │    │    │
          └────┴────┴────┴────┴────┴────┴────┴────┘
                     ▲                   ▲
                    head               tail
                  (next pop)         (next push)

  DEPTH = 8 (power of 2 — index = ptr & MASK)
  Occupancy = (tail - head + DEPTH) % DEPTH = 3
  Full  = occupancy == DEPTH - 1
  Empty = head == tail
```

---

### 3.2 FIFO with backpressure

```
  Producer (Fetch)                        Consumer (Decode)
  ────────────────                        ─────────────────
  push(pkt) ──────────▶ ┌─────────────┐ ──────────▶ pop(pkt)
                         │ FIFO depth  │
                         │    = 16     │
                         └─────────────┘
                               │
                         full? │
                               ▼
                         stall_out.write(true) ──▶ upstream stall

  VP: if (fifo_.num_free() == 0) { ++stall_cycles_; delay += CLK_PERIOD; }
```

---

### 3.3 sc_fifo vs ring buffer selection guide

```
  Use sc_fifo when:                Use RingBuffer<T,N> when:
  ─────────────────                ──────────────────────────
  Crossing SC_THREAD boundaries    Within a single SC_METHOD
  Blocking read/write needed       Non-blocking, always polled
  SystemC event sync needed        Pure data structure, no kernel
  Inter-module communication       Intra-module pipeline register
```

---

## 4. Cache Hierarchy Diagrams

### 4.1 Three-level cache hierarchy with latencies

```
  CPU Core
     │
     ▼
  ┌─────────────────────────────────────────┐
  │  L1 I-Cache (32 KB, 8-way, 64B lines)  │  HIT:  4 ns
  │  L1 D-Cache (48 KB, 12-way, 64B lines) │  MISS: → L2
  └──────────────────┬──────────────────────┘
                     │ miss
                     ▼
  ┌─────────────────────────────────────────┐
  │  L2 Unified (512 KB, 8-way, 64B lines) │  HIT: 12 ns
  └──────────────────┬──────────────────────┘
                     │ miss
                     ▼
  ┌─────────────────────────────────────────┐
  │  L3 Shared (8 MB, 16-way, 64B lines)   │  HIT: 40 ns
  └──────────────────┬──────────────────────┘
                     │ miss
                     ▼
  ┌─────────────────────────────────────────┐
  │  DRAM (DDR5)                            │  RAS(35) + CAS(14) + BW
  └─────────────────────────────────────────┘
```

---

### 4.2 Cache set-associative structure

```
  Address: [ TAG (42 bits) | SET INDEX (6 bits) | OFFSET (6 bits) ]
                                     │
                              set = addr[11:6]
                                     │
                                     ▼
  Set 0:  ┌──────┬──────┬──────┬──────┐
          │ way0 │ way1 │ way2 │ way3 │  ← 4-way set
          └──────┴──────┴──────┴──────┘
              ▲
         tag compare × 4 ways (parallel)
         hit = any(tags[set][w] == tag && valid[set][w])
```

---

### 4.3 Cache miss fill path

```
  L1 miss
     │
     ├──▶ L2 probe ──▶ L2 hit ──▶ fill L1 line (64B) ──▶ +12 ns
     │
     └──▶ L2 miss ──▶ L3 probe ──▶ L3 hit ──▶ fill L2+L1 ──▶ +40 ns
                            │
                            └──▶ L3 miss ──▶ DRAM fetch ──▶ +49–130 ns
                                            (RAS+CAS+BW for 64B)
```

---

## 5. Memory Controller & DRAM Diagrams

### 5.1 DRAM open-page timing

```
  Bank state: IDLE → ACT → READ/WRITE → PRE → IDLE

  ──tRAS──────────────────────────────────────────────────────▶
  ──tRCD────────────────────────────▶
  │         │                       │
  ACT       │     ──tCL──────────▶  PRE
            │     │              │
            │     READ           data valid
            │
            tRCD = row-to-column delay (35 ns typical DDR5)
            tCL  = CAS latency        (14 ns typical DDR5)
            tRP  = row precharge      (15 ns typical DDR5)

  Open-page hit:  0    + tCL  + BW  =  14 ns + BW
  Open-page miss: tRCD + tCL  + BW  =  49 ns + BW
  Closed-page:    tRP  + tRCD + tCL + BW = 64 ns + BW
```

### 5.2 Memory controller request queue

```
  Core 0 ──▶ ┐
  Core 1 ──▶ ├──▶ ┌────────────────────┐ ──▶ DRAM Bank 0
  Core 2 ──▶ ┤    │  MC Request Queue  │ ──▶ DRAM Bank 1
  Core 3 ──▶ ┘    │  depth = 32        │ ──▶ DRAM Bank 2
                  │  FR-FCFS scheduler │ ──▶ DRAM Bank 3
                  └────────────────────┘
                  Arbitration: FR-FCFS (First-Ready, First-Come-First-Served)
```

---

## 6. MMU & Address Decode Diagrams

### 6.1 Virtual-to-physical address translation

```
  Virtual Address [63:0]
         │
         ▼
  ┌──────────────┐
  │     TLB      │  HIT (1 cycle) → Physical Address
  │  (64 entries)│
  └──────┬───────┘
         │ MISS
         ▼
  ┌──────────────┐
  │  Page Table  │  Walk: 4 levels × DRAM_LATENCY = ~316 ns
  │  Walker (HW) │
  └──────┬───────┘
         │
         ▼
  Physical Address → Cache hierarchy
```

### 6.2 MPU region tree (sorted vector, binary search)

```
              [0x0000_0000 – 0xFFFF_FFFF]
             /                            \
  [0x0000_0000–0x0FFF_FFFF]    [0x1000_0000–0xFFFF_FFFF]
   Boot ROM (RO, no-exec)       /                       \
                    [0x1000–0x4FFF]           [0x5000–0xFFFF_FFFF]
                     SRAM (RW)                 /              \
                                  [0x5000–0xBFFF]    [0xC000–0xFFFF_FFFF]
                                   Peripheral (RW)    DRAM (RW, exec)

  Lookup: binary search on sorted region list → O(log N)
  VP:     delay += REGION_LOOKUP_LATENCY;
```

### 6.3 Address decode trie (bus fabric)

```
  Upper 4 bits of address → slave select

  Root
  ├── 0b0000 → Slave 0 (SRAM,      0x0000_0000)
  ├── 0b0001 → Slave 1 (Flash,     0x1000_0000)
  ├── 0b0010 → Slave 2 (Peripheral,0x2000_0000)
  ├── 0b0011 → Slave 3 (PCIe MMIO, 0x3000_0000)
  └── 0b1xxx → Slave 4 (DRAM,      0x8000_0000–0xFFFF_FFFF)

  Router strips upper bits, forwards offset to selected slave.
```

---

## 7. NoC & Interconnect Diagrams

### 7.1 2D mesh NoC (4×4)

```
  (0,0)──(1,0)──(2,0)──(3,0)
    │      │      │      │
  (0,1)──(1,1)──(2,1)──(3,1)
    │      │      │      │
  (0,2)──(1,2)──(2,2)──(3,2)
    │      │      │      │
  (0,3)──(1,3)──(2,3)──(3,3)

  Routing: XY dimension-ordered (deterministic, deadlock-free)
  Hop latency: NOC_HOP_LATENCY = 3 ns
  Max hops (corner-to-corner): (4-1) + (4-1) = 6 hops = 18 ns
  Link BW: NOC_LINK_BW = 16 bytes/ns (128 Gbps)
```

### 7.2 Ring NoC

```
  R0 ──▶ R1 ──▶ R2 ──▶ R3
  ▲                       │
  └───────────────────────┘

  Unidirectional ring: max hops = N-1
  Bidirectional ring:  max hops = N/2
  VP: delay += min(clockwise_hops, counter_hops) * NOC_HOP_LATENCY;
```

### 7.3 Crossbar interconnect

```
  Master 0 ──┐
  Master 1 ──┤                ┌──▶ Slave 0
  Master 2 ──┼──▶ Crossbar ──┼──▶ Slave 1
  Master 3 ──┤  (N×M switch) └──▶ Slave 2
  Master 4 ──┘

  Non-blocking: any master to any slave simultaneously (no conflict at switch)
  Blocking:     same slave from two masters → arbitration needed
  Arbitration latency: BUS_ARB_LATENCY = 1 ns
```

---

## 8. Bus & Arbitration Diagrams

### 8.1 Round-robin arbitration timing

```
  Cycle:   1    2    3    4    5    6    7    8    9
           │    │    │    │    │    │    │    │    │
  M0 req:  ████      ████           ████
  M1 req:       ████      ████ ████      ████
  M2 req:  ████ ████      ████      ████      ████

  Grant:   M0   M1   M0   M1   M2   M0   M1   M2   ...
           (RR cycles through requesting masters in order)

  Wait for M0 (cycle 5): M1 and M2 served first → wait = 2 cycles
  delay += 2 * CLK_PERIOD;
```

### 8.2 Priority arbitration

```
  Priority:  HIGH     MEDIUM     LOW
  Masters:   M0  ──▶  M1    ──▶  M2
              │         │          │
              └─────────┴──────────┘
                        │
                    Arbiter
                        │ grants M0 first if requesting
                        ▼
                    Shared Bus

  M0 always wins if active → M2 may starve under high M0 load
  VP: delay += (master_id * PRIORITY_PENALTY);
```

### 8.3 TDMA arbitration slot map

```
  Frame (8 slots × 1 ns each = 8 ns frame period):

  ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
  │ M0   │ M1   │ M2   │ M3   │ M0   │ M1   │ M2   │ M3   │
  └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘
   slot0  slot1  slot2  slot3  slot4  slot5  slot6  slot7

  M0 guaranteed access every 2 slots (2 ns worst-case wait)
  Predictable WCET — suitable for real-time systems
```

---

## 9. DMA Engine Diagrams

### 9.1 DMA lifecycle

```
  CPU writes descriptor to DMA register
           │
           ▼
  ┌─────────────────┐
  │  Descriptor     │  ① Fetch descriptor from DRAM
  │  Fetch (DRAM)   │     delay += DRAM_LATENCY  (≈80 ns)
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  Arbitration    │  ② Request bus grant
  │  (RR arbiter)   │     delay += arb_delay
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  Burst Transfer │  ③ Transfer bytes via AXI burst
  │  (AXI4)         │     delay += bytes / DMA_BW_BYTES_PER_NS
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  IRQ to CPU     │  ④ Raise completion interrupt
  │  (IRQ line)     │     delay += IRQ_DELIVERY_LATENCY  (≈2 ns)
  └─────────────────┘
```

### 9.2 DMA descriptor queue

```
  ┌────┬────┬────┬────┬────┬────┬────┬────┐
  │ D0 │ D1 │ D2 │ D3 │    │    │    │    │
  └────┴────┴────┴────┴────┴────┴────┴────┘
   ▲                   ▲
  head               tail
  (processing)       (next submit)

  DEPTH = 8 descriptors
  Full = fatal error — CPU must not submit more than 8 outstanding DMA ops
```

---

## 10. Clock Domain Crossing Diagrams

### 10.1 2-FF synchroniser

```
  Source domain (fast, 2 GHz)          Dest domain (slow, 1 GHz)
  ───────────────────────────          ─────────────────────────
  Signal ──▶ ┌────┐ ──▶ ┌────┐ ──▶  Safe output
             │ FF1│     │ FF2│
             └────┘     └────┘
              clk_src    clk_dst   clk_dst

  Latency = 2 × DST_CLK_PERIOD = 2 ns (at 1 GHz destination)
  Metastability resolved by FF2 — modelled as fixed latency, not random
```

### 10.2 Async FIFO with gray-code pointers

```
  Write domain (clk_w)            Read domain (clk_r)
  ────────────────────            ───────────────────
  wr_ptr (binary) ──▶ bin2gray ──▶ 2-FF sync ──▶ wr_ptr_sync (gray)
                                                        │
  mem[wr_ptr % D] = data                         empty = (rd_ptr_gray == wr_ptr_sync)

  rd_ptr (binary) ──▶ bin2gray ──▶ 2-FF sync ──▶ rd_ptr_sync (gray)
       │                                               │
  data = mem[rd_ptr % D]                        full  = (wr_ptr_gray == ~rd_ptr_sync[MSB:MSB-1])

  DEPTH must be power of 2 for gray-code pointer arithmetic to be correct.
```

### 10.3 CDC latency budget

```
  Total CDC latency = SYNC_STAGES × DST_CLK_PERIOD

  Example: 2-FF sync, 1 GHz dst clock
  CDC_LATENCY = 2 × 1 ns = 2 ns

  This is added to the TLM delay annotation when a transaction crosses domains:
  delay += CDC_LATENCY;
```

---

## 11. Register File Diagrams

### 11.1 Integer register file (32 × 64-bit)

```
  Read port A ──▶ rs1[4:0] ──▶ ┌─────────────────────────────┐
  Read port B ──▶ rs2[4:0] ──▶ │  Register File              │ ──▶ data_A
  Write port  ──▶ rd [4:0] ──▶ │  32 registers × 64 bits     │ ──▶ data_B
  Write data  ──▶ wdata    ──▶ │  2R / 1W (dual-read)        │
  Write enable──▶ wen      ──▶ └─────────────────────────────┘

  r0 always reads 0 (hardwired zero — write ignored)
  Read latency:  RF_READ_LATENCY  = 1 ns
  Write latency: RF_WRITE_LATENCY = 1 ns (written at WB stage)
```

### 11.2 Register bank with metadata (Flyweight)

```
  ┌────────────────────────────────────────────────────────────┐
  │  RegisterMeta (shared, const after construction)           │
  │  ┌────────┬───────────┬──────────┬────────────────────┐   │
  │  │ width  │ reset_val │ read_only│ name               │   │
  │  ├────────┼───────────┼──────────┼────────────────────┤   │
  │  │ 32     │ 0x0       │ false    │ "CTRL"             │   │
  │  │ 32     │ 0xFFFF    │ true     │ "STATUS"           │   │
  │  │ 64     │ 0x0       │ false    │ "ADDR"             │   │
  │  └────────┴───────────┴──────────┴────────────────────┘   │
  └────────────────────────────────────────────────────────────┘
         ↕ (index lookup — no copy)
  ┌────────────────────────┐
  │  Values (per instance) │
  │  values_[0] = 0x0      │
  │  values_[1] = 0xFFFF   │
  │  values_[2] = 0x0      │
  └────────────────────────┘
```

---

## 12. TLM‑2.0 Mapping Diagrams

### 12.1 b_transport call flow

```
  Initiator (SC_THREAD)                    Target (b_transport)
  ─────────────────────                    ────────────────────
  pl_.set_command(READ)
  pl_.set_address(0x1000)
  pl_.set_data_length(64)
  delay = 0 ns
        │
        │  isock->b_transport(pl_, delay)
        ├─────────────────────────────────▶  ① arbiter_.request(id_)  += 1 ns
        │                                    ② cache_.probe(addr)
        │                                       hit  → += 4 ns
        │                                       miss → += 80 ns + BW
        │                                    ③ do_transfer(pl_)
        │                                    ④ pl_.set_response_status(OK)
        ◀─────────────────────────────────  return (delay = 5–85 ns)
        │
  wait(delay)   ← initiator advances simulation clock
```

### 12.2 nb_transport 4-phase handshake

```
  Time ──────────────────────────────────────────────────────────▶

  Initiator:  ──BEGIN_REQ──────────────────────────BEGIN_RESP──▶
                            ◀──END_REQ──               ◀──END_RESP──
  Target:                              ──BEGIN_RESP──▶

  Phase annotations:
  BEGIN_REQ  → END_REQ  : arbiter + cmd decode latency    (+1 ns)
  END_REQ    → BEGIN_RESP: memory access + bandwidth       (+85 ns)
  BEGIN_RESP → END_RESP : data return + bus latency        (+1 ns)
```

### 12.3 Multi-master TLM system

```
  ┌──────────┐  isock0                          tsock0  ┌─────────────┐
  │ Master 0 │────────────┐                  ┌──────────│  Slave 0    │
  └──────────┘            │                  │          │  (SRAM)     │
                          ▼                  │          └─────────────┘
  ┌──────────┐  isock1  ┌────────────────┐   │ isock0
  │ Master 1 │─────────▶│    Router      │───┤          ┌─────────────┐
  └──────────┘          │  (addr decode  │   │ isock1   │  Slave 1    │
                        │  + arbitration)│───┘          │  (DRAM)     │
  ┌──────────┐  isock2  └────────────────┘              └─────────────┘
  │ Master 2 │────────────▲
  └──────────┘
```

---

## 13. VP Performance Modelling Diagrams

### 13.1 Latency decomposition waterfall

```
  Operation: Core 0 reads 64B from DRAM (cold miss)

  Component              │ Latency  │ Cumulative
  ───────────────────────┼──────────┼───────────
  Bus arbitration        │  +1 ns   │   1 ns
  L1 probe (miss)        │  +4 ns   │   5 ns
  L2 probe (miss)        │ +12 ns   │  17 ns
  L3 probe (miss)        │ +40 ns   │  57 ns
  DRAM RAS               │ +35 ns   │  92 ns
  DRAM CAS               │ +14 ns   │ 106 ns
  DRAM BW (64B @ 8GBps)  │  +8 ns   │ 114 ns
  ───────────────────────┴──────────┴───────────
  Total                              114 ns
```

### 13.2 Bandwidth throttling model

```
  Request: 256 bytes on 16 GB/s bus

  Transfer time = bytes / BW_bytes_per_ns
               = 256   / 16
               = 16 ns

  Bus transactions = ceil(256 / BUS_WIDTH_BYTES)
                   = ceil(256 / 64)
                   = 4 beats

  delay += 1 × ARB_LATENCY + 4 × BEAT_LATENCY
         = 1 ns            + 4 ns
         = 5 ns   (bus overhead, not counting memory latency)
```

### 13.3 Queue occupancy and stall probability

```
  Queue depth = D = 16
  Arrival rate = λ requests/ns
  Service rate = μ requests/ns

  Utilisation  ρ = λ / μ
  Avg occupancy L = ρ / (1 - ρ)   [M/M/1 queue model]
  Avg wait      W = L / λ = 1 / (μ - λ)

  Example: λ=0.8/ns, μ=1.0/ns → ρ=0.8, L=4.0, W=4 ns avg queue wait

  VP model:
  const double rho = arrival_rate_ / service_rate_;
  delay += sc_time(1.0 / (service_rate_ - arrival_rate_), SC_NS);
```

### 13.4 IPC vs ROB depth curve (architecture exploration)

```
  IPC
  2.0 │                                    ●─────────
      │                              ●─────
  1.5 │                        ●─────
      │                  ●─────
  1.0 │            ●─────
      │      ●─────
  0.5 │ ●────
      └──────┬──────┬──────┬──────┬──────┬──────▶ ROB depth
             8      16     32     64     128    256

  Knee of curve ≈ ROB=64 — beyond this, IPC gains diminish
  AI sweep: binary search for minimum ROB achieving IPC ≥ target
```

---

## 14. AI‑Testability Instrumentation Diagrams

### 14.1 Observation points in a full VP system

```
  ┌──────────┐  ①dump_state()  ┌──────────┐  ②dump_state()  ┌──────────┐
  │  Fetch   │────────────────▶│  Decode  │────────────────▶│  Issue   │
  └──────────┘                 └──────────┘                 └──────────┘
       │ ①                          │ ②                          │ ③
       ▼                            ▼                            ▼
  pc, valid                   insn, valid                  rd,rs1,rs2,valid

  ┌──────────┐  ④dump_state()  ┌──────────┐  ⑤dump_state()
  │ Execute  │────────────────▶│  WB      │
  └──────────┘                 └──────────┘
       │ ④                          │ ⑤
       ▼                            ▼
  result, fwd                commit_pc, reg_write

  ┌────────────────────────────────────────────┐
  │  AI Harness                                │
  │  after sc_start(CLK_PERIOD):               │
  │  snap = {①,②,③,④,⑤}.join(" | ")           │
  │  assert snap == golden[cycle]              │
  └────────────────────────────────────────────┘
```

### 14.2 TLM subsystem AI observation points

```
  ① dump_config()                    ③ dump_stats() after run
       │                                  │
       ▼                                  ▼
  ┌─────────┐  b_transport  ┌─────────┐  ┌─────────┐
  │  AI     │──────────────▶│ Router  │─▶│ Memory  │
  │Initiator│               │ (⑤log) │  │  (⑥log)│
  └─────────┘               └────┬────┘  └─────────┘
       │ ② apply_stimulus()      │
       │                    ④ dump_state()
       ▼
  pl_ fields logged:
  "op=R addr=0x1000 bytes=64"
```

---

## 15. Diagram Drawing Rules

### Rule DIAG‑07 — Box naming convention

```
  ┌──────────────┐
  │  ModuleName  │  ← exact sc_module name or class name
  │  (type)      │  ← SC_MODULE / struct / class
  └──────────────┘
```

### Rule DIAG‑08 — Arrow labelling convention

```
  ──signal_name──▶      sc_signal or sc_out
  ══fifo_name════▶      sc_fifo
  ──────────────▶       TLM b_transport (unlabelled = TLM)
  - - - - - - -▶       Optional / conditional path
  ◀─────────────        Bidirectional or return
```

### Rule DIAG‑09 — Latency annotation convention

```
  ──▶ [+N ns] ──▶      adds N ns to delay
  ──▶ [hit: +4ns / miss: +80ns]   conditional latency
```

### Rule DIAG‑10 — AI observation point convention

```
  ① ② ③ ...   numbered circles mark dump_state() call points
  Numbered list below diagram maps ① → field names observed
```

---

## 16. Anti‑Patterns

| Anti‑Pattern | Consequence | Fix |
|---|---|---|
| Box without a module name | Diagram untraceable to code | Every box has exact class/module name |
| Arrow without a signal/socket name | Connection untraceable | Every arrow labelled with signal/socket |
| Magic latency numbers in diagram | Untraceable to named constants | All latencies labelled with constant name |
| Unbounded queue shown without depth | Hides stall behaviour | Every FIFO labelled with `depth=N` |
| Diagram with random arrows | Diagram not deterministic | Fixed layout, no curved random paths |
| No AI observation points | AI cannot verify diagram maps to code | Add ① ② ③ at every state dump point |

---

## 17. Glossary

| Term | Definition |
|---|---|
| **Box** | A rectangle in a diagram representing a named module, class, or hardware unit |
| **Arrow** | A directed edge representing an `sc_signal`, `sc_fifo`, or TLM socket connection |
| **Observation point** | Marked location (①②③) where `dump_state()` is called by the AI harness |
| **Waterfall diagram** | Cumulative latency breakdown showing each component's contribution |
| **Open-page hit** | DRAM access to a row that is already activated — avoids RAS latency |
| **Gray code** | Binary encoding where adjacent values differ by exactly one bit — used in CDC FIFOs |
| **XY routing** | NoC routing that first traverses X hops then Y hops — deterministic, deadlock-free |
| **FR-FCFS** | First-Ready, First-Come-First-Served — DRAM scheduler that prioritises open-row requests |
| **TDMA** | Time-Division Multiple Access — slot-based bus arbitration with guaranteed WCET |
| **Superscalar** | Processor that issues more than one instruction per clock cycle |
| **ROB** | Reorder Buffer — tracks in-flight instructions for out-of-order execution |
