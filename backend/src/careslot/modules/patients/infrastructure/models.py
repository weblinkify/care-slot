from datetime import datetime
from uuid import UUID

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from careslot.shared.db import Base, UTCDateTime


class PatientRow(Base):
    __tablename__ = "pat_patients"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    # Envelope-encrypted (shared.crypto). Never stored or logged in plaintext.
    identity_code_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    # HMAC blind index: uniqueness + exact lookup without decrypting. NULL after erasure.
    identity_code_index: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    erased_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
