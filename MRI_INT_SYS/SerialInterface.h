#ifndef SERIAL_INTERFACE_H
#define SERIAL_INTERFACE_H

#include <Arduino.h>
#include "Types.h"

// A command read from serial, plus which group it targets (if any).
// `group` is only meaningful for CMD_START/CMD_STOP/CMD_RESET/CMD_RESET_HORNET
// — every other command is group-agnostic (GROUP_NONE).
// Uses explicit constructors (not default member initializers) so brace-init
// works the same regardless of the toolchain's exact C++ standard version.
struct ParsedCmd {
  Cmd   cmd;
  Group group;
  ParsedCmd() : cmd(CMD_NONE), group(GROUP_NONE) {}
  ParsedCmd(Cmd c, Group g) : cmd(c), group(g) {}
};

class SerialInterface {
public:
  // Reads at most one byte per call. S/X/R/H are held pending until the
  // next call supplies an 'A'/'B' group tag (or the pending wait times out
  // — see Timing::CMD_GROUP_TAG_TIMEOUT_MS); an invalid/late tag drops the
  // pending command rather than reinterpreting the stray byte.
  static ParsedCmd readSerialCmd(uint32_t now);

  static void printScientific(float value);
  static void printStateName(State s);

  static void printCsvHeader();
  static void printCsvLineAveraged(uint32_t ms,
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
                                   bool maintMode);

  static void printHelpNormal();
  static void printHelpMaint();

  // Per-group status is printed by StateMachine::printStatus(); this just
  // prints the shared command-help block once ahead of both groups' status.

  static void printStartupBanner(bool restoredA, State stateA,
                                 bool relA_Pump1, bool relA_Pump2, bool relA_Hornet,
                                 bool restoredB, State stateB,
                                 bool relB_Pump1, bool relB_Pump2, bool relB_Hornet,
                                 bool maintMode,
                                 float toGauge8V, float adcCorrection);

private:
  static char     _pendingChar;   // 0 = no group-tag command pending
  static uint32_t _pendingSince;
};

#endif // SERIAL_INTERFACE_H
