#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ============================================================================
// PIN ASSIGNMENTS
// ============================================================================

namespace Pins {
  // Analog inputs — 2 UHV gauges, 2 foreline gauges
  constexpr uint8_t UHV_GAUGE_A      = A0;
  constexpr uint8_t UHV_GAUGE_B      = A4;
  constexpr uint8_t FORELINE_GAUGE_A = A8;
  constexpr uint8_t FORELINE_GAUGE_B = A14;

  // Pump OK/Normal digital inputs (active LOW, INPUT_PULLUP)
  constexpr uint8_t TV850i_A_OK = 26;
  constexpr uint8_t TV850i_B_OK = 28;
  constexpr uint8_t TV350i_A_OK = 30;
  constexpr uint8_t TV350i_B_OK = 32;

  // Relay outputs — 4 pump relays + 2 Hornet gauge relays
  constexpr uint8_t RELAY_TV850i_A = 40;
  constexpr uint8_t RELAY_TV850i_B = 42;
  constexpr uint8_t RELAY_TV350i_A = 44;
  constexpr uint8_t RELAY_TV350i_B = 46;
  constexpr uint8_t RELAY_HORNET_A = 36;
  constexpr uint8_t RELAY_HORNET_B = 38;
}

// ============================================================================
// TIMING CONSTANTS (milliseconds)
// ============================================================================

namespace Timing {
  constexpr uint32_t GAUGE_WARMUP_MS         = 5000UL;
  constexpr uint32_t LOG_INTERVAL_MS         = 1000UL;
  constexpr uint32_t PUMP_OK_DEBOUNCE_MS     = 2000UL;
  constexpr uint32_t FORELINE_STABLE_MS      = 2000UL;
  constexpr uint32_t PUMP_OK_LOST_TIMEOUT_MS = 15UL * 1000UL;
  constexpr uint32_t HORNET_GRACE_PERIOD_MS  = 5000UL;
  constexpr uint32_t MAINT_ARM_WINDOW_MS     = 5000UL;
  constexpr uint32_t MAINT_IDLE_TIMEOUT_MS   = 10UL * 60UL * 1000UL;

  // Max gap between a group-command letter (S/X/R/H) and its 'A'/'B' tag
  // before the pending command is dropped. Generous margin: the Python app
  // writes both bytes in a single serial.write() call (microseconds apart
  // in the UART FIFO); a human typing into a terminal easily lands within it.
  constexpr uint32_t CMD_GROUP_TAG_TIMEOUT_MS = 500UL;
}

// ============================================================================
// PRESSURE THRESHOLDS (Torr)
// ============================================================================

namespace Thresholds {
  constexpr float FORELINE_SAFE_START_TORR = 5.0f;
  constexpr float FORELINE_TRIP_TORR       = 5.0f;
  constexpr float HORN_TRIP_RISE_TORR      = 7.0e-4f;
  constexpr float HORN_TRIP_FALL_TORR      = 5.0e-4f;
}

// ============================================================================
// GAUGE CALIBRATION
// ============================================================================

namespace Calibration {
  constexpr float TO_GAUGE_8V    = 8.0f / 5.0f;  // voltage-divider scale into gauge domain
  constexpr float ADC_CORRECTION = 2.442f / 2.628f; // 0.9782: corrects Arduino ADC offset
}

// ============================================================================
// EEPROM ADDRESSES
// ============================================================================

// Two independent groups, each with its own state + relays + fault flags.
// MAGIC and MAINT_MODE are the only shared/global slots.
namespace EEPROM_Addr {
  constexpr int MAGIC          = 0;   // shared

  constexpr int A_STATE        = 1;
  constexpr int A_RELAY_PUMP1  = 2;   // TV850i-A
  constexpr int A_RELAY_PUMP2  = 3;   // TV850i-B
  constexpr int A_RELAY_HORNET = 4;   // Hornet-A
  constexpr int A_FAULT_HORNET = 5;
  constexpr int A_FAULT_SYSTEM = 6;

  constexpr int B_STATE        = 7;
  constexpr int B_RELAY_PUMP1  = 8;   // TV350i-A
  constexpr int B_RELAY_PUMP2  = 9;   // TV350i-B
  constexpr int B_RELAY_HORNET = 10;  // Hornet-B
  constexpr int B_FAULT_HORNET = 11;
  constexpr int B_FAULT_SYSTEM = 12;

  constexpr int MAINT_MODE     = 13;  // shared

  // Bumped from 0xA5: the pre-split layout wrote a single shared state/fault
  // set at different addresses. Bumping the magic value forces a fresh,
  // safe start on the first boot after this firmware update instead of
  // reading stale/uninitialized bytes as if they were valid per-group state.
  constexpr uint8_t MAGIC_VALUE = 0xA6;
}

#endif // CONFIG_H
