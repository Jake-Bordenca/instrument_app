# MRI_INTLK_SYS.md

## Purpose

Coding conventions and integration rules for this repository. For system
architecture, the firmware state machine, the fault model, the serial
protocol, and how to change interlock setpoints, see [README.md](../README.md)
and [state_machine.mmd](state_machine.mmd) — this file does not duplicate
that content.

---

## Integration rules

- Do not modify `MRI_INT_SYS/` firmware unless there is a genuine hardware bug
  or setpoint change to make (see README.md §3 for the setpoint-change
  checklist).
- New pump-group or interlock behavior belongs inside the single
  `StateMachine` class (`MRI_INT_SYS/StateMachine.h/.cpp`) so both Group A and
  Group B pick it up automatically — never special-case one group in the
  `.ino`, and never duplicate logic per group.
- New CSV/serial fields must be mirrored into `Services/SerialComms.py`'s
  `_parse_line()` `required` set and return dict, using the existing
  snake_case + `_a`/`_b` suffix convention.
- Do not tightly couple pressure logging to gauge display code.
- Keep service-layer classes (`SerialComms`, `PressureLogger`) free of GUI
  logic.
- Keep GUI pages (`pressure_page`, `maintenance_page`) free of direct serial
  I/O.
- Maintain the existing data flow:
  `Arduino → SerialComms → PyQt signals → PressurePage + PressureLogger`.
- Acquisition runs on a timer; the GUI must remain responsive. Do not block
  the UI thread.
- Preserve readability for a research codebase maintained by non-software
  specialists.

---

## Developer notes

This is research instrumentation software. Prioritize:

- Readable code with explicit field names
- Clear mapping between Arduino CSV columns and Python dict keys
- Recoverable logged data (CSV files should have correct headers)
- Modular layers so the GUI page does not contain hardware logic
