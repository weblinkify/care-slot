"""Print the OpenAPI document: `python -m careslot.openapi > api/openapi.json`.

The spec is committed (`api/openapi.json`) and reviewed like code: API changes show up as a
readable diff in the PR. CI regenerates it and fails on drift; the frontend's TypeScript
types are generated from it (`npm run gen:api`), so client and server cannot silently diverge.
"""

import json
import sys

from careslot.main import create_app
from careslot.shared.config import Settings


def main() -> None:
    # Generated with the mock IdP mounted so the demo/local contract is complete.
    spec = create_app(Settings(environment="local")).openapi()
    json.dump(spec, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
