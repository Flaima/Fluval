import logging
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from .core.device import Device
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    device: Device = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FluvalProgramSelect(device)])

class FluvalProgramSelect(SelectEntity):
    def __init__(self, device: Device):
        self.device = device
        attr = device.attribute("mode")
        self._attr_name = f"{device.name} Programm"
        self._attr_options = attr.get("options", [])
        self._attr_current_option = attr.get("default", "manual")
        self._available = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.device.mac)},
            "connections": {("bluetooth", self.device.mac)},
            "name": self.device.name,
            "manufacturer": "Fluval",
            "model": "BLE Aquarium Light",
        }
        self._attr_unique_id = f"{self.device.mac.replace(':', '')}_select"

    @property
    def available(self):
        return self._available

    async def async_select_option(self, option: str):
        self._attr_current_option = option
        self.device.set_value("mode", option)
        self.async_write_ha_state()