"""Shared fixtures for the Audac MTX test suite."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components from this repository."""
    yield


@pytest.fixture
def mock_setup_entry():
    """Prevent the integration from actually being set up."""
    with patch(
        "custom_components.audac_mtx.async_setup_entry", return_value=True
    ) as mock:
        yield mock


@pytest.fixture
def mock_mtx_client():
    """Mock the MTX TCP client used by the config flow."""
    with (
        patch(
            "custom_components.audac_mtx.mtx_client.MTXClient.connect",
            new_callable=AsyncMock,
        ) as connect,
        patch(
            "custom_components.audac_mtx.mtx_client.MTXClient.disconnect",
            new_callable=AsyncMock,
        ),
    ):
        yield connect


@pytest.fixture
def mock_xmp_client():
    """Mock the XMP44 TCP client used by the config flow."""
    with (
        patch(
            "custom_components.audac_mtx.xmp44_client.XMP44Client.connect",
            new_callable=AsyncMock,
        ) as connect,
        patch(
            "custom_components.audac_mtx.xmp44_client.XMP44Client.disconnect",
            new_callable=AsyncMock,
        ),
    ):
        yield connect
