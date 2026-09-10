/*
 * Copyright (c) 2026, gem5 Contributors
 * All rights reserved.
 */

#include "AI_BOILER_PLATE_GEN/address_translation.hh"

#include <sstream>

namespace gem5
{

AddressTranslation::AddressTranslation(const AddressTranslationParams &params)
    : SimObject(params),
      pageBits(params.page_bits),
      pageSize(checkedPageSize(params.page_bits)),
      pageMask(pageSize - 1),
      physicalOffset(params.physical_offset),
      hitLatency(params.hit_latency),
      missLatency(params.miss_latency),
      indexMask(checkedIndexMask(params.tlb_entries)),
      entries(params.tlb_entries)
{
}

AddressTranslation::TranslationResult
AddressTranslation::translate(Addr virtual_address)
{
    const Addr virtual_page = virtual_address >> pageBits;
    const std::size_t index = indexFor(virtual_page);
    Entry &entry = entries[index];
    const bool hit = entry.valid && entry.virtualPage == virtual_page;

    if (hit) {
        ++hitCount;
    } else {
        ++missCount;
        entry.virtualPage = virtual_page;
        entry.physicalPage = virtual_page + physicalOffset;
        entry.valid = true;
    }

    const Addr physical_address =
        (entry.physicalPage << pageBits) | (virtual_address & pageMask);
    return {physical_address, hit, hit ? hitLatency : missLatency};
}

void
AddressTranslation::reset()
{
    for (Entry &entry : entries) {
        entry = Entry{};
    }
    hitCount = 0;
    missCount = 0;
}

std::string
AddressTranslation::dumpState() const
{
    std::ostringstream stream;
    stream << "AddressTranslation{entries=" << entries.size()
           << ", hits=" << hitCount << ", misses=" << missCount << '}';
    return stream.str();
}

uint64_t
AddressTranslation::hits() const
{
    return hitCount;
}

uint64_t
AddressTranslation::misses() const
{
    return missCount;
}

bool
AddressTranslation::isPowerOfTwo(uint64_t value)
{
    return value != 0 && (value & (value - 1)) == 0;
}

uint64_t
AddressTranslation::checkedPageSize(uint64_t page_bits)
{
    if (page_bits == 0 || page_bits >= 63) {
        fatal("page_bits must be in the range [1, 62]");
    }
    return UINT64_C(1) << page_bits;
}

uint64_t
AddressTranslation::checkedIndexMask(uint64_t entry_count)
{
    if (!isPowerOfTwo(entry_count)) {
        fatal("tlb_entries must be a non-zero power of two");
    }
    return entry_count - 1;
}

std::size_t
AddressTranslation::indexFor(Addr virtual_page) const
{
    return static_cast<std::size_t>(virtual_page & indexMask);
}

} // namespace gem5