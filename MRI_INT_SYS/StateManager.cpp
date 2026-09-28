#include "StateManager.h"
#include "Config.h"
#include <EEPROM.h>

// Per-group address bundle, resolved once via switch() rather than array
// indexing on the Group enum's raw value — keeps EEPROM layout immune to a
// future reordering of GROUP_A/GROUP_B.
namespace {
  struct GroupAddrs {
    int state;
    int relayPump1;
    int relayPump2;
    int relayHornet;
    int faultHornet;
    int faultSystem;
  };

  GroupAddrs addrsFor(Group g) {
    switch (g) {
      case GROUP_A:
        return { EEPROM_Addr::A_STATE, EEPROM_Addr::A_RELAY_PUMP1,
                 EEPROM_Addr::A_RELAY_PUMP2, EEPROM_Addr::A_RELAY_HORNET,
                 EEPROM_Addr::A_FAULT_HORNET, EEPROM_Addr::A_FAULT_SYSTEM };
      case GROUP_B:
      default:
        return { EEPROM_Addr::B_STATE, EEPROM_Addr::B_RELAY_PUMP1,
                 EEPROM_Addr::B_RELAY_PUMP2, EEPROM_Addr::B_RELAY_HORNET,
                 EEPROM_Addr::B_FAULT_HORNET, EEPROM_Addr::B_FAULT_SYSTEM };
    }
  }
}

void StateManager::saveGroup(Group g, const GroupState& s) {
  const GroupAddrs a = addrsFor(g);
  EEPROM.update(EEPROM_Addr::MAGIC, EEPROM_Addr::MAGIC_VALUE);
  EEPROM.update(a.state,       (uint8_t)s.state);
  EEPROM.update(a.relayPump1,  s.relayPump1  ? 1 : 0);
  EEPROM.update(a.relayPump2,  s.relayPump2  ? 1 : 0);
  EEPROM.update(a.relayHornet, s.relayHornet ? 1 : 0);
  EEPROM.update(a.faultHornet, s.faultHornet ? 1 : 0);
  EEPROM.update(a.faultSystem, s.faultSystem ? 1 : 0);
}

bool StateManager::restoreGroup(Group g, GroupState& s) {
  if (EEPROM.read(EEPROM_Addr::MAGIC) != EEPROM_Addr::MAGIC_VALUE) return false;

  const GroupAddrs a = addrsFor(g);
  const uint8_t savedState = EEPROM.read(a.state);

  s.relayPump1  = EEPROM.read(a.relayPump1)  != 0;
  s.relayPump2  = EEPROM.read(a.relayPump2)  != 0;
  s.relayHornet = EEPROM.read(a.relayHornet) != 0;
  s.faultHornet = EEPROM.read(a.faultHornet) != 0;
  s.faultSystem = EEPROM.read(a.faultSystem) != 0;

  if (savedState == STATE_RUN ||
      savedState == STATE_ENABLE_HORNET_WAIT ||
      savedState == STATE_IDLE) {
    s.state       = (State)savedState;
    s.faultHornet = false;
    s.faultSystem = false;
    return true;
  }

  if (savedState == STATE_FAULT) {
    s.state = STATE_FAULT;
    return true;
  }

  return false;
}

void StateManager::saveMaintMode(bool active) {
  EEPROM.update(EEPROM_Addr::MAGIC, EEPROM_Addr::MAGIC_VALUE);
  EEPROM.update(EEPROM_Addr::MAINT_MODE, active ? 1 : 0);
}

bool StateManager::readMaintMode() {
  if (EEPROM.read(EEPROM_Addr::MAGIC) != EEPROM_Addr::MAGIC_VALUE) return false;
  return EEPROM.read(EEPROM_Addr::MAINT_MODE) != 0;
}

void StateManager::clear() {
  EEPROM.update(EEPROM_Addr::MAGIC, 0x00);
}
