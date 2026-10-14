"""Patients use cases. Every successful read or write of patient data is audited."""

from collections.abc import Callable
from uuid import UUID

from careslot.modules.patients.application.ports import CareRelationship, PatientRepository
from careslot.modules.patients.domain.model import Patient, PersonalIdentityCode
from careslot.shared.audit import AccessReason, AuditRecord, AuditSink
from careslot.shared.clock import Clock
from careslot.shared.errors import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from careslot.shared.events import DomainEvent
from careslot.shared.principal import Principal, Role

CLINICAL_REASONS = frozenset({AccessReason.TREATMENT, AccessReason.APPOINTMENT_PREPARATION})


class PatientNotFoundError(NotFoundError):
    title = "Patient not found"


class PatientService:
    def __init__(
        self,
        repo: PatientRepository,
        audit: AuditSink,
        care_relationship: CareRelationship,
        publish: Callable[[DomainEvent], None],
        clock: Clock,
    ) -> None:
        self._repo = repo
        self._audit = audit
        self._care_relationship = care_relationship
        self._publish = publish
        self._clock = clock

    def get_own_record(self, principal: Principal) -> Patient:
        if principal.role is not Role.PATIENT:
            raise ForbiddenError()
        patient = self._load(principal.subject)
        self._record(principal, "patient.read", patient.id, AccessReason.SELF_SERVICE)
        return patient

    def get_for_clinician(
        self, principal: Principal, patient_id: UUID, reason: AccessReason
    ) -> Patient:
        """A clinician may open a patient record only (1) with a clinical purpose and (2)
        when a care relationship exists. Both conditions are checked before any data is read,
        and the access is audited with the stated purpose."""
        if principal.role is not Role.CLINICIAN:
            raise ForbiddenError()
        if reason not in CLINICAL_REASONS:
            raise BusinessRuleError("A clinical reason is required to open a patient record.")
        if not self._care_relationship(principal.subject, patient_id):
            # No relationship: indistinguishable from "no such patient" (no enumeration).
            raise PatientNotFoundError()
        patient = self._load(patient_id)
        self._record(principal, "patient.read", patient.id, reason)
        return patient

    def erase_own_record(self, principal: Principal) -> Patient:
        """Right to erasure, self-service. Anonymises the patient and lets other modules react
        (PatientErased): scheduling cancels future appointments, consent drops its history.
        The audit log is kept - it is pseudonymous (ids only) and retained under a legal
        obligation (GDPR art. 17(3)(b)), and its hash chain stays intact."""
        if principal.role is not Role.PATIENT:
            raise ForbiddenError()
        patient = self._load(principal.subject)
        patient.erase(self._clock())
        self._repo.save(patient)
        self._record(principal, "patient.erase", patient.id, AccessReason.DATA_SUBJECT_REQUEST)
        for event in patient.pending_events:
            self._publish(event)
        patient.pending_events.clear()
        return patient

    def register(
        self, patient_id: UUID, full_name: str, identity_code: PersonalIdentityCode
    ) -> Patient:
        """Used by onboarding/seed. Identity codes are unique (checked via blind index)."""
        if self._repo.find_by_identity_code(identity_code) is not None:
            raise ConflictError("A patient with this identity code already exists.")
        patient = Patient(
            id=patient_id,
            full_name=full_name,
            identity_code=identity_code,
            created_at=self._clock(),
        )
        self._repo.add(patient)
        self._record(None, "patient.create", patient.id, AccessReason.SYSTEM_JOB)
        return patient

    def _load(self, patient_id: UUID) -> Patient:
        patient = self._repo.get(patient_id)
        if patient is None:
            raise PatientNotFoundError()
        return patient

    def _record(
        self, actor: Principal | None, action: str, patient_id: UUID, reason: AccessReason
    ) -> None:
        self._audit(
            AuditRecord(
                actor=actor,
                action=action,
                resource_type="patient",
                resource_id=str(patient_id),
                patient_id=patient_id,
                reason=reason,
            )
        )
