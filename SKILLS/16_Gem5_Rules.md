# gem5 C++ Engineering Rules — Syntax, Patterns & Idioms

**Version:** 2.0 — July 2026
**Standard:** Strict — Mandatory for All gem5 Contributors & <5‑Year Engineers
**Source:** Deep-extracted from `src/cpu/o3/*.cc`, `src/cpu/o3/*.hh`, `src/mem/*.hh`,
`src/base/*.hh`, `src/sim/*.hh`, `CONTRIBUTING.md`, `.clang-format`
**Rule range:** G‑01 — G‑135 (72 new rules added in v2.0)
**Sections:** 41 sections including LRM-depth: DynInst lifecycle, register rename, scoreboard,
SMT policies, statistics deep dive, probe points, event queue, drain protocol,
memory system, RefCounting, utility types, CRTP, ports, squash state machine
**Prerequisites:** `02_C++_Rules.md`, `09_Class_Design.md`

---

## Table of Contents

1. [Philosophy of gem5 C++ Code](#1-philosophy-of-gem5-c-code)
2. [File & Header Rules](#2-file--header-rules)
3. [Naming Conventions](#3-naming-conventions)
4. [Formatting & Style Rules](#4-formatting--style-rules)
5. [Namespace Rules](#5-namespace-rules)
6. [gem5 Type System](#6-gem5-type-system)
7. [Class Design in gem5](#7-class-design-in-gem5)
8. [SimObject & Parameter Rules](#8-simobject--parameter-rules)
9. [Inter‑Stage Communication — TimeBuffer & Wire](#9-interstage-communication--timebuffer--wire)
10. [gem5 Memory System — Packet & Request](#10-gem5-memory-system--packet--request)
11. [Logging & Debugging — DPRINTF / panic / fatal](#11-logging--debugging--dprintf--panic--fatal)
12. [Statistics — `statistics::Group`](#12-statistics--statisticsgroup)
13. [SConscript & Build Rules](#13-sconscript--build-rules)
14. [O3 CPU Architecture Patterns](#14-o3-cpu-architecture-patterns)
15. [Error Handling Rules](#15-error-handling-rules)
16. [Python / SimObject Config Rules](#16-python--simobject-config-rules)
17. [Git & Contribution Rules](#17-git--contribution-rules)
18. [Anti‑Patterns](#18-anti-patterns)
19. [Complete Code Examples from the Repo](#19-complete-code-examples-from-the-repo)
20. [Checklist](#20-checklist)
21. [Glossary](#21-glossary)

---

## 1. Philosophy of gem5 C++ Code

gem5 is a **discrete-event, cycle-accurate computer architecture simulator**.
Its C++ rules exist for three reasons:

| Reason | Implication |
|---|---|
| **Simulation correctness** | Deterministic, reproducible results across runs and machines |
| **Readability over cleverness** | Next reader must understand at a glance |
| **Architecture documentation** | Code is the specification — structure reflects silicon |

> **From `CONTRIBUTING.md`:** _"our style-guide must be adhered to"_ — the style
> guide is enforced by `.clang-format` and CI checks. A PR that fails CI will
> not be merged.

---

## 2. File & Header Rules

### Rule G‑01 — Header files use the `.hh` extension; source files use `.cc`

```
src/cpu/o3/cpu.hh        ✅ correct
src/cpu/o3/cpu.h         ❌ wrong extension
src/cpu/o3/cpu.cpp       ❌ wrong extension — gem5 uses .cc
```

### Rule G‑02 — Every header MUST have an include guard using the file path

The guard symbol encodes the full path, replacing `/` with `_` and
prepending/appending `__`:

```cpp
// ✅ From src/cpu/o3/comm.hh — exact gem5 pattern
#ifndef __CPU_O3_COMM_HH__
#define __CPU_O3_COMM_HH__

// ... declarations ...

#endif // __CPU_O3_COMM_HH__
```

```cpp
// ✅ From src/mem/packet.hh
#ifndef __MEM_PACKET_HH__
#define __MEM_PACKET_HH__
```

`#pragma once` is **not** the gem5 standard — use the path-encoded `#ifndef` guard.

### Rule G‑03 — Every file MUST have the BSD/ARM copyright block

```cpp
/*
 * Copyright (c) <YEAR> <HOLDER>
 * All rights reserved
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, ...
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, ...
 */
```

### Rule G‑04 — Include order: gem5 headers before system headers; `<Python.h>` first if needed

`.clang-format` enforces include sorting with these priorities:

| Priority | Pattern | Example |
|---|---|---|
| 1 | `<Python.h>` | Python embedding |
| 2 | `"file.hh"` (same directory, no path) | `"cpu.hh"` |
| 3 | `<system>` | `<vector>`, `<cassert>` |
| 4 | `<gem5/...>` | Public gem5 API |
| 5 | `"path/to/file.hh"` | `"cpu/o3/comm.hh"` |

```cpp
// ✅ Correct order (from src/cpu/o3/fetch.hh)
#include "arch/generic/decoder.hh"
#include "arch/generic/mmu.hh"
#include "base/random.hh"
#include "base/statistics.hh"
#include "cpu/o3/comm.hh"
#include "cpu/o3/dyn_inst_ptr.hh"
#include "cpu/timebuf.hh"
#include "mem/packet.hh"
#include "mem/port.hh"
#include "sim/eventq.hh"
```

### Rule G‑05 — Include only what the file directly uses

No transitive `#include` chains. If `comm.hh` needs `DynInstPtr`, it includes
`cpu/o3/dyn_inst_ptr.hh` directly — it does not rely on it being pulled in via
another header.

---

## 3. Naming Conventions

Extracted from `CONTRIBUTING.md` and `src/cpu/o3/cpu.hh`.

### Rule G‑06 — Naming table (mandatory)

| Symbol kind | Convention | Example from repo |
|---|---|---|
| Class / struct | `UpperCamelCase` | `CPU`, `DynInst`, `FetchStruct`, `ROB` |
| Member variable | `lowerCamelCase` | `numThreads`, `fetchWidth` |
| Member variable with public accessor | `_lowerCamelCase` (leading underscore) | `_status`, `_fooBar` |
| Local variable | `snake_case` | `num_insts`, `fetch_pc` |
| Function / method | `lowerCamelCase` | `tick()`, `squash()`, `getFooBar()` |
| Function parameter | `snake_case` | `int parameter_one`, `ThreadID tid` |
| Macro | `ALL_CAPS_WITH_UNDERSCORES` | `GEM5_DEPRECATED`, `EXAMPLE_MACRO` |
| Enum value | `UpperCamelCase` (inside `enum`) | `Running`, `Idle`, `Halted` |
| Namespace | `lowercase` | `gem5`, `o3` |
| Template parameter | `UpperCamelCase` | `class Impl`, `typename T` |

```cpp
// ✅ Correct — from src/cpu/o3/cpu.hh
class CPU : public BaseCPU
{
  public:
    enum Status { Running, Idle, Halted, Blocked, SwitchedOut };

    BaseMMU *mmu;            // member, lowerCamelCase
    Status _status;          // member with accessor, leading underscore

    void
    tick();                  // method, lowerCamelCase, return type on own line

    int
    getNumThreads(ThreadID tid) const;  // parameter: snake_case
};
```

### Rule G‑07 — Template parameters use `UpperCamelCase`

```cpp
template <class Impl>   // ✅ UpperCamelCase
class Fetch { ... };
```

---

## 4. Formatting & Style Rules

All formatting is enforced by `.clang-format` (BasedOnStyle: LLVM with gem5 overrides).

### Rule G‑08 — 4 spaces per indent, never tabs

```cpp
// ✅
void
tick()
{
    if (status == Running) {
        doWork();
    }
}

// ❌ Tab characters forbidden
void tick() {
	doWork();   // tab — rejected by CI
}
```

### Rule G‑09 — Maximum 79 characters per line

Lines exceeding 79 characters are rejected by CI.

```cpp
// ✅ Multi-line break for long lines
fatal("fetchWidth (%d) is larger than compiled limit (%d),\n",
      params.fetchWidth, MaxWidth);
```

### Rule G‑10 — Function return type on its own line for definitions

```cpp
// ✅ Definition — return type on own line (from CONTRIBUTING.md example)
int
CPU::getNumThreads(ThreadID tid) const
{
    return numThreads;
}

// ❌ Return type on same line as function name (declarations in .hh are fine)
int CPU::getNumThreads(ThreadID tid) const { ... }
```

### Rule G‑11 — Function/class/struct braces on their own line

```cpp
// ✅ Correct (BraceWrapping: AfterFunction/Class/Struct: true)
class Fetch
{
  public:
    void tick();
};

void
Fetch::tick()
{
    // ...
}
```

### Rule G‑12 — `if`/`for`/`while` opening brace on the same line as the condition

```cpp
// ✅ Correct (AfterControlStatement: false)
if (cacheBlocked) {
    return;
}

for (int i = 0; i < numThreads; i++) {
    fetchStatus[i] = Idle;
}

// ❌ Wrong — brace on new line after control statement
if (cacheBlocked)
{
    return;
}
```

### Rule G‑13 — Always use braces after control statements

`.clang-format` has `InsertBraces: true` — even single-statement bodies need braces.

```cpp
// ✅
if (cacheBlocked) {
    return;
}

// ❌ No-brace single line — rejected by clang-format
if (cacheBlocked)
    return;
```

### Rule G‑14 — Access modifiers indented 2 spaces; members/methods indented 4 spaces

```cpp
// ✅ Correct — from CONTRIBUTING.md example
class ExampleClass
{
  private:              // 2 spaces
    int _fooBar;        // 4 spaces
    int barFoo;

  public:               // 2 spaces
    int
    getFooBar()         // 4 spaces
    {
        return _fooBar;
    }
};
```

### Rule G‑15 — Pointer/reference on the right (attached to variable name)

```cpp
// ✅ Correct (PointerAlignment: Right)
Packet *pkt;
const RequestPtr &req;

// ❌ Wrong
Packet* pkt;
const RequestPtr& req;
```

### Rule G‑16 — Constructor initialisers: each on its own line, `:` before first

```cpp
// ✅ Correct (BreakConstructorInitializers: BeforeColon)
Fetch::Fetch(CPU *_cpu, const BaseO3CPUParams &params)
    : cpu(_cpu),
      fetchWidth(params.fetchWidth),
      numThreads(params.numThreads)
{
}
```

---

## 5. Namespace Rules

### Rule G‑17 — All gem5 code lives inside `namespace gem5`

```cpp
// ✅ From src/cpu/o3/cpu.hh
namespace gem5
{

// ... all code here ...

} // namespace gem5
```

### Rule G‑18 — Subsystems use a nested namespace

```cpp
// ✅ O3 CPU code in namespace gem5::o3
namespace gem5
{
namespace o3
{

class CPU : public BaseCPU { ... };

} // namespace o3
} // namespace gem5
```

### Rule G‑19 — Closing brace MUST have `// namespace <name>` comment

```cpp
} // namespace o3
} // namespace gem5
```

### Rule G‑20 — Namespace bodies are NOT indented

```cpp
// ✅ Correct (NamespaceIndentation: None)
namespace gem5
{

class CPU { };   // no extra indent from namespace

} // namespace gem5

// ❌ Wrong
namespace gem5
{
    class CPU { };   // extra indent from namespace — forbidden
}
```

### Rule G‑21 — No `using namespace` in headers — explicit qualification only

```cpp
// ✅
gem5::Tick t = curTick();

// ❌ In a header
using namespace gem5;
```

---

## 6. gem5 Type System

Core types are defined in `src/base/types.hh`. Always use these — never raw
`int`, `long`, or `unsigned` for simulation quantities.

### Rule G‑22 — Use gem5 simulation types

| gem5 type | Underlying type | Purpose |
|---|---|---|
| `Tick` | `uint64_t` | Simulation time in ticks (1 Tick = 1 ps by default) |
| `Cycles` | integer | Clock cycle count — distinct from Tick to prevent mixing |
| `Counter` | `int64_t` | Statistics counter |
| `Addr` | `uint64_t` | Physical / virtual address |
| `MicroPC` | `uint16_t` | Micro-program counter |
| `RegVal` | `uint64_t` | Register value |
| `RegIndex` | `uint16_t` | Architectural register index |
| `ThreadID` | `int16_t` | Hardware thread identifier |
| `ContextID` | `int` | OS context identifier |
| `PortID` | `int16_t` | Memory port identifier |
| `Fault` | `std::shared_ptr<FaultBase>` | Fault/exception carrier |
| `InstSeqNum` | `uint64_t` | Instruction sequence number |

```cpp
// ✅ Correct — uses gem5 types
Tick curTick = cpu->clockEdge();
Addr fetchPC = pc[tid]->instAddr();
Cycles lat(3);

// ❌ Forbidden — raw types for simulation quantities
uint64_t curTick = ...;   // should be Tick
unsigned long addr = ...; // should be Addr
```

### Rule G‑23 — `DynInstPtr` is a reference-counted pointer — never raw `DynInst *` for ownership

```cpp
// ✅ Correct — DynInstPtr = RefCountingPtr<DynInst>
DynInstPtr inst = rob.readTailInst(tid);

// ❌ Wrong — raw pointer, no reference counting
DynInst *inst = rob.readTailInst(tid);
```

### Rule G‑24 — `PacketPtr` is `Packet *` — ownership follows gem5 memory system conventions

```cpp
// ✅ Correct usage (from fetch.hh)
PacketPtr retryPkt;
bool recvTimingResp(PacketPtr pkt);
```

---

## 7. Class Design in gem5

### Rule G‑25 — Stage classes (Fetch, Decode, Rename, IEW, Commit) follow this structure

Each pipeline stage is a class (not an `SC_MODULE`) with:
- A pointer to the owning `CPU` object
- Named `TimeBuffer::wire` connections to adjacent stages
- A `tick()` method called by `CPU::tick()` each cycle
- An inner `*StatGroup : public statistics::Group` struct

```cpp
// ✅ Pattern extracted from src/cpu/o3/fetch.hh
class Fetch
{
  public:
    /** Inner port class for cache access */
    class IcachePort : public RequestPort { ... };

    /** Constructor */
    Fetch(CPU *_cpu, const BaseO3CPUParams &params);

    /** Main per-cycle method */
    void tick();

    /** Squash from a later stage */
    void squash(const PCStateBase &new_pc, const InstSeqNum seq_num,
                DynInstPtr &squashing_inst, ThreadID tid);

    /** Statistics nested struct */
    struct FetchStatGroup : public statistics::Group
    {
        statistics::Scalar predictedBranches;
        statistics::Vector status;
        statistics::Formula idleRate;
        // ...
    } fetchStats;

  private:
    CPU *cpu;
    // TimeBuffer wires for each adjacent stage
    TimeBuffer<TimeStruct>::wire toCommit;
    TimeBuffer<FetchStruct>::wire toDecode;
    TimeBuffer<DecodeStruct>::wire fromDecode;
};
```

### Rule G‑26 — Never inherit from multiple concrete base classes — use composition

gem5 stage classes compose, not inherit. `Fetch` *has-a* `IcachePort`, not
*is-a*.

### Rule G‑27 — Private members use `lowerCamelCase` — NOT trailing underscores

```cpp
// ✅ gem5 style (from src/cpu/o3/fetch.hh)
CPU *cpu;
unsigned fetchWidth;
bool cacheBlocked;

// ❌ SKILLS style trailing underscore — do NOT use in gem5 code
CPU *cpu_;
unsigned fetchWidth_;
```

> **Important:** gem5 uses `lowerCamelCase` for members (no trailing underscore),
> which differs from the SKILLS `02_C++_Rules.md` convention. In this repo,
> follow gem5 convention.

---

## 8. SimObject & Parameter Rules

### Rule G‑28 — Every configurable hardware component is a `SimObject`

A `SimObject` is the bridge between Python configuration (`.py` files) and
C++ simulation objects. It defines parameters that are set from Python config scripts.

```python
# ✅ From src/cpu/o3/BaseO3CPU.py
class BaseO3CPU(BaseCPU):
    type = 'BaseO3CPU'
    cxx_header = "cpu/o3/cpu.hh"
    cxx_class = 'gem5::o3::CPU'

    fetchWidth = Param.Unsigned(8, "Fetch width")
    decodeWidth = Param.Unsigned(8, "Decode width")
    robSize = Param.Unsigned(192, "ROB size")
```

### Rule G‑29 — C++ constructor receives params via `const BaseO3CPUParams &`

```cpp
// ✅ Correct pattern
CPU::CPU(const BaseO3CPUParams &params)
    : BaseCPU(params),
      fetchWidth(params.fetchWidth),
      decodeWidth(params.decodeWidth)
{
    // validate
    if (params.fetchWidth > MaxWidth) {
        fatal("fetchWidth (%d) is larger than compiled limit (%d),\n",
              params.fetchWidth, MaxWidth);
    }
}
```

### Rule G‑30 — Compiled limits use `static constexpr` in a `limits.hh`

```cpp
// ✅ From src/cpu/o3/limits.hh — exact pattern
namespace gem5
{
namespace o3
{

static constexpr int MaxWidth   = 16;
static constexpr int MaxThreads = 4;

} // namespace o3
} // namespace gem5
```

---

## 9. Inter‑Stage Communication — TimeBuffer & Wire

### Rule G‑31 — Use `TimeBuffer<T>` for inter-stage communication, not raw signals

`TimeBuffer<T>` is a cyclic array that models a pipeline register with
configurable read-latency and write-latency. Stages write to a wire, and
the CPU advances all buffers each cycle in `CPU::tick()`.

```cpp
// ✅ From src/cpu/o3/cpu.hh — declaration
TimeBuffer<TimeStruct>  timeBuffer;
TimeBuffer<FetchStruct> fetchQueue;
TimeBuffer<DecodeStruct> decodeQueue;
TimeBuffer<RenameStruct> renameQueue;
TimeBuffer<IEWStruct>   iewQueue;
```

### Rule G‑32 — Communication structs are plain structs in `comm.hh`

```cpp
// ✅ From src/cpu/o3/comm.hh — exact pattern
/** Struct that defines the information passed from fetch to decode. */
struct FetchStruct
{
    int size;
    DynInstPtr insts[MaxWidth];
    Fault fetchFault;
    InstSeqNum fetchFaultSN;
    bool clearFetchFault;
};

/** Struct that defines the information passed from decode to rename. */
struct DecodeStruct
{
    int size;
    DynInstPtr insts[MaxWidth];
};
```

### Rule G‑33 — `insts[]` arrays in comm structs are sized with `MaxWidth`, not a runtime value

```cpp
// ✅ Compile-time constant from limits.hh
DynInstPtr insts[MaxWidth];   // MaxWidth = 16

// ❌ Runtime-sized — forbidden in comm structs
DynInstPtr *insts;            // pointer — no size guarantee
```

### Rule G‑34 — `TimeBuffer::wire` is the correct way to reference a time-displaced slot

```cpp
// ✅ Wires set up in CPU constructor
toIEW = renameQueue.getWire(0);       // write this cycle
fromIEW = iewQueue.getWire(-iewToRenameDelay);  // read from N cycles ago
```

---

## 10. gem5 Memory System — Packet & Request

### Rule G‑35 — Memory requests use `Request` + `Packet`

```
RequestPtr req = std::make_shared<Request>(addr, size, flags, requestorId);
PacketPtr  pkt = new Packet(req, MemCmd::ReadReq);
pkt->allocate();
port.sendTimingReq(pkt);
```

### Rule G‑36 — `PacketPtr` ownership follows the gem5 memory system protocol

- **Timing requests:** sender allocates; receiver may hold or return.
- **Timing responses:** responder may reuse the packet; sender must not access after `sendTimingReq` until `recvTimingResp`.
- Never `delete` a `PacketPtr` that is in-flight.

### Rule G‑37 — Use `MemCmd` enum for command type — never raw integers

```cpp
// ✅
PacketPtr pkt = new Packet(req, MemCmd::ReadReq);
if (pkt->isRead()) { ... }
if (pkt->isWrite()) { ... }

// ❌ Raw integer
PacketPtr pkt = new Packet(req, 0);   // what is 0?
```

### Rule G‑38 — Memory ports inherit from `RequestPort` or `ResponsePort`

```cpp
// ✅ From src/cpu/o3/fetch.hh
class IcachePort : public RequestPort
{
  protected:
    Fetch *fetch;
  public:
    IcachePort(Fetch *_fetch, CPU *_cpu);
  protected:
    virtual bool recvTimingResp(PacketPtr pkt);
    virtual void recvReqRetry();
};
```

---

## 11. Logging & Debugging — DPRINTF / panic / fatal

### Rule G‑39 — Use `DPRINTF` for debug logging — never `std::cout` or `printf`

`DPRINTF` is compiled out in non-debug builds and is controlled by named
debug flags (e.g. `Fetch`, `Commit`, `Activity`).

```cpp
// ✅ Correct (from src/cpu/o3/fetch.cc)
DPRINTF(Fetch, "[tid:%i] Waking up from cache miss.\n", tid);
DPRINTF(Activity, "Activating stage.\n");
DPRINTF(Fetch, "[tid:%i] Fetching cache line %#x for addr %#x\n",
        tid, fetchBufferPC[tid], pc);

// ❌ Forbidden
std::cout << "fetch: waking up from cache miss\n";
printf("tid %d: waking up\n", tid);
```

### Rule G‑40 — `DPRINTF` format strings use gem5 format specifiers

| Specifier | Meaning | Example |
|---|---|---|
| `%i` | Integer (like `%d`) | `[tid:%i]` |
| `%#x` | Hex with `0x` prefix | `%#x` for addresses |
| `%s` | String | `%s` for `PCStateBase::print()` |
| `%llu` | `uint64_t` (sequence numbers) | `[sn:%llu]` |

```cpp
// ✅ Correct format
DPRINTF(Commit, "[tid:%i] Instruction [sn:%llu] PC %s is head of ROB.\n",
        tid, inst->seqNum, inst->pcState());
```

### Rule G‑41 — `panic()` for impossible conditions — aborts simulation immediately

```cpp
// ✅ Unreachable code — programmer error
panic("cannot drain partially through a HTM transaction");
```

### Rule G‑42 — `fatal()` for user/configuration errors — aborts with message

```cpp
// ✅ Configuration error — user's fault
fatal("fetchWidth (%d) is larger than compiled limit (%d),\n",
      params.fetchWidth, MaxWidth);

fatal("numThreads (%d) is larger than compiled limit (%d),\n",
      params.numThreads, MaxThreads);
```

### Rule G‑43 — `panic_if()` / `fatal_if()` for conditional versions

```cpp
// ✅
fatal_if(params.fetchWidth > MaxWidth,
         "fetchWidth (%d) exceeds MaxWidth (%d)", params.fetchWidth, MaxWidth);

panic_if(!cpu->getInstPort().isConnected(),
         "Instruction port is not connected");
```

### Rule G‑44 — `warn()` for non-fatal configuration issues

```cpp
warn("fetchBuffer size (%u) is not a multiple of the cache block (%u).\n",
     fetchBufferSize, cacheBlkSize);
```

### Rule G‑45 — `assert()` for simulation invariants

```cpp
// ✅ From src/cpu/o3/fetch.cc
assert(bac != nullptr);
assert(ftq != nullptr);
assert(!cpu->switchedOut());
assert(isDrained());
assert(retryPkt == NULL);
```

---

## 12. Statistics — `statistics::Group`

### Rule G‑46 — Statistics are declared in a nested `*StatGroup` struct inside the class

```cpp
// ✅ From src/cpu/o3/fetch.hh — exact pattern
struct FetchStatGroup : public statistics::Group
{
    FetchStatGroup(CPU *cpu, Fetch *fetch);

    statistics::Vector   status;          // per-thread vector
    statistics::Scalar   predictedBranches;
    statistics::Scalar   miscStallCycles;
    statistics::Scalar   cacheLines;
    statistics::Scalar   icacheSquashes;
    statistics::Distribution nisnDist;   // distribution histogram
    statistics::Formula  idleRate;       // derived formula
} fetchStats;
```

### Rule G‑47 — Statistics MUST be named and described at construction

```cpp
// ✅ From fetch.cc
FetchStatGroup::FetchStatGroup(CPU *cpu, Fetch *fetch)
    : statistics::Group(cpu, "fetch"),
      ADD_STAT(predictedBranches, statistics::units::Count::get(),
               "Number of branches that fetch has predicted taken"),
      ADD_STAT(cacheLines, statistics::units::Count::get(),
               "Number of cache lines fetched")
{
    idleRate = status[Idle] / cpu->baseStats.numCycles;
}
```

### Rule G‑48 — Use `statistics::Scalar` for single counts, `statistics::Vector` for per-thread

```cpp
statistics::Scalar  totalInstructions;   // one number
statistics::Vector  instrPerThread;      // one per thread
```

### Rule G‑49 — Never increment statistics with `++` on `Scalar` — use `+=` or the stat's `++` operator

```cpp
// ✅
fetchStats.predictedBranches++;
fetchStats.cacheLines += numFetched;

// ❌ Assign as if it were an integer
fetchStats.predictedBranches = fetchStats.predictedBranches + 1;  // wrong API
```

---

## 13. SConscript & Build Rules

### Rule G‑50 — Every new `.cc`/`.hh` file MUST be registered in the `SConscript`

```python
# ✅ From src/cpu/o3/SConscript — pattern
if env['TARGET_ISA'] != 'null':
    Source('cpu.cc')
    Source('fetch.cc')
    Source('decode.cc')
    Source('commit.cc')
    DebugFlag('Fetch')
    DebugFlag('Commit')
    SimObject('BaseO3CPU.py', sim_objects=['BaseO3CPU'])
```

### Rule G‑51 — Debug flags are registered with `DebugFlag()` in SConscript

```python
# ✅ Each DPRINTF flag must be declared
DebugFlag('Fetch')
DebugFlag('Activity')
DebugFlag('Scoreboard')
```

### Rule G‑52 — `SimObject()` registers Python config files with their C++ class

```python
# ✅
SimObject('BaseO3CPU.py', sim_objects=['BaseO3CPU'])
SimObject('O3CPU.py',     sim_objects=[], tags=['isa'])
```

### Rule G‑53 — Compile-time ISA guards use `env['TARGET_ISA']`

```python
# ✅ Only compile for non-null ISA
if env['TARGET_ISA'] != 'null':
    Source('isa_specific_file.cc')
```

---

## 14. O3 CPU Architecture Patterns

Patterns extracted from `src/cpu/o3/` that every contributor must know.

### 14.1 Pipeline stage ownership

```
CPU owns all stages:
  Fetch  → Decode → Rename → IEW (Issue/Execute/Writeback) → Commit

CPU::tick() calls each stage's tick() in reverse order:
  commit.tick() → iew.tick() → rename.tick() → decode.tick() → fetch.tick()
  (reverse order to prevent same-cycle forwarding)
```

### 14.2 `DynInst` — the in-flight instruction object

`DynInst` is the central data structure carrying all state for a single in-flight instruction. It is reference-counted via `DynInstPtr`.

```cpp
// Fields every stage interacts with (from src/cpu/o3/dyn_inst.hh)
InstSeqNum seqNum;      // unique sequence number — monotonically increasing
const StaticInstPtr staticInst;  // decoded static instruction
PCStateBase *pcState;   // PC at issue
bool squashed;          // marked for squash
bool executed;          // execution complete
Fault fault;            // any fault generated
```

### 14.3 ROB — Reorder Buffer

```cpp
// From src/cpu/o3/rob.hh
class ROB
{
  public:
    /** ROB statuses */
    enum Status { Running, Idle, ROBSquashing };

    typedef std::pair<RegIndex, RegIndex> UnmapInfo;
    typedef std::list<DynInstPtr>::iterator InstIt;

    // Commit from head, allocate at tail
    bool isFull(ThreadID tid) const;
    bool isEmpty(ThreadID tid) const;
    DynInstPtr readHeadInst(ThreadID tid);
    void retireHead(ThreadID tid);
};
```

### 14.4 Scoreboard — register readiness tracking

```cpp
// From src/cpu/o3/scoreboard.hh
// Tracks which physical registers have results written back
// Used by IEW to determine if operands are ready for issue
```

### 14.5 Squash protocol

When a misprediction or fault is detected (in Commit or IEW), the stage:
1. Sets `squashing = true`
2. Writes the correct PC to the `TimeBuffer` back to Fetch
3. All earlier stages drain and discard in-flight instructions by checking `squashed` flag

---

## 15. Error Handling Rules

### Rule G‑54 — Use the gem5 error hierarchy in order

| Severity | Function | When to use |
|---|---|---|
| Fatal — user error | `fatal(fmt, ...)` | Bad config, parameter out of range |
| Fatal — conditional | `fatal_if(cond, fmt, ...)` | Check in one line |
| Panic — programmer error | `panic(fmt, ...)` | Should never happen |
| Panic — conditional | `panic_if(cond, fmt, ...)` | Inline invariant check |
| Warning | `warn(fmt, ...)` | Non-fatal misconfiguration |
| Assert | `gem5_assert(cond)` / `assert(cond)` | Debug-build invariant |

### Rule G‑55 — No C++ exceptions in simulation hot paths

gem5 uses `Fault` (a `shared_ptr<FaultBase>`) to propagate hardware faults
through the pipeline — not C++ exceptions.

```cpp
// ✅ gem5 fault propagation
Fault fault = cpu->read(req, data, tid);
if (fault != NoFault) {
    iewStage->generateTCEvent(tid);
}

// ❌ C++ exception — forbidden in simulation
throw std::runtime_error("memory fault");
```

---

## 16. Python / SimObject Config Rules

### Rule G‑56 — Python config files inherit from the correct gem5 base class

```python
# ✅ CPU config
class O3CPU(BaseO3CPU):
    type = 'O3CPU'
    cxx_header = "cpu/o3/cpu.hh"
    cxx_class  = 'gem5::o3::CPU'
```

### Rule G‑57 — Parameter names in Python MUST exactly match C++ `params.*` member names

```python
# ✅ Python
fetchWidth = Param.Unsigned(8, "Fetch width")

# ✅ C++ — must match exactly
CPU::CPU(const BaseO3CPUParams &params)
    : fetchWidth(params.fetchWidth)   // ← same name
```

### Rule G‑58 — Use `Param.Unsigned`, `Param.Int`, `Param.Bool`, `Param.String` appropriately

```python
fetchWidth    = Param.Unsigned(8,   "Fetch width in instructions")
smtNumFetchingThreads = Param.Int(1, "SMT threads to fetch from")
switched_out  = Param.Bool(False,   "Initially switched out")
```

---

## 17. Git & Contribution Rules

### Rule G‑59 — Develop on the `develop` branch — never on `stable`

```bash
git switch develop
git switch -c my-feature   # work on a local branch from develop
```

### Rule G‑60 — Commit message format: `subsystem,subsystem: Short description`

```
# ✅ Correct commit message format (from CONTRIBUTING.md)
cpu,o3: Fix ROB head pointer wraparound on full-ROB squash

The ROB head pointer was not correctly wrapped when a squash occurred
with the ROB exactly full, causing one entry to be leaked.

Jira Issue: https://gem5.atlassian.net/browse/GEM5-XXXX
```

```
# ❌ Wrong — no subsystem tag, no description
Fixed a bug in the ROB
```

### Rule G‑61 — One logical change per PR — keep PRs small and focused

### Rule G‑62 — All CI checks must pass before merge

CI runs: clang-format check, unit tests, style checks, and build tests.

```bash
# Run style check locally before pushing
cd /path/to/gem5
./util/style/check_style.py --fix src/cpu/o3/my_file.cc
```

### Rule G‑63 — Keep `git log` clean — squash fixup commits before final push

```bash
git rebase -i develop   # squash small fix commits
git push --force
```

---

## 18. Anti‑Patterns

| Anti‑Pattern | Consequence | gem5 Fix |
|---|---|---|
| `.h` / `.cpp` extensions | CI style check fails | Use `.hh` / `.cc` |
| `#pragma once` instead of path-encoded `#ifndef` | Non-standard for gem5 | `#ifndef __CPU_O3_FOO_HH__` |
| `std::cout` / `printf` logging | Bypasses debug flag system | `DPRINTF(Flag, ...)` |
| Raw `int`/`unsigned` for addresses | Type confusion with Tick/Cycles | `Addr`, `Tick`, `Cycles` |
| Raw `DynInst *` for ownership | Leak when squashed | `DynInstPtr` (ref-counted) |
| Statistics as plain member `int` | Not collected by gem5 stats framework | `statistics::Scalar` |
| `throw` in simulation | Bypasses fault mechanism | Return `Fault` object |
| Member trailing underscore (`cpu_`) | Wrong gem5 naming convention | `lowerCamelCase` (`cpu`) |
| Brace on new line after `if`/`for` | Rejected by `.clang-format` | Brace on same line |
| Return type on same line as function definition | Rejected by `.clang-format` | Return type on own line |
| Tabs | Rejected by CI | 4-space indent |
| Line > 79 chars | Rejected by CI | Break at 79 |
| Committing on `stable` branch | Not accepted upstream | Use `develop` branch |
| One giant PR with multiple features | Hard to review — likely rejected | One feature per PR |

---

## 19. Complete Code Examples from the Repo

### 19.1 Minimal correct header file structure

```cpp
/*
 * Copyright (c) 2026 Example Corp
 * All rights reserved
 * ...BSD license block...
 */

#ifndef __CPU_O3_MY_STAGE_HH__
#define __CPU_O3_MY_STAGE_HH__

#include "base/statistics.hh"
#include "base/types.hh"
#include "cpu/o3/comm.hh"
#include "cpu/o3/limits.hh"
#include "cpu/timebuf.hh"

namespace gem5
{

struct BaseO3CPUParams;

namespace o3
{

class CPU;

/**
 * MyStage implements the XYZ pipeline stage.
 */
class MyStage
{
  public:
    MyStage(CPU *_cpu, const BaseO3CPUParams &params);

    /** Main per-cycle entry point. */
    void tick();

    struct MyStageStats : public statistics::Group
    {
        MyStageStats(CPU *cpu, MyStage *stage);
        statistics::Scalar cyclesActive;
        statistics::Scalar squashes;
    } stageStats;

  private:
    CPU *cpu;
    unsigned width;
    unsigned numThreads;

    TimeBuffer<FetchStruct>::wire fromFetch;
    TimeBuffer<DecodeStruct>::wire toDecode;
};

} // namespace o3
} // namespace gem5

#endif // __CPU_O3_MY_STAGE_HH__
```

### 19.2 Minimal correct source file structure

```cpp
/*
 * Copyright (c) 2026 Example Corp
 * ...
 */

#include "cpu/o3/my_stage.hh"

#include "base/logging.hh"
#include "base/trace.hh"
#include "cpu/o3/cpu.hh"
#include "debug/MyStage.hh"
#include "params/BaseO3CPU.hh"

namespace gem5
{
namespace o3
{

MyStage::MyStage(CPU *_cpu, const BaseO3CPUParams &params)
    : cpu(_cpu),
      width(params.decodeWidth),
      numThreads(params.numThreads),
      stageStats(_cpu, this)
{
    if (width > MaxWidth) {
        fatal("decodeWidth (%d) exceeds MaxWidth (%d)\n", width, MaxWidth);
    }
}

void
MyStage::tick()
{
    for (ThreadID tid = 0; tid < numThreads; tid++) {
        if (!fromFetch->insts[tid]) {
            continue;
        }
        DPRINTF(MyStage, "[tid:%i] Processing instruction [sn:%llu]\n",
                tid, fromFetch->insts[tid]->seqNum);
        stageStats.cyclesActive++;
    }
}

MyStage::MyStageStats::MyStageStats(CPU *cpu, MyStage *stage)
    : statistics::Group(cpu, "my_stage"),
      ADD_STAT(cyclesActive, statistics::units::Cycle::get(),
               "Cycles this stage was active"),
      ADD_STAT(squashes, statistics::units::Count::get(),
               "Number of squashes received")
{
}

} // namespace o3
} // namespace gem5
```

### 19.3 `comm.hh` inter-stage struct pattern

```cpp
// ✅ From src/cpu/o3/comm.hh — exact pattern to follow for new stages
struct MyStageToNextStruct
{
    int size;                      // number of valid entries this cycle
    DynInstPtr insts[MaxWidth];    // instructions being forwarded
    bool squash;                   // squash signal
    InstSeqNum squashedSeqNum;     // first invalid sequence number
};
```

---

## 20. Checklist

Use this checklist for every gem5 PR.

### File & header
- [ ] File extension is `.hh` (header) or `.cc` (source)
- [ ] Include guard is path-encoded (`#ifndef __CPU_O3_FOO_HH__`)
- [ ] Copyright block present
- [ ] Includes in correct order (gem5 headers before system)
- [ ] Only directly-used headers included

### Naming
- [ ] Classes: `UpperCamelCase`
- [ ] Member variables: `lowerCamelCase` (no trailing underscore)
- [ ] Member variables with accessor: `_lowerCamelCase` (leading underscore)
- [ ] Local variables: `snake_case`
- [ ] Function parameters: `snake_case`
- [ ] Macros: `ALL_CAPS`
- [ ] Namespaces: `lowercase`

### Formatting (enforced by `.clang-format`)
- [ ] 4-space indent, no tabs
- [ ] Lines ≤ 79 characters
- [ ] Return type on own line in definitions
- [ ] Class/function braces on own line
- [ ] `if`/`for` braces on same line as condition
- [ ] Braces always present (even for single statements)
- [ ] Access modifiers indented 2 spaces, content 4 spaces
- [ ] Pointer `*` / reference `&` attached to variable name

### Namespaces
- [ ] All code in `namespace gem5`
- [ ] Subsystem code in nested namespace
- [ ] Closing braces have `// namespace <name>` comments
- [ ] No indentation inside namespace

### gem5 types
- [ ] `Tick` for simulation time, not `uint64_t`
- [ ] `Addr` for addresses, not `unsigned long`
- [ ] `DynInstPtr` for instruction ownership, not raw `DynInst *`
- [ ] `Fault` for hardware faults, not exceptions

### Logging & errors
- [ ] `DPRINTF` used, not `std::cout`/`printf`
- [ ] Debug flag registered in `SConscript`
- [ ] `fatal()` for configuration errors
- [ ] `panic()` for programmer errors
- [ ] `assert()` for simulation invariants
- [ ] No C++ `throw` in simulation code

### Statistics
- [ ] Stats declared in nested `*StatGroup : public statistics::Group`
- [ ] All stats registered with `ADD_STAT` in constructor
- [ ] `statistics::Scalar`/`Vector`/`Formula` used (not raw int)

### Build
- [ ] New `.cc` files registered in `SConscript`
- [ ] New debug flags registered with `DebugFlag()`
- [ ] New SimObjects registered with `SimObject()`

### Git
- [ ] Working on `develop` branch (not `stable`)
- [ ] Commit message: `subsystem: Short description` + body + Jira
- [ ] PR is small and focused on one change

---

## 21. Glossary

| Term | Definition |
|---|---|
| **`.hh` / `.cc`** | gem5 file extensions for C++ headers and sources |
| **`Tick`** | gem5 simulation time unit — `uint64_t`, 1 Tick = 1 ps by default |
| **`Cycles`** | Clock cycle count type — distinct from `Tick` to prevent mixing |
| **`Addr`** | Physical/virtual address type — `uint64_t` |
| **`DynInst`** | Dynamic instruction object — carries all in-flight state for one instruction |
| **`DynInstPtr`** | Reference-counted smart pointer to `DynInst` |
| **`PacketPtr`** | `Packet *` — gem5 memory request/response carrier |
| **`Fault`** | `shared_ptr<FaultBase>` — hardware fault/exception propagation type |
| **`InstSeqNum`** | Monotonically increasing instruction sequence number — `uint64_t` |
| **`ThreadID`** | Hardware SMT thread identifier — `int16_t` |
| **`RegVal`** | Register value type — `uint64_t` |
| **`TimeBuffer<T>`** | Cyclic array modelling a pipeline register with configurable latency |
| **`TimeBuffer::wire`** | Reference to a specific time-displaced slot in a `TimeBuffer` |
| **`DPRINTF`** | gem5 debug print macro — compiled out in non-debug builds |
| **`fatal()`** | Terminates simulation with user-facing error message (configuration error) |
| **`panic()`** | Terminates simulation with programmer error message (should-never-happen) |
| **`warn()`** | Non-fatal warning — simulation continues |
| **`SimObject`** | gem5 base class bridging Python configuration and C++ simulation |
| **`statistics::Group`** | Base class for nested statistics structs |
| **`statistics::Scalar`** | Single-value simulation statistic |
| **`statistics::Vector`** | Per-thread / per-index statistics array |
| **`statistics::Formula`** | Derived statistic computed from other stats (e.g. `idleRate = idle / total`) |
| **`ADD_STAT`** | Macro registering a statistic member with its name, units, and description |
| **`SConscript`** | gem5 build file — registers sources, debug flags, and SimObjects |
| **`DebugFlag`** | SConscript declaration that enables a `DPRINTF` flag |
| **`MaxWidth`** | Compile-time limit on issue width (16) from `limits.hh` |
| **`MaxThreads`** | Compile-time limit on SMT thread count (4) from `limits.hh` |
| **`squash`** | Pipeline flush triggered by misprediction or fault — marks in-flight insts invalid |
| **`ROB`** | Reorder Buffer — holds in-flight instructions in program order |
| **`IEW`** | Issue/Execute/Writeback — the combined out-of-order execution stage |
| **`BAC`** | Branch Address Calculator — decoupled front-end component |
| **`FTQ`** | Fetch Target Queue — stores fetch targets from the branch predictor |
| **`develop` branch** | gem5 main development branch — all PRs target this |
| **`stable` branch** | gem5 release branch — only updated on official releases |

---

## 22. DynInst Lifecycle & State Machine

> **Source evidence:** `src/cpu/o3/dyn_inst.hh`, `src/cpu/o3/dyn_inst_ptr.hh`

`DynInst` is the central object that represents one in-flight instruction from fetch
to commit.  Every rule in this section is derived directly from the class declaration.

### Rule G‑64 — `DynInst` carries all in-flight state — never duplicate it elsewhere

Every pipeline stage that needs to know the state of an instruction reads it from the
`DynInst` object, never from a parallel shadow copy.

### Rule G‑65 — Instruction lifecycle is tracked via a `std::bitset<NumStatus>`

The `Status` enum inside `DynInst` lists every legal lifecycle state.  The bitset
allows multiple states to be set simultaneously (e.g. `Committed` + `Squashed`).

```cpp
// src/cpu/o3/dyn_inst.hh — the full lifecycle enum
enum Status
{
    IqEntry,            ///< Instruction is in the IQ
    RobEntry,           ///< Instruction is in the ROB
    LsqEntry,           ///< Instruction is in the LSQ
    Completed,          ///< Instruction has completed
    ResultReady,        ///< Instruction has its result
    CanIssue,           ///< Instruction can issue and execute
    Issued,             ///< Instruction has issued
    Executed,           ///< Instruction has executed
    CanCommit,          ///< Instruction can commit
    AtCommit,           ///< Instruction has reached commit
    Committed,          ///< Instruction has committed
    Squashed,           ///< Instruction is squashed
    SquashedInIQ,       ///< Instruction is squashed in the IQ
    SquashedInLSQ,      ///< Instruction is squashed in the LSQ
    SquashedInROB,      ///< Instruction is squashed in the ROB
    PinnedRegsRenamed,
    PinnedRegsWritten,
    PinnedRegsSquashDone,
    RecoverInst,        ///< Is a recover instruction
    BlockingInst,       ///< Is a blocking instruction
    ThreadsyncWait,
    SerializeBefore,
    SerializeAfter,
    SerializeHandled,
    NumStatus           ///< Sentinel — size of the bitset
};
```

**Lifecycle ASCII diagram:**

```
FETCH → IqEntry → CanIssue → Issued → Executed → ResultReady → CanCommit
                                                                    │
                                                                 Committed
                                                                    or
                                                                 Squashed
```

### Rule G‑66 — Flags are stored in a separate `std::bitset<MaxFlags>`

Instruction flags (translation status, memory ordering, etc.) are distinct from
lifecycle status.  Never conflate them.

```cpp
// src/cpu/o3/dyn_inst.hh
enum Flags
{
    NotAnInst,
    TranslationStarted,
    TranslationCompleted,
    PossibleLoadViolation,
    HitExternalSnoop,
    EffAddrValid,
    RecordResult,
    Predicate,
    MemAccPredicate,
    PredTaken,
    IsStrictlyOrdered,
    ReqMade,
    MemOpDone,
    HtmFromTransaction,
    NoCapableFU,    ///< No FU can execute this instruction
    MaxFlags        ///< Sentinel
};
```

### Rule G‑67 — `DynInstPtr` is `RefCountingPtr<DynInst>` — never use a raw owning pointer

```cpp
// src/cpu/o3/dyn_inst_ptr.hh
using DynInstPtr      = RefCountingPtr<DynInst>;
using DynInstConstPtr = RefCountingPtr<const DynInst>;
```

Non-owning observers may hold a raw `DynInst *`, but ownership is always
transferred through `DynInstPtr`.

### Rule G‑68 — Register mappings are stored as pointer arrays inside `DynInst`

The renaming arrays are heap-allocated in a custom `Arrays` struct to allow
compile-time-unknown counts:

```cpp
// src/cpu/o3/dyn_inst.hh
struct Arrays
{
    size_t numSrcs;
    size_t numDests;

    RegId         *flatDestIdx;
    PhysRegIdPtr  *destIdx;
    PhysRegIdPtr  *prevDestIdx;   // previous mapping — needed for squash
    PhysRegIdPtr  *srcIdx;
    uint8_t       *readySrcIdx;   // 1 bit per src: is it ready?
};
```

### Rule G‑69 — Getter/setter pairs use function overloading, not separate names

gem5 uses the same function name for get (no extra arg) and set (extra arg):

```cpp
// GOOD — gem5 pattern from dyn_inst.hh
PhysRegIdPtr renamedDestIdx(int idx) const;          // getter
void         renamedDestIdx(int idx, PhysRegIdPtr p); // setter

// BAD — do NOT use separate names
PhysRegIdPtr getRenamedDestIdx(int idx) const;
void         setRenamedDestIdx(int idx, PhysRegIdPtr p);
```

---

## 23. Register File, Rename Map & Free List Patterns

> **Source evidence:** `src/cpu/o3/regfile.hh`, `src/cpu/o3/rename_map.hh`,
> `src/cpu/o3/free_list.hh`

### Rule G‑70 — Each register class has its own physical register file vector

```cpp
// src/cpu/o3/regfile.hh
class PhysRegFile
{
  private:
    using PhysIds = std::vector<PhysRegId>;
    using IdRange = std::pair<PhysIds::iterator, PhysIds::iterator>;

    std::vector<RegVal>    intRegFile;
    std::vector<RegVal>    floatRegFile;
    std::vector<VecRegContainer> vectorRegFile;
    std::vector<VecElem>   vectorElemRegFile;
    std::vector<VecPredRegContainer> vecPredRegFile;
    std::vector<MatRegContainer>    matRegFile;
    std::vector<RegVal>    ccRegFile;

    PhysIds intRegIds;
    PhysIds floatRegIds;
    // ... one PhysIds per register class
};
```

### Rule G‑71 — Rename maps use two-level architecture: `SimpleRenameMap` + `UnifiedRenameMap`

```cpp
// src/cpu/o3/rename_map.hh
class SimpleRenameMap
{
  private:
    using Arch2PhysMap = std::vector<PhysRegIdPtr>;
    Arch2PhysMap map;
    SimpleFreeList *freeList;

  public:
    typedef std::pair<PhysRegIdPtr, PhysRegIdPtr> RenameInfo;
    // Returns {new_phys_reg, old_phys_reg} — old is needed for squash rollback
    RenameInfo rename(const RegId& arch_reg);

    PhysRegIdPtr lookup(const RegId& arch_reg) const;
    void         setEntry(const RegId& arch_reg, PhysRegIdPtr phys_reg);
};
```

`RenameInfo` carries both the new and the previous mapping so that squash can
roll back in one step.

### Rule G‑72 — Expose iterators by forwarding from the underlying container

```cpp
// src/cpu/o3/rename_map.hh
using iterator       = Arch2PhysMap::iterator;
using const_iterator = Arch2PhysMap::const_iterator;

iterator       begin()        { return map.begin(); }
const_iterator begin()  const { return map.begin(); }
const_iterator cbegin() const { return map.cbegin(); }
```

**Rule:** Forward `begin`, `end`, `cbegin`, `cend` to the underlying container
rather than exposing the container itself.

### Rule G‑73 — Free lists use `std::queue<PhysRegIdPtr>` for FIFO allocation

```cpp
// src/cpu/o3/free_list.hh
class SimpleFreeList
{
  private:
    std::queue<PhysRegIdPtr> freeRegs;
  public:
    // Template method for bulk population
    template<class InputIt>
    void addRegs(InputIt first, InputIt last) {
        std::for_each(first, last,
            [this](PhysRegIdPtr reg){ freeRegs.push(reg); });
    }
    PhysRegIdPtr getReg();
    unsigned numFreeRegs() const { return freeRegs.size(); }
};
```

### Rule G‑74 — The `UnifiedFreeList` is an array of `SimpleFreeList`, one per register class

```cpp
// src/cpu/o3/free_list.hh
class UnifiedFreeList
{
  private:
    const std::string _name;  // non-SimObject uses explicit _name
    std::array<SimpleFreeList, CCRegClass + 1> freeLists;
    // CCRegClass is the highest enum value — sets array size
};
```

### Rule G‑75 — Non-SimObject classes that need `name()` declare `const std::string _name`

```cpp
// Pattern from scoreboard.hh and free_list.hh
class Scoreboard
{
  private:
    const std::string _name;  // underscore prefix because it is not a SimObject
  public:
    std::string name() const { return _name; }
};
```

---

## 24. Dependency Tracking & Scoreboard

> **Source evidence:** `src/cpu/o3/dep_graph.hh`, `src/cpu/o3/scoreboard.hh`

### Rule G‑76 — Scoreboard is a `std::vector<bool>` over unified physical register space

```cpp
// src/cpu/o3/scoreboard.hh
class Scoreboard
{
  private:
    const std::string _name;
    std::vector<bool> regScoreBoard;
    GEM5_CLASS_VAR_USED unsigned numPhysRegs;  // debug-only size check

  public:
    bool getReg   (PhysRegIdPtr phys_reg) const;
    void setReg   (PhysRegIdPtr phys_reg);
    void unsetReg (PhysRegIdPtr phys_reg);
};
```

### Rule G‑77 — `isAlwaysReady()` must be checked before every scoreboard access

Miscellaneous registers (condition codes, PC) are always considered ready because
they are only written non-speculatively.

```cpp
// src/cpu/o3/scoreboard.hh — mandatory guard
bool
Scoreboard::getReg(PhysRegIdPtr phys_reg) const
{
    if (phys_reg->isAlwaysReady())
        return true;
    assert(phys_reg->flatIndex() < numPhysRegs);
    return regScoreBoard[phys_reg->flatIndex()];
}
```

### Rule G‑78 — The `GEM5_CLASS_VAR_USED` macro suppresses unused-variable warnings on debug members

```cpp
// src/cpu/o3/scoreboard.hh
GEM5_CLASS_VAR_USED unsigned numPhysRegs;
// This member is only read inside assert() — the macro prevents
// the compiler from warning in release builds where assert() is compiled out.
```

### Rule G‑79 — `DependencyGraph<T>` is templated on `DynInstPtr`

```cpp
// src/cpu/o3/dep_graph.hh
template <class DynInstPtr>
class DependencyGraph
{
  private:
    struct DependencyEntry
    {
        DynInstPtr inst;
        DependencyEntry *next;
    };
    typedef DependencyEntry DepEntry;
    std::vector<DepEntry *> dependGraph;  // indexed by phys reg flat index
};
```

---

## 25. SMT Queue Policies & Per-Thread Resource Patterns

> **Source evidence:** `src/cpu/o3/commit.cc`, `src/cpu/o3/rob.cc`,
> `src/cpu/o3/inst_queue.cc`, `src/cpu/o3/rename.cc`

### Rule G‑80 — All per-thread arrays are sized to `MaxThreads`, not `numThreads`

`numThreads` is a runtime value.  Arrays MUST be statically sized to `MaxThreads`
to avoid dynamic allocation and ensure deterministic layout.

```cpp
// GOOD
CommitStatus commitStatus[MaxThreads];
bool         trapSquash[MaxThreads];
bool         tcSquash[MaxThreads];
DynInstPtr   squashAfterInst[MaxThreads];

// BAD
std::vector<CommitStatus> commitStatus(numThreads);  // dynamic, forbidden
```

### Rule G‑81 — Per-thread arrays are initialised in a `for (ThreadID tid = 0; tid < MaxThreads; tid++)` loop

```cpp
// src/cpu/o3/commit.cc — constructor body
for (ThreadID tid = 0; tid < MaxThreads; tid++) {
    commitStatus[tid]        = Idle;
    changedROBNumEntries[tid] = false;
    trapSquash[tid]           = false;
    tcSquash[tid]             = false;
    squashAfterInst[tid]      = nullptr;
    pc[tid].reset(params.isa[0]->newPCState());
    youngestSeqNum[tid]       = 0;
    lastCommitedSeqNum[tid]   = 0;
    trapInFlight[tid]         = false;
    committedStores[tid]      = false;
    checkEmptyROB[tid]        = false;
    renameMap[tid]            = nullptr;
    htmStarts[tid]            = 0;
    htmStops[tid]             = 0;
}
```

### Rule G‑82 — `SMTQueuePolicy` determines resource sharing — always checked during construction

```cpp
// Three legal policies
enum class SMTQueuePolicy { Dynamic, Partitioned, Threshold };

// Pattern from rob.cc
if (robPolicy == SMTQueuePolicy::Dynamic) {
    // All threads share the full resource pool
    maxEntries[tid] = numEntries;
} else if (robPolicy == SMTQueuePolicy::Partitioned) {
    int part_amt = numEntries / numThreads;
    maxEntries[tid] = part_amt;
} else if (robPolicy == SMTQueuePolicy::Threshold) {
    maxEntries[tid] = params.smtROBThreshold;
}
```

### Rule G‑83 — Stage-wide status is `_status`; per-thread status is `stageStatus[MaxThreads]`

```cpp
// commit.hh
CommitStatus _status;           // overall commit stage status
CommitStatus _nextStatus;       // deferred next value (set in current cycle,
                                //   applied at start of next)
ThreadStatus commitStatus[MaxThreads];  // per-thread status
```

### Rule G‑84 — Deferred status updates use `_nextStatus`

In gem5, the pipeline processes one cycle at a time.  `_status` must not change
mid-cycle because other stages read it.  Stage classes maintain `_nextStatus` and
swap it at the start of the next `tick()`.

```cpp
// Pattern seen in commit.cc, iew.cc, rename.cc
_status     = Active;      // current cycle value
_nextStatus = Inactive;    // will take effect next cycle
```

### Rule G‑85 — Stage name is returned by `name()` as `cpu->name() + ".stagename"`

Every pipeline stage (not a `SimObject` itself) delegates naming to the CPU object:

```cpp
// commit.cc line 155
std::string Commit::name() const { return cpu->name() + ".commit"; }

// iew.cc
std::string IEW::name() const { return cpu->name() + ".iew"; }

// rename.cc
std::string Rename::name() const { return cpu->name() + ".rename"; }
```

---

## 26. Statistics — Deep Dive: `ADD_STAT`, `init`, `flags`, `prereq`, `Formula`

> **Source evidence:** `src/cpu/o3/commit.cc` (lines 168–200),
> `src/cpu/o3/rename.cc`, `src/cpu/o3/iew.cc`, `src/base/statistics.hh`

### Rule G‑86 — Statistics are declared in a nested `*Stats` struct that inherits `statistics::Group`

```cpp
// From commit.hh
struct CommitStats : public statistics::Group
{
    CommitStats(CPU *cpu, Commit *commit);

    statistics::Vector      status;
    statistics::Scalar      commitSquashedInsts;
    statistics::Scalar      branchMispredicts;
    statistics::Distribution numCommittedDist;
    statistics::Scalar      commitEligibleSamples;
    // ...
} stats;   // ← single member of the outer class
```

### Rule G‑87 — `ADD_STAT` is the ONLY way to register a statistic member

`ADD_STAT` must appear in the `statistics::Group` constructor's **member initializer list**,
not in the body.  It binds the C++ member name, units, and description simultaneously.

```cpp
// src/cpu/o3/commit.cc — correct pattern
Commit::CommitStats::CommitStats(CPU *cpu, Commit *commit)
    : statistics::Group(cpu, "commit"),
      ADD_STAT(status,
               statistics::units::Cycle::get(),
               "Commit status cycles"),
      ADD_STAT(commitSquashedInsts,
               statistics::units::Count::get(),
               "The number of squashed insts skipped by commit"),
      ADD_STAT(branchMispredicts,
               statistics::units::Count::get(),
               "The number of times a branch was mispredicted"),
      ADD_STAT(commitEligibleSamples,
               statistics::units::Cycle::get(),
               "number cycles where commit BW limit reached")
{
    // Post-construction configuration in the body:
    using namespace statistics;

    status
        .init(ThreadStatusMax)
        .flags(statistics::pdf | statistics::nozero);

    for (int i = 0; i < ThreadStatusMax; ++i) {
        status.subname(i, statusStrings[i]);
        status.subdesc(i, statusDefinitions[i]);
    }
    commitSquashedInsts.prereq(commitSquashedInsts);
    branchMispredicts.prereq(branchMispredicts);
}
```

### Rule G‑88 — `Vector` stats must call `.init(N)` in the constructor body

```cpp
// Correct
status.init(ThreadStatusMax).flags(statistics::pdf | statistics::nozero);

// Forbidden — init not called
statistics::Vector status;  // with no subsequent .init() call
```

### Rule G‑89 — Sub-index names and descriptions must be registered with `.subname()` / `.subdesc()`

```cpp
for (int i = 0; i < ThreadStatusMax; ++i) {
    status.subname(i, statusStrings[i]);   // "running", "idle", ...
    status.subdesc(i, statusDefinitions[i]);
}
```

The string arrays `statusStrings[]` and `statusDefinitions[]` are parallel to the
`ThreadStatus` enum and sized to `ThreadStatusMax`.

### Rule G‑90 — `.prereq()` suppresses a statistic if another statistic is zero

```cpp
// "Don't print commitSquashedInsts if it was never incremented"
commitSquashedInsts.prereq(commitSquashedInsts);
```

### Rule G‑91 — `statistics::Formula` is used for derived stats, never `statistics::Scalar` with manual computation

```cpp
// Correct — iew.cc pattern
ADD_STAT(branchMispredictRate,
         statistics::units::Rate<Count, Count>::get(),
         "Branch misprediction rate",
         predictedTakenIncorrect + predictedNotTakenIncorrect)
```

### Rule G‑92 — The statistics `Group` parent is the CPU, never `this`

```cpp
// GOOD — parent group is the CPU
: statistics::Group(cpu, "commit")

// BAD — self-parent makes hierarchy wrong
: statistics::Group(this, "commit")
```

### Rule G‑93 — Available unit types for `ADD_STAT`

| Unit Type | Meaning |
|-----------|---------|
| `statistics::units::Count::get()` | dimensionless count |
| `statistics::units::Cycle::get()` | clock cycles |
| `statistics::units::Tick::get()` | simulation ticks |
| `statistics::units::Byte::get()` | bytes |
| `statistics::units::Rate<A,B>::get()` | ratio of two unit types |

---

## 27. Probe Points & Performance Tracing

> **Source evidence:** `src/cpu/o3/commit.cc`, `src/cpu/o3/rename.hh`,
> `src/cpu/o3/iew.hh`, `src/cpu/o3/commit.hh`

### Rule G‑94 — Probe points are raw `ProbePointArg<T> *` members — not smart pointers

```cpp
// commit.hh
ProbePointArg<DynInstPtr> *ppCommit;
ProbePointArg<DynInstPtr> *ppCommitStall;
ProbePointArg<DynInstPtr> *ppSquash;

// rename.hh
typedef std::pair<InstSeqNum, PhysRegIdPtr> SeqNumRegPair;
ProbePointArg<DynInstPtr>    *ppRename;
ProbePointArg<SeqNumRegPair> *ppSquashInRename;
```

The CPU's `ProbeManager` owns the probe points.  The stage holds a non-owning raw
pointer.

### Rule G‑95 — Probe points are registered in `regProbePoints()`, not in the constructor

```cpp
// src/cpu/o3/commit.cc
void
Commit::regProbePoints()
{
    ppCommit = new ProbePointArg<DynInstPtr>(
            cpu->getProbeManager(), "Commit");
    ppCommitStall = new ProbePointArg<DynInstPtr>(
            cpu->getProbeManager(), "CommitStall");
    ppSquash = new ProbePointArg<DynInstPtr>(
            cpu->getProbeManager(), "Squash");
}
```

### Rule G‑96 — Probe point names are string literals — use PascalCase

Legal names seen in the repo:

| Stage | Probe Name |
|-------|------------|
| Fetch | `"Fetch"` |
| Rename | `"Rename"`, `"SquashInRename"` |
| IEW | `"Mispredict"`, `"Dispatch"`, `"Execute"`, `"ToCommit"` |
| Commit | `"Commit"`, `"CommitStall"`, `"Squash"` |

### Rule G‑97 — Probe point types use the most specific type available

Use `ProbePointArg<DynInstPtr>` for instruction-level events and
`ProbePointArg<std::pair<InstSeqNum, PhysRegIdPtr>>` for rename-specific events
rather than a generic payload.

---

## 28. Event Queue & `ClockedObject` Patterns

> **Source evidence:** `src/sim/eventq.hh`, `src/sim/clocked_object.hh`,
> `src/cpu/o3/cpu.cc`

### Rule G‑98 — `tick()` is scheduled via an `EventFunctionWrapper` with a lambda

```cpp
// src/cpu/o3/cpu.cc — constructor member init list
tickEvent(
    [this] { tick(); },        // lambda captures only `this`
    "O3CPU tick",
    false,
    Event::CPU_Tick_Pri)       // explicit priority
```

Lambdas in event callbacks MUST capture only `this` — no by-value captures of
simulation objects.

### Rule G‑99 — Event priorities are `Event::Priority` enum values — never magic integers

```cpp
// Legal priorities from src/sim/eventq.hh
Event::Minimum_Pri          = SCHAR_MIN
Event::Debug_Enable_Pri     = -101
Event::Debug_Break_Pri      = -100
Event::CPU_Switch_Pri       = -31
Event::Delayed_Writeback_Pri = -1
Event::Default_Pri          = 0
Event::DVFS_Update_Pri      = 31
Event::Serialize_Pri        = 32
Event::CPU_Tick_Pri         = 50
Event::CPU_Exit_Pri         = 100
Event::Maximum_Pri          = SCHAR_MAX
```

### Rule G‑100 — `ClockedObject` subclasses use `clockEdge(Cycles n)` for future scheduling

```cpp
// Schedule an event N cycles from the current clock edge
schedule(myEvent, clockEdge(Cycles(latency)));

// NOT: clockEdge() + latency * clockPeriod()
```

### Rule G‑101 — Thread-local event queue access uses `curEventQueue()`

```cpp
// src/sim/eventq.hh
extern __thread EventQueue *_curEventQueue;
inline EventQueue *curEventQueue() { return _curEventQueue; }
```

Never cache the event queue pointer across function calls; always use
`curEventQueue()`.

### Rule G‑102 — Simulation quantum (`simQuantum`) governs multi-queue synchronisation

When writing events across event queues, the target tick must be at least
`simQuantum` ticks in the future.

---

## 29. Drain & Serialisation Protocol

> **Source evidence:** `src/sim/drain.hh`, `src/sim/sim_object.hh`

### Rule G‑103 — Every `SimObject` that holds in-flight state MUST implement `Drainable`

`SimObject` inherits from `Drainable` already; subclasses MUST override
`drain()` and `drainResume()` if they buffer work.

### Rule G‑104 — `DrainState` is a scoped enum — use the full qualifier

```cpp
// src/sim/drain.hh
enum class DrainState
{
    Running,   ///< Simulation is running normally
    Draining,  ///< Buffers draining before serialisation
    Drained,   ///< Buffers empty, ready for checkpoint
    Resuming,  ///< Transient during simulator resume
};
```

```cpp
// GOOD
if (drainState() == DrainState::Drained) { ... }

// BAD — implicit conversion
if (drainState() == 2) { ... }
```

### Rule G‑105 — `DrainManager` is a singleton — access via `DrainManager::instance()`

```cpp
// src/sim/drain.hh — Meyer's singleton pattern
static DrainManager &
instance()
{
    static DrainManager _instance;   // constructed on first use, destroyed on exit
    return _instance;
}
```

Copy constructor is deleted:

```cpp
DrainManager(DrainManager &) = delete;
```

### Rule G‑106 — `SimObject` initialisation sequence must be respected

From `src/sim/sim_object.hh`:

```
1. SimObject::init()
2. SimObject::regStats()
3a. SimObject::initState()    — fresh start
3b. SimObject::loadState()    — checkpoint restore
4. SimObject::resetStats()
5. SimObject::startup()
6. Drainable::drainResume()   — if resuming from checkpoint
```

Call order is pre-order depth-first: parent before children.

### Rule G‑107 — `SimObject` is constructed with a `Params` struct typedef

```cpp
// sim_object.hh
typedef SimObjectParams Params;

// Constructor signature pattern
MyComponent(const MyComponentParams &params);
```

---

## 30. Memory System Deep Dive — `Request`, `Packet`, Command Types

> **Source evidence:** `src/mem/request.hh`, `src/mem/packet.hh`,
> `src/mem/port.hh`

### Rule G‑108 — `Request` is created before `Packet` — never create a `Packet` without a `Request`

```cpp
// Correct creation sequence
auto req = std::make_shared<Request>(
    vaddr, size, flags, requestorId);
auto pkt = new Packet(req, MemCmd::ReadReq);
pkt->allocate();
```

### Rule G‑109 — `RequestPtr` is `std::shared_ptr<Request>` — use `make_shared`

```cpp
// src/mem/request.hh
typedef std::shared_ptr<Request> RequestPtr;

// GOOD
RequestPtr req = std::make_shared<Request>(...);

// BAD
RequestPtr req = new Request(...);  // raw new with shared_ptr
```

### Rule G‑110 — `MemCmd` command table — use named enum members, not integers

Key `MemCmd` commands from `src/mem/packet.hh`:

| Command | Direction | Meaning |
|---------|-----------|---------|
| `ReadReq` | Request | Read data from memory |
| `ReadResp` | Response | Read data returned |
| `WriteReq` | Request | Write data to memory |
| `WriteResp` | Response | Write acknowledged |
| `WritebackDirty` | Functional | Writeback dirty cache line |
| `WritebackClean` | Functional | Writeback clean cache line |
| `HardPFReq` | Request | Hardware prefetch request |
| `UpgradeReq` | Request | Upgrade shared → exclusive |
| `ReadExReq` | Request | Read exclusive (for write) |
| `LoadLockedReq` | Request | LL/SC load-linked |
| `StoreCondReq` | Request | LL/SC store-conditional |
| `SwapReq` | Request | Atomic swap |
| `InvalidCmd` | — | Sentinel / uninitialized |

### Rule G‑111 — `Request` flags are bit-encoded `uint64_t` — use named constants only

```cpp
// src/mem/request.hh — flags
enum : FlagsType {
    INST_FETCH        = 0x00000001,  ///< Instruction fetch
    PHYSICAL          = 0x00000002,  ///< Already physical address
    UNCACHEABLE       = 0x00000004,
    STRICT_ORDER      = 0x00000008,
    PRIVILEGED        = 0x00008000,
    LOCKED_RMW        = 0x00100000,
    LLSC              = 0x00200000,  ///< Load-linked, store-conditional
    MEM_SWAP          = 0x00400000,
    ATOMIC_NO_RETURN  = 0x40000000,
};
```

### Rule G‑112 — Packet extensions use the `Extensible<Packet>` CRTP pattern

```cpp
// src/mem/port.hh — TracingExtension example
class TracingExtension
    : public gem5::Extension<Packet, TracingExtension>
{
  public:
    TracingExtension() = default;
    explicit TracingExtension(const std::stack<std::string> &q);

    std::unique_ptr<ExtensionBase> clone() const override
    {
        return std::make_unique<TracingExtension>(trace_);
    }
    // ...
};
```

### Rule G‑113 — Ports inherit from `RequestPort` or `ResponsePort`, never from both

```cpp
// Correct: IcachePort inside Fetch
class IcachePort : public RequestPort
{
  public:
    IcachePort(const std::string &_name, Fetch *_fetch, CPU *_cpu);
  protected:
    bool recvTimingResp(PacketPtr pkt) override;
    void recvReqRetry() override;
};
```

---

## 31. `RefCounting`, Smart Pointers & Ownership Semantics

> **Source evidence:** `src/base/refcnt.hh`, `src/cpu/o3/dyn_inst_ptr.hh`,
> `src/mem/request.hh`

### Rule G‑114 — `RefCounted` base class enables `RefCountingPtr<T>` ownership

```cpp
// src/base/refcnt.hh
class RefCounted
{
  private:
    mutable int count = 0;  // mutable: const objects can still be ref-counted

    friend void intrusive_ptr_add_ref(const RefCounted *);
    friend void intrusive_ptr_release(const RefCounted *);
};

template <class T>
class RefCountingPtr
{
  public:
    // Move semantics supported
    RefCountingPtr(RefCountingPtr &&r);
    RefCountingPtr &operator=(RefCountingPtr &&r);

    // Implicit conversion to raw pointer (non-owning view)
    operator T *() const { return data; }
};
```

### Rule G‑115 — Use `std::shared_ptr<T>` for wide ownership; `RefCountingPtr<T>` for performance-critical instruction-level objects

| Smart pointer | When to use |
|---|---|
| `RefCountingPtr<DynInst>` (`DynInstPtr`) | In-flight instructions — high-frequency |
| `std::shared_ptr<Request>` (`RequestPtr`) | Memory requests — moderate frequency |
| `std::shared_ptr<FaultBase>` (`Fault`) | Hardware faults — low frequency |
| `std::unique_ptr<PCStateBase>` | PC state — single owner |
| `std::unique_ptr<T>` (general) | Any single-owner heap object |
| Raw `T *` (non-owning) | Observer/read-only access to already-owned object |

### Rule G‑116 — `GEM5_NO_INLINE` on `del()` prevents inlining of the destructor hot path

```cpp
// src/base/refcnt.hh
GEM5_NO_INLINE static void del(T *p) { delete p; }
```

This is a deliberate micro-optimisation.  Do not remove it.

---

## 32. gem5 Utility Types — `bitfield`, `sat_counter`, `Flags`, `circular_queue`

> **Source evidence:** `src/base/bitfield.hh`, `src/base/sat_counter.hh`,
> `src/base/flags.hh`

### Rule G‑117 — Use `bits(val, hi, lo)` / `bits(val, bit)` for bitfield extraction

```cpp
// src/base/bitfield.hh — constexpr, zero overhead
template <class T>
constexpr T bits(T val, unsigned first, unsigned last);

template <class T>
constexpr T bits(T val, unsigned bit);

// Usage
uint32_t opcode = bits(instr, 31, 26);  // bits [31:26]
bool     sign   = bits(instr, 31);      // single bit
```

### Rule G‑118 — Use `insertBits` / `mbits` for constructing bit patterns

```cpp
// src/base/bitfield.hh
template <class T, class B>
constexpr T insertBits(T val, unsigned first, unsigned last, B bit_val);

// Extract masked bits
template <class T>
constexpr T mbits(T val, unsigned first, unsigned last);
```

### Rule G‑119 — Use `GenericSatCounter<T>` for saturating counters; mark constructor `explicit`

```cpp
// src/base/sat_counter.hh
template <class T>
class GenericSatCounter
{
  public:
    // Always explicit to prevent accidental implicit construction
    explicit GenericSatCounter(unsigned bits, T initial_val = 0);

    // Increment with saturation
    GenericSatCounter &operator++();
    GenericSatCounter &operator--();
};

using SatCounter8  = GenericSatCounter<uint8_t>;
using SatCounter16 = GenericSatCounter<uint16_t>;

// Usage in branch predictors
SatCounter8 counter{2, 1};  // 2-bit counter, initial value = Weakly Taken
```

### Rule G‑120 — Use `Flags<T>` for bit-packed flag fields — never raw `uint64_t`

```cpp
// src/base/flags.hh
template <typename T>
class Flags
{
    static_assert(std::is_unsigned_v<T>, "Flag type must be unsigned");
    T _flags = 0;
  public:
    bool isSet(Type mask) const    { return (_flags & mask) != 0; }
    bool allSet(Type mask) const   { return (_flags & mask) == mask; }
    bool noneSet(Type mask) const  { return (_flags & mask) == 0; }

    void set(Type mask)   { _flags |= mask; }
    void clear(Type mask) { _flags &= ~mask; }
};

// Concrete usage
typedef uint64_t FlagsType;
typedef gem5::Flags<FlagsType> RequestFlags;
```

---

## 33. CRTP & Template Patterns in gem5

> **Source evidence:** `src/base/refcnt.hh`, `src/mem/port.hh`,
> `src/mem/request.hh`, `src/cpu/o3/dep_graph.hh`

### Rule G‑121 — CRTP is used for static polymorphism; prefer it over virtual when no dynamic dispatch is needed

```cpp
// Pattern: Extension<Packet, TracingExtension>
// The derived class passes itself as a template parameter
template <class Base, class Derived>
class Extension : public Base::ExtensionBase { ... };

class TracingExtension
    : public gem5::Extension<Packet, TracingExtension>
{
    std::unique_ptr<ExtensionBase> clone() const override
    { return std::make_unique<TracingExtension>(*this); }
};
```

### Rule G‑122 — Template parameters use `UpperCamelCase` by convention

```cpp
// GOOD — from dep_graph.hh
template <class DynInstPtr>
class DependencyGraph { ... };

// GOOD — from refcnt.hh
template <class T>
class RefCountingPtr { ... };

// BAD
template <class dyninstptr>      // lowercase
template <class DYNINSTPTR>      // all caps
```

### Rule G‑123 — Template class definitions MUST be in the `.hh` file

Templates require full visibility at every point of instantiation.  Do not split
template class definitions into `.cc` files (except for explicit instantiation).

### Rule G‑124 — Use `std::conditional_t` and `std::is_const_v` for const/non-const template pairs

```cpp
// src/base/refcnt.hh — selecting the right pointer type
using TisConst    = std::is_const<T>;
using ConstVers   = RefCountingPtr<const std::remove_const_t<T>>;
using NonConstVers = RefCountingPtr<std::remove_const_t<T>>;
using OtherType = std::conditional_t<TisConst::value, NonConstVers, ConstVers>;
```

---

## 34. Nested Port Classes & Translation Callback Patterns

> **Source evidence:** `src/cpu/o3/fetch.hh`, `src/mem/port.hh`

### Rule G‑125 — Memory ports are always nested classes inside the component that owns them

```cpp
// src/cpu/o3/fetch.hh
class Fetch
{
  public:
    // Port is a nested class — it knows its parent
    class IcachePort : public RequestPort
    {
      private:
        Fetch *fetch;
        CPU   *cpu;
      public:
        IcachePort(const std::string &_name, Fetch *_fetch, CPU *_cpu);
      protected:
        bool recvTimingResp(PacketPtr pkt) override;
        void recvReqRetry() override;
    };
  private:
    IcachePort icachePort;  // member: single instance owned by Fetch
};
```

### Rule G‑126 — Translation callbacks inherit `BaseMMU::Translation` and implement `finish()`

```cpp
// src/cpu/o3/fetch.hh
class FetchTranslation : public BaseMMU::Translation
{
  private:
    Fetch *fetch;
  public:
    explicit FetchTranslation(Fetch *_fetch) : fetch(_fetch) {}
    void finish(const Fault &fault,
                const RequestPtr &req,
                ThreadContext *tc,
                BaseMMU::Mode mode) override;
    bool squashed() const override;
};
```

### Rule G‑127 — Async translation completion uses an `Event` nested inside the stage

```cpp
// Pattern from fetch.hh — FinishTranslationEvent
class FinishTranslationEvent : public Event
{
  private:
    Fetch *fetch;
    Fault fault;
    RequestPtr req;
  public:
    FinishTranslationEvent(Fetch *f) : fetch(f) {}
    void setFault(const Fault &f)   { fault = f; }
    void setReq(const RequestPtr &r){ req = r; }
    void process() override;  // implemented in fetch.cc
};
```

---

## 35. Squash Protocol — Full State Machine

> **Source evidence:** `src/cpu/o3/commit.cc`, `src/cpu/o3/rob.cc`,
> `src/cpu/o3/comm.hh`, `src/cpu/o3/iew.hh`

### Rule G‑128 — Squash is initiated at commit; all upstream stages receive it via `TimeStruct`

```cpp
// src/cpu/o3/comm.hh — TimeStruct carries squash signal backwards
struct TimeStruct
{
    struct CommitComm
    {
        bool squash;           // set to true when commit triggers squash
        bool robSquashing;
        InstSeqNum doneSeqNum; // instructions at or below this are safe
        ThreadID   tid;
    } commitInfo[MaxThreads];
    // ...
};
```

### Rule G‑129 — Each stage maintains `squashIt[MaxThreads]` iterators for ROB walk

```cpp
// src/cpu/o3/rob.cc
squashIt[tid]        = instList[tid].end();   // initialised to end (invalid)
squashedSeqNum[tid]  = 0;
doneSquashing[tid]   = true;
```

During squash, the ROB walks from `squashIt[tid]` towards the head, marking
instructions squashed.  The iterator is advanced `squashWidth` steps per cycle.

### Rule G‑130 — `trapSquash[]` and `tcSquash[]` are separate flags — do not conflate them

```cpp
// src/cpu/o3/commit.cc
bool trapSquash[MaxThreads];  // squash triggered by a trap/exception
bool tcSquash[MaxThreads];    // squash triggered by a ThreadContext change
DynInstPtr squashAfterInst[MaxThreads];  // instruction after which to squash
```

| Flag | Trigger | Scope |
|------|---------|-------|
| `trapSquash[tid]` | Hardware fault, interrupt | Single thread |
| `tcSquash[tid]` | Thread context write (e.g. CSR write) | Single thread |
| `squashAfterInst[tid]` | Serialisation point | Single thread |

### Rule G‑131 — `IEWStruct` in `comm.hh` carries misprediction info from IEW to commit

```cpp
// src/cpu/o3/comm.hh
struct IEWStruct
{
    int size;
    DynInstPtr insts[MaxWidth];

    DynInstPtr mispredictInst[MaxThreads];   // the branch that mispredicted
    Addr       mispredPC[MaxThreads];
    InstSeqNum squashedSeqNum[MaxThreads];
    std::unique_ptr<PCStateBase> pc[MaxThreads]; // correct target PC

    bool squash[MaxThreads];
    bool branchMispredict[MaxThreads];
    bool branchTaken[MaxThreads];
    bool includeSquashInst[MaxThreads];  // include mispredict inst in squash?
};
```

### Rule G‑132 — Squash events use `processTrapEvent(ThreadID tid)` as a deferred callback

```cpp
// src/cpu/o3/commit.cc
void
Commit::processTrapEvent(ThreadID tid)
{
    // Executed from the event queue, not inline
    trapSquash[tid] = true;
}
```

Trap processing is deferred to an event to ensure squash happens at a clean
cycle boundary.

---

## 36. Section 14 — O3 CPU Architecture Patterns (Extended)

The following subsections augment Section 14 with deeper detail extracted from
the implementation files.

### 14.6 Constructor initialisation order for `CPU`

```cpp
// src/cpu/o3/cpu.cc — abridged member init list
CPU::CPU(const BaseO3CPUParams &params)
    : BaseCPU(params),
      mmu(params.mmu),
      tickEvent([this] { tick(); }, "O3CPU tick",
                false, Event::CPU_Tick_Pri),
      threadExitEvent([this] { exitThreads(); }, "CPU exit",
                      false, Event::CPU_Exit_Pri),
#ifndef NDEBUG
      instcount(0),
#endif
      removeInstsThisCycle(false),
      bac(this, params),    // front-end: branch address calculator
      ftq(this, params),    // fetch target queue
      fetch(this, params),
      decode(this, params),
      rename(this, params),
      iew(this, params),
      commit(this, params),
      regFile(...),
      freeList(...),
      rob(this, params),
      scoreboard(...)
```

**Rules derived from this:**

1. Stages are initialised with `(this, params)` — the CPU pointer comes first.
2. Front-end (`bac`, `ftq`, `fetch`) before back-end (`decode`, `rename`, `iew`, `commit`).
3. `#ifndef NDEBUG` guards debug-only members.
4. Event callbacks use `[this] { method(); }` lambdas.

### 14.7 Parallel string arrays for status statistics

```cpp
// src/cpu/o3/fetch.cc — pattern replicated in every stage
std::string Fetch::FetchStatGroup::statusStrings[ThreadStatusMax] = {
    "running",
    "idle",
    "squashing",
    "blocked",
    "fetching",
    "trapPending",
    // ...
};

std::string Fetch::FetchStatGroup::statusDefinitions[ThreadStatusMax] = {
    "Number of cycles fetch ran normally",
    "Number of cycles fetch was idle",
    // ...
};
```

**Rule G‑133:** For every `statistics::Vector` indexed by a status enum, declare
parallel `statusStrings[]` and `statusDefinitions[]` arrays of the same size
(`ThreadStatusMax`).

### 14.8 Priority list for SMT commit scheduling

```cpp
// src/cpu/o3/commit.cc
if (commitPolicy == CommitPolicy::RoundRobin) {
    for (ThreadID tid = 0; tid < numThreads; tid++) {
        priority_list.push_back(tid);
    }
}
```

**Rule G‑134:** Round-robin scheduling uses a `std::list<ThreadID> priority_list`
that is rotated after each thread commits.  Never use a plain array for priority
ordering — the list rotation semantics are required.

### 14.9 `Fault` and interrupt handling

```cpp
// src/cpu/o3/commit.cc
interrupt = NoFault;  // initialised to NoFault sentinel

// Checking
if (interrupt != NoFault) { ... }

// Processing: commit.processTrapEvent() sets trapSquash[tid] = true
```

**Rule G‑135:** Always compare `Fault` to `NoFault`, not to `nullptr`.
`NoFault` is a typed shared_ptr sentinel, not a null pointer.

---

## 37. Naming Conventions — Extended Reference Table

The following table supplements Rule G‑06 with all patterns observed in
`src/cpu/o3/`, `src/mem/`, `src/base/`, and `src/sim/`.

| Entity | Convention | Example |
|--------|-----------|---------|
| Class / struct | `UpperCamelCase` | `DynInst`, `PhysRegFile`, `SimpleFreeList` |
| Enum class | `UpperCamelCase` | `DrainState`, `SMTQueuePolicy` |
| Enum member | `UpperCamelCase` | `DrainState::Running`, `CommitPolicy::RoundRobin` |
| Plain enum member | `UpperCamelCase` | `Running`, `Idle`, `ThreadStatusMax` |
| `static constexpr` | `UpperCamelCase` | `MaxWidth`, `MaxThreads` |
| `static const` flag | `UpperCamelCase` | `Scheduled`, `AutoDelete`, `IsExitEvent` |
| Public member variable | `lowerCamelCase` | `seqNum`, `staticInst`, `cpu`, `freeList` |
| Private member variable | `lowerCamelCase` or `_lowerCamelCase` | `_name`, `_status`, `regScoreBoard` |
| Private member (exposed accessor) | `_lowerCamelCase` | `_numSrcs`, `_destIdx` |
| Method | `lowerCamelCase` | `getReg()`, `setReg()`, `numFreeEntries()` |
| Boolean query method | `is` / `has` prefix | `isAlwaysReady()`, `isSnooping()`, `isDrained()` |
| Template parameter (type) | `UpperCamelCase` | `DynInstPtr`, `T`, `InputIt` |
| Template parameter (non-type) | `lowerCamelCase` | `N`, `size` |
| Local variable | `snake_case` | `part_amt`, `tid`, `phys_reg` |
| Function parameter | `snake_case` | `phys_reg`, `arch_reg`, `_my_name` |
| `typedef` alias | `UpperCamelCase` | `RenameInfo`, `DepEntry`, `FlagsType` |
| `using` alias | `UpperCamelCase` | `Arch2PhysMap`, `IdRange`, `DynInstPtr` |
| Namespace | `snake_case` / short | `gem5`, `o3`, `statistics`, `prefetch` |
| Debug flag | `UpperCamelCase` | `Scoreboard`, `Commit`, `IEW`, `ROB` |
| DPRINTF format string | uses `\n` at end | `"Setting reg %i (%s) as ready\n"` |
| Macro | `UPPER_CASE` | `DPRINTF`, `ADD_STAT`, `GEM5_NO_INLINE` |

---

## 38. Anti-Patterns (Extended)

The following entries supplement Section 18.

| Anti-pattern | Evidence | Rule violated |
|---|---|---|
| `std::cout` inside a stage | Not in any `.cc` file in `src/cpu/o3/` | G‑39 |
| `printf` inside simulation | Not in any `.cc` file in `src/cpu/o3/` | G‑39 |
| `throw std::runtime_error(...)` in a stage | gem5 never throws in hot paths | G‑55 |
| `nullptr` instead of `NoFault` | `fault = nullptr` is always wrong | G‑135 |
| Raw `new DynInst(...)` stored in a raw pointer | All stores use `DynInstPtr` | G‑67 |
| `auto` for return types of public API methods | Makes API unreadable | G‑06 |
| `using namespace gem5` in a header | Pollutes all includers | G‑21 |
| Mutable state in a `statistics::Scalar` set manually | Must use `ADD_STAT` | G‑87 |
| Per-thread array sized `numThreads` | Runtime size, loses cache coherence | G‑80 |
| `std::list` for in-flight instruction queues | Poor cache locality; use only where O(1) splice needed | — |
| `unordered_map` for probe point registry | Non-deterministic iteration | Rule C‑29 |
| `EventFunctionWrapper` lambda capturing non-`this` | Lifetime hazard | G‑98 |
| Magic priority integer in `schedule()` | Use `Event::CPU_Tick_Pri` etc. | G‑99 |
| `initBefore` / `initAfter` in constructor body | Must be in initializer list | G‑87 |

---

## 39. Complete Code Examples (Extended)

### 39.1 Minimal stage class (non-SimObject)

```cpp
// mysubsystem/my_stage.hh
#ifndef __CPU_O3_MY_STAGE_HH__
#define __CPU_O3_MY_STAGE_HH__

#include <string>
#include <vector>

#include "base/statistics.hh"
#include "base/types.hh"
#include "cpu/o3/comm.hh"
#include "cpu/o3/dyn_inst_ptr.hh"
#include "cpu/o3/limits.hh"
#include "params/BaseO3CPU.hh"

namespace gem5
{
namespace o3
{

class CPU;

class MyStage
{
  public:
    MyStage(CPU *cpu, const BaseO3CPUParams &params);

    std::string name() const;
    void        tick();
    void        setTimeBuffer(TimeBuffer<TimeStruct> *tb_ptr);

  private:
    enum StageStatus { Active, Inactive };
    enum ThreadStatus { Running, Idle, Squashing, ThreadStatusMax };

    CPU        *cpu;
    StageStatus _status;
    StageStatus _nextStatus;
    ThreadStatus threadStatus[MaxThreads];

    struct MyStageStats : public statistics::Group
    {
        MyStageStats(CPU *cpu, MyStage *stage);
        statistics::Scalar cycles;
        statistics::Vector threadCycles;
    } stats;
};

} // namespace o3
} // namespace gem5

#endif // __CPU_O3_MY_STAGE_HH__
```

### 39.2 Minimal stage implementation

```cpp
// mysubsystem/my_stage.cc
#include "cpu/o3/my_stage.hh"

#include "base/trace.hh"
#include "debug/MyStage.hh"
#include "cpu/o3/cpu.hh"

namespace gem5
{
namespace o3
{

MyStage::MyStage(CPU *_cpu, const BaseO3CPUParams &params)
    : cpu(_cpu),
      _status(Inactive),
      _nextStatus(Inactive),
      stats(_cpu, this)
{
    for (ThreadID tid = 0; tid < MaxThreads; tid++) {
        threadStatus[tid] = Idle;
    }
}

std::string
MyStage::name() const
{
    return cpu->name() + ".mystage";
}

MyStage::MyStageStats::MyStageStats(CPU *cpu, MyStage *stage)
    : statistics::Group(cpu, "mystage"),
      ADD_STAT(cycles,
               statistics::units::Cycle::get(),
               "Cycles in MyStage"),
      ADD_STAT(threadCycles,
               statistics::units::Cycle::get(),
               "Cycles per thread")
{
    threadCycles
        .init(MaxThreads)
        .flags(statistics::nozero);
    for (int i = 0; i < MaxThreads; ++i)
        threadCycles.subname(i, std::to_string(i));
}

void
MyStage::tick()
{
    DPRINTF(MyStage, "Ticking MyStage, status=%d\n",
            static_cast<int>(_status));
    _status = _nextStatus;
}

} // namespace o3
} // namespace gem5
```

### 39.3 Scoreboard-style non-SimObject with `_name`

```cpp
// Illustrates GEM5_CLASS_VAR_USED + _name pattern
class MyTracker
{
  private:
    const std::string     _name;
    std::vector<bool>     ready;
    GEM5_CLASS_VAR_USED unsigned numEntries;  // checked only in assert()

  public:
    MyTracker(const std::string &my_name, unsigned n)
        : _name(my_name), ready(n, true), numEntries(n)
    {}

    std::string name() const { return _name; }

    bool get(unsigned idx) const
    {
        assert(idx < numEntries);
        return ready[idx];
    }

    void set(unsigned idx, bool val)
    {
        assert(idx < numEntries);
        DPRINTF(Scoreboard, "Tracker %s: idx %u → %d\n",
                _name, idx, val);
        ready[idx] = val;
    }
};
```

---

## 40. Checklist (Extended)

In addition to the checklist in Section 20, verify:

### DynInst & Register Rename
- [ ] All instruction ownership uses `DynInstPtr`, never raw `DynInst *`
- [ ] `DynInst::Status` bits set/cleared via member methods, not direct bitset access
- [ ] `isAlwaysReady()` checked before every scoreboard read/write
- [ ] `RenameInfo` pair captures both new and previous physical register mapping
- [ ] Getter/setter pairs use function overloading (same name, different signature)

### Per-Thread Resource Management
- [ ] Per-thread arrays sized `[MaxThreads]`, not `[numThreads]`
- [ ] Per-thread arrays initialised in `for (ThreadID tid = 0; tid < MaxThreads; tid++)` loop
- [ ] `SMTQueuePolicy` checked in constructor; `maxEntries[tid]` set accordingly
- [ ] `_status` + `_nextStatus` used for deferred stage state update
- [ ] `squashAfterInst[tid]` initialised to `nullptr` in constructor

### Statistics
- [ ] `ADD_STAT` in member initializer list, not constructor body
- [ ] `Vector` stats call `.init(N)` in constructor body
- [ ] Sub-names and sub-descriptions registered for every `Vector` indexed by enum
- [ ] `.prereq()` called for conditionally-interesting stats
- [ ] `statistics::Group` parent is the CPU, not `this`
- [ ] `Formula` used for derived stats, not manual computation in `Scalar`

### Probe Points
- [ ] Probe points registered in `regProbePoints()`, not the constructor
- [ ] Probe point names are `PascalCase` string literals
- [ ] Probe point member is a raw `ProbePointArg<T> *`, not `unique_ptr`

### Events & Timing
- [ ] `schedule()` calls use `clockEdge(Cycles(n))`, not tick arithmetic
- [ ] Event priorities use named `Event::*_Pri` constants
- [ ] Lambda event callbacks capture only `[this]`

### Memory System
- [ ] `Request` created before `Packet`; `RequestPtr` is `make_shared<Request>`
- [ ] `MemCmd` enum value used, not integer literal
- [ ] `Fault` compared to `NoFault`, not `nullptr`
- [ ] Port classes are nested inside their owning component

### Drain / Serialisation
- [ ] `DrainState` enum class values fully qualified
- [ ] `drain()` and `drainResume()` overridden in any `SimObject` with buffered state

---

## 41. Glossary (Extended)

The following entries supplement Section 21.

| Term | Definition |
|---|---|
| **`RefCountingPtr<T>`** | gem5 intrusive reference-counting smart pointer; base requires `RefCounted` |
| **`DynInstConstPtr`** | `RefCountingPtr<const DynInst>` — read-only instruction pointer |
| **`InstSeqNum`** | `uint64_t` monotonic instruction sequence number |
| **`PhysRegIdPtr`** | Pointer to a physical register identity object |
| **`RegId`** | Architectural register identity (class + index) |
| **`SMTQueuePolicy`** | Enum controlling how a shared resource is partitioned across SMT threads: Dynamic, Partitioned, Threshold |
| **`MaxWidth`** | `static constexpr int = 16` — maximum pipeline issue width |
| **`MaxThreads`** | `static constexpr int = 4` — maximum SMT thread count |
| **`ADD_STAT`** | Macro binding a `statistics::*` member to its gem5 name, units, and description |
| **`statistics::Vector`** | Per-index statistic array (e.g. one entry per SMT thread) |
| **`statistics::Formula`** | Derived statistic computed as an expression over other stats |
| **`statistics::Distribution`** | Histogram statistic |
| **`ThreadStatusMax`** | Enum sentinel equal to the number of thread status values; used to size arrays and loops |
| **`ProbePointArg<T>`** | Typed probe point; external listeners attach via `ProbeManager` |
| **`RenameInfo`** | `std::pair<PhysRegIdPtr, PhysRegIdPtr>` returning new + previous physical mapping |
| **`DepEntry`** | `typedef DependencyEntry<DynInstPtr>` — node in the dependency graph |
| **`SatCounter8`** | `GenericSatCounter<uint8_t>` — saturating counter used in branch predictors |
| **`Flags<T>`** | Typed bit-packed flag wrapper over unsigned integer |
| **`DrainState`** | Scoped enum: `Running`, `Draining`, `Drained`, `Resuming` |
| **`DrainManager`** | Singleton managing drain/resume lifecycle across all `Drainable` objects |
| **`EventFunctionWrapper`** | Wraps a `std::function<void()>` as a gem5 `Event` |
| **`clockEdge(Cycles n)`** | Returns the tick of the n-th future clock edge; use instead of tick arithmetic |
| **`simQuantum`** | Minimum tick gap for cross-queue event scheduling in parallel simulation |
| **`GEM5_CLASS_VAR_USED`** | Macro suppressing unused-variable warnings for debug-only class members |
| **`GEM5_NO_INLINE`** | Macro preventing the compiler from inlining a specific function |
| **`GEM5_UNLIKELY(x)`** | Branch prediction hint: `x` is expected to be false |
| **`NoFault`** | `std::shared_ptr<FaultBase>` sentinel representing no hardware fault |
| **`RequestorID`** | `uint16_t` identifier for the requestor of a memory request |
| **`PacketId`** | `uint64_t` unique packet identifier |
| **`MemCmd`** | Enum of memory command types: `ReadReq`, `WriteReq`, `UpgradeReq`, etc. |
| **`TracingExtension`** | CRTP extension to `Packet` for request tracing |
| **`IcachePort`** | Nested `RequestPort` subclass inside `Fetch` connecting to the I-cache |
| **`FetchTranslation`** | Nested `BaseMMU::Translation` subclass inside `Fetch` for async address translation |
| **`trapSquash[tid]`** | Per-thread flag set by `processTrapEvent()` to initiate a squash from a trap |
| **`tcSquash[tid]`** | Per-thread flag for squash triggered by a thread context write |
| **`squashAfterInst[tid]`** | `DynInstPtr` marking the instruction after which all subsequent insts should be squashed |
| **`priority_list`** | `std::list<ThreadID>` rotated each cycle for round-robin SMT commit scheduling |
