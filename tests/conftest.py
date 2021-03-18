"""Fixtures for UniFi methods."""
from unittest.mock import patch

from locationsharinglib import Person
import pytest

from homeassistant import setup
from custom_components.google_maps.config_flow import COOKIE, DOMAIN
from homeassistant.const import CONF_USERNAME

from tests.common import MockConfigEntry

TEST_USERNAME = "test-user@gmail.com"
TEST_COOKIE = "test-cookie"
CONFIG = {CONF_USERNAME: TEST_USERNAME, COOKIE: TEST_COOKIE}
UNIQUE_ID = f"{DOMAIN}-{TEST_USERNAME}"
SERVICE = "homeassistant.components.google_maps.config_flow.Service"

TEST_LOCATIONS = {
    1: [
        None,
        [None, 1.0, 2.0],
        1000000000000,
        0,
        "Unknown",
        None,
        "Internet",
        3600000,
    ],
    2: [
        None,
        [None, 1.0, 2.0],
        100000000000,
        1000,
        "Unknown",
        None,
        "Internet",
        3600000,
    ],
}


def get_test_person(person=1):
    """Get a Person object for testing."""
    return Person(
        [
            TEST_USERNAME,
            TEST_LOCATIONS[person],
            None,
            None,
            None,
            None,
            [None, None, TEST_USERNAME, TEST_USERNAME],
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ]
    )


async def setup_entry(hass):
    """Mock and setup a config entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=CONFIG)
    entry.add_to_hass(hass)

    assert await setup.async_setup_component(hass, DOMAIN, {})
    return entry


@pytest.fixture(autouse=True, name="mock_service", scope="module")
def mock_service_fixture():
    """Mock the azure event hub producer client."""
    with patch(
        f"{SERVICE}.get_all_people", return_value=[get_test_person()]
    ) as mock_get_all_people, patch(
        f"{SERVICE}.__init__", return_value=None
    ) as mock_init:
        yield (
            mock_init,
            mock_get_all_people,
        )
