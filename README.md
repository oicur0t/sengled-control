# Sengled WiFi Bulb Rescue Project

## WARNING, THIS HAS NOT BEEN SUCCESSFULLY TESTED YET. THIS IS ALPHA STAGE AT BEST.

## Overview

This project provides emergency local control for Sengled WiFi bulbs when the official cloud service is down or unreliable. It implements a local cloud service emulator and UDP control system, allowing you to regain control of your smart bulbs without dependence on Sengled's servers.

## Background

Sengled's cloud service has experienced significant outages, leaving users unable to control their WiFi bulbs. This project was created to address that exact problem by:

1. **Emulating Sengled's cloud services** locally to satisfy bulb registration requirements
2. **Enabling direct UDP control** of bulbs on your local network
3. **Providing MongoDB integration** for advanced automation and logging
4. **Supporting the complete setup process** for new/factory reset bulbs

## Credits

This project builds upon excellent reverse engineering work by:

- **[u/Skodd](https://www.reddit.com/user/Skodd/)** - Original reverse engineering of Sengled WiFi bulb protocol ([Reddit Post](https://www.reddit.com/r/SengledUS/comments/1mi4oc1/reverse_engineering_sengled_wifi_bulb/))
- **[WebThingsIO/sengled-adapter](https://github.com/WebThingsIO/sengled-adapter/blob/master/pkg/client.py)** - Cloud API patterns and endpoint documentation
- **[jfarmer08/ha-sengledapi](https://github.com/jfarmer08/ha-sengledapi)** - Additional API response format examples

## Features

- ✅ **Local cloud service emulation** - Replace dead Sengled servers
- ✅ **Direct UDP control** - No cloud dependency for paired bulbs  
- ✅ **Complete setup process** - Set up new bulbs pointing to your local server
- ✅ **MongoDB integration** - Store device states, scenes, and telemetry
- ✅ **Network discovery** - Find and test bulbs on your network
- ✅ **Web API** - RESTful endpoints for automation systems
- ✅ **Home Assistant ready** - Easy integration with HA and other platforms

## Quick Start

### 1. Rescue Already-Paired Bulbs

If your bulbs were previously working but are now orphaned due to cloud outage:

```bash
# Install dependencies
sudo apt install python3-flask python3-requests

# Run the rescue server
sudo python3 sengled_cloud_rescue.py
```

Configure your router to redirect these domains to your server IP:
- `ucenter.cloud.sengled.com`
- `life2.cloud.sengled.com`
- `us-mqtt.cloud.sengled.com`

Watch for `🎉 RESCUED BULB` messages, then test UDP control on the rescued bulb IPs.

### 2. Test UDP Control

For bulbs that are already connected to WiFi:

```bash
# Find bulbs on your network
python3 debug_bulb.py

# Test specific bulb (replace with actual IP)
python3 -c "
import socket, json
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5)
cmd = {'func': 'set_device_switch', 'param': {'switch': 1}}
sock.sendto(json.dumps(cmd).encode(), ('192.168.1.70', 9080))
print(sock.recvfrom(1024))
"
```

### 3. Setup New Bulbs

For factory reset bulbs or new installations:

```bash
# Start cloud emulator
python3 sengled_cloud_emulator.py

# Use setup helper (requires RC4 key from Sengled app)
python3 sengled_setup_helper.py
```

## File Overview

| File | Purpose |
|------|---------|
| `sengled_cloud_rescue.py` | **Main rescue server** - Comprehensive cloud service replacement |
| `debug_bulb.py` | **Network discovery** - Find and test bulbs on your network |
| `sengled_cloud_emulator.py` | **Simple cloud emulator** - Basic registration endpoints |
| `sengled_setup_helper.py` | **Bulb setup** - Configure new bulbs to use local server |
| `sengled_mongodb_system.py` | **MongoDB integration** - Advanced automation and logging |

## How It Works

### The Problem
Sengled WiFi bulbs depend on cloud services for:
1. Initial registration after connecting to WiFi
2. MQTT broker information for real-time control
3. Session management and authentication

When these services are down, bulbs become unresponsive even on your local network.

### The Solution
This project provides local replacements for all critical cloud endpoints:

1. **`/life2/device/accessCloud.json`** - Device registration
2. **`/jbalancer/new/bimqtt`** - MQTT broker information  
3. **`/user/app/customer/v2/AuthenCross.json`** - Authentication
4. **UDP port 9080** - Direct local control commands

Once bulbs successfully register with the local server, they respond to UDP commands like:
```json
{"func": "set_device_switch", "param": {"switch": 1}}
{"func": "set_device_brightness", "param": {"brightness": 75}}
{"func": "set_device_color_temp", "param": {"color_temp": 4000}}
```

## Network Setup

### DNS Redirect Method (Recommended)
Configure your router to redirect Sengled domains to your local server:
- Router Admin → DNS Settings → Static DNS entries
- Point `*.cloud.sengled.com` to your server IP

### Firewall/iptables Method
```bash
# Redirect traffic to local server
sudo iptables -t nat -A OUTPUT -d 54.230.159.114 -p tcp --dport 80 -j DNAT --to-destination 192.168.1.79:80
sudo iptables -t nat -A PREROUTING -d 54.230.159.114 -p tcp --dport 80 -j DNAT --to-destination 192.168.1.79:80
```

## MongoDB Integration

For advanced users, the MongoDB integration provides:

```python
from sengled_mongodb_system import SengledMongoDBSystem

# Connect to MongoDB Atlas or local instance
system = SengledMongoDBSystem("mongodb://localhost:27017")

# Send commands and log automatically
system.send_command_to_bulb(device_uuid, {
    "func": "set_device_brightness", 
    "param": {"brightness": 50}
})

# Execute scenes
system.execute_scene("movie_night")

# Query device history
commands = system.commands.find({"device_uuid": device_uuid})
```

## Supported Bulb Models

Based on community testing:
- ✅ **W31-N11** (Element Classic WiFi)
- ✅ **W31-N11HDL** (Element Classic WiFi Dimmable)
- ✅ **E21-N1EA** (Element Color Plus A19)
- ⚠️ **Other models** - May work but untested

## Troubleshooting

### No UDP Response
1. Verify bulb is connected to WiFi (check router device list)
2. Ensure bulb completed cloud registration step
3. Try power cycling the bulb
4. Check firewall isn't blocking UDP port 9080

### Bulbs Not Registering
1. Confirm DNS redirect is working: `nslookup ucenter.cloud.sengled.com`
2. Check server logs for incoming requests
3. Verify bulbs can reach your server IP
4. Try factory reset and manual setup process

### Network Discovery Issues
1. Ensure you're on the same network/subnet as bulbs
2. Try scanning different IP ranges (192.168.0.x vs 192.168.1.x)
3. Check for network segmentation/VLANs blocking discovery

## Contributing

This project addresses an ongoing issue affecting many Sengled users. Contributions welcome:

- Test additional bulb models and report compatibility
- Improve setup process automation
- Add support for color bulbs and advanced features
- Enhance MongoDB schema and automation capabilities

## Security Notes

- This project runs a local HTTP server that responds to bulb requests
- Only run on trusted networks
- Consider firewall rules to limit access to the rescue server
- The setup process requires extracting encryption keys from the Sengled app

## License

MIT License - Feel free to use, modify, and distribute.

## Disclaimer

This is an unofficial project created to address service outages. Use at your own risk. This project does not modify bulb firmware or void warranties - it only provides alternative cloud services that bulbs can connect to voluntarily.
