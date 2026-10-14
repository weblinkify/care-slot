"""Event wiring: which module reacts to which other module's events.

Lives in the composition root so the dependency graph between modules is visible in one
place, and so no module needs to know who listens to its events.
"""

from careslot.modules import consent, scheduling
from careslot.modules.patients import PatientErased
from careslot.shared.events import EventBus


def wire_event_handlers(bus: EventBus) -> None:
    # Right to erasure fans out: free the patient's future slots, drop consent history.
    bus.subscribe(PatientErased, scheduling.on_patient_erased)
    bus.subscribe(PatientErased, consent.on_patient_erased)
