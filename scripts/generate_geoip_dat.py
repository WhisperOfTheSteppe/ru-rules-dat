#!/usr/bin/env python3
"""Generate geoip.dat (V2Ray protobuf format) from plain CIDR text files.

V2Ray GeoIP protobuf schema:
  message CIDR { bytes ip = 1; uint32 prefix = 2; }
  message GeoIP { string country_code = 1; repeated CIDR cidr = 2; }
  message GeoIPList { repeated GeoIP entry = 1; }

We encode manually to avoid needing .proto compilation.
"""

import struct
import sys
import socket
import os


def encode_varint(value):
    """Encode an integer as a protobuf varint."""
    parts = []
    while value > 0x7F:
        parts.append((value & 0x7F) | 0x80)
        value >>= 7
    parts.append(value & 0x7F)
    return bytes(parts)


def encode_field(field_number, wire_type, data):
    """Encode a protobuf field."""
    tag = encode_varint((field_number << 3) | wire_type)
    if wire_type == 2:  # length-delimited
        return tag + encode_varint(len(data)) + data
    elif wire_type == 0:  # varint
        return tag + encode_varint(data)
    return tag + data


def parse_cidr(cidr_str):
    """Parse a CIDR string into (ip_bytes, prefix_length)."""
    cidr_str = cidr_str.strip()
    if not cidr_str or cidr_str.startswith('#'):
        return None

    if '/' in cidr_str:
        ip_str, prefix_str = cidr_str.split('/', 1)
        prefix = int(prefix_str)
    else:
        ip_str = cidr_str
        prefix = 32  # single IP

    try:
        ip_bytes = socket.inet_aton(ip_str)
    except socket.error:
        try:
            ip_bytes = socket.inet_pton(socket.AF_INET6, ip_str)
        except socket.error:
            print(f"WARNING: skipping invalid CIDR: {cidr_str}", file=sys.stderr)
            return None

    return (ip_bytes, prefix)


def encode_cidr(ip_bytes, prefix):
    """Encode a CIDR as protobuf CIDR message."""
    msg = encode_field(1, 2, ip_bytes)  # ip
    msg += encode_field(2, 0, prefix)   # prefix
    return msg


def encode_geoip(country_code, cidrs):
    """Encode a GeoIP entry."""
    msg = encode_field(1, 2, country_code.encode('utf-8'))  # country_code
    for ip_bytes, prefix in cidrs:
        cidr_msg = encode_cidr(ip_bytes, prefix)
        msg += encode_field(2, 2, cidr_msg)  # cidr (repeated)
    return msg


def encode_geoip_list(entries):
    """Encode the GeoIPList."""
    msg = b''
    for country_code, cidrs in entries:
        geoip_msg = encode_geoip(country_code, cidrs)
        msg += encode_field(1, 2, geoip_msg)  # entry (repeated)
    return msg


def load_cidrs_from_file(filepath):
    """Load CIDRs from a text file (one per line)."""
    cidrs = []
    with open(filepath, 'r') as f:
        for line in f:
            result = parse_cidr(line)
            if result:
                cidrs.append(result)
    return cidrs


# Private subnets (RFC 1918, RFC 5737, RFC 6598, etc.)
PRIVATE_CIDRS = [
    ("10.0.0.0", 8),
    ("100.64.0.0", 10),
    ("127.0.0.0", 8),
    ("169.254.0.0", 16),
    ("172.16.0.0", 12),
    ("192.0.0.0", 24),
    ("192.0.2.0", 24),
    ("192.168.0.0", 16),
    ("198.18.0.0", 15),
    ("198.51.100.0", 24),
    ("203.0.113.0", 24),
    ("224.0.0.0", 4),
    ("240.0.0.0", 4),
    ("255.255.255.255", 32),
]


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <ru-ip.txt> <output.dat>", file=sys.stderr)
        sys.exit(1)

    ru_ip_file = sys.argv[1]
    output_file = sys.argv[2]

    # Load RU CIDRs
    print(f"Loading RU CIDRs from {ru_ip_file}...")
    ru_cidrs = load_cidrs_from_file(ru_ip_file)
    print(f"  {len(ru_cidrs)} RU CIDRs loaded")

    # Build private CIDRs
    private_cidrs = [(socket.inet_aton(ip), prefix) for ip, prefix in PRIVATE_CIDRS]
    print(f"  {len(private_cidrs)} private CIDRs")

    # Encode
    entries = [
        ("RU", ru_cidrs),
        ("PRIVATE", private_cidrs),
    ]
    data = encode_geoip_list(entries)

    # Write
    with open(output_file, 'wb') as f:
        f.write(data)

    size_kb = os.path.getsize(output_file) / 1024
    print(f"Written {output_file} ({size_kb:.1f} KB)")


if __name__ == '__main__':
    main()
