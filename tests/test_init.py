"""Tests for the Google Maps integration."""
# from tests.async_mock import patch
from unittest.mock import patch

from homeassistant.components.google_maps.config_flow import DOMAIN, InvalidCookies
from homeassistant.config_entries import (
    ENTRY_STATE_LOADED,
    ENTRY_STATE_NOT_LOADED,
    ENTRY_STATE_SETUP_ERROR,
    ENTRY_STATE_SETUP_RETRY,
    SOURCE_REAUTH,
)
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant

from .conftest import setup_entry


async def test_config_entry_unload(hass: HomeAssistant, mock_service) -> None:
    """Test the configuration entry loaded."""
    entry = await setup_entry(hass)

    assert entry.state == ENTRY_STATE_LOADED
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data[DOMAIN]
    assert entry.state == ENTRY_STATE_NOT_LOADED


async def test_config_entry_retry(hass: HomeAssistant, mock_service) -> None:
    """Test the configuration entry needing to be re-authenticated."""
    mock_service[1].return_value = []
    entry = await setup_entry(hass)
    assert entry.state == ENTRY_STATE_SETUP_RETRY


async def test_config_entry_reauth(hass: HomeAssistant, mock_service) -> None:
    """Test the configuration entry needing to be re-authenticated."""
    with patch.object(hass.config_entries.flow, "async_init") as mock_flow_init:
        mock_service[0].side_effect = InvalidCookies
        entry = await setup_entry(hass)
        assert entry.state == ENTRY_STATE_SETUP_ERROR

        mock_flow_init.assert_called_once_with(
            DOMAIN, context={CONF_SOURCE: SOURCE_REAUTH}, data=entry
        )
