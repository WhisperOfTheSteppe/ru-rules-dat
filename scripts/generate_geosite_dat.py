#!/usr/bin/env python3
"""Generate geosite.dat (V2Ray protobuf format) from plain domain text files.

V2Ray GeoSite protobuf schema (proto3):
  message Domain {
    enum Type { Plain = 0; Regex = 1; Domain = 2; Full = 3; }
    Type type = 1;
    string value = 2;
  }
  message GeoSite { string country_code = 1; repeated Domain domain = 2; }
  message GeoSiteList { repeated GeoSite entry = 1; }
"""

import sys
import os

from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf.message_factory import GetMessageClass


def build_message_classes():
    """Build protobuf message classes dynamically from schema."""
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "geosite.proto"
    file_proto.package = "v2ray.core.app.router.routercommon"
    file_proto.syntax = "proto3"

    # Domain message with enum
    domain_desc = file_proto.message_type.add()
    domain_desc.name = "Domain"

    # Domain.Type enum
    type_enum = domain_desc.enum_type.add()
    type_enum.name = "Type"
    for name, number in [("Plain", 0), ("Regex", 1), ("RootDomain", 2), ("Full", 3)]:
        v = type_enum.value.add()
        v.name = name
        v.number = number

    f = domain_desc.field.add()
    f.name = "type"
    f.number = 1
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    f.type_name = ".v2ray.core.app.router.routercommon.Domain.Type"
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f = domain_desc.field.add()
    f.name = "value"
    f.number = 2
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

    # GeoSite message
    geosite_desc = file_proto.message_type.add()
    geosite_desc.name = "GeoSite"
    f = geosite_desc.field.add()
    f.name = "country_code"
    f.number = 1
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f = geosite_desc.field.add()
    f.name = "domain"
    f.number = 2
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    f.type_name = ".v2ray.core.app.router.routercommon.Domain"
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED

    # GeoSiteList message
    list_desc = file_proto.message_type.add()
    list_desc.name = "GeoSiteList"
    f = list_desc.field.add()
    f.name = "entry"
    f.number = 1
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    f.type_name = ".v2ray.core.app.router.routercommon.GeoSite"
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)

    GeoSiteList = GetMessageClass(
        pool.FindMessageTypeByName("v2ray.core.app.router.routercommon.GeoSiteList"))

    return GeoSiteList


def load_domains(filepath):
    """Load domains from text file (one per line, # comments)."""
    domains = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                domains.append(line)
    return domains


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <domains.txt> <output.dat>", file=sys.stderr)
        sys.exit(1)

    domains_file = sys.argv[1]
    output_file = sys.argv[2]

    GeoSiteList = build_message_classes()

    domains = load_domains(domains_file)
    print(f"  {len(domains)} domains loaded")

    geosite_list = GeoSiteList()

    # RU-DIRECT: custom Russian domains on non-.ru TLDs
    entry = geosite_list.entry.add()
    entry.country_code = "RU-DIRECT"
    for d in domains:
        domain = entry.domain.add()
        domain.type = 2  # RootDomain (match domain + all subdomains)
        domain.value = d

    # RU-TLD: Russian TLDs as regex
    tld_entry = geosite_list.entry.add()
    tld_entry.country_code = "RU-TLD"
    for tld in ["ru", "su", "xn--p1ai"]:
        domain = tld_entry.domain.add()
        domain.type = 2  # RootDomain
        domain.value = tld

    data = geosite_list.SerializeToString()
    with open(output_file, 'wb') as f:
        f.write(data)

    size_kb = os.path.getsize(output_file) / 1024
    print(f"  Written {output_file} ({size_kb:.1f} KB)")


if __name__ == '__main__':
    main()
