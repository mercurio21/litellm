import hashlib
from typing import Final

import pytest

from litellm.proxy.mcp_server.db import _mcp_identifier_lock_keys, merge_user_env_vars

from .test_mcp_env_vars import _transactional_env_vars_prisma, env_vars_salt_key  # noqa: F401


@pytest.fixture
def security_blake2b_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """hashlib.blake2b as a FIPS Python build ships it: refused unless the caller passes usedforsecurity=False."""
    real_blake2b: Final = hashlib.blake2b

    def blake2b(data: bytes = b"", *, digest_size: int = 64, usedforsecurity: bool = True) -> "hashlib._Hash":
        if usedforsecurity:
            raise ValueError("blake2b is blocked when usedforsecurity=True")
        return real_blake2b(data, digest_size=digest_size, usedforsecurity=False)

    monkeypatch.setattr(hashlib, "blake2b", blake2b)


def test_identifier_lock_keys_are_unchanged() -> None:
    assert _mcp_identifier_lock_keys("GitHub", None, "gh") == (
        int.from_bytes(hashlib.blake2b(b"mcp_identifier:gh", digest_size=8).digest(), "big", signed=True),
        -1498181317228972674,
    )


@pytest.mark.usefixtures("security_blake2b_blocked")
def test_identifier_lock_keys_work_where_security_blake2b_is_blocked() -> None:
    assert _mcp_identifier_lock_keys("GitHub") == (-1498181317228972674,)


@pytest.mark.asyncio
@pytest.mark.usefixtures("security_blake2b_blocked", "env_vars_salt_key")
async def test_merge_user_env_vars_takes_its_lock_where_security_blake2b_is_blocked() -> None:
    merged: Final = await merge_user_env_vars(
        _transactional_env_vars_prisma(), "alice", "srv-1", {"TOKEN": "abc"}, allowed_names=["TOKEN"]
    )

    assert merged == {"TOKEN": "abc"}
