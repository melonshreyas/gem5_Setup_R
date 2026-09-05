# C++ Engineering Rules for Deterministic Hardware Modelling, SystemC, VP & AI‑Testable Code

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for <5‑Year Engineers

---

## Table of Contents

1. [Philosophy of C++ in Hardware Modelling](#1-philosophy-of-c-in-hardware-modelling)
2. [Header/Source Separation Rules](#2-headersource-separation-rules)
3. [Declaration vs Definition Rules](#3-declaration-vs-definition-rules)
4. [Include Rules](#4-include-rules)
5. [Namespace Rules](#5-namespace-rules)
6. [Type Rules](#6-type-rules)
7. [Const‑Correctness Rules](#7-constcorrectness-rules)
8. [Reference & Pointer Rules](#8-reference--pointer-rules)
9. [Memory & Lifetime Rules](#9-memory--lifetime-rules)
10. [Class Design Rules](#10-class-design-rules)
11. [Special Member Functions Rules](#11-special-member-functions-rules)
12. [Operator Overloading Rules](#12-operator-overloading-rules)
13. [Function Rules](#13-function-rules)
14. [Template Rules](#14-template-rules)
15. [STL Usage Rules](#15-stl-usage-rules)
16. [Error Handling Rules](#16-error-handling-rules)
17. [Logging Rules](#17-logging-rules)
18. [AI‑Testability Rules](#18-aitestability-rules)
19. [Performance Rules](#19-performance-rules)
20. [Anti‑Patterns](#20-anti-patterns)
21. [Code Examples](#21-code-examples)
22. [Hardware‑Aligned C++ Patterns](#22-hardwarealigned-c-patterns)
23. [SystemC‑Safe C++ Rules](#23-systemcsafe-c-rules)
24. [TLM‑Safe C++ Rules](#24-tlmsafe-c-rules)
25. [Glossary](#25-glossary)

---

## 1. Philosophy of C++ in Hardware Modelling

C++ for hardware modelling is **NOT** general‑purpose C++. It must be:

| Property | Meaning |
|---|---|
| **Deterministic** | Same inputs → same outputs, always |
| **Explicit** | No implicit behaviour, conversions, or surprises |
| **Safe** | No UB, no dangling references, no leaks |
| **Hardware‑aligned** | Reflects real pipeline/bus/register semantics |
| **AI‑testable** | Pure functions, no hidden state, clear interfaces |
| **SystemC‑compatible** | Obeys SC_METHOD/SC_THREAD constraints |
| **VP‑compatible** | Suitable for virtual prototype integration |
| **Performance‑predictable** | O-complexity known at design time |

This document defines strict rules that **MUST** be followed.

---

## 2. Header/Source Separation Rules

### Rule C‑01 — Headers contain declarations only

**Headers MUST contain:**
- Class declarations
- Struct declarations
- Function declarations
- Template definitions
- Inline functions
- `constexpr` functions
- `extern` variable declarations

**Headers MUST NOT contain:**
- Non‑inline function definitions
- Global variable definitions
- Static variable definitions
- Large includes
- `using namespace` directives

### Rule C‑02 — Every header MUST have include guards

**Allowed — traditional guards:**
```cpp
#ifndef MODULE_H
#define MODULE_H
// ...
#endif
```

**Allowed — pragma once:**
```cpp
#pragma once
```

**Forbidden:**
- Multiple include guards in the same file
- Missing include guards entirely

---

## 3. Declaration vs Definition Rules

### Rule C‑03 — Declarations in headers, definitions in `.cpp`

```cpp
// coord.h
struct Coord { int x, y; };
Coord operator+(const Coord&, const Coord&);
```

```cpp
// coord.cpp
Coord operator+(const Coord& a, const Coord& b) { ... }
```

### Rule C‑04 — Templates MUST be defined in headers

Templates require full visibility at the point of instantiation. Place all template definitions in the header.

---

## 4. Include Rules

### Rule C‑05 — Include only what you use

**Forbidden:**
```cpp
#include <bits/stdc++.h>
#include <iostream>   // if only using std::string
```

**Allowed:**
```cpp
#include <string>
#include <vector>
#include <map>
```

### Rule C‑06 — No circular includes

Use forward declarations to break cycles:
```cpp
class Packet;   // forward declaration — do not #include "packet.h"
```

---

## 5. Namespace Rules

### Rule C‑07 — NEVER use `using namespace std;` in headers

`using namespace std;` is only permitted inside `.cpp` function bodies. It is **never** allowed at file scope in a header.

### Rule C‑08 — Use explicit namespace qualification

```cpp
std::string name;
std::vector<int> vec;
```

---

## 6. Type Rules

### Rule C‑09 — Prefer fixed‑width integer types

| Use | Avoid |
|---|---|
| `uint32_t`, `uint64_t` | `int`, `long` |
| `int32_t`, `int64_t` | `short`, `unsigned int` |

Fixed‑width types make hardware register widths explicit and portable.

### Rule C‑10 — Prefer `enum class`

```cpp
enum class State { IDLE, BUSY, WAIT };
```

`enum class` prevents accidental integer promotion and name collisions.

---

## 7. Const‑Correctness Rules

### Rule C‑11 — Const everything that can be const

`const` applies to:
- Variables
- Methods
- References
- Pointers
- Function parameters
- Return types

```cpp
int get() const;
const uint32_t MAX_DEPTH = 16;
```

### Rule C‑12 — Const reference is the default parameter type

```cpp
void process(const Packet& p);   // correct
void process(Packet p);          // forbidden unless a copy is required
```

---

## 8. Reference & Pointer Rules

### Rule C‑13 — Prefer references over pointers

| Use references when | Use pointers when |
|---|---|
| Object MUST exist | Ownership is explicit |
| Null is not meaningful | Null is a valid state |
| No ownership transfer | Polymorphism requires indirection |

### Rule C‑14 — NEVER return references to locals

**Forbidden (undefined behaviour):**
```cpp
const int& f() {
    int x = 10;
    return x;   // UB — dangling reference
}
```

---

## 9. Memory & Lifetime Rules

### Rule C‑15 — Prefer automatic storage

Use stack variables by default. Heap allocation must be justified.

### Rule C‑16 — Prefer RAII

| Use | Avoid |
|---|---|
| `std::unique_ptr` | Raw `new` |
| `std::shared_ptr` | Raw `delete` |
| `std::vector` | C‑style arrays with manual memory |

### Rule C‑17 — No dynamic allocation in hot paths

**Forbidden inside:**
- `SC_METHOD` callbacks
- `b_transport` handlers
- Tight simulation loops

---

## 10. Class Design Rules

### Rule C‑18 — All data members MUST be private

No public data members. Expose state only through accessors.

### Rule C‑19 — Use `explicit` constructors

```cpp
explicit Packet(int size);   // correct
Packet(int size);            // forbidden — allows implicit conversion
```

### Rule C‑20 — No implicit conversions

**Forbidden:**
```cpp
Packet p = 10;   // implicit construction
```

---

## 11. Special Member Functions Rules

### Rule C‑21 — Define or delete all special members

You MUST explicitly define or delete every special member function:

```cpp
class Bus {
public:
    Bus() = default;
    Bus(const Bus&) = delete;
    Bus& operator=(const Bus&) = delete;
    Bus(Bus&&) = default;
    Bus& operator=(Bus&&) = default;
    ~Bus() = default;
};
```

Leaving special members implicit is forbidden for non‑trivial types.

---

## 12. Operator Overloading Rules

### Rule C‑22 — Only overload operators that improve clarity

| Allowed | Forbidden |
|---|---|
| `<<`, `>>` | `&&`, `\|\|` |
| `==`, `!=` | `,` |
| `+`, `-`, `*`, `/` | `->`, `.` |

### Rule C‑23 — Stream operators MUST return stream by reference

```cpp
std::ostream& operator<<(std::ostream& os, const Coord& c);
```

---

## 13. Function Rules

### Rule C‑24 — No default arguments in definitions

**Allowed (declaration in header):**
```cpp
void f(int x = 10);
```

**Forbidden (definition):**
```cpp
void f(int x = 10) { ... }   // default argument in definition
```

### Rule C‑25 — Functions MUST be small

Maximum **40 lines** per function body. Extract helpers for larger logic.

---

## 14. Template Rules

### Rule C‑26 — Templates MUST be simple

**Forbidden:**
- Template metaprogramming
- SFINAE tricks
- Complex CRTP hierarchies

**Allowed:**
- Simple class templates (`template<typename T>`)
- Simple function templates

---

## 15. STL Usage Rules

### Rule C‑27 — Prefer `vector`

`std::vector` is the default container. Justify any deviation.

### Rule C‑28 — Avoid `list`

`std::list` has poor cache locality. Use `std::deque` if front insertion is needed.

### Rule C‑29 — Avoid `unordered_map`

`std::unordered_map` has non‑deterministic iteration order. Use `std::map` for deterministic traversal.

---

## 16. Error Handling Rules

### Rule C‑30 — No exceptions in SystemC/VP

**Forbidden:**
```cpp
throw std::runtime_error("fail");
```

**Allowed:**
- Status/return codes
- `SC_REPORT_ERROR` / `SC_REPORT_FATAL`

---

## 17. Logging Rules

### Rule C‑31 — Logging MUST be deterministic

**Correct:**
```cpp
std::ostringstream oss;
oss << "State=" << st;
SC_REPORT_INFO("TAG", oss.str().c_str());
```

**Forbidden:**
- `printf`
- `std::cout`
- `std::cerr`

These bypass SystemC's time‑stamped reporting and produce non‑deterministic output ordering.

---

## 18. AI‑Testability Rules

### Rule C‑32 — All functions MUST be testable

Functions MUST have:
- Clear, typed inputs
- Clear, typed outputs
- No hidden state
- No observable side effects beyond the return value

### Rule C‑33 — No floating‑point nondeterminism

Fix the rounding mode at process start. Never compare floats with `==`. Use integer arithmetic for cycle counts and addresses.

---

## 19. Performance Rules

### Rule C‑34 — No O(n²) algorithms in modelling loops

**Forbidden:**
- Bubble sort
- Insertion sort
- Selection sort inside per‑cycle callbacks

**Allowed:**
- `std::sort` — O(n log n)
- Binary search — O(log n)
- Hash lookup on known‑bounded tables — O(1) amortised

---

## 20. Anti‑Patterns

The following patterns are **forbidden** in this codebase:

| Anti‑Pattern | Reason |
|---|---|
| Hidden global state | Breaks determinism and testability |
| Implicit conversions | Source of silent bugs |
| Raw pointers without ownership | Leads to leaks and dangling refs |
| Returning references to locals | Undefined behaviour |
| `using namespace std` in headers | Pollutes consumer namespaces |
| Dynamic allocation in hot paths | Non‑deterministic timing |
| Logging inside critical loops | Perturbs simulation timing |
| Floating‑point nondeterminism | Breaks reproducibility |
| Unbounded recursion | Stack overflow risk |
| Unbounded containers | Memory and timing unpredictability |

---

## 21. Code Examples

### 21.1 Good Example — Deterministic Class

```cpp
class Coord {
private:
    int32_t x_;
    int32_t y_;

public:
    explicit Coord(int32_t x, int32_t y) : x_(x), y_(y) {}

    Coord(const Coord&) = default;
    Coord& operator=(const Coord&) = default;
    ~Coord() = default;

    int32_t x() const { return x_; }
    int32_t y() const { return y_; }
};
```

### 21.2 Bad Example — Hidden State

```cpp
// FORBIDDEN — static local state breaks determinism
static int counter = 0;
int next_id() { return ++counter; }
```

---

## 22. Hardware‑Aligned C++ Patterns

### 22.1 Pipeline Stage Pattern

```cpp
struct Stage {
    bool     busy = false;
    Packet   pkt  = {};
};

std::array<Stage, NUM_STAGES> pipeline = {};
```

### 22.2 FIFO Pattern

```cpp
class FIFO {
private:
    std::vector<Packet> q_;
    std::size_t         capacity_;

public:
    explicit FIFO(std::size_t cap) : capacity_(cap) { q_.reserve(cap); }

    FIFO(const FIFO&) = delete;
    FIFO& operator=(const FIFO&) = delete;

    bool push(const Packet& p);
    Packet pop();
    bool empty() const { return q_.empty(); }
    bool full()  const { return q_.size() >= capacity_; }
};
```

---

## 23. SystemC‑Safe C++ Rules

| Rule | Description |
|---|---|
| **C‑35** | No blocking calls (`wait()`, `sleep()`) inside `SC_METHOD` |
| **C‑36** | No dynamic allocation (`new`, `malloc`) inside `SC_METHOD` |
| **C‑37** | No logging (`cout`, `printf`) inside `SC_METHOD` |
| **C‑38** | No shared mutable state across `SC_THREAD`/`SC_METHOD` processes without sensitivity lists |

---

## 24. TLM‑Safe C++ Rules

| Rule | Description |
|---|---|
| **C‑39** | `b_transport` MUST be deterministic — same payload → same effect |
| **C‑40** | No exceptions inside `b_transport` — use TLM response status |
| **C‑41** | No dynamic allocation inside `b_transport` hot path |
| **C‑42** | No logging in critical TLM paths — use debug build guards |

---

## 25. Glossary

| Term | Definition |
|---|---|
| **Determinism** | Same inputs → same outputs, every run |
| **RAII** | Resource Acquisition Is Initialization — lifetime tied to scope |
| **UB** | Undefined Behaviour — compiler is free to do anything |
| **O(n)** | Linear time complexity |
| **O(n²)** | Quadratic time complexity |
| **TLM** | Transaction Level Modelling |
| **VP** | Virtual Prototype |
| **SC_METHOD** | Combinational SystemC process — no blocking allowed |
| **SC_THREAD** | Sequential SystemC process — blocking with `wait()` allowed |
| **SFINAE** | Substitution Failure Is Not An Error — advanced template technique |
| **CRTP** | Curiously Recurring Template Pattern |
