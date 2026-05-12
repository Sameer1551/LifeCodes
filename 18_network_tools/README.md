# Networking & Internet Tools

A collection of 10 command-line utilities for network operations, web testing, and internet utilities.

## Installation

```bash
pip install -r requirements.txt
```

## Tools

### 21. website_status_checker.py

Check uptime and HTTP status of websites.

```bash
# Check single URL
python website_status_checker.py -u https://google.com

# Check multiple URLs from file
python website_status_checker.py -f urls.txt

# Output as JSON
python website_status_checker.py -u https://google.com --json

# Custom timeout
python website_status_checker.py -u https://google.com --timeout 30
```

**Options:**
- `-u/--url`: URL to check
- `-f/--file`: File with URLs (one per line)
- `--timeout`: Request timeout in seconds (default: 10)
- `--no-redirects`: Don't follow redirects
- `--no-verify-ssl`: Skip SSL verification
- `--json`: JSON output

---

### 22. port_scanner.py

Scan open ports on a host.

```bash
# Scan common ports
python port_scanner.py -H localhost

# Scan specific port range
python port_scanner.py -H example.com -p 1-1000

# Scan specific ports
python port_scanner.py -H example.com -p 80,443,22,21

# Scan all ports
python port_scanner.py -H example.com --all

# Faster scanning
python port_scanner.py -H example.com --threads 200
```

**Options:**
- `-H/--host`: Target host or IP (required)
- `-p/--ports`: Port range (default: 1-1024)
- `--timeout`: Connection timeout (default: 1.0)
- `--threads`: Number of threads (default: 100)
- `--common`: Scan only common ports (1-1024)
- `--all`: Scan all ports (1-65535)
- `--json`: JSON output

---

### 23. dns_lookup_tool.py

Resolve domain names to IP addresses and DNS records.

```bash
# Basic lookup
python dns_lookup_tool.py -d google.com

# Specific record types
python dns_lookup_tool.py -d google.com -t MX NS

# All record types
python dns_lookup_tool.py -d google.com --all

# Reverse lookup (IP to domain)
python dns_lookup_tool.py -i 8.8.8.8 --reverse
```

**Options:**
- `-d/--domain`: Domain to lookup
- `-i/--ip`: IP for reverse lookup
- `-t/--type`: Record types (A, AAAA, MX, NS, TXT, CNAME, SOA, SRV)
- `--reverse`: Perform reverse DNS lookup
- `--all`: Query all record types
- `--json`: JSON output

---

### 24. ip_geolocation.py

Find geographic location of an IP address.

```bash
# Look up specific IP
python ip_geolocation.py -i 8.8.8.8

# Get your public IP location
python ip_geolocation.py --my-ip

# Look up multiple IPs from file
python ip_geolocation.py -f ips.txt
```

**Options:**
- `-i/--ip`: IP address to locate
- `-f/--file`: File with IP addresses
- `--my-ip`: Get location of your public IP
- `--json`: JSON output

---

### 25. internet_speed_test.py

Test internet download and upload speeds.

```bash
# Full speed test
python internet_speed_test.py

# Test only download
python internet_speed_test.py --download

# Test only upload
python internet_speed_test.py --upload

# Test only ping
python internet_speed_test.py --ping

# List available servers
python internet_speed_test.py --list-servers
```

**Options:**
- `--download`: Test download speed only
- `--upload`: Test upload speed only
- `--ping`: Test ping only
- `--server`: Specific server ID to use
- `--list-servers`: List available servers
- `--json`: JSON output

---

### 26. url_metadata_fetcher.py

Fetch title, description, and Open Graph data from URLs.

```bash
# Fetch metadata from single URL
python url_metadata_fetcher.py -u https://example.com

# Fetch from multiple URLs
python url_metadata_fetcher.py -f urls.txt

# Custom timeout
python url_metadata_fetcher.py -u https://example.com --timeout 15
```

**Options:**
- `-u/--url`: URL to fetch metadata from
- `-f/--file`: File with URLs
- `--timeout`: Request timeout (default: 10)
- `--json`: JSON output

**Extracted Data:**
- Title, description, H1
- Open Graph tags (og:title, og:description, og:image)
- Twitter Card tags
- Favicon, canonical URL

---

### 27. http_request_tester.py

Test REST APIs and make HTTP requests.

```bash
# GET request
python http_request_tester.py -u https://api.example.com/users

# POST request with JSON body
python http_request_tester.py -u https://api.example.com/users -m POST \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}'

# With Bearer token
python http_request_tester.py -u https://api.example.com/users --bearer YOUR_TOKEN

# With Basic auth
python http_request_tester.py -u https://api.example.com/users --auth user:pass

# Save response to file
python http_request_tester.py -u https://api.example.com/users -o response.json
```

**Options:**
- `-u/--url`: Request URL (required)
- `-m/--method`: HTTP method (GET, POST, PUT, DELETE, PATCH)
- `-H/--header`: Request headers (key:value, can repeat)
- `-d/--data`: Request body
- `--auth`: Basic auth (username:password)
- `--bearer`: Bearer token
- `--timeout`: Request timeout (default: 30)
- `-o/--output`: Save response to file
- `--json-output`: Full result as JSON

---

### 28. network_latency_checker.py

Ping servers and measure network latency.

```bash
# Ping a host
python network_latency_checker.py -H google.com

# Ping multiple hosts
python network_latency_checker.py -f hosts.txt

# TCP ping (connect to port)
python network_latency_checker.py -H example.com --tcp --port 443

# Custom ping count
python network_latency_checker.py -H google.com -c 10
```

**Options:**
- `-H/--host`: Host to ping
- `-f/--file`: File with hosts
- `-c/--count`: Number of packets (default: 4)
- `--timeout`: Timeout per ping (default: 2)
- `--tcp`: Use TCP ping instead of ICMP
- `--port`: Port for TCP ping (default: 80)
- `--json`: JSON output

---

### 29. proxy_checker.py

Validate and test proxy servers.

```bash
# Check single proxy
python proxy_checker.py -p http://proxy.example.com:8080

# Check SOCKS proxy
python proxy_checker.py -p socks5://proxy.example.com:1080

# Check proxies from file
python proxy_checker.py -f proxies.txt

# Custom test URL
python proxy_checker.py -p http://proxy:8080 --test-url http://example.com
```

**Options:**
- `-p/--proxy`: Proxy URL (http://host:port or socks5://host:port)
- `-f/--file`: File with proxy URLs
- `--test-url`: URL to test against
- `--timeout`: Request timeout (default: 10)
- `--json`: JSON output

---

### 30. download_manager.py

Multi-thread file downloader.

```bash
# Download single file
python download_manager.py -u https://example.com/file.zip -o file.zip

# Download with multiple threads
python download_manager.py -u https://example.com/file.zip --threads 8

# Download multiple files
python download_manager.py -f urls.txt -d downloads/

# Custom chunk size
python download_manager.py -u https://example.com/file.zip --chunk-size 5
```

**Options:**
- `-u/--url`: URL to download
- `-o/--output`: Output file path
- `-f/--file`: File with URLs
- `-d/--directory`: Output directory for batch downloads
- `--threads`: Threads per file (default: 4)
- `--chunk-size`: Chunk size in MB (default: 1)
- `--timeout`: Request timeout (default: 30)
- `--json`: JSON output

---

## Dependencies

```
requests>=2.31.0      # HTTP requests
aiohttp>=3.9.0        # Async HTTP
dnspython>=2.4.0      # DNS lookups
beautifulsoup4>=4.12.0 # HTML parsing
lxml>=4.9.0           # Parser for BeautifulSoup
speedtest-cli>=2.1.0  # Speed testing
tqdm>=4.66.0          # Progress bars
urllib3>=2.0.0        # URL handling
```

## Notes

- All tools support `--json` for machine-readable output
- All network operations have configurable timeouts
- Free/public APIs are used where possible (no API keys required)
- `speedtest-cli` requires internet access to speedtest.net servers
- `port_scanner.py` requires ICMP ping support (may need admin/root for some scans)

## License

MIT License