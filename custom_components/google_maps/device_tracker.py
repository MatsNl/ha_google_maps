"""Support for tracking People through Google Maps."""
from typing import Optional

from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.const import ATTR_BATTERY_CHARGING, ATTR_GPS_ACCURACY
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util, slugify

from .const import (
    ATTR_ADDRESS,
    ATTR_ADDRESS_SHORT,
    ATTR_FULL_NAME,
    ATTR_LAST_SEEN,
    ATTR_NICKNAME,
    COORDINATOR,
    DOMAIN,
    LOGGER,
    UNLOADER,
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Google Maps trackers."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = domain_data[COORDINATOR]
    tracked = set()
    max_accuracy = config_entry.options.get(ATTR_GPS_ACCURACY)

    @callback
    def _add_new_people():
        """Track newly reported Persons."""
        new_people = [
            person for person in coordinator.data.values() if person.id not in tracked
        ]
        if new_people:
            tracked.update([person.id for person in new_people])
            async_add_entities(
                [MapsEntity(coordinator, person, max_accuracy) for person in new_people]
            )

    domain_data[UNLOADER].append(coordinator.async_add_listener(_add_new_people))

    _add_new_people()
    return True


class MapsEntity(TrackerEntity, CoordinatorEntity):
    """A class representing a Google Maps Person tracker."""

    def __init__(self, coordinator, person, max_accuracy):
        """Initialize the Maps Tracker entity."""
        super().__init__(coordinator)
        self._person = person
        self._max_accuracy = max_accuracy
        self.__accurate = True

    @property
    def _id(self):
        """Return the id as reported by google maps api."""
        return self._person.id

    @property
    def unique_id(self):
        """Return the unique_id for the entity."""
        return f"google_maps_{slugify(self._person.id)}"

    @property
    def name(self):
        """Return the full name as reported by google maps."""
        return f"Google Maps {self._person.full_name}"

    @property
    def location_accuracy(self):
        """Return the location accuracy of the device."""
        return self._person.accuracy

    @property
    def latitude(self) -> Optional[float]:
        """Return latitude value of the device."""
        return self._person.latitude

    @property
    def longitude(self) -> Optional[float]:
        """Return longitude value of the device."""
        return self._person.longitude

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_GPS

    @property
    def battery_level(self):
        """Return the battery level of the device."""
        return self._person.battery_level

    @property
    def entity_picture(self):
        """Return account picture."""
        return self._person.picture_url

    @property
    def accurate(self):
        """Return bool indicating whether last update was sufficiently accurate."""
        return self.__accurate

    @accurate.setter
    def accurate(self, bool):
        """Toggle accurate property and log accordingly."""
        if not bool == self.accurate:
            if bool:
                LOGGER.info(f"{self._person.nickname} accuracy improved")
            else:
                LOGGER.info(
                    f"Ignoring {self._person.nickname} update because expected GPS accuracy {self._max_accuracy} is not met"
                )
        self.__accurate = bool

    @property
    def state_attributes(self):
        """Return the device state attributes."""
        attr = {}
        attr.update(super().state_attributes)
        attr[ATTR_ADDRESS] = self._person.address
        attr[ATTR_ADDRESS_SHORT] = (
            self.state
            if self.state != "not_home"
            else self._person.address.split(",")[0]
        )
        attr[ATTR_FULL_NAME] = self._person.full_name
        attr[ATTR_NICKNAME] = self._person.nickname

        attr[ATTR_BATTERY_CHARGING] = self._person.charging
        attr[ATTR_LAST_SEEN] = dt_util.as_local(self._person.datetime)
        return attr

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update = self.coordinator.data.get(self._id)
        if not update:
            LOGGER.warning(f"No data received for {self._person.nickname}")
        elif self._person.datetime > update.datetime:
            LOGGER.debug(
                f"Ignoring {self._person.nickname} update because timestamp is older than last timestamp"
            )
            LOGGER.debug(f"{self._person.datetime} > {update.datetime}")
        elif self._max_accuracy and update.accuracy > self._max_accuracy:
            self.accurate = False
        else:
            self.accurate = True
            self._person = update
            self.async_write_ha_state()
