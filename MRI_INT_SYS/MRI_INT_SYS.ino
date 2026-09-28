/* INT_SYS (Mega 2560) — two independent pump-group interlocks + MAINT mode
   - CSV logging at 1 Hz (3-sample rolling average)
   - TWO INDEPENDENT PUMP GROUPS, sharing only WARMUP timing and MAINT:
     * Group A: TV850i-A + TV850i-B pumps, Foreline-A, Hornet/UHV-A
     * Group B: TV350i-A + TV350i-B pumps, Foreline-B, Hornet/UHV-B
     * A fault in one group never affects the other group's pumps/Hornet.
   - Safety interlocks per group: thresholds, hysteresis, debounce, timeouts
   - Per-group Start/Stop/Reset commands over Serial: SA/SB, XA/XB, RA/RB, HA/HB
     * DUAL FAULT SYSTEM (per group):
       - Hornet-x fault (UHV-x > 7e-4 Torr): only turns off Hornet-x, pumps continue
       - System-x fault (Foreline-x > 5 Torr, either pump-x OK lost/timeout): turns off group x
       - Hx = reset Hornet-x fault only, Rx = reset all of group x's faults
     * Single-pump degraded operation: Hornet-x stays energized as long as at
       least one of group x's two pumps is OK (no threshold change)
   - STATE PERSISTENCE: each group's state + relays + faults saved to EEPROM
     independently and restored after reset/reconnection; MAINT mode flag is
     shared/global
     * Allows safe serial reconnection without stopping either group's pumps
     * State saved every second and on every state/relay change
     * Only safe states (IDLE, RUN, ENABLE_HORNET_WAIT, FAULT) are restored, per group
   - MAINTENANCE MODE: allows manual relay control via Serial (shared/global)
     * Enter/exit MAINT: send 'M' twice within 5 seconds
     * While in MAINT: interlocks and sequencing are bypassed for BOTH groups
     * Auto-timeout: if no MAINT commands for 10 minutes, outputs forced OFF and exit MAINT
     * MAINT mode state is also persisted across resets

   Relay wiring:
     TV850i-A relay: D40    TV850i-B relay: D42
     TV350i-A relay: D44    TV350i-B relay: D46
     Hornet-A relay: D36    Hornet-B relay: D38

   Pump OK inputs (active LOW):
     TV850i-A: D26    TV850i-B: D28
     TV350i-A: D30    TV350i-B: D32

   Gauge inputs:
     UHV-A: A0    Foreline-A: A8                     (Group A)
     UHV-B: A4    Foreline-B: A14                    (Group B)

   CALIBRATION APPLIED:
   - ADC correction factor: 0.9782 (Arduino read 3.296V vs actual 3.224V)
*/

#include <Arduino.h>
#include "Config.h"
#include "Types.h"
#include "Relay.h"
#include "Pump.h"
#include "Gauge.h"
#include "StateManager.h"
#include "SerialInterface.h"
#include "MaintenanceMode.h"
#include "StateMachine.h"

// ============================================================================
// HARDWARE COMPONENTS
// ============================================================================

static Relay relTV850iA(Pins::RELAY_TV850i_A);
static Relay relTV850iB(Pins::RELAY_TV850i_B);
static Relay relTV350iA(Pins::RELAY_TV350i_A);
static Relay relTV350iB(Pins::RELAY_TV350i_B);
static Relay relHornetA(Pins::RELAY_HORNET_A);
static Relay relHornetB(Pins::RELAY_HORNET_B);

static Pump pumpTV850iA(Pins::TV850i_A_OK);
static Pump pumpTV850iB(Pins::TV850i_B_OK);
static Pump pumpTV350iA(Pins::TV350i_A_OK);
static Pump pumpTV350iB(Pins::TV350i_B_OK);

static Gauge gaugeUHV_A (Pins::UHV_GAUGE_A,      0.10f, hornetVoltsToTorr);
static Gauge gaugeUHV_B (Pins::UHV_GAUGE_B,      0.10f, hornetVoltsToTorr);
static Gauge gaugeFore_A(Pins::FORELINE_GAUGE_A, 0.10f, stingerVoltsToTorr);
static Gauge gaugeFore_B(Pins::FORELINE_GAUGE_B, 0.10f, stingerVoltsToTorr);

// ============================================================================
// CONTROLLERS — two fully independent pump groups
// ============================================================================

static StateMachine groupA(GROUP_A, "Group A",
  relTV850iA, relTV850iB, relHornetA,
  pumpTV850iA, pumpTV850iB,
  gaugeUHV_A, gaugeFore_A);

static StateMachine groupB(GROUP_B, "Group B",
  relTV350iA, relTV350iB, relHornetB,
  pumpTV350iA, pumpTV350iB,
  gaugeUHV_B, gaugeFore_B);

static MaintenanceMode maint;

// ============================================================================
// LOOP-LOCAL LOGGING STATE
// ============================================================================

static uint32_t tLastLog          = 0;
static float    logSum_uhvV_A     = 0.0f;
static float    logSum_uhvV_B     = 0.0f;
static float    logSum_foreV_A    = 0.0f;
static float    logSum_foreV_B    = 0.0f;
static float    logSum_uhvTorr_A  = 0.0f;
static float    logSum_uhvTorr_B  = 0.0f;
static float    logSum_foreTorr_A = 0.0f;
static float    logSum_foreTorr_B = 0.0f;
static uint8_t  logSampleCount    = 0;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  relTV850iA.begin();
  relTV850iB.begin();
  relTV350iA.begin();
  relTV350iB.begin();
  relHornetA.begin();
  relHornetB.begin();

  pumpTV850iA.begin();
  pumpTV850iB.begin();
  pumpTV350iA.begin();
  pumpTV350iB.begin();

  gaugeUHV_A.reset();
  gaugeUHV_B.reset();
  gaugeFore_A.reset();
  gaugeFore_B.reset();

  Serial.begin(115200);
  delay(100);

  // Both groups start their WARMUP countdown from the same boot timestamp.
  // This is duplication, not a shared timer — each StateMachine instance
  // independently tracks its own _tBoot, so they only *appear* synchronized
  // because they were both given the same `now`. Do not "simplify" this
  // into one shared timer; that would couple the two groups.
  const uint32_t bootNow = millis();
  groupA.begin(bootNow);
  groupB.begin(bootNow);

  StateManager::GroupState savedA, savedB;
  const bool restoredA = StateManager::restoreGroup(GROUP_A, savedA);
  const bool restoredB = StateManager::restoreGroup(GROUP_B, savedB);
  if (restoredA) groupA.applyRestoredState(savedA);
  if (restoredB) groupB.applyRestoredState(savedB);
  const bool restoredMaint = StateManager::readMaintMode();

  SerialInterface::printCsvHeader();
  SerialInterface::printStartupBanner(
    restoredA, groupA.getState(),
    relTV850iA.get(), relTV850iB.get(), relHornetA.get(),
    restoredB, groupB.getState(),
    relTV350iA.get(), relTV350iB.get(), relHornetB.get(),
    restoredMaint,
    Calibration::TO_GAUGE_8V,
    Calibration::ADC_CORRECTION);

  if (restoredMaint) {
    maint.handleToggle(millis(), false); // arm
    maint.handleToggle(millis(), false); // enter (prints help again — acceptable)
  }
}

// ============================================================================
// LOOP
// ============================================================================

void loop() {
  const uint32_t now = millis();

  // --------- Read sensors ---------
  gaugeUHV_A.update();
  gaugeUHV_B.update();
  gaugeFore_A.update();
  gaugeFore_B.update();

  // --------- Periodic logging (3-sample rolling average) ---------
  if ((now - tLastLog) >= Timing::LOG_INTERVAL_MS) {
    tLastLog = now;

    logSum_uhvV_A     += gaugeUHV_A.volts();
    logSum_uhvV_B     += gaugeUHV_B.volts();
    logSum_foreV_A    += gaugeFore_A.volts();
    logSum_foreV_B    += gaugeFore_B.volts();
    logSum_uhvTorr_A  += gaugeUHV_A.torr();
    logSum_uhvTorr_B  += gaugeUHV_B.torr();
    logSum_foreTorr_A += gaugeFore_A.torr();
    logSum_foreTorr_B += gaugeFore_B.torr();

    if (++logSampleCount >= 3) {
      SerialInterface::printCsvLineAveraged(
        now,
        logSum_uhvV_A     / 3.0f, logSum_uhvV_B     / 3.0f,
        logSum_foreV_A    / 3.0f, logSum_foreV_B    / 3.0f,
        logSum_uhvTorr_A  / 3.0f, logSum_uhvTorr_B  / 3.0f,
        logSum_foreTorr_A / 3.0f, logSum_foreTorr_B / 3.0f,
        groupA.getState(), groupB.getState(),
        pumpTV850iA.rawOk(), pumpTV850iB.rawOk(),
        pumpTV350iA.rawOk(), pumpTV350iB.rawOk(),
        relTV850iA.get(), relTV850iB.get(),
        relTV350iA.get(), relTV350iB.get(),
        relHornetA.get(), relHornetB.get(),
        groupA.faultHornet(), groupA.faultSystem(),
        groupB.faultHornet(), groupB.faultSystem(),
        maint.isActive()
      );
      logSum_uhvV_A     = 0.0f;
      logSum_uhvV_B     = 0.0f;
      logSum_foreV_A    = 0.0f;
      logSum_foreV_B    = 0.0f;
      logSum_uhvTorr_A  = 0.0f;
      logSum_uhvTorr_B  = 0.0f;
      logSum_foreTorr_A = 0.0f;
      logSum_foreTorr_B = 0.0f;
      logSampleCount    = 0;
    }

    // Periodic EEPROM save (on every log tick, not just relay changes).
    StateManager::saveGroup(GROUP_A, groupA.snapshot());
    StateManager::saveGroup(GROUP_B, groupB.snapshot());
    StateManager::saveMaintMode(maint.isActive());
  }

  // --------- Read command ---------
  ParsedCmd pc = SerialInterface::readSerialCmd(now);

  // --------- MAINT toggle handling ---------
  if (pc.cmd == CMD_MAINT_TOGGLE) {
    const bool pumpsAOn = groupA.pumpsRunning();
    const bool pumpsBOn = groupB.pumpsRunning();
    MaintToggleResult result = maint.handleToggle(now, pumpsAOn || pumpsBOn);

    if (result == MAINT_ENTERED || result == MAINT_EXITED) {
      if (result == MAINT_EXITED) {
        groupA.setStateAfterMaintExit(pumpsAOn);
        groupB.setStateAfterMaintExit(pumpsBOn);
      }
      StateManager::saveGroup(GROUP_A, groupA.snapshot());
      StateManager::saveGroup(GROUP_B, groupB.snapshot());
      StateManager::saveMaintMode(maint.isActive());
    }
    return;
  }

  // Clear stale MAINT arm attempt.
  maint.clearArmIfExpired(now);

  // --------- MAINT active behavior ---------
  if (maint.isActive()) {
    if (maint.timedOut(now)) {
      Serial.println(F("MAINT timeout. Outputs forced OFF; exiting MAINT."));
      groupA.allOff();
      groupB.allOff();
      maint.forceExit();
      groupA.setStateAfterMaintExit(false);
      groupB.setStateAfterMaintExit(false);
      StateManager::saveGroup(GROUP_A, groupA.snapshot());
      StateManager::saveGroup(GROUP_B, groupB.snapshot());
      StateManager::saveMaintMode(false);
      return;
    }

    // These commands already address individual relays directly and bypass
    // both state machines entirely — no group routing needed here. Note
    // CMD_STOP now requires "XA"/"XB" (either resolves the same way here)
    // rather than a bare 'X', since 'X' alone is held pending for a group
    // tag by the parser regardless of MAINT mode.
    switch (pc.cmd) {
      case CMD_TV850i_A_ON:  relTV850iA.write(true);  maint.touch(now); break;
      case CMD_TV850i_A_OFF: relTV850iA.write(false); maint.touch(now); break;
      case CMD_TV850i_B_ON:  relTV850iB.write(true);  maint.touch(now); break;
      case CMD_TV850i_B_OFF: relTV850iB.write(false); maint.touch(now); break;
      case CMD_TV350i_A_ON:  relTV350iA.write(true);  maint.touch(now); break;
      case CMD_TV350i_A_OFF: relTV350iA.write(false); maint.touch(now); break;
      case CMD_TV350i_B_ON:  relTV350iB.write(true);  maint.touch(now); break;
      case CMD_TV350i_B_OFF: relTV350iB.write(false); maint.touch(now); break;
      case CMD_HORNET_A_ON:  relHornetA.write(true);  maint.touch(now); break;
      case CMD_HORNET_A_OFF: relHornetA.write(false); maint.touch(now); break;
      case CMD_HORNET_B_ON:  relHornetB.write(true);  maint.touch(now); break;
      case CMD_HORNET_B_OFF: relHornetB.write(false); maint.touch(now); break;
      case CMD_ALL_OFF:
        relTV850iA.write(false); relTV850iB.write(false);
        relTV350iA.write(false); relTV350iB.write(false);
        relHornetA.write(false); relHornetB.write(false);
        maint.touch(now);
        Serial.println(F("MAINT: ALL OFF"));
        break;
      case CMD_STATUS:
        SerialInterface::printHelpMaint();
        maint.touch(now);
        break;
      case CMD_STOP:
        relTV850iA.write(false); relTV850iB.write(false);
        relTV350iA.write(false); relTV350iB.write(false);
        relHornetA.write(false); relHornetB.write(false);
        maint.touch(now);
        Serial.println(F("MAINT: ALL OFF"));
        break;
      default: break;
    }

    return; // do not run interlocks/state machines in MAINT
  }

  // --------- Normal mode: status query reports both groups ---------
  if (pc.cmd == CMD_STATUS) {
    SerialInterface::printHelpNormal();
    groupA.printStatus();
    groupB.printStatus();
  }

  // --------- Normal mode: safety trips then state machines, per group ---------
  groupA.checkSafetyTrips(now);
  groupA.handleCommand(pc.group == GROUP_A ? pc.cmd : CMD_NONE);
  groupA.update(now);

  groupB.checkSafetyTrips(now);
  groupB.handleCommand(pc.group == GROUP_B ? pc.cmd : CMD_NONE);
  groupB.update(now);
}
