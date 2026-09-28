#ifndef STATE_MANAGER_H
#define STATE_MANAGER_H

#include <Arduino.h>
#include "Types.h"

// Handles saving and restoring per-group state to/from EEPROM.
// Each group's state is fully independent of the other's; MAINT mode is the
// one piece of state that's still shared/global.
class StateManager {
public:
  struct GroupState {
    State state;
    bool  relayPump1;
    bool  relayPump2;
    bool  relayHornet;
    bool  faultHornet;
    bool  faultSystem;
  };

  // Writes one group's fields via EEPROM.update (only writes on actual byte change).
  static void saveGroup(Group g, const GroupState& s);

  // Reads one group's EEPROM slot; populates s and returns true only for
  // safe/restorable states (same rule as before: IDLE/RUN/ENABLE_HORNET_WAIT
  // restore with fault flags cleared, FAULT restores with flags intact).
  static bool restoreGroup(Group g, GroupState& s);

  // Shared MAINT-mode flag, independent of either group's state.
  static void saveMaintMode(bool active);
  static bool readMaintMode();

  // Invalidates the magic byte so next boot is a fresh start.
  static void clear();
};

#endif // STATE_MANAGER_H
