import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.bluetooth import async_ble_device_from_address
from .const import DOMAIN
from .core.device import Device

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["light", "number", "switch", "select", "binary_sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fluval Lamp integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    mac = entry.data["mac"]
    name = entry.data.get("name", "Fluval Lampe")
    ble_device = async_ble_device_from_address(hass, mac, connectable=True)
    if not ble_device:
        _LOGGER.error(f"BLE-Gerät {mac} nicht gefunden!")
        return False
    device = Device(name, ble_device, None)
    device.unique_id = f"{mac.replace(':', '')}_device"
    hass.data[DOMAIN][entry.entry_id] = device
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setups(entry, [platform])
        )
    _LOGGER.debug("Fluval Lamp setup complete for entry %s", entry.entry_id)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok