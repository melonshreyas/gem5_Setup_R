# Address Translation Boilerplate

This folder contains two levels of the same model:

- `short_address_translation.cc` is a standalone C++17 example. It maps a
  virtual page to a physical page with a fixed offset.
- `address_translation.hh` and `address_translation.cc` are a gem5-style
  `SimObject` with a deterministic direct-mapped TLB.

## Short example

```sh
c++ -std=c++17 -Wall -Wextra -pedantic \
    short_address_translation.cc -o short_address_translation
./short_address_translation
```

The expected output is similar to:

```text
PA=0x1002345 hit=true
```

## Detailed gem5 model

The Python parameters configure the generated `AddressTranslationParams`:

| Parameter | Meaning | Example |
| --- | --- | --- |
| `page_bits` | Log2 of page size | `12` for 4 KiB |
| `physical_offset` | Offset added to the virtual page number | `0x1000` |
| `tlb_entries` | Direct-mapped entry count; must be a power of two | `64` |
| `hit_latency` | Hit latency in cycles | `1` |
| `miss_latency` | Miss latency in cycles | `12` |

The component is intentionally local to this folder. To build it as part of a
gem5 binary, add this directory to the appropriate parent `SConscript` or move
the files under a selected `src/` subsystem and update the include path to
match the final location.

The model is not a full MMU: it has no page table, permissions, faults, or
memory port. It is a focused starting point for experimenting with translation
latency and TLB replacement behavior.