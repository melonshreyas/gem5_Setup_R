/*
 * Small address-translation example.
 *
 * This is intentionally independent of gem5 so the core mapping can be
 * compiled and tested in isolation.
 */

#include <cstdint>
#include <iomanip>
#include <iostream>

struct TranslationResult
{
    uint64_t physical_address;
    bool hit;
};

TranslationResult
translate(uint64_t virtual_address, uint64_t page_size,
           uint64_t physical_offset)
{
    const uint64_t page_offset = virtual_address % page_size;
    const uint64_t virtual_page = virtual_address / page_size;
    const uint64_t physical_page = virtual_page + physical_offset;

    return {physical_page * page_size + page_offset, true};
}

int
main()
{
    constexpr uint64_t page_size = 4096;
    constexpr uint64_t physical_offset = 0x1000;
    const TranslationResult result =
        translate(0x2345, page_size, physical_offset);

    std::cout << "PA=0x" << std::hex << result.physical_address
              << " hit=" << std::boolalpha << result.hit << '\n';
    return 0;
}