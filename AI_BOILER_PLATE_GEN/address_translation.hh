/*
 * Copyright (c) 2026, gem5 Contributors
 * All rights reserved.
 */

#ifndef __AI_BOILER_PLATE_GEN_ADDRESS_TRANSLATION_HH__
#define __AI_BOILER_PLATE_GEN_ADDRESS_TRANSLATION_HH__

#include <cstdint>
#include <string>
#include <vector>

#include "base/types.hh"
#include "params/AddressTranslation.hh"
#include "sim/sim_object.hh"

namespace gem5
{

/// Models a deterministic direct-mapped TLB with a configurable page map.
class AddressTranslation : public SimObject
{
  public:
    struct TranslationResult
    {
        Addr physicalAddress;
        bool hit;
        Tick latency;
    };

    explicit AddressTranslation(const AddressTranslationParams &params);
    ~AddressTranslation() noexcept override = default;

    TranslationResult translate(Addr virtual_address);
    void reset();
    std::string dumpState() const;

    uint64_t hits() const;
    uint64_t misses() const;

  private:
    struct Entry
    {
        Addr virtualPage = 0;
        Addr physicalPage = 0;
        bool valid = false;
    };

    static bool isPowerOfTwo(uint64_t value);
    static uint64_t checkedPageSize(uint64_t page_bits);
    static uint64_t checkedIndexMask(uint64_t entry_count);
    std::size_t indexFor(Addr virtual_page) const;

    const uint64_t pageBits;
    const uint64_t pageSize;
    const uint64_t pageMask;
    const uint64_t physicalOffset;
    const Tick hitLatency;
    const Tick missLatency;
    const uint64_t indexMask;
    std::vector<Entry> entries;
    uint64_t hitCount = 0;
    uint64_t missCount = 0;
};

} // namespace gem5

#endif // __AI_BOILER_PLATE_GEN_ADDRESS_TRANSLATION_HH__