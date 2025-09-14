import logging
from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from .core.device import Device
from .const import DOMAIN
from .core.client import to_hex

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    device: Device = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FluvalLamp(device)])

class FluvalLamp(LightEntity):
    def __init__(self, device: Device):
        self.device = device
        self._attr_name = device.name
        self._attr_supported_color_modes = {ColorMode.RGB}
        self._attr_color_mode = ColorMode.RGB
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_is_on = False
        self._available = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.device.mac)},
            "connections": {("bluetooth", self.device.mac)},
            "name": self.device.name,
            "manufacturer": "Fluval",
            "model": "BLE Aquarium Light",
        }
        entry_id = getattr(device, 'entry_id', None)
        suffix = f"_{entry_id}" if entry_id else ""
        self._attr_unique_id = f"{self.device.mac.replace(':', '')}_light{suffix}"

    @property
    def available(self):
        return self._available

    @property
    def icon(self):
        return "mdi:fishbowl"

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        if "brightness" in kwargs:
            self._attr_brightness = kwargs["brightness"]
        if "rgb_color" in kwargs:
            self._attr_rgb_color = kwargs["rgb_color"]
        self.device.set_value("led_on_off", True)
        _LOGGER.debug(f"Sende Einschalt-Kommando an Lampe: is_on={self._attr_is_on}, brightness={self._attr_brightness}, rgb={self._attr_rgb_color}")
        try:
            payload = bytearray([0x00] * 16)
            payload[0] = 0x01 if self._attr_is_on else 0x00
            if self._attr_is_on:
                r, g, b = self._attr_rgb_color
                brightness_factor = self._attr_brightness / 255
                payload[1] = int(r * brightness_factor)
                payload[2] = int(g * brightness_factor)
                payload[3] = int(b * brightness_factor)
                payload[4] = 128
                payload[5] = 128
            from .core.encryption import add_crc, encrypt
            payload = add_crc(payload)
            packet = encrypt(payload)
            self.device.client.send(packet)
            _LOGGER.debug(f"Kommando gesendet: {to_hex(packet)}")
        except Exception as e:
            _LOGGER.error(f"Fehler beim Senden des Einschalt-Kommandos: {e}")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        self.device.set_value("led_on_off", False)
        _LOGGER.debug(f"Sende Ausschalt-Kommando an Lampe: is_on={self._attr_is_on}")
        try:
            payload = bytearray([0x00] * 16)
            from .core.encryption import add_crc, encrypt
            payload = add_crc(payload)
            packet = encrypt(payload)
            self.device.client.send(packet)
            _LOGGER.debug(f"Kommando gesendet: {to_hex(packet)}")
        except Exception as e:
            _LOGGER.error(f"Fehler beim Senden des Ausschalt-Kommandos: {e}")
        self.async_write_ha_state()