import asyncio
from collections.abc import Callable
import contextlib
import logging
import time

from bleak import BleakClient, BleakError, BleakGATTCharacteristic, BLEDevice
from bleak_retry_connector import establish_connection

from . import encryption

_LOGGER = logging.getLogger(__name__)

ACTIVE_TIME = 120
COMMAND_TIME = 15

class Client:
    def __init__(
        self,
        device: BLEDevice,
        status_callback: Callable = None,
        update_callback: Callable = None,
    ) -> None:
        self.device = device
        self.status_callback = status_callback
        self.update_callback = update_callback

        self.client: BleakClient | None = None

        self.ping_future: asyncio.Future | None = None
        self.ping_task: asyncio.Task | None = None
        self.ping_time = 0

        self.send_data = None
        self.send_time = 0
        self.connect_task = asyncio.create_task(self._connect())

        self.receive_buffer = b""
        _LOGGER.debug(f"Client initialisiert für Gerät: {self.device}")

    def ping(self):
        self.ping_time = time.time() + ACTIVE_TIME
        _LOGGER.debug(f"Ping gestartet. Nächster Timeout: {self.ping_time}")
        if not self.ping_task:
            _LOGGER.debug("Starte neuen Ping-Loop Task.")
            self.ping_task = asyncio.create_task(self._ping_loop())

    def notify_callback(self, sender: BleakGATTCharacteristic, data: bytearray):
        _LOGGER.debug(f"Empfangenes Paket von {sender}: {to_hex(data)}")
        decrypted = decrypt(data)
        _LOGGER.debug(f"Entschlüsselte Daten: {to_hex(decrypted)}")
        if len(decrypted) == 17:
            self.receive_buffer += decrypted
            _LOGGER.debug(f"Buffer nach Empfang: {to_hex(self.receive_buffer)}")
        else:
            _LOGGER.debug("Got all data: %s ", to_hex(self.receive_buffer))
            self.update_callback(self.receive_buffer)
            self.receive_buffer = b""

    async def _connect(self):
        _LOGGER.debug(f"Versuche Verbindung zu BLE-Gerät: {self.device.address}")
        self.client = await establish_connection(
            BleakClient, self.device, self.device.address
        )
        _LOGGER.debug(f"Verbindung hergestellt: {self.client}")

        await self.client.start_notify(
            "00001002-0000-1000-8000-00805F9B34FB", self.notify_callback
        )
        _LOGGER.debug("Notification-Callback registriert.")

        if self.status_callback:
            self.status_callback(True)

        result = await self.client.read_gatt_char("00001004-0000-1000-8000-00805F9B34FB")
        _LOGGER.debug(f"GATT-Charakteristik gelesen (Step 0): {to_hex(result)}")

        cmd = encrypt([0x68, 0x05])
        _LOGGER.debug(f"Sende Init-Kommando: {to_hex(cmd)}")
        await self.client.write_gatt_char(
            "00001001-0000-1000-8000-00805F9B34FB",
            data=cmd,
            response=False,
        )

    def send(self, data: bytes):
        _LOGGER.debug(f"Sende Daten an Fluval: {to_hex(data)}")
        self.send_time = time.time() + COMMAND_TIME
        self.send_data = data

        self.ping()

        if self.ping_future:
            self.ping_future.cancel()

    async def _ping_loop(self):
        loop = asyncio.get_event_loop()
        _LOGGER.debug("Starte Ping-Loop.")
        while time.time() < self.ping_time or True:
            try:
                self.client = await establish_connection(
                    BleakClient, self.device, self.device.address
                )
                _LOGGER.debug(f"Ping-Loop: Verbindung hergestellt: {self.client}")
                if self.status_callback:
                    self.status_callback(True)

                while time.time() < self.ping_time or True:
                    result = await self.client.read_gatt_char(
                        "00001004-0000-1000-8000-00805F9B34FB"
                    )
                    _LOGGER.debug(f"Heartbeat-Read: {to_hex(result)}")
                    if self.send_data:
                        if time.time() < self.send_time:
                            packet = encrypt(self.send_data)
                            _LOGGER.debug(f"Ping-Loop: Sende Paket: {to_hex(packet)}")
                            await self.client.write_gatt_char(
                                "00001002-0000-1000-8000-00805F9B34FB",
                                data=packet,
                                response=True,
                            )
                        self.send_data = None

                    self.ping_future = loop.create_future()
                    loop.call_later(10, self.ping_future.cancel)
                    with contextlib.suppress(asyncio.CancelledError):
                        await self.ping_future

                await self.client.disconnect()
                _LOGGER.debug("Ping-Loop: Verbindung getrennt.")
            except TimeoutError:
                _LOGGER.debug("Ping-Loop: TimeoutError")
                pass
            except BleakError as e:
                _LOGGER.debug("Ping-Loop: BleakError", exc_info=e)
            except Exception as e:
                _LOGGER.warning("Ping-Loop: Exception", exc_info=e)
            finally:
                self.client = None
                if self.status_callback:
                    self.status_callback(False)
                await asyncio.sleep(1)

        self.ping_task = None

def encrypt(data: bytearray) -> bytearray:
    data = encryption.add_crc(data)
    return encryption.encrypt(data)

def decrypt(data: bytearray) -> bytearray:
    return encryption.decrypt(data)

def to_hex(data: bytes) -> str:
    return " ".join(format(x, "02x") for x in data)