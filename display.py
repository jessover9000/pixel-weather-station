"""Send raw RGB frames to the iDotMatrix 64x64 display over BLE.

Protocol reverse-engineered from https://github.com/tomglenn/idx-ai (ble.js).
The 64x64 display expects flat RGB bytes (64*64*3 = 12 288 B) wrapped in
4 096-byte chunks, each prefixed with a 9-byte header.  Chunks are split
into 509-byte BLE packets; all but the last use write-without-response for
speed, and the final packet uses write-with-response as a sync barrier.
"""

import asyncio
import logging
import struct
from typing import List

from bleak import BleakClient, BleakScanner
from PIL import Image

import config

log = logging.getLogger(__name__)

SERVICE_UUID = "000000fa-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000fa02-0000-1000-8000-00805f9b34fb"
BLE_PACKET_SIZE = 509
MAX_CHUNK_PAYLOAD = 4096
HEADER_SIZE = 9
SET_DRAW_MODE = bytearray([5, 0, 4, 1, 1])

MAX_RETRIES = 2


async def set_brightness(client: BleakClient, percent: int) -> None:
    """Set display brightness (0–100)."""
    val = max(0, min(100, percent))
    cmd = bytearray([0x05, 0x00, 0x04, 0x80, val])
    await client.write_gatt_char(WRITE_CHAR_UUID, cmd, response=True)
    log.info("brightness set to %d%%", val)


def _image_to_rgb(img: Image.Image) -> bytes:
    """Convert a Pillow image to flat RGB bytes (row-major, 3 bytes/pixel)."""
    img = img.convert("RGB").resize(
        (config.DISPLAY_SIZE, config.DISPLAY_SIZE), Image.LANCZOS
    )
    return img.tobytes()


def _encode_chunks(rgb: bytes) -> List[List[bytearray]]:
    """Build chunked BLE packet groups from raw RGB data.

    Returns a list of groups; each group is a list of <=509-byte packets.
    """
    total = len(rgb)
    offset = 0
    chunk_idx = 0
    groups: List[List[bytearray]] = []

    while offset < total:
        payload_size = min(MAX_CHUNK_PAYLOAD, total - offset)
        packet_len = payload_size + HEADER_SIZE

        header = struct.pack("<H", packet_len)
        header += b"\x00\x00"
        header += bytes([0x02 if chunk_idx > 0 else 0x00])
        header += struct.pack("<I", total)

        full_chunk = bytearray(header) + bytearray(rgb[offset : offset + payload_size])

        packets: List[bytearray] = []
        p = 0
        while p < len(full_chunk):
            end = min(p + BLE_PACKET_SIZE, len(full_chunk))
            packets.append(full_chunk[p:end])
            p = end
        groups.append(packets)

        offset += payload_size
        chunk_idx += 1

    return groups


async def _find_device() -> str:
    """Return the BLE address of the first iDotMatrix device found."""
    log.info("scanning for iDotMatrix device...")
    devices = await BleakScanner.discover(timeout=8, return_adv=True)
    for _key, (device, adv) in devices.items():
        name = adv.local_name or ""
        if name.startswith("IDM"):
            log.info("found %s (%s)", name, device.address)
            return device.address
    raise RuntimeError("no iDotMatrix device found — is it powered on?")


async def _send_frame(client: BleakClient, img: Image.Image) -> None:
    """Send a single Pillow image frame to the connected display."""
    rgb = _image_to_rgb(img)
    groups = _encode_chunks(rgb)
    all_packets = [pkt for group in groups for pkt in group]

    for i, pkt in enumerate(all_packets):
        is_last = i == len(all_packets) - 1
        await client.write_gatt_char(
            WRITE_CHAR_UUID, pkt, response=is_last
        )


async def send_frames(frames: List[Image.Image], loop: bool = True) -> None:
    """Connect to the display and send *frames* in a loop.

    If *loop* is True the animation repeats until the weather is refreshed
    (caller should wrap this in a task and cancel it).  If False, each frame
    is sent once and the function returns.
    """
    address = config.BLE_ADDRESS or await _find_device()

    log.info("connecting to %s ...", address)
    async with BleakClient(address, timeout=15) as client:
        log.info("connected — sending SetDrawMode(1)")
        await client.write_gatt_char(WRITE_CHAR_UUID, SET_DRAW_MODE, response=True)
        await asyncio.sleep(0.1)

        while True:
            for frame in frames:
                await _send_frame(client, frame)
                await asyncio.sleep(config.FRAME_DELAY)
            if not loop:
                break


def send_to_display(frames: List[Image.Image], loop: bool = True) -> None:
    """Blocking wrapper around :func:`send_frames` with retry logic."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            asyncio.run(send_frames(frames, loop=loop))
            return
        except asyncio.CancelledError:
            return
        except Exception as exc:
            last_err = exc
            log.warning("attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
    raise RuntimeError(f"failed after {MAX_RETRIES} attempts") from last_err
