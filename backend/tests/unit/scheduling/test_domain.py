"""Business rules of the Appointment aggregate. No database, no HTTP - runs in milliseconds."""

from datetime import timedelta
from uuid import uuid4

import pytest

from careslot.modules.scheduling.domain.model import (
    CHANGE_CUTOFF,
    Appointment,
    AppointmentNotActiveError,
    AppointmentStatus,
    ChangeWindowClosedError,
    SlotInPastError,
)
from tests.unit.scheduling.fakes import NOW, FakeSchedulingRepository


@pytest.fixture
def repo() -> FakeSchedulingRepository:
    return FakeSchedulingRepository()


def test_booking_a_future_slot_records_an_event(repo: FakeSchedulingRepository) -> None:
    slot = repo.make_slot(timedelta(days=1))
    appt = Appointment.book(patient_id=uuid4(), slot=slot, now=NOW)

    assert appt.status is AppointmentStatus.BOOKED
    assert (appt.starts_at, appt.clinician_id) == (slot.starts_at, slot.clinician_id)
    assert [e.name for e in appt.pending_events] == ["AppointmentBooked"]


def test_cannot_book_a_slot_that_has_started(repo: FakeSchedulingRepository) -> None:
    with pytest.raises(SlotInPastError):
        Appointment.book(patient_id=uuid4(), slot=repo.make_slot(timedelta(0)), now=NOW)


def test_cancel_inside_the_cutoff_is_rejected(repo: FakeSchedulingRepository) -> None:
    appt = Appointment.book(patient_id=uuid4(), slot=repo.make_slot(timedelta(hours=3)), now=NOW)
    too_late = appt.starts_at - CHANGE_CUTOFF + timedelta(minutes=1)

    with pytest.raises(ChangeWindowClosedError):
        appt.cancel(now=too_late)


def test_cancel_exactly_at_the_cutoff_is_allowed(repo: FakeSchedulingRepository) -> None:
    appt = Appointment.book(patient_id=uuid4(), slot=repo.make_slot(timedelta(hours=3)), now=NOW)
    appt.cancel(now=appt.starts_at - CHANGE_CUTOFF)
    assert appt.status is AppointmentStatus.CANCELLED


def test_cannot_cancel_twice(repo: FakeSchedulingRepository) -> None:
    appt = Appointment.book(patient_id=uuid4(), slot=repo.make_slot(timedelta(days=1)), now=NOW)
    appt.cancel(now=NOW)
    with pytest.raises(AppointmentNotActiveError):
        appt.cancel(now=NOW)


def test_reschedule_moves_time_and_clinician(repo: FakeSchedulingRepository) -> None:
    appt = Appointment.book(patient_id=uuid4(), slot=repo.make_slot(timedelta(days=1)), now=NOW)
    new_slot = repo.make_slot(timedelta(days=2))
    appt.reschedule(new_slot=new_slot, now=NOW)

    assert (appt.slot_id, appt.starts_at) == (new_slot.id, new_slot.starts_at)
    assert [e.name for e in appt.pending_events][-1] == "AppointmentRescheduled"


def test_events_are_broker_ready_and_carry_ids_only(repo: FakeSchedulingRepository) -> None:
    appt = Appointment.book(patient_id=uuid4(), slot=repo.make_slot(timedelta(days=1)), now=NOW)
    message = appt.pending_events[0].to_message()

    assert message["name"] == "AppointmentBooked"
    assert set(message) == {
        "name",
        "event_id",
        "occurred_at",
        "appointment_id",
        "patient_id",
        "clinician_id",
        "starts_at",
    }
    assert all(isinstance(v, str) for v in message.values())
