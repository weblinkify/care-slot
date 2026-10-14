"""Use-case tests: authorisation, ownership and orchestration. Security rules are tested
negatively - each test proves a forbidden action is actually forbidden."""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from careslot.modules.scheduling.application.services import (
    AppointmentNotFoundError,
    SchedulingService,
)
from careslot.modules.scheduling.domain.model import SlotUnavailableError
from careslot.shared.errors import BusinessRuleError, ForbiddenError
from careslot.shared.principal import Principal, Role
from tests.unit.scheduling.fakes import NOW, FakeSchedulingRepository, RecordingPublisher


@pytest.fixture
def repo() -> FakeSchedulingRepository:
    return FakeSchedulingRepository()


@pytest.fixture
def events() -> RecordingPublisher:
    return RecordingPublisher()


@pytest.fixture
def service(repo: FakeSchedulingRepository, events: RecordingPublisher) -> SchedulingService:
    return SchedulingService(repo=repo, publish=events, clock=lambda: NOW)


def patient() -> Principal:
    return Principal(subject=uuid4(), role=Role.PATIENT)


def test_patient_books_for_themselves_and_event_is_published(
    service: SchedulingService, repo: FakeSchedulingRepository, events: RecordingPublisher
) -> None:
    me = patient()
    appt = service.book(me, repo.make_slot(timedelta(days=1)).id)

    assert appt.patient_id == me.subject
    assert events.names == ["AppointmentBooked"]
    assert appt.pending_events == []  # flushed exactly once


def test_slot_cannot_be_double_booked(
    service: SchedulingService, repo: FakeSchedulingRepository
) -> None:
    slot = repo.make_slot(timedelta(days=1))
    service.book(patient(), slot.id)
    with pytest.raises(SlotUnavailableError):
        service.book(patient(), slot.id)


def test_cancelled_slot_becomes_bookable_again(
    service: SchedulingService, repo: FakeSchedulingRepository
) -> None:
    slot, me = repo.make_slot(timedelta(days=1)), patient()
    service.cancel(me, service.book(me, slot.id).id)

    assert slot in service.available_slots(repo.clinician.id, NOW, NOW + timedelta(days=2))
    service.book(patient(), slot.id)


@pytest.mark.parametrize("role", [Role.CLINICIAN, Role.ADMIN])
def test_only_patients_can_book(
    service: SchedulingService, repo: FakeSchedulingRepository, role: Role
) -> None:
    with pytest.raises(ForbiddenError):
        service.book(Principal(subject=uuid4(), role=role), repo.make_slot(timedelta(days=1)).id)


def test_patient_cannot_see_another_patients_appointment(
    service: SchedulingService, repo: FakeSchedulingRepository
) -> None:
    appt = service.book(patient(), repo.make_slot(timedelta(days=1)).id)
    # 404, not 403: the response must not reveal that the appointment exists.
    with pytest.raises(AppointmentNotFoundError):
        service.get_appointment(patient(), appt.id)


@pytest.mark.parametrize("action", ["cancel", "reschedule"])
def test_patient_cannot_change_another_patients_appointment(
    service: SchedulingService, repo: FakeSchedulingRepository, action: str
) -> None:
    appt = service.book(patient(), repo.make_slot(timedelta(days=1)).id)
    intruder = patient()
    with pytest.raises(AppointmentNotFoundError):
        if action == "cancel":
            service.cancel(intruder, appt.id)
        else:
            service.reschedule(intruder, appt.id, repo.make_slot(timedelta(days=2)).id)


def test_clinician_sees_own_appointment_but_not_others(
    service: SchedulingService, repo: FakeSchedulingRepository
) -> None:
    appt = service.book(patient(), repo.make_slot(timedelta(days=1)).id)
    own = Principal(subject=repo.clinician.id, role=Role.CLINICIAN)
    other = Principal(subject=uuid4(), role=Role.CLINICIAN)

    assert service.get_appointment(own, appt.id).id == appt.id
    with pytest.raises(AppointmentNotFoundError):
        service.get_appointment(other, appt.id)


def test_admin_cannot_browse_appointments(
    service: SchedulingService, repo: FakeSchedulingRepository
) -> None:
    appt = service.book(patient(), repo.make_slot(timedelta(days=1)).id)
    with pytest.raises(AppointmentNotFoundError):
        service.get_appointment(Principal(subject=uuid4(), role=Role.ADMIN), appt.id)


def test_reschedule_frees_the_old_slot(
    service: SchedulingService, repo: FakeSchedulingRepository, events: RecordingPublisher
) -> None:
    me = patient()
    old, new = repo.make_slot(timedelta(days=1)), repo.make_slot(timedelta(days=2))
    appt = service.book(me, old.id)
    service.reschedule(me, appt.id, new.id)

    free = service.available_slots(repo.clinician.id, NOW, NOW + timedelta(days=3))
    assert old in free and new not in free
    assert events.names == ["AppointmentBooked", "AppointmentRescheduled"]


def test_slot_search_window_is_bounded(
    service: SchedulingService, repo: FakeSchedulingRepository
) -> None:
    with pytest.raises(BusinessRuleError):
        service.available_slots(repo.clinician.id, NOW, NOW + timedelta(days=60))


def test_clinician_day_uses_clinic_timezone(
    service: SchedulingService, repo: FakeSchedulingRepository
) -> None:
    # 23:30 UTC on 2 March is 01:30 on 3 March in Helsinki (UTC+2): it belongs to the 3rd.
    late = repo.make_slot(timedelta(hours=15, minutes=30))
    service.book(patient(), late.id)
    me = Principal(subject=repo.clinician.id, role=Role.CLINICIAN)

    assert service.clinician_day(me, date(2026, 3, 2)) == []
    assert len(service.clinician_day(me, date(2026, 3, 3))) == 1
