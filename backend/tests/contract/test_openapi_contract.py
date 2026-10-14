"""API contract tests generated from our own OpenAPI document (schemathesis).

For every operation, schemathesis generates valid *and* edge-case requests from the schema and
checks that the API: never returns a 5xx, only returns documented status codes, returns the
documented content types and that every response body matches its declared schema. This is
what keeps "API-first" honest: the spec is not documentation that drifts, it is a test oracle.
"""

from uuid import UUID

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.specs.openapi.checks import positive_data_acceptance

from careslot.main import create_app
from careslot.shared.principal import Role
from careslot.shared.security import issue_token

pytestmark = [pytest.mark.contract, pytest.mark.integration]

# Lazy: the app is built after the database fixture has configured the environment.
schema = schemathesis.pytest.from_fixture("api_schema")

PATIENT = UUID("a1000000-0000-4000-8000-000000000001")


@pytest.fixture
def api_schema(database_url: str) -> schemathesis.schemas.BaseSchema:
    return schemathesis.openapi.from_asgi("/api/v1/openapi.json", create_app())


@schema.parametrize()
@settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_api_conforms_to_its_contract(case: schemathesis.Case) -> None:
    # Authenticate as a patient. Operations for other roles must then answer with a
    # documented 403 problem - which the conformance checks verify too.
    token = issue_token(PATIENT, Role.PATIENT)
    case.call_and_validate(
        headers={"Authorization": f"Bearer {token}"},
        # Some rules span several fields or depend on state and cannot be expressed in OpenAPI
        # (search window must be positive, change cut-off, slot already taken). The API
        # answers those with *documented* 409/422 problem responses, so "schema-valid input
        # must be accepted" does not hold by design. Every conformance check still runs.
        excluded_checks=[positive_data_acceptance],
    )
