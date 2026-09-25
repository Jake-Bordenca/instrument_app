#include "SerialInterface.h"
#include "Config.h"

char     SerialInterface::_pendingChar  = 0;
uint32_t SerialInterface::_pendingSince = 0;

// Returns the state name as a flash string.
static const __FlashStringHelper* stateToStr(State s) {
  switch (s) {
    case STATE_GAUGE_ANALOG_ON_WAIT: return F("WARMUP");
    case STATE_IDLE:                 return F("IDLE");
    case STATE_START_PUMPS:          return F("START_PUMPS");
    case STATE_WAIT_PUMPS_OK:        return F("WAIT_PUMPS_OK");
    case STATE_ENABLE_HORNET_WAIT:   return F("ENABLE_HORNET_WAIT");
    case STATE_RUN:                  return F("RUN");
    case STATE_FAULT:                return F("FAULT");
    default:                         return F("UNKNOWN");
  }
}

// Maps a pending group-command letter (S/X/R/H) to its generic Cmd.
static Cmd baseCmdFor(char pending) {
  switch (pending) {
    case 'S': case 's': return CMD_START;
    case 'X': case 'x': return CMD_STOP;
    case 'R': case 'r': return CMD_RESET;
    case 'H': case 'h': return CMD_RESET_HORNET;
    default:            return CMD_NONE;
  }
}

ParsedCmd SerialInterface::readSerialCmd(uint32_t now) {
  // Drop a stale pending group-tag wait.
  if (_pendingChar != 0 && (now - _pendingSince) > Timing::CMD_GROUP_TAG_TIMEOUT_MS) {
    _pendingChar = 0;
  }

  if (!Serial.available()) return ParsedCmd{};
  const int c = Serial.read();
  if (c < 0) return ParsedCmd{};
  const char ch = (char)c;

  if (_pendingChar != 0) {
    const char pending = _pendingChar;
    _pendingChar = 0;
    if (ch == 'A' || ch == 'a') return ParsedCmd{ baseCmdFor(pending), GROUP_A };
    if (ch == 'B' || ch == 'b') return ParsedCmd{ baseCmdFor(pending), GROUP_B };
    // Invalid/ambiguous tag — fail closed: drop the pending command rather
    // than reinterpreting this byte as a fresh one.
    return ParsedCmd{};
  }

  switch (ch) {
    // Group-tagged commands: wait for the 'A'/'B' tag before returning.
    case 'S': case 's': case 'X': case 'x':
    case 'R': case 'r': case 'H': case 'h':
      _pendingChar  = ch;
      _pendingSince = now;
      return ParsedCmd{};

    case '?':           return ParsedCmd{ CMD_STATUS, GROUP_NONE };
    case 'M': case 'm': return ParsedCmd{ CMD_MAINT_TOGGLE, GROUP_NONE };

    // MAINT relay controls (only acted on while MAINT is active; see .ino)
    case '1': return ParsedCmd{ CMD_TV850i_A_ON,  GROUP_NONE };
    case '2': return ParsedCmd{ CMD_TV850i_A_OFF, GROUP_NONE };
    case '3': return ParsedCmd{ CMD_TV850i_B_ON,  GROUP_NONE };
    case '4': return ParsedCmd{ CMD_TV850i_B_OFF, GROUP_NONE };
    case '5': return ParsedCmd{ CMD_TV350i_A_ON,  GROUP_NONE };
    case '6': return ParsedCmd{ CMD_TV350i_A_OFF, GROUP_NONE };
    case '7': return ParsedCmd{ CMD_TV350i_B_ON,  GROUP_NONE };
    case '8': return ParsedCmd{ CMD_TV350i_B_OFF, GROUP_NONE };
    case 'A': case 'a': return ParsedCmd{ CMD_HORNET_A_ON,  GROUP_NONE };
    case 'B': case 'b': return ParsedCmd{ CMD_HORNET_A_OFF, GROUP_NONE };
    case 'C': case 'c': return ParsedCmd{ CMD_HORNET_B_ON,  GROUP_NONE };
    case 'D': case 'd': return ParsedCmd{ CMD_HORNET_B_OFF, GROUP_NONE };

    case '0': return ParsedCmd{ CMD_ALL_OFF, GROUP_NONE };

    default: return ParsedCmd{};
  }
}

void SerialInterface::printScientific(float value) {
  if (value == 0.0f) { Serial.print(F("0.00e+00")); return; }

  if (value < 0.0f) { Serial.print('-'); value = -value; }

  int exponent = 0;
  if (value >= 10.0f) {
    while (value >= 10.0f) { value /= 10.0f; exponent++; }
  } else if (value < 1.0f) {
    while (value < 1.0f)   { value *= 10.0f; exponent--; }
  }

  Serial.print(value, 2);
  Serial.print('e');
  if (exponent >= 0) { Serial.print('+'); } else { Serial.print('-'); exponent = -exponent; }
  if (exponent < 10) Serial.print('0');
  Serial.print(exponent);
}

void SerialInterface::printStateName(State s) {
  Serial.print(stateToStr(s));
}

void SerialInterface::printCsvHeader() {
  // NOTE: on tv850i*/tv350i*/rel_tv850i*/rel_tv350i* fields, the _A/_B
  // suffix identifies the PUMP sub-unit within a group. On stateA/stateB
  // and fault_*A/fault_*B fields, _A/_B identifies the INTERLOCK GROUP.
  // These two axes coincide on this hardware (both TV850i pumps are in
  // Group A, both TV350i pumps in Group B) but are conceptually different.
  Serial.println(F("ms,uhvV_A,uhvV_B,foreV_A,foreV_B,uhvTorr_A,uhvTorr_B,foreTorr_A,foreTorr_B,"
                   "stateA,stateB,tv850iA_ok,tv850iB_ok,tv350iA_ok,tv350iB_ok,"
                   "rel_tv850iA,rel_tv850iB,rel_tv350iA,rel_tv350iB,rel_hornetA,rel_hornetB,"
                   "fault_hornetA,fault_systemA,fault_hornetB,fault_systemB,maint"));
}

void SerialInterface::printCsvLineAveraged(uint32_t ms,
                                           float uhvV_A,     float uhvV_B,
                                           float foreV_A,    float foreV_B,
                                           float uhvTorr_A,  float uhvTorr_B,
                                           float foreTorr_A, float foreTorr_B,
                                           State stateA,     State stateB,
                                           bool tv850iA_ok, bool tv850iB_ok,
                                           bool tv350iA_ok, bool tv350iB_ok,
                                           bool relTV850iA, bool relTV850iB,
                                           bool relTV350iA, bool relTV350iB,
                                           bool relHornetA, bool relHornetB,
                                           bool faultHornetA, bool faultSystemA,
                                           bool faultHornetB, bool faultSystemB,
                                           bool maintMode) {
  Serial.print(F("ms: ")); Serial.print(ms); Serial.print(F(", "));
  Serial.print(F("uhvV_A: ")); Serial.print(uhvV_A, 4); Serial.print(F(", "));
  Serial.print(F("uhvV_B: ")); Serial.print(uhvV_B, 4); Serial.print(F(", "));
  Serial.print(F("foreV_A: ")); Serial.print(foreV_A, 4); Serial.print(F(", "));
  Serial.print(F("foreV_B: ")); Serial.print(foreV_B, 4); Serial.print(F(", "));
  Serial.print(F("uhvTorr_A: ")); printScientific(uhvTorr_A); Serial.print(F(", "));
  Serial.print(F("uhvTorr_B: ")); printScientific(uhvTorr_B); Serial.print(F(", "));
  Serial.print(F("foreTorr_A: ")); printScientific(foreTorr_A); Serial.print(F(", "));
  Serial.print(F("foreTorr_B: ")); printScientific(foreTorr_B); Serial.print(F(", "));
  Serial.print(F("stateA: ")); printStateName(stateA); Serial.print(F(", "));
  Serial.print(F("stateB: ")); printStateName(stateB); Serial.print(F(", "));
  Serial.print(F("tv850iA_ok: ")); Serial.print(tv850iA_ok ? F("OK") : F("NO")); Serial.print(F(", "));
  Serial.print(F("tv850iB_ok: ")); Serial.print(tv850iB_ok ? F("OK") : F("NO")); Serial.print(F(", "));
  Serial.print(F("tv350iA_ok: ")); Serial.print(tv350iA_ok ? F("OK") : F("NO")); Serial.print(F(", "));
  Serial.print(F("tv350iB_ok: ")); Serial.print(tv350iB_ok ? F("OK") : F("NO")); Serial.print(F(", "));
  Serial.print(F("rel_tv850iA: ")); Serial.print(relTV850iA ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("rel_tv850iB: ")); Serial.print(relTV850iB ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("rel_tv350iA: ")); Serial.print(relTV350iA ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("rel_tv350iB: ")); Serial.print(relTV350iB ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("rel_hornetA: ")); Serial.print(relHornetA ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("rel_hornetB: ")); Serial.print(relHornetB ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("fault_hornetA: ")); Serial.print(faultHornetA ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("fault_systemA: ")); Serial.print(faultSystemA ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("fault_hornetB: ")); Serial.print(faultHornetB ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("fault_systemB: ")); Serial.print(faultSystemB ? 1 : 0); Serial.print(F(", "));
  Serial.print(F("maint: ")); Serial.println(maintMode ? 1 : 0);
}

void SerialInterface::printHelpNormal() {
  Serial.println(F("Commands: SA/SB=start, XA/XB=stop, HA/HB=clear Hornet fault, "
                   "RA/RB=reset all, M M=MAINT, ?=status"));
}

void SerialInterface::printHelpMaint() {
  Serial.println(F("MAINT relay controls:"));
  Serial.println(F("  1/2=TV850i-A ON/OFF   3/4=TV850i-B ON/OFF"));
  Serial.println(F("  5/6=TV350i-A ON/OFF   7/8=TV350i-B ON/OFF"));
  Serial.println(F("  A/B=Hornet-A ON/OFF   C/D=Hornet-B ON/OFF"));
  Serial.println(F("  0=ALL OFF   M=exit MAINT   ?=this help"));
}

void SerialInterface::printStartupBanner(bool restoredA, State stateA,
                                         bool relA_Pump1, bool relA_Pump2, bool relA_Hornet,
                                         bool restoredB, State stateB,
                                         bool relB_Pump1, bool relB_Pump2, bool relB_Hornet,
                                         bool maintMode,
                                         float toGauge8V, float adcCorrection) {
  if (restoredA || restoredB) {
    Serial.println(F("=== STATE RESTORED FROM PREVIOUS SESSION ==="));

    Serial.print(F("Group A: "));
    if (restoredA) {
      printStateName(stateA);
      Serial.print(F("  Pump1=")); Serial.print(relA_Pump1 ? F("ON") : F("OFF"));
      Serial.print(F(" Pump2="));  Serial.print(relA_Pump2 ? F("ON") : F("OFF"));
      Serial.print(F(" Hornet=")); Serial.println(relA_Hornet ? F("ON") : F("OFF"));
    } else {
      Serial.println(F("fresh start"));
    }

    Serial.print(F("Group B: "));
    if (restoredB) {
      printStateName(stateB);
      Serial.print(F("  Pump1=")); Serial.print(relB_Pump1 ? F("ON") : F("OFF"));
      Serial.print(F(" Pump2="));  Serial.print(relB_Pump2 ? F("ON") : F("OFF"));
      Serial.print(F(" Hornet=")); Serial.println(relB_Hornet ? F("ON") : F("OFF"));
    } else {
      Serial.println(F("fresh start"));
    }

    if (maintMode) {
      Serial.println(F("Maintenance mode was active."));
      printHelpMaint();
    } else {
      printHelpNormal();
    }
    Serial.println(F("============================================"));
  } else {
    Serial.println(F("=== FRESH START (No previous state) ==="));
    printHelpNormal();
  }

  Serial.println(F("=== CALIBRATION INFO ==="));
  Serial.print(F("Voltage divider ratio: 8V -> 5V, scale factor = "));
  Serial.println(toGauge8V, 4);
  Serial.print(F("ADC correction factor: "));
  Serial.println(adcCorrection, 4);
  Serial.println(F("========================"));
}
