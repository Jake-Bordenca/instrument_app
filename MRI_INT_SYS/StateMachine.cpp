#include "StateMachine.h"
#include "Config.h"
#include "SerialInterface.h"

StateMachine::StateMachine(Group id, const char* _label,
                           Relay& relPump1, Relay& relPump2, Relay& relHornet,
                           Pump&  pump1,    Pump&  pump2,
                           Gauge& gaugeUHV, Gauge& gaugeFore)
  : _id(id), _label(_label),
    _relPump1(relPump1), _relPump2(relPump2), _relHornet(relHornet),
    _pump1(pump1), _pump2(pump2),
    _gaugeUHV(gaugeUHV), _gaugeFore(gaugeFore),
    _state(STATE_GAUGE_ANALOG_ON_WAIT),
    _faultHornet(false), _faultSystem(false),
    _tBoot(0), _tForeSafeSince(0), _tHornetOnSince(0)
{}

void StateMachine::begin(uint32_t now) {
  _tBoot = now;
}

// ---- Private helpers --------------------------------------------------------

bool StateMachine::debounceTrue(bool raw, uint32_t holdMs, uint32_t& sinceMs) {
  const uint32_t now = millis();
  if (!raw) { sinceMs = 0; return false; }
  if (sinceMs == 0) sinceMs = now;
  return (now - sinceMs) >= holdMs;
}

void StateMachine::saveState() const {
  StateManager::saveGroup(_id, snapshot());
}

void StateMachine::setPump1(bool on) {
  if (_relPump1.get() != on) { _relPump1.write(on); saveState(); }
}

void StateMachine::setPump2(bool on) {
  if (_relPump2.get() != on) { _relPump2.write(on); saveState(); }
}

void StateMachine::setHornet(bool on) {
  if (_relHornet.get() != on) {
    _relHornet.write(on);
    if (on) _tHornetOnSince = millis();
    saveState();
  }
}

void StateMachine::allOff() {
  setPump1(false);
  setPump2(false);
  setHornet(false);
}

// ---- Public interface -------------------------------------------------------

void StateMachine::applyRestoredState(const StateManager::GroupState& s) {
  _state       = s.state;
  _faultHornet = s.faultHornet;
  _faultSystem = s.faultSystem;

  if (s.state == STATE_FAULT) {
    allOff();
    return;
  }

  // Drive relay pins directly to match restored state.
  _relPump1.write(s.relayPump1);
  _relPump2.write(s.relayPump2);
  _relHornet.write(s.relayHornet);
}

void StateMachine::checkSafetyTrips(uint32_t now) {
  // Foreline over threshold triggers a system fault for this group only.
  const bool foreTrip = _gaugeFore.torr() > Thresholds::FORELINE_TRIP_TORR;
  if (!_faultSystem && foreTrip) {
    _faultSystem = true;
    _state = STATE_FAULT;
    allOff();
    saveState();
    Serial.print(_label);
    Serial.println(F(": FAULT foreline overpressure (>5 Torr). All outputs OFF."));
  }

  // UHV gauge over threshold (after grace period) triggers this group's
  // hornet fault. Each group has its own grace-period timer, so one
  // group's Hornet relay cycling never affects the other's grace window.
  const bool gracePassed = (_tHornetOnSince != 0) &&
                           ((now - _tHornetOnSince) > Timing::HORNET_GRACE_PERIOD_MS);
  const bool uhvTrip = _gaugeUHV.torr() > Thresholds::HORN_TRIP_RISE_TORR;
  if (!_faultHornet && _state == STATE_RUN && _relHornet.get() &&
      gracePassed && uhvTrip) {
    _faultHornet = true;
    setHornet(false);
    saveState();
    Serial.print(_label);
    Serial.println(F(": FAULT hornet overpressure (>7e-4 Torr). Hornet OFF, pumps continue."));
  }
}

void StateMachine::handleCommand(Cmd cmd) {
  switch (cmd) {
    case CMD_STOP:
      allOff();
      _state = STATE_IDLE;
      saveState();
      Serial.print(_label);
      Serial.println(F(": STOP. Outputs OFF, state IDLE."));
      break;

    case CMD_RESET_HORNET:
      if (_faultHornet) {
        _faultHornet = false;
        saveState();
        Serial.print(_label);
        Serial.println(F(": Hornet fault cleared. Hornet will auto-enable if in RUN."));
      } else {
        Serial.print(_label);
        Serial.println(F(": No Hornet fault to clear."));
      }
      break;

    case CMD_RESET:
      if (_faultHornet || _faultSystem) {
        const bool foreStillHigh = _gaugeFore.torr() > Thresholds::FORELINE_SAFE_START_TORR;
        if (_faultSystem && foreStillHigh) {
          Serial.print(_label);
          Serial.println(F(": RESET denied. Foreline pressure still too high."));
        } else {
          _faultHornet = false;
          _faultSystem = false;
          _state = STATE_IDLE;
          saveState();
          Serial.print(_label);
          Serial.println(F(": All faults cleared. State IDLE."));
        }
      } else {
        Serial.print(_label);
        Serial.println(F(": No faults to clear."));
      }
      break;

    case CMD_START:
      if (_faultSystem) {
        Serial.print(_label);
        Serial.println(F(": START denied. System fault active. Use R to reset."));
      } else if (_state != STATE_IDLE && _state != STATE_GAUGE_ANALOG_ON_WAIT) {
        Serial.print(_label);
        Serial.println(F(": START denied. Not in IDLE state."));
      } else {
        _state = STATE_START_PUMPS;
        _tForeSafeSince = 0;
        saveState();
        Serial.print(_label);
        Serial.println(F(": START requested."));
      }
      break;

    default:
      break;
  }
}

void StateMachine::update(uint32_t now) {
  switch (_state) {
    case STATE_GAUGE_ANALOG_ON_WAIT: {
      allOff();
      if ((now - _tBoot) >= Timing::GAUGE_WARMUP_MS) {
        _state = STATE_IDLE;
        saveState();
        Serial.print(_label);
        Serial.println(F(": Warmup complete. State IDLE."));
      }
      break;
    }

    case STATE_IDLE: {
      allOff();
      break;
    }

    case STATE_START_PUMPS: {
      // This group's foreline gauge must be below threshold before starting.
      const bool foreSafe = _gaugeFore.torr() <= Thresholds::FORELINE_SAFE_START_TORR;
      const bool foreSafeStable = debounceTrue(foreSafe, Timing::FORELINE_STABLE_MS, _tForeSafeSince);

      if (foreSafeStable) {
        setPump1(true);
        setPump2(true);
        _pump1.resetTimers();
        _pump2.resetTimers();
        _state = STATE_WAIT_PUMPS_OK;
        saveState();
        Serial.print(_label);
        Serial.println(F(": Both pumps commanded ON; waiting for OK signals."));
      } else {
        setPump1(false);
        setPump2(false);
      }
      setHornet(false);
      break;
    }

    case STATE_WAIT_PUMPS_OK: {
      setHornet(false);

      const bool pump1Ok = _pump1.okStable(Timing::PUMP_OK_DEBOUNCE_MS, now);
      const bool pump2Ok = _pump2.okStable(Timing::PUMP_OK_DEBOUNCE_MS, now);

      if (pump1Ok && pump2Ok) {
        _pump1.resetTimers();
        _pump2.resetTimers();
        _state = STATE_RUN;
        saveState();
        Serial.print(_label);
        Serial.println(F(": Both pumps OK. Entering RUN state."));
      }
      break;
    }

    case STATE_ENABLE_HORNET_WAIT: {
      // Unused transition state — fall straight through to RUN.
      _state = STATE_RUN;
      saveState();
      break;
    }

    case STATE_RUN: {
      setPump1(true);
      setPump2(true);

      const bool pump1Lost = _pump1.lostTimeout(Timing::PUMP_OK_LOST_TIMEOUT_MS, now);
      const bool pump2Lost = _pump2.lostTimeout(Timing::PUMP_OK_LOST_TIMEOUT_MS, now);

      if (pump1Lost || pump2Lost) {
        _faultSystem = true;
        _state = STATE_FAULT;
        allOff();
        saveState();
        Serial.print(_label);
        Serial.println(pump1Lost
          ? F(": FAULT pump 1 OK lost for 15s. All outputs OFF.")
          : F(": FAULT pump 2 OK lost for 15s. All outputs OFF."));
        break;
      }

      // Hornet stays energized as long as at least one pump in this group
      // is instantaneously OK (single-pump degraded operation) — no change
      // to HORN_TRIP_RISE_TORR in this condition.
      const bool atLeastOnePumpOk = _pump1.rawOk() || _pump2.rawOk();
      setHornet(!_faultHornet && atLeastOnePumpOk);
      break;
    }

    case STATE_FAULT: {
      allOff();
      break;
    }

    default: {
      _faultSystem = true;
      _state = STATE_FAULT;
      allOff();
      Serial.print(_label);
      Serial.println(F(": FAULT unknown state. Outputs OFF."));
      break;
    }
  }
}

void StateMachine::setStateAfterMaintExit(bool pumpsWereRunning) {
  if (pumpsWereRunning) {
    _state = STATE_RUN;
    _pump1.resetTimers();
    _pump2.resetTimers();
    if (_relHornet.get()) _faultHornet = false;
  } else {
    _state = STATE_IDLE;
  }
}

StateManager::GroupState StateMachine::snapshot() const {
  StateManager::GroupState s;
  s.state       = _state;
  s.relayPump1  = _relPump1.get();
  s.relayPump2  = _relPump2.get();
  s.relayHornet = _relHornet.get();
  s.faultHornet = _faultHornet;
  s.faultSystem = _faultSystem;
  return s;
}

void StateMachine::printStatus() const {
  Serial.print(_label);
  Serial.print(F(": "));
  SerialInterface::printStateName(_state);
  Serial.println();
  Serial.print(F("  Pump1=")); Serial.print(_relPump1.get() ? F("ON") : F("OFF"));
  Serial.print(F(" Pump2="));  Serial.print(_relPump2.get() ? F("ON") : F("OFF"));
  Serial.print(F(" Hornet=")); Serial.println(_relHornet.get() ? F("ON") : F("OFF"));
  Serial.print(F("  Faults: Hornet=")); Serial.print(_faultHornet ? F("YES") : F("NO"));
  Serial.print(F(", System="));         Serial.println(_faultSystem ? F("YES") : F("NO"));
  Serial.print(F("  Foreline=")); SerialInterface::printScientific(_gaugeFore.torr()); Serial.println(F(" Torr"));
  Serial.print(F("  UHV="));      SerialInterface::printScientific(_gaugeUHV.torr());  Serial.println(F(" Torr"));
}
