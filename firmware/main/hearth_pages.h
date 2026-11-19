#pragma once
// Daytime page rotation and night schedule for the Note4C, Pacific local time.
// Daytime is 07:00-22:00; pages rotate weather -> today -> groceries on clock
// ticks :00,:10,:20,... Outside that window the device sleeps until 07:00.

inline const char* HearthSlotPage(int slot) {
    static const char* const pages[3] = {"weather", "today", "groceries"};
    return pages[((slot % 3) + 3) % 3];
}

inline int HearthRotationSlot(int minute) { return (minute / 10) % 3; }

inline bool HearthDaytime(int hour) { return hour >= 7 && hour < 22; }

// Seconds from secs_since_midnight until the next occurrence of target_hour.
inline long long HearthSecondsUntilHour(int secs_since_midnight, int target_hour) {
    long long wait = target_hour * 3600LL - secs_since_midnight;
    return wait > 0 ? wait : wait + 86400;
}
