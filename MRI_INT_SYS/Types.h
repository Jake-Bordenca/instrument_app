#ifndef TYPES_H
#define TYPES_H

#include <Arduino.h>

// ============================================================================
// STATE MACHINE
// ============================================================================

// Integer values are stored in EEPROM — do not reorder or renumber.
enum State : uint8_t {
  STATE_GAUGE_ANALOG_ON_WAIT = 0,
  STATE_IDLE,
  STATE_START_PUMPS,
  STATE_WAIT_PUMPS_OK,
  STATE_ENABLE_HORNET_WAIT,  // unused; transitions immediately to RUN
  STATE_RUN,
  STATE_FAULT
};

// ============================================================================
// PUMP GROUPS
// ============================================================================

// Identifies which independent pump group a command/EEPROM slot belongs to.
enum Group : uint8_t {
  GROUP_A = 0,
  GROUP_B = 1,
  GROUP_NONE = 2   // command has no group target (?, M, MAINT relay chars)
};

// ============================================================================
// SERIAL COMMANDS
// ============================================================================

enum Cmd : uint8_t {
  CMD_NONE = 0,
  CMD_START,
  CMD_STOP,
  CMD_STATUS,
  CMD_RESET,
  CMD_MAINT_TOGGLE,
  CMD_RESET_HORNET,     // normal mode: clear Hornet fault only
  // MAINT relay commands
  CMD_TV850i_A_ON,  CMD_TV850i_A_OFF,
  CMD_TV850i_B_ON,  CMD_TV850i_B_OFF,
  CMD_TV350i_A_ON,  CMD_TV350i_A_OFF,
  CMD_TV350i_B_ON,  CMD_TV350i_B_OFF,
  CMD_HORNET_A_ON,  CMD_HORNET_A_OFF,
  CMD_HORNET_B_ON,  CMD_HORNET_B_OFF,
  CMD_ALL_OFF
};

// ============================================================================
// GAUGE CONVERSION FUNCTION TYPE
// ============================================================================

typedef float (*VoltsToPressureFn)(float);

#endif // TYPES_H
