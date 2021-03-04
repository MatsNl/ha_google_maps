"""Test the google_maps config flow."""
from homeassistant import config_entries, setup
from homeassistant.components.google_maps.config_flow import (
    CannotConnect,
    InvalidCookies,
)
from homeassistant.components.google_maps.const import COOKIE, DOMAIN
from homeassistant.const import (
    ATTR_GPS_ACCURACY,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from .conftest import CONFIG, TEST_COOKIE, TEST_USERNAME

from tests.common import MockConfigEntry


async def test_form(hass, mock_service):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: TEST_USERNAME},
    )
    await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["step_id"] == "auth"
    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"cookie": "test-cookie"},
    )
    await hass.async_block_till_done()
    assert result3["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result3["title"] == TEST_USERNAME
    assert result3["data"] == {CONF_USERNAME: TEST_USERNAME, COOKIE: TEST_COOKIE}

    assert mock_service[1].call_count == 1


async def test_form_invalid_auth(hass, mock_service):
    """Test we handle invalid auth."""
    mock_service[0].side_effect = InvalidCookies
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: TEST_USERNAME},
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {COOKIE: TEST_COOKIE},
    )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass, mock_service):
    """Test we handle cannot connect error."""
    mock_service[0].side_effect = CannotConnect
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: TEST_USERNAME},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {COOKIE: TEST_COOKIE},
    )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_reauth_success(hass: HomeAssistant, mock_service):
    """Test reauth flow."""
    mock_service[0].side_effect = None
    entry = MockConfigEntry(domain=DOMAIN, data=CONFIG)
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            CONF_SOURCE: config_entries.SOURCE_REAUTH,
        },
        data=entry,
    )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == config_entries.SOURCE_REAUTH
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["step_id"] == "auth"
    result3 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {COOKIE: TEST_COOKIE},
    )
    assert result3["type"] == RESULT_TYPE_ABORT
    assert result3["reason"] == "reauth_successful"


async def test_options_flow(hass, mock_service):
    """Test updating options."""

    entry = MockConfigEntry(domain=DOMAIN, data=CONFIG)
    entry.add_to_hass(hass)

    assert await setup.async_setup_component(hass, DOMAIN, {}) is True
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "init"
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 100, ATTR_GPS_ACCURACY: 0},
    )
    await hass.async_block_till_done()
    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["data"][CONF_SCAN_INTERVAL] == 100
    assert result2["data"][ATTR_GPS_ACCURACY] is None
