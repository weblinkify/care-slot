import pytest
from pydantic import ValidationError

from careslot.shared.config import Settings


def test_log_level_is_case_insensitive() -> None:
    assert Settings(log_level="debug").log_level == "DEBUG"  # type: ignore[arg-type]


def test_unknown_log_level_is_rejected_at_startup() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="VERBOSE")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("environment", "production", "ephemeral_keys"),
    [
        ("local", False, True),
        ("test", False, True),
        ("staging", False, False),
        ("production", True, False),
    ],
)
def test_environment_flags(environment: str, production: bool, ephemeral_keys: bool) -> None:
    settings = Settings(environment=environment)  # type: ignore[arg-type]
    assert settings.is_production is production
    assert settings.allows_ephemeral_keys is ephemeral_keys
