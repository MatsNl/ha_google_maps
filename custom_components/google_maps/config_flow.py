"""Config flow for google_maps integration."""
from tempfile import NamedTemporaryFile
from typing import Optional

from locationsharinglib import Service
from locationsharinglib.locationsharinglibexceptions import InvalidCookies
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import ATTR_GPS_ACCURACY, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import COOKIE, DEFAULT_SCAN_INTERVAL, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        CONF_USERNAME: str,
    }
)
STEP_AUTH_DATA_SCHEMA = vol.Schema({COOKIE: str})


async def get_api(hass, data) -> Optional[Service]:
    """Get the Google Maps Api object."""
    username = data[CONF_USERNAME]
    cookie = data[COOKIE]
    try:
        with NamedTemporaryFile() as cf:
            cf.write(
                "\n".join([lin for lin in cookie.split(sep=" ") if "\t" in lin]).encode(
                    "utf-8"
                )
            )
            return await hass.async_add_executor_job(Service, cf.name, username)

    except InvalidCookies as err:
        raise InvalidAuth(
            "Cookies invalid or expired. Provide new cookies to retry"
        ) from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for google_maps."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self._username = None
        self._reauth = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Define the config flow to handle options."""
        return MapsOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self.context["title_placeholders"] = {
                CONF_USERNAME: self._username,
            }
            await self.async_set_unique_id(f"{DOMAIN}-{self._username}")
            self._abort_if_unique_id_configured()
            return await self.async_step_auth()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors={}
        )

    async def async_step_auth(self, user_input=None):
        """Handle the authorization step."""
        if user_input is None:
            return self.async_show_form(
                step_id="auth", data_schema=STEP_AUTH_DATA_SCHEMA
            )
        user_input[CONF_USERNAME] = self._username
        errors = {}
        try:
            await get_api(self.hass, user_input)
            if self._reauth:
                self.hass.config_entries.async_update_entry(
                    self._reauth, data=user_input
                )
                await self.hass.config_entries.async_reload(self._reauth.entry_id)
                return self.async_abort(reason="reauth_successful")
            return self.async_create_entry(
                title=user_input[CONF_USERNAME], data=user_input
            )
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except (InvalidAuth, InvalidCookies):
            errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="auth",
            data_schema=STEP_AUTH_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, user_input=None):
        """Handle reauthorization in case cookies are invalid."""
        if not self._reauth:
            await self.async_set_unique_id(f"{DOMAIN}-{self._username}")
            self._reauth = user_input
            self._username = user_input.data[CONF_USERNAME]
            self._description_placeholders = {CONF_USERNAME: self._username}
            user_input = None

        if user_input is None:
            return self.async_show_form(step_id="reauth", data_schema=vol.Schema({}))

        return await self.async_step_auth()


class MapsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a Google Maps options flow."""

    def __init__(self, entry: config_entries.ConfigEntry):
        """Initialize."""
        self._entry = entry

    async def async_step_init(self, user_input: Optional[dict] = None):
        """Manage the options."""
        if user_input is not None:
            if user_input[ATTR_GPS_ACCURACY] == 0:
                user_input[ATTR_GPS_ACCURACY] = None
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self._entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ): cv.positive_int,
            vol.Optional(
                ATTR_GPS_ACCURACY,
                default=self._entry.options.get(ATTR_GPS_ACCURACY),
            ): cv.positive_int,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
