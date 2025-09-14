import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from .core.device import Device
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    device: Device = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FluvalMoonlightSwitch(device)])

class FluvalMoonlightSwitch(SwitchEntity):
    def __init__(self, device: Device):
        self.device = device
        self._attr_name = f"{device.name} Mondlicht"
        self._is_on = False
        self._available = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.device.mac)},
            "connections": {("bluetooth", self.device.mac)},
            "name": self.device.name,
            "manufacturer": "Fluval",
            "model": "BLE Aquarium Light",
        }
        self._attr_unique_id = f"{self.device.mac.replace(':', '')}_moonlight"

    @property
    def is_on(self):
        return self._is_on

    @property
    def available(self):
        return self._available

    @property
    def icon(self):
        return "mdi:weather-night"

    async def async_turn_on(self, **kwargs):
        self._is_on = True
        self.device.set_value("moonlight", True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._is_on = False
        self.device.set_value("moonlight", False)
        self.async_write_ha_state()