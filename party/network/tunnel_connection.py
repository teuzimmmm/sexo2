"""Keep TLS verification while handling delayed ISP DNS for temporary tunnel names."""

import asyncio
import ipaddress
import socket
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
import requests
import websockets

_VERIFIED_ADDRESSES = {}


def _resolve_cloudflare(hostname):
    response = requests.get(
        "https://cloudflare-dns.com/dns-query",
        params={"name": hostname, "type": "A"},
        headers={"Accept": "application/dns-json"},
        timeout=8,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("Status") != 0:
        raise socket.gaierror("Temporary tunnel DNS is not ready")
    for answer in data.get("Answer", []):
        if answer.get("type") == 1:
            address = ipaddress.ip_address(answer.get("data", ""))
            if address.version == 4 and address.is_global:
                return str(address)
    raise socket.gaierror("Temporary tunnel has no public address")


def _remember(host, ws):
    address = getattr(ws, "remote_address", None)
    if isinstance(address, tuple) and isinstance(address[0], str):
        try:
            parsed = ipaddress.ip_address(address[0])
            if parsed.is_global:
                _VERIFIED_ADDRESSES[host] = (str(parsed), time.monotonic() + 120)
        except ValueError:
            pass


async def connect_with_dns_fallback(url, **kwargs):
    parts = urlsplit(url)
    host = parts.hostname or ""
    is_tunnel = parts.scheme == "wss" and host.endswith(".trycloudflare.com")
    try:
        ws = await websockets.connect(url, **kwargs)
        # Only remember a direct connection that already passed certificate validation.
        if is_tunnel and kwargs.get("proxy", True) is None:
            _remember(host, ws)
        return ws
    except socket.gaierror:
        if not is_tunnel:
            raise
        cached = _VERIFIED_ADDRESSES.get(host)
        address = (
            cached[0] if cached and cached[1] > time.monotonic() else await asyncio.to_thread(_resolve_cloudflare, host)
        )
        # URI keeps the original HTTP Host and TLS certificate is checked against
        # the original name. No trust checks are disabled and no OS DNS is changed.
        fallback = dict(kwargs)
        fallback.update(host=address, port=parts.port or 443, server_hostname=host, proxy=None)
        ws = await websockets.connect(url, **fallback)
        _remember(host, ws)
        return ws


@asynccontextmanager
async def secure_connection(url, **kwargs):
    ws = await connect_with_dns_fallback(url, **kwargs)
    try:
        yield ws
    finally:
        await ws.close()
