# ru-rules-dat

Routing rules for VPN/proxy clients optimized for Russia. Auto-updated weekly.

**Logic:** Russian IPs + Russian domains -> DIRECT, everything else -> PROXY.

## Files

All files are published to the [`release`](https://github.com/WhisperOfTheSteppe/ru-rules-dat/tree/release) branch.

| File | Format | Clients |
|------|--------|---------|
| `ru-ip.txt` | Plain CIDR | General, Podkop |
| `ru-domains.txt` | Plain domains | General, Podkop |
| `ru-ip-shadowrocket.list` | `IP-CIDR,x.x.x.x/y,no-resolve` | Shadowrocket |
| `ru-domains-shadowrocket.list` | `DOMAIN-SUFFIX,domain` | Shadowrocket |
| `private-ip-shadowrocket.list` | `IP-CIDR,x.x.x.x/y,no-resolve` | Shadowrocket |
| `shadowrocket.conf` | Full config | Shadowrocket |
| `geoip.dat` | V2Ray protobuf (`ru`, `private`) | Happ, V2RayNG |
| `ru-ip.srs` | sing-box binary rule-set | NekoBox, sing-box |
| `ru-domains.srs` | sing-box binary rule-set | NekoBox, sing-box |

## Usage

### Shadowrocket (iOS)

Import the ready-made config:

```
https://raw.githubusercontent.com/WhisperOfTheSteppe/ru-rules-dat/release/shadowrocket.conf
```

Settings -> Config -> Download Config From URL -> paste the link.

### Happ (iOS)

In routing settings, set the custom GeoIP URL:

```
https://raw.githubusercontent.com/WhisperOfTheSteppe/ru-rules-dat/release/geoip.dat
```

Routing rules:
- `geoip:ru` -> Direct
- `geoip:private` -> Direct
- Default -> Proxy

For domains: add entries from `ru-domains.txt` to DirectSites manually, or use the [Happ routing builder](https://routing.happ.su).

### V2RayNG (Android)

Replace the built-in geoip.dat:

1. Download `geoip.dat` from the release branch
2. Place it in `/Android/data/com.v2ray.ang/files/assets/`
3. In routing settings: `geoip:ru` -> Direct, `geoip:private` -> Direct

### NekoBox / sing-box (Android)

Use remote rule-sets in your sing-box config:

```json
{
  "route": {
    "rule_set": [
      {
        "tag": "ru-ip",
        "type": "remote",
        "format": "binary",
        "url": "https://raw.githubusercontent.com/WhisperOfTheSteppe/ru-rules-dat/release/ru-ip.srs"
      },
      {
        "tag": "ru-domains",
        "type": "remote",
        "format": "binary",
        "url": "https://raw.githubusercontent.com/WhisperOfTheSteppe/ru-rules-dat/release/ru-domains.srs"
      }
    ],
    "rules": [
      { "rule_set": "ru-ip", "outbound": "direct" },
      { "rule_set": "ru-domains", "outbound": "direct" },
      { "ip_is_private": true, "outbound": "direct" }
    ],
    "final": "proxy"
  }
}
```

## Data Sources

- **IP ranges:** [ipdeny.com](https://www.ipdeny.com/ipblocks/) (aggregated RU zones, updated daily)
- **Domains:** Hand-curated list of Russian services on non-.ru TLDs (`data/ru-direct-domains.txt`)
- **Private subnets:** RFC 1918 + RFC 5737 + RFC 6598

## Build

To run locally:

```bash
# Prerequisites: curl, awk, python3
# Optional: geoip CLI (Go), sing-box CLI

bash scripts/build.sh
# Output goes to ./output/
```

## Schedule

GitHub Action runs every Thursday at 06:00 UTC and on push to `data/`, `scripts/`, or `config/`.

## Contributing

To add domains: edit `data/ru-direct-domains.txt` and submit a PR.
