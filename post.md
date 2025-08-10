 Reverse Engineering Sengled Wifi Bulb
Sengled Setup

[EDIT] I did it !!! u/FalconFour wanted a list of servers that sengled uses, I checked the decompiled app for servers and found a japanese one that is not dead and I was able to figure out the https response that the bulb needs so I can emulate it locally.

https://i.imgur.com/e7AVl56.png

https://i.imgur.com/eVwHwst.png

https://i.imgur.com/7j4DdSU.png
TL;DR

    If your bulb is already paired , you can control it using UDP commands (no encryption, no cloud).

    Wi-Fi setup for unpaired bulbs is nearly complete — but currently blocked by a missing response from a dead cloud URL.

    I cracked the RC4 encryption used during Wi-Fi setup (only the credential step is encrypted).

    I sniffed MQTT messages and analyzed the decompiled app to understand how commands are sent.

    I sniffed router traffic and discovered that Google Home controls the bulbs via local UDP.

    UDP works — I’ve successfully tested it using a simple Python script. You just need the bulb's local IP.

    I’ll keep updating this thread with more progress. If I get stuck, bored, or move on, I’ll dump everything I’ve got.

Hey everyone,

Just wanted to share a progress update for those trying to regain control of their Sengled Wi-Fi bulbs now that the cloud is dead.

In short: I’ve cracked the weak encryption used by Sengled, sniffed MQTT commands, and made significant progress on the Wi-Fi setup protocol. But there are still a few missing pieces.

Here’s what’s working:

    I cracked the RC4 encryption used to send Wi-Fi credentials to the bulb during setup. The key is hardcoded in the app as a Base64 string.

Wi-Fi Setup Flow (Full Breakdown)

When you plug in a new bulb:

    It starts an ad-hoc AP (a temporary Wi-Fi network) at 192.168.8.1

    The phone connects and talks to the bulb over UDP

Here’s the step-by-step:
Step 1: startConfigRequest

{
  "name": "startConfigRequest",
  "totalStep": 1,
  "curStep": 1,
  "payload": {
    "protocol": 1
  }
}

Response:

{
  "payload": {
    "mac": "AA:BB:CC:DD:EE:FF",
    "result": true
  }
}

Step 2: scanWifiRequest

{
  "name": "scanWifiRequest",
  "totalStep": 1,
  "curStep": 1,
  "payload": {}
}

(No direct response, but triggers scan)
Step 3: getAPListRequest

{
  "name": "getAPListRequest",
  "totalStep": 1,
  "curStep": 1,
  "payload": {}
}

Response:

It return the list of Wifi networks that the bulb detects.

{
  "payload": {
    "routers": [
      {
        "ssid": "MyWiFi",
        "bssid": "AA:BB:CC:DD:EE:FF",
        "signal": 85,
        "security": "WPA2"
      }
    ]
  }
}

Step 4: Re-handshake (same as Step 1)
Step 5: setParamsRequest (ENCRYPTED)

You, normally through the app, select the wifi network you want the bulb to connect to along with the WiFi password. It's sent back to the bulb but in a encrypted form. There also two url, normally they point to sengled servers but to take control we replace that with a custom server (in my test, I used my PC at that 192.168.0.100 ip and I run a HTTP server to see what the bulb is looking for.

Unencrypted form:

{
  "name": "setParamsRequest",
  "totalStep": 1,
  "curStep": 1,
  "payload": {
    "userID": "618",
    "appServerDomain": "http://192.168.1.100:80/life2/device/accessCloud.json",
    "jbalancerDomain": "http://192.168.1.100:80/jbalancer/new/bimqtt",
    "timeZone": "America/Chicago",
    "routerInfo": {
      "ssid": "MyWiFi",
      "password": "mypassword123"
    }
  }
}

This payload is encrypted using RC4 and then Base64-encoded.
Step 6: endConfigRequest

{
  "name": "endConfigRequest",
  "totalStep": 1,
  "curStep": 1,
  "payload": {}
}

Response:

{
  "payload": {
    "result": true
  }
}

After this, the bulb reboots and joins the LAN.
What Happens Next (HTTP Cloud Call)

Once connected to Wi-Fi, the bulb tries to POST to a cloud URL:

POST /life2/device/accessCloud.json
Host: 192.168.0.100
User-Agent: ESP32 HTTP Client/1.0
Content-Type: application/json

Body:

{
  "deviceUuid": "E8:DB:84:F9:BE:B4",
  "userId": "618",
  "productCode": "wifielement",
  "typeCode": "W31-N11"
}

This happens about 2 seconds after the bulb joins the network. I’ve redirected this request to my PC (192.168.0.100), which logs the request but doesn’t know what to return.

Because of that, the bulb retries for ~30 seconds, then gives up and resets to pairing mode. This is the main blocker right now. If anyone has the original cloud response captured, it could solve the issue entirely.
MQTT Firmware Upgrade

I also figured out how firmware upgrades are triggered through MQTT. It's done by sending a message to the following topic:

Topic:

wifibulb/80:A0:36:E1:8E:B8/update

Payload:

http://192.168.0.100/custom-firmware.bin

The bulb will attempt to download and flash this file directly.

That said, I haven’t tested whether firmware upgrades can be triggered through UDP — no evidence of that yet. I don't think I can actually flash anything right now because the Wi-Fi setup process is still incomplete until I solve the missing HTTP response step.
Example MQTT Message

Turn on and set Color Temperature:

Topic:

wifielement/80:A0:36:E1:8E:B8/update

Payload:

Os$[{"dn":"80:A0:36:E1:8E:B8","type":"colorTemperature","value":"2700","time":1662036404644},
    {"dn":"80:A0:36:E1:8E:B8","type":"switch","value":"1","time":1662036404644}]

Local UDP Control

Google Home still controls the bulb somehow. I sniffed the traffic and found out why:

UDP packets are sent directly to the bulb's LAN IP on port 9080. I’ve replicated this using a basic Python script.

Here’s one of the command to turn the bulb on:

{"func": "set_device_switch", "param": {"switch": 1}}

And to turn it off:

{"func": "set_device_switch", "param": {"switch": 0}}

Response:

{"result": {"ret": 0}}

No authentication, no encryption — it just works as long as you have the bulb’s IP.
Why This Matters

If we fully crack the setup process, we can bring these bulbs back to life. Once paired, they can be controlled via local UDP or MQTT — no cloud needed. That means:

    You can use them with Home Assistant via custom integrations or automations.

    Existing integrations like the official Sengled HA integration (which relied on the now-dead cloud) can be bypassed entirely.

    The bulbs become fully local, cloud-free smart lights.

I’m currently exploring both directions:

    Cloud emulation: To spoof the missing /accessCloud.json and prevent reset

    UDP-only control: For raw LAN control without worrying about cloud at all

If you’ve got old captures from a working setup (when the cloud was up), please share. That could unblock the last piece.

More updates if I don't burn out or get too annoyed, I’ll post what I've done so far.

This post was partially made possible thanks to this earlier Reddit thread: https://old.reddit.com/r/SengledUS/comments/1m09ndy/busting_the_wifi_bulbs_open_decoding_the_setup/ it helped pinpoint pieces of the Wi-Fi setup process.
