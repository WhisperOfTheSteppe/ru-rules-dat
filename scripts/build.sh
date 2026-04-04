#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/output"
TEMP_DIR="${REPO_ROOT}/tmp"
GITHUB_USER="WhisperOfTheSteppe"
REPO_NAME="ru-rules-dat"
BASE_URL="https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/release"

# Private subnets
PRIVATE_CIDRS=(
  "10.0.0.0/8"
  "172.16.0.0/12"
  "192.168.0.0/16"
  "127.0.0.0/8"
  "100.64.0.0/10"
  "169.254.0.0/16"
  "192.0.0.0/24"
  "192.0.2.0/24"
  "198.18.0.0/15"
  "198.51.100.0/24"
  "203.0.113.0/24"
  "224.0.0.0/4"
  "240.0.0.0/4"
  "255.255.255.255/32"
)

mkdir -p "$OUTPUT_DIR" "$TEMP_DIR"

echo "=== Step 1: Download RU IP ranges from ipdeny.com ==="
curl -fsSL -o "${TEMP_DIR}/ru-aggregated.zone" \
  "https://www.ipdeny.com/ipblocks/data/aggregated/ru-aggregated.zone"

RU_IP_COUNT=$(wc -l < "${TEMP_DIR}/ru-aggregated.zone")
echo "Downloaded ${RU_IP_COUNT} RU CIDR ranges"

echo "=== Step 2: Generate plain-text files ==="
# ru-ip.txt — plain CIDR list
cp "${TEMP_DIR}/ru-aggregated.zone" "${OUTPUT_DIR}/ru-ip.txt"

# ru-domains.txt — strip comments and empty lines
grep -v '^#' "${REPO_ROOT}/data/ru-direct-domains.txt" \
  | grep -v '^$' \
  | sed 's/[[:space:]]*$//' \
  > "${OUTPUT_DIR}/ru-domains.txt"

DOMAIN_COUNT=$(wc -l < "${OUTPUT_DIR}/ru-domains.txt")
echo "Processed ${DOMAIN_COUNT} domains"

echo "=== Step 3: Generate Shadowrocket formats ==="

# ru-ip-shadowrocket.list
awk '{print "IP-CIDR,"$0",no-resolve"}' "${OUTPUT_DIR}/ru-ip.txt" \
  > "${OUTPUT_DIR}/ru-ip-shadowrocket.list"

# ru-domains-shadowrocket.list
awk '{print "DOMAIN-SUFFIX,"$0}' "${OUTPUT_DIR}/ru-domains.txt" \
  > "${OUTPUT_DIR}/ru-domains-shadowrocket.list"

# private-ip-shadowrocket.list
{
  for cidr in "${PRIVATE_CIDRS[@]}"; do
    echo "IP-CIDR,${cidr},no-resolve"
  done
} > "${OUTPUT_DIR}/private-ip-shadowrocket.list"

# shadowrocket.conf — full config
cat > "${OUTPUT_DIR}/shadowrocket.conf" <<CONF
[General]
bypass-system = true
skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10, localhost, *.local
bypass-tun = 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.0.0.0/24, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255/32
dns-server = 8.8.8.8, 8.8.4.4, 1.1.1.1

[Rule]
# Russian domains on non-.ru TLDs -> DIRECT
RULE-SET,${BASE_URL}/ru-domains-shadowrocket.list,DIRECT

# Russian TLDs -> DIRECT
DOMAIN-SUFFIX,ru,DIRECT
DOMAIN-SUFFIX,su,DIRECT
DOMAIN-SUFFIX,xn--p1ai,DIRECT

# Russian IPs -> DIRECT
RULE-SET,${BASE_URL}/ru-ip-shadowrocket.list,DIRECT

# Private subnets -> DIRECT
RULE-SET,${BASE_URL}/private-ip-shadowrocket.list,DIRECT

# Everything else -> PROXY
FINAL,PROXY
CONF

echo "Shadowrocket files generated"

echo "=== Step 4: Generate geoip.dat ==="
PYTHON_CMD="python3"
command -v python3 &> /dev/null || PYTHON_CMD="python"

$PYTHON_CMD "${REPO_ROOT}/scripts/generate_geoip_dat.py" \
  "${OUTPUT_DIR}/ru-ip.txt" \
  "${OUTPUT_DIR}/geoip.dat"
echo "geoip.dat generated"

echo "=== Step 5: Generate sing-box .srs rule-sets ==="
SINGBOX_CMD="sing-box"
if ! command -v sing-box &> /dev/null; then
  if [ -f "${REPO_ROOT}/scripts/sing-box.exe" ]; then
    SINGBOX_CMD="${REPO_ROOT}/scripts/sing-box.exe"
  elif [ -f "${REPO_ROOT}/scripts/sing-box" ]; then
    SINGBOX_CMD="${REPO_ROOT}/scripts/sing-box"
  fi
fi

# Build IP rule-set JSON
$PYTHON_CMD - "${OUTPUT_DIR}/ru-ip.txt" "${TEMP_DIR}/ru-ip.json" <<'PYSCRIPT'
import json, sys
infile, outfile = sys.argv[1], sys.argv[2]
cidrs = [line.strip() for line in open(infile) if line.strip()]
json.dump({'version': 2, 'rules': [{'ip_cidr': cidrs}]}, open(outfile, 'w'), indent=2)
print(f'IP rule-set: {len(cidrs)} CIDRs')
PYSCRIPT
$SINGBOX_CMD rule-set compile "${TEMP_DIR}/ru-ip.json" -o "${OUTPUT_DIR}/ru-ip.srs"

# Build domain rule-set JSON
$PYTHON_CMD - "${OUTPUT_DIR}/ru-domains.txt" "${TEMP_DIR}/ru-domains.json" <<'PYSCRIPT'
import json, sys
infile, outfile = sys.argv[1], sys.argv[2]
domains = [line.strip() for line in open(infile) if line.strip()]
json.dump({'version': 2, 'rules': [{'domain_suffix': domains}]}, open(outfile, 'w'), indent=2)
print(f'Domain rule-set: {len(domains)} domains')
PYSCRIPT
$SINGBOX_CMD rule-set compile "${TEMP_DIR}/ru-domains.json" -o "${OUTPUT_DIR}/ru-domains.srs"

echo "sing-box .srs files generated"

echo "=== Step 6: Summary ==="
echo "Output files:"
ls -lh "${OUTPUT_DIR}/"
echo ""
echo "Build complete!"
