"""Patients bounded context: minimal patient identity, encrypted identity codes, erasure.

PUBLIC INTERFACE: domain events only. Other modules react to `PatientErased`; they never read
patient tables.
"""

from careslot.modules.patients.domain.events import PatientErased

__all__ = ["PatientErased"]
