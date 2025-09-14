import logging
from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from .core.device import Device
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    device: Device = hass.data[DOMAIN][entry.entry_id]
    entities = [FluvalChannel(device, channel) for channel in device.numbers()]
    async_add_entities(entities)

class FluvalChannel(NumberEntity):
    def __init__(self, device: Device, channel: str):
        self.device = device
        self.channel = channel
        attr = device.attribute(channel)
        self._attr_name = f"{device.name} {channel.title()}"
        self._attr_min_value = attr.get("min", 0)
        self._attr_max_value = attr.get("max", 1000)
        self._attr_native_value = attr.get("value", 0)
        self._available = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.device.mac)},
            "connections": {("bluetooth", self.device.mac)},
            "name": self.device.name,
            "manufacturer": "Fluval",
            "model": "BLE Aquarium Light",
        }
        self._attr_unique_id = f"{self.device.mac.replace(':', '')}_{self.channel}"

    @property
    def available(self):
        return self._available

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = int(value)
        self.device.set_value(self.channel, int(value))
        _LOGGER.debug(f"Sende Kanal-Kommando: {self.channel}={int(value)}")
        try:
            payload = bytearray([0x00] * 16)
            channel_index = int(self.channel.split('_')[1])  # channel_1 -> 1
            if 1 <= channel_index <= 5:
                payload[channel_index] = int(value)
            from .core.encryption import add_crc, encrypt
            payload = add_crc(payload)
            packet = encrypt(payload)
            self.device.client.send(packet)
            _LOGGER.debug(f"Kanal-Kommando gesendet: {self.channel}={int(value)}, Paket: {to_hex(packet)}")
        except Exception as e:
            _LOGGER.error(f"Fehler beim Senden des Kanal-Kommandos: {e}")
        self.async_write_ha_state()