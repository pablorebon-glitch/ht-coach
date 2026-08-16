# Input Behavior

Alpha 0.6.7 HF-06 defines the page-only mouse-wheel policy for the desktop UI.

## Page-only wheel policy

Ordinary mouse-wheel input scrolls the active page. Hovering over a closed value
control is not considered an intentional value change.

Protected controls include:

- closed combo boxes;
- tab bars;
- spin boxes and date/time edits;
- sliders and other wheel-reactive value controls covered by the shared Qt types.

When the wheel is used over one of those controls, HT Coach forwards the wheel
event to the nearest page scroll area, preferring the Match page scroll area when
the control lives inside the Match workspace. The protected control keeps its
current value, does not emit a user-change signal, and does not trigger
recalculation.

## Deliberate input still works

The policy changes mouse-wheel behavior only. The following remain deliberate
ways to change controls:

- clicking a combo box item;
- opening a combo popup and scrolling its visible option list;
- keyboard navigation, including Tab, Shift+Tab and arrow keys;
- typing in editable fields;
- using explicit buttons or arrows on controls that provide them.

## Exceptions

Real scrollable content keeps native wheel behavior when it is the intended
scroll target. Examples include long tables, text views, dedicated inner scroll
areas and explicitly open combo-box popups.

At the top or bottom of a page, extra wheel input is allowed to do nothing. It
must not change tabs, selectors, player orders, match navigation or tactical
state.

## Implementation

`ht_coach_app/ui/input_behavior.py` owns the centralized
`PageOnlyWheelEventFilter`. It is installed idempotently from application startup
and from Match/Formation Board construction so tests that create a raw
`QApplication` receive the same policy.

The filter is UI-only. It does not modify persistence semantics, optimizer
behavior, rating formulas, probabilities, PRE/POST parsing or Match Intelligence.
