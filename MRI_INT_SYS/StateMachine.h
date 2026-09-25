#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include <Arduino.h>
#include "Types.h"
#include "Relay.h"
#include "Pump.h"
#include "Gauge.h"
#include "StateManager.h"

// Owns the state machine and safety interlocks for ONE independent pump
// group (2 pumps + 1 Hornet gauge relay, gated by 1 foreline gauge and 1
// UHV gauge). Instantiate one per group; instances never reference each
// other's hardware or state. Holds references to hardware objects; does
// not own them.
class StateMachine {
public:
  StateMachine(Group id, const char* label,
               Relay& relPump1, Relay& relPump2, Relay& relHornet,
               Pump&  pump1,    Pump&  pump2,
               Gauge& gaugeUHV, Gauge& gaugeFore);

  // Call once from setup() to record boot time. Pass the same `now` to both
  // group instances so their independent WARMUP timers elapse together —
  // this is duplication, not a shared timer; each instance owns its own
  // _tBoot and counts down independently.
  void begin(uint32_t now);

  // Run safety trips (foreline + hornet overpressure) for this group. Call
  // before update().
  void checkSafetyTrips(uint32_t now);

  // Process one normal-mode command already routed to this group.
  void handleCommand(Cmd cmd);

  // Advance this group's state machine one step.
  void update(uint32_t now);

  // Turn this group's relay outputs off.
  void allOff();

  // Apply state and relay outputs restored from EEPROM.
  void applyRestoredState(const StateManager::GroupState& s);

  // Print this group's status block (used for the '?' command).
  void printStatus() const;

  // ---- Accessors ----
  State getState()     const { return _state; }
  bool  faultHornet()  const { return _faultHornet; }
  bool  faultSystem()  const { return _faultSystem; }
  bool  pumpsRunning() const { return _relPump1.get() && _relPump2.get(); }

  // Used by the main loop after MAINT exit to re-enter RUN or IDLE.
  void setStateAfterMaintExit(bool pumpsWereRunning);

  // Build a GroupState snapshot for EEPROM persistence.
  StateManager::GroupState snapshot() const;

private:
  Group _id;
  const char* _label;

  Relay& _relPump1;
  Relay& _relPump2;
  Relay& _relHornet;

  Pump&  _pump1;
  Pump&  _pump2;

  Gauge& _gaugeUHV;
  Gauge& _gaugeFore;

  State    _state;
  bool     _faultHornet;
  bool     _faultSystem;
  uint32_t _tBoot;
  uint32_t _tForeSafeSince;
  uint32_t _tHornetOnSince;

  // Relay wrappers: perform change detection and EEPROM save on actual change.
  void setPump1(bool on);
  void setPump2(bool on);
  void setHornet(bool on);

  void saveState() const;

  // Generic rising-edge debounce helper.
  static bool debounceTrue(bool raw, uint32_t holdMs, uint32_t& sinceMs);
};

#endif // STATE_MACHINE_H
