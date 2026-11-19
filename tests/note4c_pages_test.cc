#include <cassert>
#include <cstdio>
#include <cstring>
#include "../firmware/main/hearth_pages.h"

int main() {
    // Rotation ticks: :00-:09 weather, :10-:19 tasks, :20-:29 groceries, repeat.
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(0)), "weather"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(9)), "weather"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(10)), "today"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(19)), "today"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(20)), "groceries"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(29)), "groceries"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(30)), "weather"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(40)), "today"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(50)), "groceries"));
    assert(!std::strcmp(HearthSlotPage(HearthRotationSlot(59)), "groceries"));

    // Daytime window is [07:00, 22:00).
    assert(!HearthDaytime(6));
    assert(HearthDaytime(7));
    assert(HearthDaytime(15));
    assert(HearthDaytime(21));
    assert(!HearthDaytime(22));
    assert(!HearthDaytime(0));
    assert(!HearthDaytime(3));

    // Wake timer always targets the next 07:00 local.
    assert(HearthSecondsUntilHour(22 * 3600, 7) == 9 * 3600);          // 22:00 -> 07:00
    assert(HearthSecondsUntilHour(23 * 3600 + 59 * 60 + 59, 7) == 7 * 3600 + 1);
    assert(HearthSecondsUntilHour(0, 7) == 7 * 3600);                  // midnight -> 07:00
    assert(HearthSecondsUntilHour(6 * 3600 + 30 * 60, 7) == 30 * 60);  // 06:30 -> 07:00
    assert(HearthSecondsUntilHour(7 * 3600, 7) == 24 * 3600);          // exactly 07:00 -> next day
    assert(HearthSecondsUntilHour(10 * 3600, 7) == 21 * 3600);         // 10:00 -> next 07:00

    std::puts("NOTE4C_PAGES_OK");
    return 0;
}
