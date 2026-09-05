# SKILLS — Engineering Standards & Reference Documents

This directory contains the engineering standards, coding rules, and reference
documents for the gem5 / SystemC / Virtual Prototype (VP) codebase.

All documents marked **Mandatory** MUST be read and followed before committing
code. Documents marked **Reference** are supplementary guides.

---

## Index

| # | File | Title | Audience | Status |
|---|------|--------|----------|--------|
| 01 | [01_Core_Philosophy.md](01_Core_Philosophy.md) | Core Philosophy for Deterministic Hardware Modelling & SystemC/VP Engineering | All engineers — read first | Mandatory |
| 02 | [02_C++_Rules.md](02_C++_Rules.md) | C++ Engineering Rules for Deterministic Hardware Modelling, SystemC, VP & AI‑Testable Code | All engineers (<5‑yr mandatory) | Mandatory |
| 03 | [03_SystemC_Rules.md](03_SystemC_Rules.md) | SystemC Engineering Rules for Deterministic Hardware Modelling | All engineers (<5‑yr mandatory) | Mandatory |
| 04 | [04_TLM2_Patterns.md](04_TLM2_Patterns.md) | Strict TLM‑2.0 Engineering Rules, Patterns, Diagrams & VP Modelling Techniques | SystemC/VP engineers (<5‑yr mandatory) | Mandatory |
| 05 | [05_VP_Performance_Modelling.md](05_VP_Performance_Modelling.md) | Strict VP Performance Modelling Rules, Patterns, Diagrams & SystemC/TLM Integration | VP/perf-modelling engineers (<5‑yr mandatory) | Mandatory |
| 06 | [06_DSA_Hardware_Patterns.md](06_DSA_Hardware_Patterns.md) | DSA Patterns Adapted for Hardware Modelling, SystemC, TLM‑2.0 & VP Performance Modelling | All engineers (<5‑yr mandatory) | Mandatory |
| 07 | [07_AI_Testing_Hooks.md](07_AI_Testing_Hooks.md) | AI Black‑Box Testing Hooks, Deterministic Logging, Structural Testability & Simulation‑Safe Instrumentation | All engineers (<5‑yr mandatory) | Mandatory |
| 08 | [08_Hardware_Diagrams.md](08_Hardware_Diagrams.md) | Hardware Architecture Diagrams for SystemC, TLM‑2.0, VP Performance Modelling & AI‑Testable Simulation | All engineers | Mandatory |
| 09 | [09_Class_Design.md](09_Class_Design.md) | Class Design Rules for Deterministic Hardware Modelling, SystemC, TLM & VP | All engineers (<5‑yr mandatory) | Mandatory |
| 10 | [10_Memory_Safety.md](10_Memory_Safety.md) | Memory Safety Rules, Patterns & Checks for Deterministic SystemC/TLM/VP Modelling | All engineers (<5‑yr mandatory) | Mandatory |
| 11 | [11_Operator_Overloading.md](11_Operator_Overloading.md) | Operator Overloading Rules for Hardware Modelling Code | All engineers (<5‑yr mandatory) | Mandatory |
| 12 | [12_Review_Checklists.md](12_Review_Checklists.md) | Code Review Checklists for C++, SystemC, TLM, VP, Memory Safety & AI‑Testability | All engineers — use in every PR | Mandatory |
| 13 | [13_AntiPatterns.md](13_AntiPatterns.md) | Anti‑Patterns in Hardware Modelling, SystemC, TLM & VP Code | All engineers | Mandatory |
| 14 | [14_Templates.md](14_Templates.md) | Reusable Templates & Code Snippets for SystemC/TLM/VP Modelling | All engineers | Reference |
| 15 | [15_Glossary.md](15_Glossary.md) | Glossary — Definitions for All Terms Used Across the SKILLS Standard | All engineers | Reference |
| 16 | [16_Gem5_Rules.md](16_Gem5_Rules.md) | gem5 C++ Engineering Rules — Syntax, Patterns & Idioms (v2.0 — LRM-depth, 135 rules, extracted from `.cc`/`.hh` source) | All gem5 contributors (<5‑yr mandatory) | Mandatory |

> Additional documents will be added here as they are authored. Re‑number
> entries to maintain a logical reading order.

---

## How to Use This Directory

1. **Read before you code.** Each document covers rules you will encounter
   during code review. Understanding them upfront prevents rework.

2. **Reference during review.** When raising or receiving a review comment,
   cite the relevant rule by its identifier (e.g. *C‑09*, *C‑17*) so the
   reasoning is traceable.

3. **Propose changes via PR.** If a rule needs updating, open a pull request
   against the relevant document. Include a rationale and any affected
   examples.

---

## Document Naming Convention

```
NN_Short_Title.md
```

| Segment | Meaning |
|---|---|
| `NN` | Two‑digit sequence number (01, 02, …) — controls reading order |
| `Short_Title` | PascalCase descriptor, underscores as word separators |

**Examples:**
```
01_Style_Guide.md
02_C++_Rules.md
03_SystemC_Patterns.md
04_TLM_Cookbook.md
05_AI_Test_Harness.md
```

---

## Document Template

Every new document MUST begin with the following front matter:

```markdown
# <Full Title>

**Version:** X.Y — Month Year
**Standard:** [Mandatory | Reference | Draft]
**Audience:** <target role / experience level>

---
```

---

---

*Documents in this directory are internal engineering standards.
They supplement but do not replace the gem5 project's
[CONTRIBUTING.md](../CONTRIBUTING.md) and
[CODE-OF-CONDUCT.md](../CODE-OF-CONDUCT.md).*
