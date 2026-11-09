"""Bootstrap the first ADMIN API key for a fresh deployment.

Production requires authentication, so the first key has to be created from the server side.
Run this once from the ``backend`` directory (with the same DATABASE_URL the API uses):

    python scripts/create_admin_key.py --name "bootstrap-admin"

The raw key is printed exactly once. Store it in a secret manager; only its SHA-256 hash
is persisted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session  # noqa: E402

from app.db.session import engine, init_db  # noqa: E402
from app.schemas.auth_api import APIKeyCreateRequest, ServiceAccountRole  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default="bootstrap-admin", help="Display name for the key")
    parser.add_argument(
        "--expires-in-days",
        type=int,
        default=None,
        help="Optional expiry in days (1-3650). Omit for a non-expiring key.",
    )
    args = parser.parse_args()

    init_db()
    with Session(engine) as session:
        response = AuthService(session).create_api_key(
            APIKeyCreateRequest(
                name=args.name,
                role=ServiceAccountRole.ADMIN,
                created_by="create_admin_key.py",
                expires_in_days=args.expires_in_days,
            ),
            actor_email="create_admin_key.py",
        )

    print("ADMIN API key created. It will not be shown again:")
    print(response.raw_key)
    print(f"key_id: {response.key_id}  workspace_id: {response.workspace_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
