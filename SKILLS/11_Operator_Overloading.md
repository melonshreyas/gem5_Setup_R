# Operator Overloading Rules for Hardware Modelling Code

**Version:** 1.0 — July 2026  
**Standard:** Strict — Mandatory for All Engineers (<5‑Year)  
**Prerequisites:** `02_C++_Rules.md`, `09_Class_Design.md`

---

## Table of Contents

1. [Philosophy](#1-philosophy)
2. [Allowed Operators & Rationale](#2-allowed-operators--rationale)
3. [Forbidden Operators & Rationale](#3-forbidden-operators--rationale)
4. [Stream Operators (`<<` / `>>`)](#4-stream-operators---)
5. [Arithmetic & Comparison Operators](#5-arithmetic--comparison-operators)
6. [Subscript Operator (`[]`)](#6-subscript-operator-)
7. [Assignment & Move Operators](#7-assignment--move-operators)
8. [Conversion Operators](#8-conversion-operators)
9. [Operators for SystemC Signal Types](#9-operators-for-systemc-signal-types)
10. [Best Practices & Rules](#10-best-practices--rules)
11. [Complete Examples](#11-complete-examples)
12. [Anti‑Patterns](#12-anti-patterns)
13. [Checklist](#13-checklist)
14. [Glossary](#14-glossary)

---

## 1. Philosophy

Operator overloading is permitted **only** when the operator mirrors a natural,
unambiguous domain operation. In hardware modelling code:

> **Overload to clarify hardware semantics. Never overload to be clever.**

| Allowed overloads | Hardware purpose |
|---|---|
| `operator<<` on payload/struct types | Structured log output for AI test parsing |
| `operator==` / `operator!=` on packet/signal types | Required by `sc_signal<T>` for change detection |
| `operator+` / `operator-` on address or latency types | Natural arithmetic on hardware quantities |
| `operator[]` on register file / cache line | Natural indexing of hardware-indexed structures |
| `explicit operator T()` | Controlled, documented type widening |

---

## 2. Allowed Operators & Rationale

| Operator | Allowed? | Condition |
|---|---|---|
| `operator<<` (stream out) | ✅ | Non-mutating, structured, key=value format |
| `operator>>` (stream in) | ✅ | For deserialisation only; document format |
| `operator==` / `operator!=` | ✅ | Required for `sc_signal<T>` change detection |
| `operator<` / `operator>` / `operator<=` / `operator>=` | ✅ | For value ordering, e.g. address comparisons |
| `operator+` / `operator-` | ✅ | Pure — returns new value, no side effects |
| `operator*` / `operator/` | ✅ with care | Only for natural domain arithmetic (e.g. bandwidth × time) |
| `operator[]` | ✅ | For container-like types; must be bounds-checked in debug |
| `explicit operator T()` | ✅ | Explicit conversions only — never implicit |

---

## 3. Forbidden Operators & Rationale

| Operator | Forbidden? | Reason |
|---|---|---|
| `operator&&` / `operator\|\|` | ❌ | Changes short-circuit evaluation semantics — dangerous |
| `operator,` | ❌ | Changes sequencing — confusing and undocumented |
| `operator->` / `operator*` (dereference) | ❌ unless smart-pointer type | Hides pointer semantics and ownership |
| `operator new` / `operator delete` | ❌ | Custom allocators in hot paths cause non-deterministic timing |
| `operator()` (call operator as simulation action) | ❌ | Hides what is being called — use named methods |
| Implicit `operator T()` | ❌ | Silent conversion — use `explicit` only |

---

## 4. Stream Operators (`<<` / `>>`)

### Rule O‑01 — `operator<<` MUST return `std::ostream&` by reference

```cpp
// ✅ Correct signature
std::ostream& operator<<(std::ostream& os, const Packet& p);

// ❌ Wrong — returns by value (forces copy, breaks chaining)
std::ostream operator<<(std::ostream os, const Packet& p);
```

### Rule O‑02 — `operator<<` MUST be side-effect free on the serialised object

The object being streamed must not be modified by `operator<<`.

### Rule O‑03 — `operator<<` output MUST use `key=value` format for AI parseability

```cpp
std::ostream& operator<<(std::ostream& os, const Packet& p) {
    os << "Packet{"
       << " cmd="    << (p.cmd == Cmd::READ ? "R" : "W")
       << " addr=0x" << std::hex << p.addr
       << " size="   << std::dec << p.size
       << " valid="  << p.valid
       << "}";
    return os;
}
```

### Rule O‑04 — `operator<<` MUST be defined as a `friend` free function, not a member

```cpp
// ✅ Friend free function — allows os << pkt syntax
class Packet {
    friend std::ostream& operator<<(std::ostream& os, const Packet& p);
};
```

### Rule O‑05 — `operator>>` MUST document its expected format precisely

```cpp
/// Parses "Packet{cmd=R addr=0x1000 size=64 valid=true}"
std::istream& operator>>(std::istream& is, Packet& p);
```

---

## 5. Arithmetic & Comparison Operators

### Rule O‑06 — Arithmetic operators MUST be pure — no side effects

```cpp
// ✅ Pure — creates and returns new value
Addr operator+(const Addr& a, uint64_t offset) {
    return Addr{a.value + offset};
}

// ❌ Hidden side effect
Addr operator+(const Addr& a, uint64_t offset) {
    ++g_addr_arith_count;   // hidden side effect — forbidden
    return Addr{a.value + offset};
}
```

### Rule O‑07 — Prefer free functions for symmetric binary operators

```cpp
// ✅ Free function — works for both (Addr + uint64) and (uint64 + Addr)
Addr operator+(const Addr& a, uint64_t offset);
Addr operator+(uint64_t offset, const Addr& a);

// Member function only works for (Addr + uint64) on the left
```

### Rule O‑08 — `operator==` and `operator!=` MUST be defined together

```cpp
bool operator==(const Packet& a, const Packet& b) {
    return a.addr == b.addr && a.size == b.size
        && a.valid == b.valid && a.cmd == b.cmd;
}
bool operator!=(const Packet& a, const Packet& b) { return !(a == b); }
```

### Rule O‑09 — `operator==` on `sc_signal` payload types is MANDATORY

`sc_signal<T>` uses `operator==` to decide whether to notify subscribers.
A missing or incorrect `operator==` causes spurious delta-cycle firings.

```cpp
// ✅ Required for sc_signal<Packet>
bool Packet::operator==(const Packet& o) const {
    return addr == o.addr && size == o.size && valid == o.valid;
}
```

### Rule O‑10 — Provide `operator<` for types used in `std::map` or `std::set`

```cpp
// ✅ Enables use as std::map key
bool operator<(const Addr& a, const Addr& b) { return a.value < b.value; }
```

---

## 6. Subscript Operator (`[]`)

### Rule O‑11 — `operator[]` MUST be provided in both `const` and non-`const` versions

```cpp
class RegisterFile {
public:
    uint32_t& operator[](uint32_t idx) {
        sc_assert(idx < values_.size());
        return values_[idx];
    }
    const uint32_t& operator[](uint32_t idx) const {
        sc_assert(idx < values_.size());
        return values_[idx];
    }
private:
    std::vector<uint32_t> values_;
};
```

### Rule O‑12 — `operator[]` MUST bounds-check in debug builds

Use `sc_assert(idx < size)` before the access.

---

## 7. Assignment & Move Operators

### Rule O‑13 — Copy and move assignment operators MUST preserve invariants

```cpp
Packet& operator=(const Packet& o) {
    if (this == &o) return *this;   // self-assignment guard
    addr  = o.addr;
    size  = o.size;
    valid = o.valid;
    return *this;
}
```

### Rule O‑14 — Assignment operators MUST return `*this` by reference

```cpp
// ✅
T& operator=(const T& o) { ...; return *this; }

// ❌ Returns void — breaks chaining (a = b = c)
void operator=(const T& o) { ... }
```

### Rule O‑15 — Assignment operators MUST NOT throw in SystemC/TLM hot paths

---

## 8. Conversion Operators

### Rule O‑16 — All conversion operators MUST be `explicit`

```cpp
// ✅ Explicit — must be requested deliberately
class Addr {
public:
    explicit operator uint64_t() const { return value_; }
private:
    uint64_t value_;
};

// Usage:
uint64_t raw = static_cast<uint64_t>(addr);   // explicit — visible in code review

// ❌ Implicit conversion — forbidden
class Addr {
    operator uint64_t() const { return value_; }   // silent implicit conversion
};
```

### Rule O‑17 — Conversion operators MUST be documented with their exact semantics

```cpp
/// Converts Address to its raw 64-bit physical byte address.
/// Precondition: address must be page-aligned.
explicit operator uint64_t() const;
```

---

## 9. Operators for SystemC Signal Types

When defining a struct or class to be used as `sc_signal<T>`, three operators are mandatory:

### Rule O‑18 — `sc_signal<T>` payload MUST define `operator==` (change detection)

### Rule O‑19 — `sc_signal<T>` payload MUST define `operator<<` (VCD tracing)

### Rule O‑20 — `sc_signal<T>` payload MAY define `operator=` (copy assignment)

```cpp
struct MemRequest {
    uint64_t addr  = 0;
    uint32_t bytes = 0;
    bool     write = false;
    bool     valid = false;

    // ① Required: change detection for sc_signal
    bool operator==(const MemRequest& o) const {
        return addr == o.addr && bytes == o.bytes
            && write == o.write && valid == o.valid;
    }
    bool operator!=(const MemRequest& o) const { return !(*this == o); }

    // ② Required: VCD trace output (and AI dump_state logging)
    friend std::ostream& operator<<(std::ostream& os, const MemRequest& r) {
        os << "MemRequest{"
           << " addr=0x" << std::hex << r.addr
           << " bytes="  << std::dec << r.bytes
           << " write="  << r.write
           << " valid="  << r.valid
           << "}";
        return os;
    }
};
```

---

## 10. Best Practices & Rules

### Rule O‑21 — Keep operator implementations short and obvious

If the operator body exceeds 5 lines, extract a named helper function.

### Rule O‑22 — Document operator semantics and complexity in the header

```cpp
/// Adds offset bytes to address. O(1). No overflow check.
Addr operator+(const Addr& a, uint64_t offset);
```

### Rule O‑23 — Never overload operators to perform I/O, allocation, or simulation side effects

```cpp
// ❌ Forbidden — operator performs I/O
Packet operator+(const Packet& a, const Packet& b) {
    std::cout << "merging packets";   // I/O in operator — forbidden
    return {a.addr, a.size + b.size};
}
```

### Rule O‑24 — Never overload operators in public APIs consumed by AI tests unless output is structured `key=value`

AI test harnesses parse `operator<<` output. Unstructured output breaks parsing.

---

## 11. Complete Examples

### 11.1 Address type with arithmetic operators

```cpp
class PhysAddr {
public:
    explicit PhysAddr(uint64_t v = 0) : value_(v) {}

    PhysAddr operator+(uint64_t offset)  const { return PhysAddr{value_ + offset}; }
    PhysAddr operator-(uint64_t offset)  const { return PhysAddr{value_ - offset}; }
    bool     operator==(const PhysAddr& o) const { return value_ == o.value_; }
    bool     operator!=(const PhysAddr& o) const { return !(*this == o); }
    bool     operator< (const PhysAddr& o) const { return value_ <  o.value_; }
    bool     operator>=(const PhysAddr& o) const { return value_ >= o.value_; }

    explicit operator uint64_t() const { return value_; }

    friend std::ostream& operator<<(std::ostream& os, const PhysAddr& a) {
        return os << "PhysAddr{0x" << std::hex << a.value_ << "}";
    }

private:
    uint64_t value_;
};
```

### 11.2 Cache line struct for `sc_signal<CacheLine>`

```cpp
struct CacheLine {
    std::array<uint8_t, 64> data{};
    uint64_t                tag   = 0;
    bool                    valid = false;
    bool                    dirty = false;

    bool operator==(const CacheLine& o) const {
        return tag == o.tag && valid == o.valid
            && dirty == o.dirty && data == o.data;
    }
    bool operator!=(const CacheLine& o) const { return !(*this == o); }

    friend std::ostream& operator<<(std::ostream& os, const CacheLine& l) {
        os << "CacheLine{"
           << " tag=0x"  << std::hex << l.tag
           << " valid="  << std::dec << l.valid
           << " dirty="  << l.dirty
           << "}";
        return os;
    }
};
```

---

## 12. Anti‑Patterns

| Anti‑Pattern | Consequence | Fix |
|---|---|---|
| Implicit conversion operator | Silent precision loss — `Addr a = 0x1000` compiles silently | `explicit operator T()` |
| `operator<<` with free-form string | AI cannot parse fields | `key=value` format |
| `operator<<` that modifies the object | `const`-correctness violation | Make it a `const` operation |
| Missing `operator!=` when `operator==` defined | Inconsistent interface | Define both together |
| Missing `operator==` on `sc_signal<T>` payload | Spurious delta-cycle firings | Always define `operator==` |
| Overloading `operator&&` / `operator||` | Changes short-circuit semantics | Use named functions |
| Operator with heap allocation | Non-deterministic timing | Operators must be pure, no allocation |
| Operator with logging | Side effect in hot path | Guard with `#ifdef DEBUG` |

---

## 13. Checklist

- [ ] `operator<<` returns `std::ostream&` by reference
- [ ] `operator<<` is side-effect free on the serialised object
- [ ] `operator<<` uses `key=value` format
- [ ] `operator==` and `operator!=` defined together
- [ ] All `sc_signal<T>` payloads define `operator==` and `operator<<`
- [ ] All conversion operators are `explicit`
- [ ] `operator[]` checks bounds in debug builds
- [ ] Arithmetic operators are pure (no side effects)
- [ ] Forbidden operators (`&&`, `||`, `,`) not overloaded
- [ ] No allocation or I/O inside any operator
- [ ] Operator complexity documented in header

---

## 14. Glossary

| Term | Definition |
|---|---|
| **Pure operator** | Operator that returns a new value without modifying any existing state |
| **Short-circuit evaluation** | `&&` and `\|\|` evaluate the right operand only if needed — overloading breaks this |
| **`sc_signal` change detection** | `sc_signal<T>` calls `operator==` to decide whether to notify processes |
| **VCD tracing** | Value Change Dump — requires `operator<<` to serialise signal values |
| **Implicit conversion** | Conversion applied automatically without an explicit `static_cast` — forbidden |
| **Explicit conversion** | Conversion requires `static_cast<T>()` — always prefer this |
