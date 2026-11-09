"""Webhook URL validation and masking helpers.

Webhook URLs are bearer-style secrets (the path segment authorizes posting to the destination),
so they are stored for delivery but never returned by the API in raw form.
"""

import ipaddress
import socket
from urllib.parse import urlsplit

MASK = "****"
_BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain", "metadata.google.internal"})


def mask_webhook_url(url: str | None) -> str:
    """Return ``scheme://host/****`` - the destination host is visible, the secret path is not."""
    if not url:
        return ""
    parts = urlsplit(url)
    host = parts.hostname or "invalid-host"
    scheme = parts.scheme or "https"
    return f"{scheme}://{host}/{MASK}"


def scrub_webhook_url(text: str | None, url: str) -> str | None:
    """Replace any occurrence of the raw webhook URL inside free text (e.g. error messages)."""
    if text is None:
        return None
    if url:
        text = text.replace(url, mask_webhook_url(url))
    return text


def validate_webhook_url(url: str) -> str:
    """Validate an outbound webhook destination. Raises ValueError when unsafe.

    Rules: HTTPS only; no credentials in the URL; no localhost or private, loopback,
    link-local or reserved IP literals (basic SSRF guard). DNS-based SSRF is not covered here
    and is listed as a remaining risk in SECURITY.md.
    """
    parts = urlsplit(url)
    if parts.scheme.lower() != "https":
        raise ValueError("Webhook URLs must use https://.")
    if parts.username or parts.password:
        raise ValueError("Webhook URLs must not embed credentials.")
    host = (parts.hostname or "").lower()
    if not host:
        raise ValueError("Webhook URL must include a host name.")
    if host in _BLOCKED_HOSTNAMES or host.endswith(".localhost"):
        raise ValueError("Webhook URL host is not allowed.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return url
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise ValueError("Webhook URL must not target private or reserved IP addresses.")
    return url


def _is_public_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_resolves_publicly(url: str) -> None:
    """Raise ValueError if the webhook host resolves to any private or reserved address.

    Run at delivery time, so a hostname that later points at an internal address is blocked
    at the moment of sending. DNS rebinding between this check and the connection is not
    fully prevented; egress filtering on the backend host remains the complete control.
    If the host does not resolve, the check passes and the HTTP request fails on its own.
    """
    host = urlsplit(url).hostname
    if not host:
        raise ValueError("Webhook URL must include a host name.")
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return
    for info in infos:
        address = str(info[4][0]).split("%", 1)[0]
        if not _is_public_address(ipaddress.ip_address(address)):
            raise ValueError("Webhook host resolves to a private or reserved address.")
