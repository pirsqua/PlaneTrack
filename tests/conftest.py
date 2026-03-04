"""Session-level test configuration."""

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def test_env():
    """Inject dummy env vars so Settings validation passes without a real .env file."""
    env_patch = {
        "OPENSKY_CLIENT_ID": "test-client",
        "OPENSKY_CLIENT_SECRET": "test-secret",
        "AZURE_ACCOUNT_NAME": "testaccount",
        "AZURE_ACCOUNT_KEY": "dGVzdA==",
        "ADLS_CONTAINER": "test",
        "PIPELINE_INTERVAL_SECONDS": "3600",  # don't fire during tests
    }
    original = {k: os.environ.get(k) for k in env_patch}
    os.environ.update(env_patch)
    yield
    for k, v in original.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
