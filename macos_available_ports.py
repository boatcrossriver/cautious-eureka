#!/usr/bin/env python3
"""List ports that are available to bind on macOS.

The script tests availability by attempting to bind sockets. That is a better
signal than only checking process tables because the kernel is the final judge
of whether a new server can listen on a port.
"""

from __future__ import annotations

import argparse
import json
import socket
from collections.abc import Iterable


MIN_PORT = 1
MAX_PORT = 65535


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assess which local macOS ports are available to bind."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host/interface to test. Use 0.0.0.0 for all IPv4 interfaces.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=MIN_PORT,
        help=f"First port to scan. Default: {MIN_PORT}.",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=MAX_PORT,
        help=f"Last port to scan. Default: {MAX_PORT}.",
    )
    parser.add_argument(
        "--protocol",
        choices=("tcp", "udp", "both"),
        default="tcp",
        help="Protocol to test. Default: tcp.",
    )
    parser.add_argument(
        "--expand",
        action="store_true",
        help="Print every available port instead of compact ranges.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    return parser.parse_args()


def validate_port_range(start: int, end: int) -> None:
    if start < MIN_PORT or end > MAX_PORT:
        raise SystemExit(f"Ports must be between {MIN_PORT} and {MAX_PORT}.")
    if start > end:
        raise SystemExit("--start must be less than or equal to --end.")


def socket_family_for_host(host: str) -> socket.AddressFamily:
    try:
        info = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SystemExit(f"Could not resolve host {host!r}: {exc}") from exc

    if not info:
        raise SystemExit(f"Could not resolve host {host!r}.")

    return info[0][0]


def can_bind(host: str, port: int, family: socket.AddressFamily, protocol: str) -> bool:
    socket_type = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM

    try:
        with socket.socket(family, socket_type) as candidate:
            candidate.bind((host, port))
            if protocol == "tcp":
                candidate.listen(1)
            return True
    except OSError:
        return False


def available_ports(
    host: str,
    start: int,
    end: int,
    family: socket.AddressFamily,
    protocol: str,
) -> list[int]:
    return [
        port
        for port in range(start, end + 1)
        if can_bind(host, port, family, protocol)
    ]


def compact_ranges(ports: Iterable[int]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    previous: int | None = None

    for port in ports:
        if start is None:
            start = previous = port
            continue

        if previous is not None and port == previous + 1:
            previous = port
            continue

        ranges.append((start, previous if previous is not None else start))
        start = previous = port

    if start is not None:
        ranges.append((start, previous if previous is not None else start))

    return ranges


def format_ranges(ranges: Iterable[tuple[int, int]]) -> list[str]:
    return [str(start) if start == end else f"{start}-{end}" for start, end in ranges]


def scan_protocol(
    host: str,
    start: int,
    end: int,
    family: socket.AddressFamily,
    protocol: str,
) -> dict[str, object]:
    ports = available_ports(host, start, end, family, protocol)
    ranges = compact_ranges(ports)
    return {
        "protocol": protocol,
        "available_count": len(ports),
        "available_ports": ports,
        "available_ranges": format_ranges(ranges),
    }


def main() -> None:
    args = parse_args()
    validate_port_range(args.start, args.end)

    family = socket_family_for_host(args.host)
    protocols = ("tcp", "udp") if args.protocol == "both" else (args.protocol,)
    results = [
        scan_protocol(args.host, args.start, args.end, family, protocol)
        for protocol in protocols
    ]

    output = {
        "host": args.host,
        "start": args.start,
        "end": args.end,
        "results": results,
    }

    if args.json:
        print(json.dumps(output, indent=2))
        return

    print(f"Host: {args.host}")
    print(f"Scanned ports: {args.start}-{args.end}")
    for result in results:
        protocol = str(result["protocol"]).upper()
        print()
        print(f"{protocol} available ports: {result['available_count']}")
        values = result["available_ports"] if args.expand else result["available_ranges"]
        print("\n".join(str(value) for value in values) or "None")


if __name__ == "__main__":
    main()
