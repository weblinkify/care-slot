"""Test doubles shared across modules' tests."""

from careslot.shared.audit import AuditRecord


class RecordingAudit:
    """AuditSink fake: lets tests assert *that* and *how* an access was audited."""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def __call__(self, record: AuditRecord) -> None:
        self.records.append(record)

    @property
    def actions(self) -> list[str]:
        return [r.action for r in self.records]
