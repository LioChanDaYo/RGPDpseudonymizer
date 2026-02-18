"""Tests for StepIndicator: step states, mode switching."""

from __future__ import annotations

from gdpr_pseudonymizer.gui.widgets.step_indicator import (
    BATCH_STEPS,
    SINGLE_STEPS,
    StepIndicator,
    StepMode,
    StepState,
)


class TestStepIndicatorCreation:
    """Widget creation."""

    def test_creates_widget(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        assert si.objectName() == "stepIndicator"

    def test_default_mode_is_single(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        assert si.mode() == StepMode.SINGLE

    def test_default_step_is_zero(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        assert si.current_step() == 0


class TestStepStates:
    """Step state transitions."""

    def test_first_step_is_active(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        assert si.step_state(0) == StepState.ACTIVE

    def test_later_steps_are_upcoming(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        assert si.step_state(1) == StepState.UPCOMING
        assert si.step_state(2) == StepState.UPCOMING
        assert si.step_state(3) == StepState.UPCOMING

    def test_advance_step(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        si.set_step(2)
        assert si.step_state(0) == StepState.COMPLETED
        assert si.step_state(1) == StepState.COMPLETED
        assert si.step_state(2) == StepState.ACTIVE
        assert si.step_state(3) == StepState.UPCOMING

    def test_step_clamped_to_max(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        si.set_step(99)
        assert si.current_step() == 3  # max index

    def test_step_clamped_to_zero(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        si.set_step(-5)
        assert si.current_step() == 0


class TestModeSwitching:
    """Mode switching between single and batch."""

    def test_switch_to_batch(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        si.set_mode(StepMode.BATCH)
        assert si.mode() == StepMode.BATCH
        assert si.step_count() == 4

    def test_mode_switch_resets_step(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        si.set_step(2)
        si.set_mode(StepMode.BATCH)
        assert si.current_step() == 0

    def test_single_step_count(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        si = StepIndicator()
        qtbot.addWidget(si)
        assert si.step_count() == 4

    def test_single_steps_names(self) -> None:
        assert SINGLE_STEPS == ["Sélection", "Analyse", "Validation", "Résultat"]

    def test_batch_steps_names(self) -> None:
        assert BATCH_STEPS == ["Sélection", "Traitement", "Validation", "Résumé"]
