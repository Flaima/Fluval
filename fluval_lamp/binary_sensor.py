import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from .core.device import Device
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    device: Device = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FluvalConnectionSensor(device)])

class FluvalConnectionSensor(BinarySensorEntity):
    def __init__(self, device: Device):
        self.device = device
        self._attr_name = f"{device.name} Verbindung"
        self._is_connected = device.connected
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.device.mac)},
            "connections": {("bluetooth", self.device.mac)},
            "name": self.device.name,
            "manufacturer": "Fluval",
            "model": "BLE Aquarium Light",
        }
        self._attr_unique_id = f"{self.device.mac.replace(':', '')}_connection"

    @property
    def is_on(self):
        return self.device.connected

    @property
    def icon(self):
        return "mdi:bluetooth"