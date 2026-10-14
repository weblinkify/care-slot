"""Scheduling bounded context: clinics, clinicians, slots and appointments.

PUBLIC INTERFACE. Other modules may import only what is re-exported here (enforced by
import-linter). Everything under domain/, application/, infrastructure/ and api/ is private.
"""

from careslot.modules.scheduling.domain.events import (
    AppointmentBooked,
    AppointmentCancelled,
    AppointmentRescheduled,
)

__all__ = ["AppointmentBooked", "AppointmentCancelled", "AppointmentRescheduled"]
