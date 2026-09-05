# DSA Patterns Adapted for Hardware Modelling, SystemC, TLM‑2.0 & VP Performance Modelling

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for SystemC/VP/Performance‑Modelling Engineers (<5‑Year)  
**Prerequisites:** `01_Core_Philosophy.md`, `02_C++_Rules.md`, `03_SystemC_Rules.md`, `04_TLM2_Patterns.md`, `05_VP_Performance_Modelling.md`

---

## Table of Contents

1. [Philosophy of Hardware‑Aligned DSA](#1-philosophy-of-hardwarealigned-dsa)
2. [Pattern 01 — Pipeline Window (Sliding Window)](#2-pattern-01--pipeline-window-sliding-window)
3. [Pattern 02 — Dual‑Port Memory Access (Two Pointer)](#3-pattern-02--dualport-memory-access-two-pointer)
4. [Pattern 03 — Clock Domain Crossing (Fast/Slow Pointer)](#4-pattern-03--clock-domain-crossing-fastslow-pointer)
5. [Pattern 04 — Bus Arbitration Merging (Merge Intervals)](#5-pattern-04--bus-arbitration-merging-merge-intervals)
6. [Pattern 05 — Hazard Detection (Monotonic Stack)](#6-pattern-05--hazard-detection-monotonic-stack)
7. [Pattern 06 — Timing Closure Search (Binary Search)](#7-pattern-06--timing-closure-search-binary-search)
8. [Pattern 07 — NoC Routing (BFS)](#8-pattern-07--noc-routing-bfs)
9. [Pattern 08 — Dependency Graph Walk (DFS)](#9-pattern-08--dependency-graph-walk-dfs)
10. [Pattern 09 — Instruction Scheduling (Topological Sort)](#10-pattern-09--instruction-scheduling-topological-sort)
11. [Pattern 10 — Connectivity Modelling (Union‑Find)](#11-pattern-10--connectivity-modelling-unionfind)
12. [Pattern 11 — Memory Region Tree (Segment Tree)](#12-pattern-11--memory-region-tree-segment-tree)
13. [Pattern 12 — Accumulated Latency (Fenwick Tree)](#13-pattern-12--accumulated-latency-fenwick-tree)
14. [Pattern 13 — Address Decode Table (Trie)](#14-pattern-13--address-decode-table-trie)
15. [Pattern 14 — LRU Eviction (LRU Cache)](#15-pattern-14--lru-eviction-lru-cache)
16. [Pattern 15 — Pipeline Buffer (Producer‑Consumer FIFO)](#16-pattern-15--pipeline-buffer-producerconsumer-fifo)
17. [Pattern 16 — Interrupt Fan‑Out (Observer)](#17-pattern-16--interrupt-fanout-observer)
18. [Pattern 17 — Control Logic (State Machine)](#18-pattern-17--control-logic-state-machine)
19. [Pattern 18 — Arbiter Selection (Strategy)](#19-pattern-18--arbiter-selection-strategy)
20. [Pattern 19 — RTL‑to‑TLM Bridge (Adapter)](#20-pattern-19--rtltotlm-bridge-adapter)
21. [Pattern 20 — Register File (Flyweight)](#21-pattern-20--register-file-flyweight)
22. [Hardware Diagrams Reference](#22-hardware-diagrams-reference)
23. [AI‑Testability Rules](#23-aitestability-rules)
24. [Anti‑Patterns](#24-anti-patterns)
25. [Checklist](#25-checklist)
26. [Glossary](#26-glossary)

---

## 1. Philosophy of Hardware‑Aligned DSA

> **Hardware modelling is structured, timed, and bounded.  
> Software DSA is generic, unbounded, and order-agnostic.  
> Every DSA pattern must be adapted — never transplanted as-is.**

### The three adaptation rules

| Rule | Software DSA | Hardware-Aligned DSA |
|---|---|---|
| **Naming** | Algorithm name (`SlidingWindow`) | Hardware name (`IssueWindow`, `ReorderBuffer`) |
| **Bounds** | Unbounded by default | Bounded by hardware constant — overflow = fatal |
| **Timing** | No timing model | Every access annotated with latency |

### Mapping table

| DSA Pattern | Hardware Structure | SKILLS Doc section |
|---|---|---|
| Sliding window | Pipeline window / issue window / ROB | §2 |
| Two pointer | Dual-port RAM / FIFO head-tail | §3 |
| Fast/slow pointer | CDC FIFO read/write pointers | §4 |
| Merge intervals | AXI burst coalescing / arbitration windows | §5 |
| Monotonic stack | Scoreboard / RAW hazard chain | §6 |
| Binary search | Timing closure / pipeline depth search | §7 |
| BFS | NoC shortest-path routing | §8 |
| DFS | RTL dependency graph / module elaboration | §9 |
| Topological sort | Instruction scheduling / stage ordering | §10 |
| Union-Find | Cache coherence domains / NoC connectivity | §11 |
| Segment tree | MMU region lookup / memory protection | §12 |
| Fenwick tree | Accumulated pipeline latency | §13 |
| Trie | Bus address decode / routing table | §14 |
| LRU | Cache / TLB / buffer eviction | §15 |
| Producer-consumer | Pipeline FIFO / DMA queue | §16 |
| Observer | Interrupt fan-out / event notification | §17 |
| FSM | Protocol engine / control logic | §18 |
| Strategy | Arbiter policy selection | §19 |
| Adapter | RTL-to-TLM bridge / protocol conversion | §20 |
| Flyweight | Register file / shared register metadata | §21 |

---

## 2. Pattern 01 — Pipeline Window (Sliding Window)

### Software definition
Process a fixed-size window of elements moving through an array.

### Hardware interpretation

A pipeline window models any structure that holds a fixed number of
**in-flight** items advancing through processing stages:

- Instruction pipeline (fetch → decode → issue → execute → writeback)
- Cache prefetch window (N cache lines ahead of PC)
- Reorder buffer (ROB) — up to N instructions in flight
- Load/store queue

### Hardware naming rule

| Software name | Hardware name to use |
|---|---|
| `SlidingWindow` | `IssueWindow`, `ReorderBuffer`, `PrefetchWindow` |

### Diagram

```
  Cycle    │  F     D     I     E     W
  ─────────┼──────────────────────────────
  I1       │  [F1]  [D1]  [I1]  [E1]  [W1]
  I2       │        [F2]  [D2]  [I2]  [E2]
  I3       │              [F3]  [D3]  [I3]
  I4       │                    [F4]  [D4]
  I5       │                          [F5]

  Window of 5 in-flight instructions slides right each cycle.
```

### SystemC example — 5-stage pipeline register array

```cpp
constexpr std::size_t PIPE_DEPTH = 5;

struct PipeSlot {
    bool     valid = false;
    uint64_t pc    = 0;
    uint32_t insn  = 0;
};

SC_MODULE(Pipeline) {
    sc_in<bool>     clk;
    sc_in<bool>     rst_n;
    sc_in<bool>     stall;

    SC_CTOR(Pipeline) {
        SC_METHOD(on_clock);
        sensitive << clk.pos() << rst_n.neg();
        dont_initialize();
    }

private:
    std::array<PipeSlot, PIPE_DEPTH> pipe_{};

    void on_clock() {
        if (!rst_n.read()) { pipe_ = {}; return; }
        if (stall.read())  { return; }

        // Shift window: stage[i] ← stage[i-1]
        for (int i = PIPE_DEPTH - 1; i > 0; --i)
            pipe_[i] = pipe_[i - 1];
        pipe_[0] = fetch_next();
    }

    PipeSlot fetch_next() { /* ... */ return {}; }
};
```

### VP performance integration

```cpp
// Each stage contributes its own latency to the total pipeline latency
constexpr sc_time FETCH_LAT  (1, SC_NS);
constexpr sc_time DECODE_LAT (1, SC_NS);
constexpr sc_time ISSUE_LAT  (1, SC_NS);
constexpr sc_time EXECUTE_LAT(1, SC_NS);
constexpr sc_time WB_LAT     (1, SC_NS);
constexpr sc_time PIPELINE_FILL_LATENCY =
    FETCH_LAT + DECODE_LAT + ISSUE_LAT + EXECUTE_LAT + WB_LAT;
```

### AI‑testability note
Pipeline state must be fully visible via `dump_state()`. No hidden
pipeline registers.

---

## 3. Pattern 02 — Dual‑Port Memory Access (Two Pointer)

### Software definition
Two indices move through an array — one from each end, or at different
speeds — to solve range or partition problems.

### Hardware interpretation

Models any structure with **independent read and write access paths**:

- Dual-port SRAM (simultaneous read + write)
- FIFO with separate head (read) and tail (write) pointers
- Ring buffer (circular queue)
- Store buffer with in-order write / out-of-order read

### Hardware naming rule

| Software name | Hardware name to use |
|---|---|
| `left`, `right` pointers | `head_ptr_`, `tail_ptr_` |
| Two-pointer array | `RingBuffer`, `CircularFifo` |

### Diagram

```
  ┌───┬───┬───┬───┬───┬───┬───┬───┐
  │   │   │ D │ D │ D │   │   │   │
  └───┴───┴───┴───┴───┴───┴───┴───┘
            ▲               ▲
          head            tail
          (read)          (write)
          ptr             ptr

  Capacity  = DEPTH
  Occupancy = (tail - head + DEPTH) % DEPTH
  Full      = occupancy == DEPTH - 1
  Empty     = head == tail
```

### SystemC / C++ example — bounded ring buffer

```cpp
template<typename T, std::size_t DEPTH>
class RingBuffer {
    static_assert(DEPTH > 0 && (DEPTH & (DEPTH - 1)) == 0,
                  "DEPTH must be a power of two");
public:
    bool push(const T& item) {
        if (full()) return false;
        mem_[tail_ & MASK] = item;
        ++tail_;
        return true;
    }

    bool pop(T& item) {
        if (empty()) return false;
        item = mem_[head_ & MASK];
        ++head_;
        return true;
    }

    bool   empty()    const { return head_ == tail_; }
    bool   full()     const { return size() == DEPTH; }
    size_t size()     const { return tail_ - head_; }
    size_t capacity() const { return DEPTH; }

private:
    static constexpr std::size_t MASK = DEPTH - 1;
    std::array<T, DEPTH> mem_{};
    std::size_t head_ = 0;
    std::size_t tail_ = 0;
};
```

### VP performance integration

```cpp
// Dual-port SRAM: simultaneous read and write in one cycle
constexpr sc_time SRAM_READ_LAT (1, SC_NS);
constexpr sc_time SRAM_WRITE_LAT(1, SC_NS);
// Both operations add their latency independently — no conflict
delay += SRAM_READ_LAT;   // read port
// write port consumed in parallel (modelled in write path)
```

---

## 4. Pattern 03 — Clock Domain Crossing (Fast/Slow Pointer)

### Software definition
Fast pointer advances 2× the speed of slow pointer to detect cycles in
a linked list.

### Hardware interpretation

A **fast clock domain** produces data faster than the **slow clock domain**
can consume it. The relationship between the two pointers models:

- Async FIFO write pointer (fast clock) vs read pointer (slow clock)
- CDC gray-code pointer comparison
- Metastability resolution synchroniser depth

### Hardware naming rule

| Software name | Hardware name to use |
|---|---|
| `fast` pointer | `wr_ptr_` (write domain) |
| `slow` pointer | `rd_ptr_` (read domain) |

### Diagram

```
  Fast clock domain             Slow clock domain
  (producer, 2 GHz)             (consumer, 1 GHz)
  ─────────────────             ─────────────────
  wr_ptr advances 2×            rd_ptr advances 1×
        │                             │
        ▼                             ▼
  ┌─────────────────────────────────────────────────────┐
  │  Async FIFO (gray-code pointers, 2-FF synchroniser) │
  └─────────────────────────────────────────────────────┘
        │                             │
  Full  = (wr_ptr_gray == ~rd_ptr_gray_sync[MSB:MSB-1])
  Empty = (rd_ptr_gray == wr_ptr_gray_sync)
```

### SystemC example — CDC FIFO module

```cpp
SC_MODULE(AsyncFifo) {
    sc_in<bool>    wr_clk;
    sc_in<bool>    rd_clk;
    sc_in<bool>    wr_en;
    sc_in<uint32_t> wr_data;
    sc_out<bool>   full;
    sc_out<bool>   empty;
    sc_out<uint32_t> rd_data;

    static constexpr std::size_t DEPTH = 16;
    static constexpr std::size_t ADDR_BITS = 4;

    SC_CTOR(AsyncFifo) {
        SC_THREAD(wr_domain);  sensitive << wr_clk.pos();
        SC_THREAD(rd_domain);  sensitive << rd_clk.pos();
        mem_.fill(0);
    }

private:
    std::array<uint32_t, DEPTH> mem_{};
    uint32_t wr_ptr_ = 0;
    uint32_t rd_ptr_ = 0;
    // Synchronised gray-code pointers (modelled as 2-cycle sync latency)
    uint32_t rd_ptr_sync_ = 0;
    uint32_t wr_ptr_sync_ = 0;

    static uint32_t to_gray(uint32_t b) { return b ^ (b >> 1); }
    bool is_full()  const { return to_gray(wr_ptr_) == (to_gray(rd_ptr_sync_) ^ (DEPTH | (DEPTH >> 1))); }
    bool is_empty() const { return to_gray(rd_ptr_) == to_gray(wr_ptr_sync_); }

    void wr_domain() {
        while (true) {
            wait();
            rd_ptr_sync_ = rd_ptr_;   // 2-FF sync modelled as 1-cycle (simplified)
            if (wr_en.read() && !is_full()) {
                mem_[wr_ptr_ % DEPTH] = wr_data.read();
                ++wr_ptr_;
            }
            full.write(is_full());
        }
    }

    void rd_domain() {
        while (true) {
            wait();
            wr_ptr_sync_ = wr_ptr_;
            if (!is_empty()) {
                rd_data.write(mem_[rd_ptr_ % DEPTH]);
                ++rd_ptr_;
            }
            empty.write(is_empty());
        }
    }
};
```

### VP performance integration

```cpp
// CDC synchroniser adds 2 destination clock cycles latency
constexpr sc_time DST_CLK_PERIOD(0.5, SC_NS);   // 2 GHz
constexpr uint32_t SYNC_STAGES = 2;
constexpr sc_time CDC_LATENCY = SYNC_STAGES * DST_CLK_PERIOD;
delay += CDC_LATENCY;
```

---

## 5. Pattern 04 — Bus Arbitration Merging (Merge Intervals)

### Software definition
Given a list of intervals, merge all overlapping ones into the minimum
set of non-overlapping intervals.

### Hardware interpretation

Models **burst coalescing** on a memory bus or DMA engine:

- Multiple small requests to contiguous addresses → one large burst
- AXI4 burst merging in a memory controller
- PCIe write combining
- Reduces arbitration overhead (1 grant instead of N)

### Hardware naming rule

| Software name | Hardware name to use |
|---|---|
| `Interval{start, end}` | `BurstRange{base_addr, end_addr}` |
| `merge()` | `coalesce_bursts()` |

### Diagram

```
  Before coalescing:
  ├──Req0──┤
           ├──Req1──┤
                    ├──Req2──────┤

  After coalescing:
  ├──────────Burst──────────────┤

  1 arbitration grant instead of 3
  Latency: 1 × arb_delay + total_bytes / BW
  vs       3 × arb_delay + total_bytes / BW
```

### C++ example — burst coalescer

```cpp
struct BurstRange {
    uint64_t base;
    uint64_t end;   // exclusive
    bool overlaps_or_adjacent(const BurstRange& o) const {
        return base <= o.end && o.base <= end;
    }
    BurstRange merge(const BurstRange& o) const {
        return {std::min(base, o.base), std::max(end, o.end)};
    }
};

std::vector<BurstRange> coalesce_bursts(std::vector<BurstRange> reqs) {
    if (reqs.empty()) return {};
    std::sort(reqs.begin(), reqs.end(),
              [](const BurstRange& a, const BurstRange& b){ return a.base < b.base; });
    std::vector<BurstRange> out;
    out.push_back(reqs[0]);
    for (std::size_t i = 1; i < reqs.size(); ++i) {
        if (out.back().overlaps_or_adjacent(reqs[i]))
            out.back() = out.back().merge(reqs[i]);
        else
            out.push_back(reqs[i]);
    }
    return out;
}
```

### VP performance integration

```cpp
const auto merged = coalesce_bursts(pending_requests_);
for (const auto& burst : merged) {
    delay += BUS_ARB_LATENCY;   // one arbitration per merged burst
    const uint64_t bytes = burst.end - burst.base;
    delay += sc_time(static_cast<double>(bytes) / BUS_BW_BYTES_PER_NS, SC_NS);
}
```

---

## 6. Pattern 05 — Hazard Detection (Monotonic Stack)

### Software definition
A monotonic stack maintains elements in increasing or decreasing order,
popping elements that violate the monotone property to find
next-greater / next-smaller elements in O(n).

### Hardware interpretation

Models **instruction dependency chains** in an out-of-order processor:

- RAW (Read-After-Write) hazard: instruction B reads a register that
  instruction A (earlier in program order) has not yet written
- Stack of pending write targets — pop when a reader is encountered
- Scoreboard dependency tracking

### Hardware naming rule

| Software name | Hardware name to use |
|---|---|
| Monotonic stack | `Scoreboard`, `DependencyChain` |
| Push element | `issue_instruction()` |
| Pop on violation | `detect_raw_hazard()` |

### Diagram

```
  Program order: I1(wr r1), I2(rd r1), I3(wr r2), I4(rd r2)

  Scoreboard state after I1 issues:
  ┌──────┬──────────┐
  │  r1  │ pending  │  ← I1 result not yet written
  └──────┴──────────┘

  I2 reads r1 → RAW detected → stall I2 until I1 commits
  I3 writes r2 → add to scoreboard
  I4 reads r2 → RAW detected → stall I4 until I3 commits
```

### C++ example — scoreboard

```cpp
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

    std::string dump() const {
        std::ostringstream oss;
        oss << "Scoreboard{";
        for (uint8_t r = 0; r < NUM_REGS; ++r)
            if (pending_[r]) oss << " r" << +r << "=pending";
        oss << "}";
        return oss.str();
    }

private:
    static constexpr uint8_t NUM_REGS = 32;
    std::array<bool, NUM_REGS> pending_{};
};
```

### VP performance integration

```cpp
void issue_stage() {
    if (scoreboard_.has_raw_hazard(insn.rs1) ||
        scoreboard_.has_raw_hazard(insn.rs2)) {
        ++raw_stall_count_;
        delay += CLK_PERIOD;   // one stall cycle
        return;
    }
    scoreboard_.mark_pending(insn.rd);
    // ... issue instruction
}
```

---

## 7. Pattern 06 — Timing Closure Search (Binary Search)

### Software definition
Divide search space in half each iteration to find a target in O(log n).

### Hardware interpretation

Models **parameter sweep** during VP architecture exploration:

- Find the minimum pipeline depth that meets a target IPC
- Find the maximum operating frequency for a given latency budget
- Find the cache size that achieves a target hit rate
- Binary search over configuration space — each probe runs a simulation

### C++ example — parameter sweep

```cpp
// Binary search for minimum ROB size achieving target IPC
uint32_t find_min_rob_for_ipc(double target_ipc,
                               uint32_t lo = 8,
                               uint32_t hi = 512) {
    uint32_t result = hi;
    while (lo <= hi) {
        const uint32_t mid = lo + (hi - lo) / 2;
        const double ipc   = simulate_with_rob(mid);
        if (ipc >= target_ipc) {
            result = mid;
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }
    return result;
}
```

### VP performance integration

```cpp
// Binary search over clock frequencies to find timing closure
uint32_t find_max_freq_mhz(uint32_t lo = 100, uint32_t hi = 4000) {
    uint32_t result = lo;
    while (lo <= hi) {
        const uint32_t mid_mhz = lo + (hi - lo) / 2;
        const sc_time  clk     = sc_time(1000.0 / mid_mhz, SC_NS);
        if (timing_closure(clk)) { result = mid_mhz; lo = mid_mhz + 1; }
        else                     { hi = mid_mhz - 1; }
    }
    return result;
}
```

---

## 8. Pattern 07 — NoC Routing (BFS)

### Software definition
BFS finds the shortest path in an unweighted graph by exploring all
neighbours level by level.

### Hardware interpretation

Models **minimum-hop routing** in a Network-on-Chip:

- Find shortest path between two router nodes
- Build static routing tables at elaboration time
- Compute hop count for latency annotation

### Diagram

```
  2D Mesh 3×3 — route (0,0) → (2,2)

  (0,0)──(1,0)──(2,0)
    │      │      │
  (0,1)──(1,1)──(2,1)
    │      │      │
  (0,2)──(1,2)──(2,2) ← destination

  BFS from (0,0): level 0={(0,0)}, level 1={(1,0),(0,1)},
                  level 2={(2,0),(1,1),(0,2)}, level 3={(2,1),(1,2)},
                  level 4={(2,2)}
  Hop count = 4 (Manhattan distance = |2-0| + |2-0| = 4)
```

### C++ example — BFS routing table builder

```cpp
struct NocNode { uint32_t row, col; };

std::vector<std::vector<uint32_t>>
build_routing_table(uint32_t rows, uint32_t cols) {
    const uint32_t N = rows * cols;
    std::vector<std::vector<uint32_t>> hops(N, std::vector<uint32_t>(N, UINT32_MAX));

    auto id = [&](uint32_t r, uint32_t c) { return r * cols + c; };

    for (uint32_t src = 0; src < N; ++src) {
        std::queue<uint32_t> q;
        q.push(src);
        hops[src][src] = 0;

        while (!q.empty()) {
            const uint32_t u = q.front(); q.pop();
            const uint32_t r = u / cols, c = u % cols;

            // 4-connected mesh neighbours
            for (auto [dr, dc] : std::array<std::pair<int,int>, 4>
                 {{{-1,0},{1,0},{0,-1},{0,1}}}) {
                const int nr = static_cast<int>(r) + dr;
                const int nc = static_cast<int>(c) + dc;
                if (nr < 0 || nr >= static_cast<int>(rows)) continue;
                if (nc < 0 || nc >= static_cast<int>(cols)) continue;
                const uint32_t v = id(nr, nc);
                if (hops[src][v] == UINT32_MAX) {
                    hops[src][v] = hops[src][u] + 1;
                    q.push(v);
                }
            }
        }
    }
    return hops;
}
```

### VP performance integration

```cpp
// Use pre-built table at elaboration, query at runtime
const uint32_t hops = routing_table_[src_id_][dst_id_];
delay += hops * NOC_HOP_LATENCY;
```

---

## 9. Pattern 08 — Dependency Graph Walk (DFS)

### Software definition
DFS explores a graph by going as deep as possible before backtracking.

### Hardware interpretation

Models **RTL elaboration** and **pipeline dependency resolution**:

- Walk the module hierarchy to discover all instances and connections
- Detect combinational loops (cycle in DFS = feedback without register)
- Identify critical path through logic cones
- Resolve transitive dependencies in out-of-order schedulers

### C++ example — combinational loop detector

```cpp
enum class VisitState { UNVISITED, IN_STACK, DONE };

bool has_combinational_loop(
    uint32_t node,
    const std::vector<std::vector<uint32_t>>& adj,
    std::vector<VisitState>& state)
{
    state[node] = VisitState::IN_STACK;
    for (uint32_t neighbour : adj[node]) {
        if (state[neighbour] == VisitState::IN_STACK) return true;   // cycle!
        if (state[neighbour] == VisitState::UNVISITED) {
            if (has_combinational_loop(neighbour, adj, state)) return true;
        }
    }
    state[node] = VisitState::DONE;
    return false;
}

void check_no_loops(const std::vector<std::vector<uint32_t>>& adj) {
    std::vector<VisitState> state(adj.size(), VisitState::UNVISITED);
    for (uint32_t i = 0; i < adj.size(); ++i) {
        if (state[i] == VisitState::UNVISITED) {
            if (has_combinational_loop(i, adj, state)) {
                SC_REPORT_FATAL("DFS", "combinational loop detected");
            }
        }
    }
}
```

---

## 10. Pattern 09 — Instruction Scheduling (Topological Sort)

### Software definition
Topological sort produces a linear ordering of DAG nodes such that every
edge u→v has u before v.

### Hardware interpretation

Models **instruction scheduling** in a compiler backend or out-of-order
processor issue logic:

- Instructions form a DAG (edges = data/control dependencies)
- Topological order = valid issue order (no instruction issued before its
  operands are ready)
- Also used to order module elaboration and TLM binding

### C++ example — Kahn's algorithm for instruction scheduling

```cpp
std::vector<uint32_t> schedule_instructions(
    uint32_t n,
    const std::vector<std::pair<uint32_t, uint32_t>>& deps)
{
    std::vector<uint32_t> in_degree(n, 0);
    std::vector<std::vector<uint32_t>> successors(n);

    for (const auto& [src, dst] : deps) {
        successors[src].push_back(dst);
        ++in_degree[dst];
    }

    // Use std::queue for deterministic FIFO order (not priority_queue)
    std::queue<uint32_t> ready;
    for (uint32_t i = 0; i < n; ++i)
        if (in_degree[i] == 0) ready.push(i);

    std::vector<uint32_t> order;
    order.reserve(n);
    while (!ready.empty()) {
        const uint32_t u = ready.front(); ready.pop();
        order.push_back(u);
        for (uint32_t v : successors[u]) {
            if (--in_degree[v] == 0) ready.push(v);
        }
    }

    if (order.size() != n) {
        SC_REPORT_FATAL("TOPO", "cycle in dependency graph — invalid schedule");
    }
    return order;
}
```

### VP performance integration

```cpp
// Issue instructions in topological order — no stalls from data deps
const auto sched = schedule_instructions(insns_.size(), deps_);
for (uint32_t i : sched) {
    delay += ISSUE_LATENCY;
    // execute insns_[i]
}
```

---

## 11. Pattern 10 — Connectivity Modelling (Union‑Find)

### Software definition
Union-Find (Disjoint Set Union) tracks connected components in O(α(n))
per operation.

### Hardware interpretation

Models **cache coherence domains** and **NoC cluster connectivity**:

- Which cores share an L3 cache slice?
- Which NoC nodes belong to the same coherence domain?
- Is node A reachable from node B without crossing a domain boundary?

### C++ example — coherence domain tracker

```cpp
class CoherenceDomain {
public:
    explicit CoherenceDomain(uint32_t n) : parent_(n), rank_(n, 0) {
        std::iota(parent_.begin(), parent_.end(), 0);
    }

    uint32_t find(uint32_t x) {
        while (parent_[x] != x) {
            parent_[x] = parent_[parent_[x]];   // path compression (halving)
            x = parent_[x];
        }
        return x;
    }

    void unite(uint32_t a, uint32_t b) {
        a = find(a); b = find(b);
        if (a == b) return;
        if (rank_[a] < rank_[b]) std::swap(a, b);
        parent_[b] = a;
        if (rank_[a] == rank_[b]) ++rank_[a];
    }

    bool connected(uint32_t a, uint32_t b) { return find(a) == find(b); }

private:
    std::vector<uint32_t> parent_;
    std::vector<uint32_t> rank_;
};
```

### VP performance integration

```cpp
// Cross-domain access requires coherence traffic — extra latency
if (!domain_.connected(src_core_, dst_core_)) {
    delay += CROSS_DOMAIN_COHERENCE_LATENCY;
}
```

---

## 12. Pattern 11 — Memory Region Tree (Segment Tree)

### Software definition
A segment tree answers range queries (sum, min, max) and point updates
in O(log n).

### Hardware interpretation

Models **MMU address decode** and **memory protection unit (MPU) region
lookup**:

- Given a physical address, find which memory region it maps to
- Efficiently query overlapping protection regions
- TLB range entries (superpages of varying sizes)

### Diagram

```
  Address space: 0x0000_0000 – 0xFFFF_FFFF

                       [0x0000_0000 – 0xFFFF_FFFF]
                      /                             \
         [0x0000_0000–0x7FFF_FFFF]     [0x8000_0000–0xFFFF_FFFF]
              /          \                   /           \
    [0x00–0x3FFF]  [0x4000–0x7FFF]   [0x8000–0xBFFF]  [0xC000–0xFFFF]
       SRAM           Flash             Peripheral         DRAM
```

### C++ example — MPU region tree

```cpp
struct MemRegion {
    uint64_t    base;
    uint64_t    end;    // exclusive
    std::string name;
    bool        exec_ok;
    bool        write_ok;
};

class MpuTree {
public:
    void add_region(MemRegion r) {
        // Sorted by base address for deterministic lookup
        regions_.insert(
            std::lower_bound(regions_.begin(), regions_.end(), r,
                [](const MemRegion& a, const MemRegion& b){ return a.base < b.base; }),
            r);
    }

    const MemRegion* lookup(uint64_t addr) const {
        // Binary search: find last region with base <= addr
        auto it = std::upper_bound(regions_.begin(), regions_.end(), addr,
            [](uint64_t a, const MemRegion& r){ return a < r.base; });
        if (it == regions_.begin()) return nullptr;
        --it;
        return (addr < it->end) ? &(*it) : nullptr;
    }

private:
    std::vector<MemRegion> regions_;   // sorted by base, deterministic iteration
};
```

---

## 13. Pattern 12 — Accumulated Latency (Fenwick Tree)

### Software definition
A Fenwick (Binary Indexed) tree supports O(log n) prefix sum queries
and O(log n) point updates.

### Hardware interpretation

Models **accumulated pipeline latency** across stages where individual
stage latencies can be updated dynamically (e.g. during frequency scaling
exploration):

- Query: total latency from stage 0 to stage k
- Update: change one stage's latency (e.g. when exploring pipeline
  re-timing)

### C++ example — pipeline latency accumulator

```cpp
class PipelineLatencyTree {
public:
    explicit PipelineLatencyTree(uint32_t n)
        : n_(n), tree_(n + 1, sc_time(SC_ZERO_TIME)) {}

    // Set latency for stage i (1-indexed internally)
    void set(uint32_t i, sc_time lat) {
        update(i + 1, lat - query_point(i + 1));
    }

    // Get total latency from stage 0 to stage i (inclusive)
    sc_time prefix(uint32_t i) const {
        return query(i + 1);
    }

private:
    uint32_t n_;
    std::vector<sc_time> tree_;

    void update(uint32_t i, sc_time delta) {
        for (; i <= n_; i += i & static_cast<uint32_t>(-static_cast<int32_t>(i)))
            tree_[i] = sc_time(tree_[i].to_double() + delta.to_double(), SC_NS);
    }

    sc_time query(uint32_t i) const {
        sc_time s(SC_ZERO_TIME);
        for (; i > 0; i -= i & static_cast<uint32_t>(-static_cast<int32_t>(i)))
            s = sc_time(s.to_double() + tree_[i].to_double(), SC_NS);
        return s;
    }

    sc_time query_point(uint32_t i) const {
        return sc_time(query(i).to_double() - query(i - 1).to_double(), SC_NS);
    }
};
```

---

## 14. Pattern 13 — Address Decode Table (Trie)

### Software definition
A trie stores strings by prefix, enabling O(key_length) lookup.

### Hardware interpretation

Models **bus address decode** as a prefix tree over address bits:

- Upper bits → select slave region
- Middle bits → select sub-region or bank
- Lower bits → offset within the selected target
- Used in NoC routing tables and PCIe BAR decode

### C++ example — address prefix decoder

```cpp
struct DecodeNode {
    std::array<DecodeNode*, 2> child{nullptr, nullptr};
    int32_t target_id = -1;   // -1 = not a leaf
};

class AddressDecoder {
public:
    AddressDecoder() : root_(std::make_unique<DecodeNode>()) {}

    // Register prefix: top `bits` bits of address map to target_id
    void add_entry(uint64_t prefix, uint32_t bits, int32_t target_id) {
        DecodeNode* node = root_.get();
        for (int32_t b = static_cast<int32_t>(bits) - 1; b >= 0; --b) {
            const uint32_t bit = (prefix >> b) & 1u;
            if (!node->child[bit])
                node->child[bit] = pool_.emplace_back(std::make_unique<DecodeNode>()).get();
            node = node->child[bit];
        }
        node->target_id = target_id;
    }

    int32_t decode(uint64_t addr, uint32_t bits) const {
        const DecodeNode* node = root_.get();
        for (int32_t b = static_cast<int32_t>(bits) - 1; b >= 0; --b) {
            const uint32_t bit = (addr >> b) & 1u;
            if (!node->child[bit]) return -1;
            node = node->child[bit];
            if (node->target_id >= 0) return node->target_id;
        }
        return node->target_id;
    }

private:
    std::unique_ptr<DecodeNode> root_;
    std::vector<std::unique_ptr<DecodeNode>> pool_;
};
```

---

## 15. Pattern 14 — LRU Eviction (LRU Cache)

### Software definition
Track the least-recently-used element in a set and evict it when the
set is full.

### Hardware interpretation

Models **set-associative cache eviction**, **TLB replacement**, and
**store buffer eviction**:

- Each cache set has W ways; LRU tracks which way is oldest
- On a miss and full set, evict the LRU way
- Must be O(1) per access and O(1) per eviction

### C++ example — O(1) LRU tracker using doubly-linked list + map

```cpp
template<typename Key, std::size_t CAPACITY>
class LruTracker {
public:
    // Access key — moves it to MRU position; returns true if already present
    bool access(const Key& k) {
        auto it = pos_.find(k);
        if (it != pos_.end()) {
            order_.splice(order_.begin(), order_, it->second);
            return true;   // hit
        }
        // Miss — insert at MRU
        if (order_.size() == CAPACITY) {
            pos_.erase(order_.back());
            order_.pop_back();
        }
        order_.push_front(k);
        pos_[k] = order_.begin();
        return false;   // miss
    }

    const Key& lru() const { return order_.back(); }
    bool        full()  const { return order_.size() == CAPACITY; }

private:
    std::list<Key>                                     order_;
    std::map<Key, typename std::list<Key>::iterator>   pos_;
};
```

### VP performance integration

```cpp
const bool hit = lru_.access(addr >> OFFSET_BITS);
delay += hit ? CACHE_HIT_LATENCY : CACHE_MISS_PENALTY;
if (!hit) ++miss_count_;
```

---

## 16. Pattern 15 — Pipeline Buffer (Producer‑Consumer FIFO)

### Software definition
A producer pushes items; a consumer pops them. A bounded buffer
decouples their rates.

### Hardware interpretation

The **fundamental hardware buffer** — every inter-stage communication
channel in a pipeline is a bounded FIFO:

- Fetch queue between fetch and decode stages
- Reorder buffer between issue and commit
- Store buffer between execute and cache

### SystemC example — sc_fifo integration

```cpp
SC_MODULE(PipeStages) {
    sc_in<bool> clk;

    SC_CTOR(PipeStages) {
        SC_THREAD(fetch_thread);  sensitive << clk.pos();
        SC_THREAD(decode_thread); sensitive << clk.pos();
    }

private:
    sc_fifo<FetchPacket> fetch_queue_{"fq", /*depth=*/FETCH_QUEUE_DEPTH};

    void fetch_thread() {
        while (true) {
            wait();
            FetchPacket pkt = do_fetch();
            if (!pkt.valid) continue;
            if (fetch_queue_.num_free() == 0) {
                SC_REPORT_FATAL(name(), "fetch queue overflow");
            }
            fetch_queue_.write(pkt);
        }
    }

    void decode_thread() {
        while (true) {
            FetchPacket pkt = fetch_queue_.read();   // blocks until available
            do_decode(pkt);
        }
    }

    FetchPacket do_fetch()       { return {}; }
    void        do_decode(const FetchPacket&) {}
};
```

---

## 17. Pattern 16 — Interrupt Fan‑Out (Observer)

### Software definition
The observer pattern notifies a list of subscribers when an event occurs.

### Hardware interpretation

Models **interrupt propagation** and **SystemC event notification**:

- Interrupt controller drives multiple CPU cores
- `sc_event::notify()` wakes all `SC_THREAD`s waiting on the event
- Signal fan-out from one driver to multiple receivers

### SystemC example — interrupt controller

```cpp
SC_MODULE(IntController) {
    sc_out<bool> irq_cpu0;
    sc_out<bool> irq_cpu1;
    sc_out<bool> irq_cpu2;

    SC_CTOR(IntController) {
        SC_METHOD(on_source);
        sensitive << source_event_;
    }

    void raise(uint32_t source_id) {
        pending_ |= (1u << source_id);
        source_event_.notify(SC_ZERO_TIME);
    }

private:
    sc_event  source_event_;
    uint32_t  pending_ = 0;

    void on_source() {
        // Fan-out: drive all CPU IRQ lines
        irq_cpu0.write(pending_ != 0);
        irq_cpu1.write(pending_ != 0);
        irq_cpu2.write(pending_ != 0);
    }
};
```

---

## 18. Pattern 17 — Control Logic (State Machine)

### Software definition
A finite state machine transitions between a finite set of states based
on inputs.

### Hardware interpretation

The **universal hardware control pattern**. Every protocol engine,
cache controller, memory controller, and bus interface is an FSM.

### Rules for hardware FSMs

1. States MUST be an `enum class` — never raw integers
2. Transitions MUST be in a `switch` statement — no computed gotos
3. Every state MUST have an explicit default case
4. State MUST be a named member variable — never implicit

### SystemC example — AXI4-Lite FSM

```cpp
enum class AxiState {
    IDLE,
    ADDR_PHASE,
    DATA_PHASE,
    RESP_PHASE,
    ERROR
};

SC_MODULE(Axi4LiteMaster) {
    sc_in<bool>  clk;
    sc_in<bool>  rst_n;
    sc_out<bool> awvalid;
    sc_in<bool>  awready;
    sc_out<bool> wvalid;
    sc_in<bool>  wready;
    sc_in<bool>  bvalid;
    sc_out<bool> bready;

    SC_CTOR(Axi4LiteMaster) {
        SC_METHOD(fsm_step);
        sensitive << clk.pos() << rst_n.neg();
        dont_initialize();
    }

    std::string dump_state() const {
        static const char* names[] = {
            "IDLE","ADDR_PHASE","DATA_PHASE","RESP_PHASE","ERROR"};
        return std::string("Axi4LiteMaster{state=")
             + names[static_cast<int>(state_)] + "}";
    }

private:
    AxiState state_ = AxiState::IDLE;

    void fsm_step() {
        if (!rst_n.read()) { state_ = AxiState::IDLE; return; }
        switch (state_) {
            case AxiState::IDLE:
                awvalid.write(true);
                state_ = AxiState::ADDR_PHASE;
                break;
            case AxiState::ADDR_PHASE:
                if (awready.read()) {
                    awvalid.write(false);
                    wvalid.write(true);
                    state_ = AxiState::DATA_PHASE;
                }
                break;
            case AxiState::DATA_PHASE:
                if (wready.read()) {
                    wvalid.write(false);
                    bready.write(true);
                    state_ = AxiState::RESP_PHASE;
                }
                break;
            case AxiState::RESP_PHASE:
                if (bvalid.read()) {
                    bready.write(false);
                    state_ = AxiState::IDLE;
                }
                break;
            case AxiState::ERROR:
            default:
                SC_REPORT_ERROR(name(), "FSM in ERROR state");
                break;
        }
    }
};
```

---

## 19. Pattern 18 — Arbiter Selection (Strategy)

### Software definition
The strategy pattern defines a family of algorithms, encapsulates each,
and makes them interchangeable at runtime.

### Hardware interpretation

Models **pluggable arbitration policies**:

- Round-robin, fixed priority, weighted fair queuing, TDMA
- Policy is selected at VP construction time (not hardcoded)
- AI testing sweeps across policies

### C++ example — arbiter strategy interface

```cpp
struct ArbiterStrategy {
    virtual ~ArbiterStrategy() = default;
    virtual sc_time grant_delay(uint32_t master_id,
                                uint32_t n_masters) = 0;
    virtual std::string name() const = 0;
};

struct RoundRobinStrategy : ArbiterStrategy {
    sc_time grant_delay(uint32_t master_id, uint32_t n_masters) override {
        const sc_time delay = last_ == master_id
            ? SC_ZERO_TIME
            : sc_time(((master_id - last_ + n_masters) % n_masters)
                      * GRANT_CYCLES * CLK_PERIOD.to_double(), SC_NS);
        last_ = (master_id + 1) % n_masters;
        return delay;
    }
    std::string name() const override { return "round-robin"; }
private:
    uint32_t last_ = 0;
    static constexpr uint32_t GRANT_CYCLES = 1;
    static constexpr sc_time CLK_PERIOD{1, SC_NS};
};

struct FixedPriorityStrategy : ArbiterStrategy {
    sc_time grant_delay(uint32_t master_id, uint32_t /*n*/) override {
        return sc_time(master_id * PRIORITY_PENALTY.to_double(), SC_NS);
    }
    std::string name() const override { return "fixed-priority"; }
private:
    static constexpr sc_time PRIORITY_PENALTY{2, SC_NS};
};
```

---

## 20. Pattern 19 — RTL‑to‑TLM Bridge (Adapter)

### Software definition
The adapter pattern converts the interface of a class into another
interface clients expect.

### Hardware interpretation

Models **RTL-to-TLM wrappers** — adapting a cycle-accurate pin-level RTL
interface into a TLM transaction-level interface:

- Pin-level AXI4 → TLM `b_transport`
- APB register access → TLM read/write
- Legacy wishbone bus → TLM socket

### C++ example — APB-to-TLM adapter

```cpp
SC_MODULE(ApbToTlmAdapter) {
    // ── Pin-level APB ports ────────────────────────────────────
    sc_in<bool>     pclk;
    sc_in<bool>     psel;
    sc_in<bool>     penable;
    sc_in<bool>     pwrite;
    sc_in<uint32_t> paddr;
    sc_in<uint32_t> pwdata;
    sc_out<uint32_t> prdata;
    sc_out<bool>     pready;

    // ── TLM initiator ──────────────────────────────────────────
    tlm_utils::simple_initiator_socket<ApbToTlmAdapter> isock{"isock"};

    SC_CTOR(ApbToTlmAdapter) {
        SC_THREAD(apb_fsm);
        sensitive << pclk.pos();
        pl_.set_byte_enable_ptr(nullptr);
        pl_.set_streaming_width(4);
    }

private:
    tlm::tlm_generic_payload pl_{};
    uint32_t                 data_buf_ = 0;

    void apb_fsm() {
        while (true) {
            wait();
            if (!psel.read() || !penable.read()) { pready.write(false); continue; }

            pl_.set_command(pwrite.read() ? tlm::TLM_WRITE_COMMAND
                                          : tlm::TLM_READ_COMMAND);
            pl_.set_address(paddr.read());
            if (pwrite.read()) data_buf_ = pwdata.read();
            pl_.set_data_ptr(reinterpret_cast<uint8_t*>(&data_buf_));
            pl_.set_data_length(4);
            pl_.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);

            sc_time delay = SC_ZERO_TIME;
            isock->b_transport(pl_, delay);
            wait(delay);

            if (!pwrite.read()) prdata.write(data_buf_);
            pready.write(pl_.get_response_status() == tlm::TLM_OK_RESPONSE);
        }
    }
};
```

---

## 21. Pattern 20 — Register File (Flyweight)

### Software definition
The flyweight pattern shares intrinsic (immutable) state across many
objects, storing only extrinsic (per-instance) state per object.

### Hardware interpretation

Models a **register file** or **register bank**:

- Intrinsic state (shared): register width, access latency, reset value
- Extrinsic state (per-register): current value, dirty bit, lock bit
- Reduces memory: N registers share one `RegisterMeta` descriptor

### C++ example — register file

```cpp
struct RegisterMeta {
    uint32_t    width_bits;
    uint32_t    reset_value;
    bool        read_only;
    std::string name;
};

class RegisterFile {
public:
    RegisterFile(const std::vector<RegisterMeta>& meta)
        : meta_(meta), values_(meta.size(), 0) {
        for (std::size_t i = 0; i < meta_.size(); ++i)
            values_[i] = meta_[i].reset_value;
    }

    uint32_t read(uint32_t idx) const {
        sc_assert(idx < meta_.size());
        return values_[idx];
    }

    bool write(uint32_t idx, uint32_t val) {
        sc_assert(idx < meta_.size());
        if (meta_[idx].read_only) return false;
        values_[idx] = val & ((1u << meta_[idx].width_bits) - 1u);
        return true;
    }

    std::string dump() const {
        std::ostringstream oss;
        for (std::size_t i = 0; i < meta_.size(); ++i)
            oss << meta_[i].name << "=0x" << std::hex << values_[i] << " ";
        return oss.str();
    }

private:
    const std::vector<RegisterMeta>& meta_;   // shared intrinsic state
    std::vector<uint32_t>            values_; // per-register extrinsic state
};
```

---

## 22. Hardware Diagrams Reference

### 22.1 All 20 patterns — hardware structure mapping

```
  Pattern 01 — Pipeline Window
  ┌──F──┬──D──┬──I──┬──E──┬──W──┐   5-stage pipeline window
  └─────┴─────┴─────┴─────┴─────┘

  Pattern 02 — Ring Buffer
  ┌───┬───┬───┬───┬───┬───┬───┬───┐
  │   │   │ D │ D │ D │   │   │   │
  └───┴───┴───┴───┴───┴───┴───┴───┘
            ▲ head          ▲ tail

  Pattern 03 — CDC FIFO
  [Fast CLK domain] ──wr_ptr──▶ ASYNC FIFO ◀──rd_ptr── [Slow CLK domain]
                               (gray code sync)

  Pattern 04 — Burst Coalescer
  ├─Req0─┤├─Req1─┤  →  ├──────Merged──────┤

  Pattern 05 — Scoreboard
  ┌──────┬──────────┐
  │ Reg  │ Pending? │  RAW hazard: stall if src reg = pending dest reg
  └──────┴──────────┘

  Pattern 07 — NoC BFS Routing
  (0,0)──(1,0)──(2,0)   BFS finds min-hop path between any two nodes
    │      │      │
  (0,1)──(1,1)──(2,1)

  Pattern 11 — MPU Region Tree
       [full addr space]
      /                \
  [0x0000–0x7FFF]  [0x8000–0xFFFF]
    SRAM+Flash        Periph+DRAM

  Pattern 15 — Pipeline FIFO
  Producer ──[FIFO depth=16]──▶ Consumer
             backpressure ◀────┘

  Pattern 17 — AXI4-Lite FSM
  IDLE → ADDR_PHASE → DATA_PHASE → RESP_PHASE → IDLE
                                      └──ERROR──┘
```

---

## 23. AI‑Testability Rules

### Rule DSA‑01 — All DSA structures MUST expose `dump()` or `dump_state()`

Every container, FSM, arbiter, and cache model must be fully inspectable.

### Rule DSA‑02 — All computation functions MUST be pure

```cpp
// ✅ Pure — no side effects
uint32_t hop_count(uint32_t src, uint32_t dst, uint32_t cols) const;
bool     has_raw_hazard(uint8_t reg) const;
int32_t  decode_address(uint64_t addr, uint32_t bits) const;
```

### Rule DSA‑03 — Container bounds MUST be compile-time constants

AI test harnesses need to know the maximum size of every structure to
generate valid stimulus.

```cpp
constexpr std::size_t ROB_DEPTH     = 192;
constexpr std::size_t LSQ_DEPTH     =  56;
constexpr std::size_t FIFO_DEPTH    =  16;
```

### Rule DSA‑04 — No `std::unordered_map` or `std::unordered_set` in any DSA pattern

Iteration order is hash-dependent and non-deterministic.

### Rule DSA‑05 — Overflow MUST be `SC_REPORT_FATAL`, never silent

```cpp
if (size() == CAPACITY) {
    SC_REPORT_FATAL(name(), "structure overflow — stimulus exceeds hardware bound");
}
```

---

## 24. Anti‑Patterns

| Anti‑Pattern | Hardware consequence | Fix |
|---|---|---|
| Naming structure after algorithm (`SlidingWindow`) | Hides hardware intent | Use hardware name (`IssueWindow`) |
| Unbounded container for pipeline buffer | Models infinite queue — hides stalls | Declare `constexpr` depth, add overflow check |
| `std::list` for LRU | Poor cache locality | Doubly-linked list with `std::map` index |
| `std::unordered_map` for address decode | Non-deterministic decode order | `std::map` or trie |
| Inline magic numbers for latency | Untraceable to hardware spec | Named `sc_time` constants |
| Random cache miss injection | Non-deterministic simulation | Deterministic trace-driven miss model |
| FSM with raw integer states | Invisible transitions | `enum class State` + `switch` |
| DFS without cycle detection | Infinite loop on combinational loop | Explicit `VisitState` tracking |
| Arbiter with `rand()` winner | Non-deterministic grant sequence | RR/priority/WFQ — all deterministic |
| Topo sort without cycle check | Silent incorrect schedule | Kahn's algorithm — detect cycle at end |

---

## 25. Checklist

Use in every code review for hardware-aligned DSA implementations.

### Naming
- [ ] Structure uses hardware name, not algorithm name
- [ ] Depth/capacity is a named `constexpr` constant

### Bounds & overflow
- [ ] Every container has an explicit hardware-derived capacity bound
- [ ] Overflow triggers `SC_REPORT_FATAL`, never silent drop or resize

### Determinism
- [ ] No `std::unordered_map` or `std::unordered_set`
- [ ] No `rand()` in any DSA computation
- [ ] Iteration over containers is always in sorted/insertion order

### Computation
- [ ] Lookup / query functions are `const` and pure
- [ ] No hidden state modified by `const` functions

### VP integration
- [ ] Latency added via `delay +=` for every DSA operation that models hardware timing
- [ ] Cache hit/miss annotates different latencies

### AI‑testability
- [ ] `dump()` or `dump_state()` method present
- [ ] All capacity bounds visible at construction time
- [ ] No floating-point in key comparisons or hash functions

---

## 26. Glossary

| Term | Definition |
|---|---|
| **Pipeline window** | Fixed number of in-flight instructions advancing through pipeline stages |
| **Ring buffer** | Circular array with head/tail pointers — O(1) push/pop, bounded capacity |
| **CDC FIFO** | Async FIFO with gray-code pointers for clock domain crossing |
| **Burst coalescing** | Merging contiguous memory requests into a single larger bus transaction |
| **Scoreboard** | Register-state tracking table for RAW/WAR/WAW hazard detection |
| **RAW hazard** | Read-After-Write: instruction B reads a register before instruction A writes it |
| **Topological sort** | Linear ordering of DAG nodes — used for dependency-respecting instruction schedules |
| **Union-Find** | DSU structure for O(α) connectivity queries — used for coherence domains |
| **Segment tree** | Range-query tree — used for MMU region and MPU protection lookup |
| **Fenwick tree** | Binary Indexed Tree — O(log n) prefix sums — used for accumulated latency |
| **Trie** | Prefix tree — used for bus address decode and routing tables |
| **LRU** | Least-Recently-Used eviction policy — O(1) with doubly-linked list + map |
| **Producer-consumer** | Decoupled pipeline stages connected by a bounded FIFO |
| **Observer** | Fan-out notification — interrupt controller drives multiple CPU IRQ lines |
| **FSM** | Finite State Machine — explicit states, transitions, and outputs |
| **Strategy** | Pluggable algorithm — arbiter policy selectable at construction time |
| **Adapter** | Interface converter — RTL pin-level to TLM transaction-level bridge |
| **Flyweight** | Shared intrinsic state — register metadata shared across register file entries |
| **NoC** | Network-on-Chip — on-die packet-switched interconnect |
| **MMU** | Memory Management Unit — hardware address translation |
| **MPU** | Memory Protection Unit — hardware access control for embedded systems |
| **CDC** | Clock Domain Crossing |
| **VP** | Virtual Prototype |
