# Glossary — Definitions for All Terms Used Across the SKILLS Standard

**Version:** 1.0 — July 2026  
**Standard:** Reference — Shared vocabulary for engineers, AI test harnesses, and code review

---

## How to Use

Reference this glossary in design documents, PR descriptions, code comments, and AI test harnesses
to ensure consistent interpretation. When raising a review comment, cite the rule and term (e.g.
*SC‑15 — sc_signal*).

---

## A

| Term | Definition |
|---|---|
| **AddressSanitizer** | Compiler instrumentation (`-fsanitize=address`) that detects memory errors (out-of-bounds, use-after-free) at runtime |
| **AI black-box testing** | AI agent drives typed stimulus into module interfaces and validates outputs against a golden reference, without access to internal implementation |
| **AiTestable** | Base interface requiring `dump_state()`, `dump_stats()`, `dump_config()`, and `reset()` — every simulation module must implement it |
| **apply_stimulus()** | Typed method that injects a `Stimulus` struct into a module without directly accessing members |
| **Arbitration** | Mechanism to grant a shared resource to one of N requesters — policies: round-robin, fixed-priority, weighted fair queuing, TDMA |
| **AXI4** | ARM AMBA Advanced eXtensible Interface version 4 — industry-standard high-performance on-chip bus protocol |
| **Async FIFO** | FIFO with separate write and read clock domains; uses gray-code pointers and 2-FF synchronisers |

---

## B

| Term | Definition |
|---|---|
| **b_transport** | TLM blocking transport — initiator blocks until target returns; all latency accumulated via `delay +=` |
| **Backpressure** | Downstream signal that stalls an upstream producer when the consumer's queue is full |
| **Bandwidth** | Maximum data rate of a channel, expressed as bytes per nanosecond (bytes/ns) or GB/s |
| **Binary Indexed Tree** | See *Fenwick tree* |
| **BFS** | Breadth-First Search — graph traversal that finds shortest paths; used for NoC routing table construction |
| **Bounded FIFO** | FIFO with a compile-time or construction-time capacity limit matching a hardware specification |
| **Burst** | A single TLM transaction carrying multiple bytes (data_length > bus_width) — one arbitration grant, N beats of data |
| **Busy cycles** | Clock cycles during which a bus or resource is actively transferring data — used to compute utilisation |

---

## C

| Term | Definition |
|---|---|
| **Cache hit** | Requested address found in cache; served at `hit_latency` |
| **Cache line** | The unit of transfer between cache levels — typically 64 bytes |
| **Cache miss** | Requested address not found in cache; data must be fetched from the next level |
| **CAS latency** | Column Address Strobe latency — DRAM column access time after row is open |
| **CDC** | Clock Domain Crossing — a signal transitioning from one clock domain to another; requires a synchroniser |
| **Checkpoint** | Serialised performance counter snapshot allowing interval measurement (warm-up excluded) |
| **CPI** | Cycles Per Instruction — inverse of IPC; lower is better |
| **CRTP** | Curiously Recurring Template Pattern — advanced C++ inheritance technique; **forbidden** in modelling code |
| **Crossbar** | N×M switch fabric that allows any master to connect to any slave simultaneously without head-of-line blocking |

---

## D

| Term | Definition |
|---|---|
| **Data hazard** | Pipeline conflict where an instruction requires a result not yet produced by an earlier instruction |
| **Delta cycle** | A zero-simulation-time evaluation step used by the SystemC kernel to settle signals within one simulation instant |
| **Dependency injection** | Passing collaborator objects through constructor or method parameters — enables mocking and testing |
| **Determinism** | Property that identical inputs and initial state produce identical outputs, every run, on every machine |
| **DFS** | Depth-First Search — graph traversal that explores deep paths; used for dependency graph walk and loop detection |
| **DMA** | Direct Memory Access — hardware block that transfers data between memory regions without CPU involvement |
| **dump_config()** | Method returning a stable `key=value` string of all construction-time parameters |
| **dump_state()** | Method returning a stable `key=value` string of all state that affects output — must be `const` and side-effect free |
| **dump_stats()** | Method returning a stable `key=value` string of performance counters (transactions, latency, hit rate, utilisation) |

---

## E

| Term | Definition |
|---|---|
| **Elaboration phase** | SystemC simulation phase before `sc_start()` — module construction, port binding, process registration |
| **Enum class** | C++11 scoped enumeration — prevents accidental integer promotion and name collisions; mandatory for FSM states |
| **Explicit constructor** | Constructor marked `explicit` — prevents implicit single-argument construction |

---

## F

| Term | Definition |
|---|---|
| **FE_TONEAREST** | IEEE 754 round-to-nearest floating-point rounding mode — set at module construction to ensure deterministic FP |
| **Fenwick tree** | Binary Indexed Tree — O(log n) prefix sum queries and point updates; used to model accumulated pipeline latency |
| **FIFO** | First-In First-Out bounded queue — fundamental hardware buffer between pipeline stages |
| **FR-FCFS** | First-Ready, First-Come-First-Served — DRAM scheduler that prioritises already-open-row requests |
| **FSM** | Finite State Machine — explicit states (`enum class`), transitions (`switch`), and outputs; mandatory for all protocol and control logic |
| **Flyweight** | Design pattern sharing immutable intrinsic state across many objects — used for register bank metadata |
| **Fuzz harness** | Test harness using seeded PRNG to generate reproducible random stimulus sequences |

---

## G

| Term | Definition |
|---|---|
| **Golden reference** | Minimal, provably-correct C++ model of expected functional behaviour — no timing, no SystemC; used as AI comparison baseline |
| **Gray code** | Binary encoding where adjacent values differ by exactly one bit — used in CDC FIFO pointer arithmetic to prevent metastability-induced counter errors |

---

## H

| Term | Definition |
|---|---|
| **Hazard** | A pipeline conflict that requires stalling or flushing — types: RAW (data), WAR (data), WAW (data), structural, control |
| **Hit rate** | Fraction of cache accesses that result in a hit — `hits / (hits + misses)` |
| **Hot path** | Code executed frequently during simulation: `SC_METHOD` callbacks, `b_transport` handlers, tight simulation loops |

---

## I

| Term | Definition |
|---|---|
| **IPC** | Instructions Per Cycle — pipeline throughput metric; `IPC = insns_retired / total_cycles` |
| **Invariant** | A condition that must always be true for a correctly-used object — verified with `sc_assert` |

---

## K

| Term | Definition |
|---|---|
| **key=value** | Log format where every field is `name=value` — machine-parseable by AI test harnesses using regex |
| **Kahn's algorithm** | O(V+E) topological sort using in-degree counting and a queue — detects cycles; used for instruction scheduling |

---

## L

| Term | Definition |
|---|---|
| **Latency** | Time from request issue to response available — decomposed into: arbitration + queueing + access + bandwidth components |
| **LeakSanitizer** | Compiler instrumentation (`-fsanitize=leak`) that detects memory leaks at program exit |
| **Little's Law** | `L = λW` — average queue length equals arrival rate times average wait time; used for queueing delay models |
| **LRU** | Least-Recently-Used eviction policy — O(1) with doubly-linked list + `std::map` index |
| **LSQ** | Load/Store Queue — hardware buffer tracking in-flight memory operations in an out-of-order processor |

---

## M

| Term | Definition |
|---|---|
| **Manhattan distance** | Shortest path in a 2D grid: `|x1-x2| + |y1-y2|` — used for NoC hop count in mesh topology |
| **Memory manager** | `tlm::tlm_mm_interface` implementation that pools TLM payload objects to avoid per-transaction `new` |
| **Metastability** | Transient undefined state when a flip-flop samples a changing input — resolved by synchroniser; modelled as fixed latency |
| **Miss penalty** | Additional latency incurred on a cache miss — time to fetch data from the next level |
| **MMU** | Memory Management Unit — hardware that performs virtual-to-physical address translation |
| **MPU** | Memory Protection Unit — hardware that enforces access permissions on physical address regions (common in embedded systems without full MMU) |
| **Move semantics** | C++11 feature transferring resource ownership without copying — `std::move()`, move constructor, move assignment |

---

## N

| Term | Definition |
|---|---|
| **nb_transport_bw** | TLM non-blocking backward transport — target notifies initiator; must not block |
| **nb_transport_fw** | TLM non-blocking forward transport — initiator sends request; must not block |
| **NoC** | Network-on-Chip — on-die packet-switched interconnect connecting processor cores, caches, and memory controllers |
| **Non-owning pointer** | Raw pointer `T*` that observes but does not own its target — must not be deleted by the observer |

---

## O

| Term | Definition |
|---|---|
| **Object pool** | Pre-allocated fixed-size set of objects reused across transactions to avoid runtime heap allocation |
| **Open-page policy** | DRAM scheduling policy that leaves the last-accessed row activated — subsequent accesses to the same row are row hits |
| **Operator==** | Equality comparison — mandatory for `sc_signal<T>` payload types for change detection |
| **Out-of-order execution** | Processor executing instructions in a different order than program order, using a ROB to commit in-order |
| **Owning pointer** | Pointer responsible for deleting its target — expressed as `std::unique_ptr<T>` in this codebase |

---

## P

| Term | Definition |
|---|---|
| **Payload** | TLM transaction data — `tlm::tlm_generic_payload` carries command, address, data pointer, length, byte enables, response status |
| **Performance model** | A simulation model that quantifies timing (latency, bandwidth, throughput) in addition to functional behaviour |
| **Pipeline** | Sequence of processing stages where data flows and is processed in steps; each stage maps to an `SC_MODULE` |
| **Pool** | See *Object pool* |
| **POR state** | Power-On-Reset state — the exact initial state of all registers and buffers immediately after reset |
| **Pure function** | Function that returns a value based only on its inputs with no observable side effects — mandatory for all lookup/compute methods |

---

## Q

| Term | Definition |
|---|---|
| **Queue** | A bounded buffer between pipeline stages — modelled with a declared hardware depth constant |
| **Queueing delay** | Time a request waits in a queue before being served — increases with occupancy |

---

## R

| Term | Definition |
|---|---|
| **RAII** | Resource Acquisition Is Initialization — resource lifetime is tied to object lifetime; destructor releases the resource |
| **RAS latency** | Row Address Strobe latency — DRAM row activation time before column access can begin |
| **RAW hazard** | Read-After-Write data dependency — instruction B reads a register before instruction A has written it |
| **Register file** | Hardware array of programmer-visible registers — modelled as `std::array<uint32_t, N>` |
| **reset()** | Method that restores a module to its exact power-on-reset state — mandatory for AI test isolation |
| **reset_stats()** | Method that clears performance counters without affecting functional state — enables warm-up exclusion |
| **ROB** | Reorder Buffer — hardware buffer holding in-flight instructions in program order for out-of-order processors |
| **Round-robin** | Arbitration policy cycling through requesting masters in order — fair, O(1) |

---

## S

| Term | Definition |
|---|---|
| **SC_CTHREAD** | Clocked SystemC thread — variant of SC_THREAD with synchronous reset support |
| **SC_HAS_PROCESS** | Macro required when a SystemC module has a named constructor (not using `SC_CTOR`) |
| **SC_METHOD** | SystemC combinational process — fires when inputs change, must not block, must not allocate |
| **SC_THREAD** | SystemC sequential process — suspends at `wait()`, models multi-cycle protocols |
| **sc_assert** | SystemC assertion macro — integrates with simulation error handler; preferred over `<cassert>` |
| **sc_event** | SystemC primitive that threads can wait on; used for custom synchronisation |
| **sc_fifo** | SystemC bounded FIFO channel with blocking read/write and correct delta-cycle semantics |
| **sc_signal** | SystemC typed wire with delta-cycle update semantics — notifies processes when value changes |
| **sc_time** | SystemC simulation time type — value plus unit (SC_NS, SC_PS, etc.) |
| **sc_time_stamp()** | Returns current simulation time — the only permitted time source in simulation code |
| **Scoreboard** | Register-state tracking table for RAW/WAR/WAW hazard detection in out-of-order pipelines |
| **SFINAE** | Substitution Failure Is Not An Error — advanced template technique; **forbidden** in modelling code |
| **Snapshot** | The string returned by `dump_state()` at a specific simulation instant — used for AI comparison |
| **Spurious delta firing** | An SC_METHOD firing caused by missing `operator==` on a signal payload, even though the value did not change |
| **Stimulus** | Typed struct encoding one test input; serialisable and deserialisable; injected via `apply_stimulus()` |
| **Store buffer** | Hardware buffer holding pending stores before they are written to cache — modelled as bounded `std::array` |

---

## T

| Term | Definition |
|---|---|
| **TDMA** | Time-Division Multiple Access — slot-based bus arbitration guaranteeing bounded worst-case access time |
| **Throughput** | Actual sustained data rate or instruction rate under load — affected by stalls, contention, and queueing |
| **Timing annotation** | The `sc_time& delay` parameter in `b_transport` — accumulates all latency contributions via `+=` |
| **TLM** | Transaction Level Modelling — OSCI standard for abstract bus communication between SystemC modules |
| **TLM‑2.0** | The current (2008) version of the OSCI TLM standard — defines `b_transport`, `nb_transport`, and `tlm_generic_payload` |
| **tlm_generic_payload** | Standard TLM payload type — carries command, address, data pointer, data length, byte enables, and response status |
| **Trie** | Prefix tree — used for bus address decode and NoC routing tables; O(key_bits) lookup |
| **TLB** | Translation Lookaside Buffer — hardware cache for virtual-to-physical address translations |
| **Topological sort** | Linear ordering of DAG nodes respecting all edge directions — used for instruction scheduling |

---

## U

| Term | Definition |
|---|---|
| **UB** | Undefined Behaviour — the C++ standard places no constraints on what happens; compilers may do anything |
| **Union-Find** | Disjoint Set Union data structure — O(α) per operation; used for cache coherence domain and connectivity modelling |
| **Utilisation** | Fraction of cycles a resource is busy — `busy_cycles / total_cycles` |

---

## V

| Term | Definition |
|---|---|
| **Value type** | Class with value semantics — copyable, comparable with `operator==`; e.g. `Packet`, `PhysAddr` |
| **VCD** | Value Change Dump — waveform file format for SystemC/RTL simulation; requires `operator<<` on signal types |
| **VP** | Virtual Prototype — full-system SystemC/TLM simulation used for software bring-up and performance analysis |

---

## W

| Term | Definition |
|---|---|
| **WAR hazard** | Write-After-Read — instruction B writes a register before instruction A has read it |
| **WAW hazard** | Write-After-Write — two instructions write the same register; the second write must not be lost |
| **WCET** | Worst-Case Execution Time — maximum time a task can take; relevant for real-time VP modelling with TDMA arbitration |
| **Write-back** | Cache write policy where dirty lines are written to the next level only on eviction |
| **Write-through** | Cache write policy where every store is immediately propagated to the next level |

---

## X

| Term | Definition |
|---|---|
| **XY routing** | NoC deterministic routing: first traverse all X hops, then all Y hops — deadlock-free in 2D mesh |

---

## Z

| Term | Definition |
|---|---|
| **Zero-copy** | Technique of passing buffer pointers without copying data — requires explicit lifetime documentation |
| **SC_ZERO_TIME** | Equivalent to `sc_time(0, SC_NS)` — represents zero simulation time delay |

---

## Abbreviations Quick Reference

| Abbreviation | Full Term |
|---|---|
| AXI | Advanced eXtensible Interface |
| BFS | Breadth-First Search |
| CDC | Clock Domain Crossing |
| CPI | Cycles Per Instruction |
| CRTP | Curiously Recurring Template Pattern |
| DFS | Depth-First Search |
| DMA | Direct Memory Access |
| DSU | Disjoint Set Union (Union-Find) |
| EU | Execution Unit |
| FSM | Finite State Machine |
| IPC | Instructions Per Cycle |
| LSQ | Load/Store Queue |
| LRU | Least-Recently-Used |
| MMU | Memory Management Unit |
| MPU | Memory Protection Unit |
| NoC | Network-on-Chip |
| POR | Power-On-Reset |
| RAII | Resource Acquisition Is Initialization |
| RAS | Row Address Strobe |
| ROB | Reorder Buffer |
| SC | SystemC |
| SFINAE | Substitution Failure Is Not An Error |
| TLB | Translation Lookaside Buffer |
| TLM | Transaction Level Modelling |
| UB | Undefined Behaviour |
| VCD | Value Change Dump |
| VP | Virtual Prototype |
| WCET | Worst-Case Execution Time |
