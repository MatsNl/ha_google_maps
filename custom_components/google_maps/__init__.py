"""The google_maps integration."""
from datetime import timedelta

from homeassistant.components.device_tracker.config_entry import (
    DOMAIN as TRACKER_DOMAIN,
)
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .config_flow import InvalidAuth, InvalidCookies, get_api
from .const import COORDINATOR, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, UNLOADER


async def async_setup(hass, config):
    """Component doesn't support configuration through configuration.yaml."""
    return True


async def async_setup_entry(hass, entry):
    """Set up Google Maps as config entry."""

    def _reauth_needed():
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={CONF_SOURCE: SOURCE_REAUTH},
                data=entry,
            )
        )

    async def _async_update_data():
        """Fetch data from API endpoint."""
        try:
            people = {
                person.id: person
                for person in await hass.async_add_executor_job(api.get_all_people)
            }
            if not people:
                raise UpdateFailed("No data received")
            return people
        except InvalidCookies as e:
            _reauth_needed()
            coordinator._async_stop_refresh(None)
            raise UpdateFailed("Cookies expired") from e

    try:
        api = await get_api(hass, entry.data)
    except InvalidAuth:
        _reauth_needed()
        return False
    coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name="Google Maps",
        update_method=_async_update_data,
        update_interval=timedelta(
            seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ),
    )
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
        UNLOADER: [entry.add_update_listener(async_reload_entry)],
    }
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, TRACKER_DOMAIN)
    )
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, config_entry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(
        config_entry, TRACKER_DOMAIN
    )

    if unload_ok:
        [undo() for undo in hass.data[DOMAIN].pop(config_entry.entry_id)[UNLOADER]]
    return unload_ok
