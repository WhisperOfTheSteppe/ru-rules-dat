#!/usr/bin/env python3
"""Generate geoip.dat (V2Ray protobuf format) from plain CIDR text files.

Uses google.protobuf library with dynamic message definitions
to produce XrayCore-compatible output.

V2Ray GeoIP protobuf schema (proto3):
  message CIDR { bytes ip = 1; uint32 prefix = 2; }
  message GeoIP { string country_code = 1; repeated CIDR cidr = 2; }
  message GeoIPList { repeated GeoIP entry = 1; }
"""

import sys
import socket
import os

from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import symbol_database
from google.protobuf.internal import decoder
from google.protobuf.internal import encoder


def build_message_classes():
    """Build protobuf message classes dynamically from schema."""
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "geoip.proto"
    file_proto.package = "v2ray.core.app.router"
    file_proto.syntax = "proto3"

    # CIDR message
    cidr_desc = file_proto.message_type.add()
    cidr_desc.name = "CIDR"
    f = cidr_desc.field.add()
    f.name = "ip"
    f.number = 1
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f = cidr_desc.field.add()
    f.name = "prefix"
    f.number = 2
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

    # GeoIP message
    geoip_desc = file_proto.message_type.add()
    geoip_desc.name = "GeoIP"
    f = geoip_desc.field.add()
    f.name = "country_code"
    f.number = 1
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f = geoip_desc.field.add()
    f.name = "cidr"
    f.number = 2
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    f.type_name = ".v2ray.core.app.router.CIDR"
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED

    # GeoIPList message
    list_desc = file_proto.message_type.add()
    list_desc.name = "GeoIPList"
    f = list_desc.field.add()
    f.name = "entry"
    f.number = 1
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    f.type_name = ".v2ray.core.app.router.GeoIP"
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED

    # Register in pool
    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)

    from google.protobuf.message_factory import GetMessageClass

    GeoIPList = GetMessageClass(
        pool.FindMessageTypeByName("v2ray.core.app.router.GeoIPList"))
    GeoIP = GetMessageClass(
        pool.FindMessageTypeByName("v2ray.core.app.router.GeoIP"))
    CIDR = GetMessageClass(
        pool.FindMessageTypeByName("v2ray.core.app.router.CIDR"))

    return GeoIPList, GeoIP, CIDR


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
        prefix = 32

    try:
        ip_bytes = socket.inet_aton(ip_str)
    except socket.error:
        try:
            ip_bytes = socket.inet_pton(socket.AF_INET6, ip_str)
        except socket.error:
            print(f"WARNING: skipping invalid CIDR: {cidr_str}", file=sys.stderr)
            return None

    return (ip_bytes, prefix)


def load_cidrs_from_file(filepath):
    """Load CIDRs from a text file (one per line)."""
    cidrs = []
    with open(filepath, 'r') as f:
        for line in f:
            result = parse_cidr(line)
            if result:
                cidrs.append(result)
    return cidrs


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

    GeoIPList, GeoIP, CIDR = build_message_classes()

    # Load RU CIDRs
    print(f"Loading RU CIDRs from {ru_ip_file}...")
    ru_cidrs_raw = load_cidrs_from_file(ru_ip_file)
    print(f"  {len(ru_cidrs_raw)} RU CIDRs loaded")

    # Build private CIDRs
    private_cidrs_raw = [(socket.inet_aton(ip), prefix) for ip, prefix in PRIVATE_CIDRS]
    print(f"  {len(private_cidrs_raw)} private CIDRs")

    # Build protobuf message
    geoip_list = GeoIPList()

    # RU entry
    ru_entry = geoip_list.entry.add()
    ru_entry.country_code = "RU"
    for ip_bytes, prefix in ru_cidrs_raw:
        cidr = ru_entry.cidr.add()
        cidr.ip = ip_bytes
        cidr.prefix = prefix

    # PRIVATE entry
    private_entry = geoip_list.entry.add()
    private_entry.country_code = "PRIVATE"
    for ip_bytes, prefix in private_cidrs_raw:
        cidr = private_entry.cidr.add()
        cidr.ip = ip_bytes
        cidr.prefix = prefix

    # Serialize and write
    data = geoip_list.SerializeToString()
    with open(output_file, 'wb') as f:
        f.write(data)

    size_kb = os.path.getsize(output_file) / 1024
    print(f"Written {output_file} ({size_kb:.1f} KB)")


if __name__ == '__main__':
    main()
