## Aug 10
I am not able to get any traffic to show to/from my bulbs, however they do connect to my wifi and declare themselves to the router as Sengled Bulbs.

### Currently
SSL Certs are expired as of Aug 4th.

A quick test:

Command:
data = {
      'dn': self.uuid,           # Device UUID
      'type': 'switch',
      'value': '1' if on else '0',
      'time': int(time.time() * 1000),
  }

Bash(cd "/Volumes/Crucial X9/Nextcloud/dev/git/segled/sengled-control" &&
      python3 test_switch_off.py)
  ⎿  🔴 SENDING SWITCH OFF COMMAND TO ALL BULBS                    
     ==================================================
     Command: {"func": "set_device_switch", "param": {"switch": 0}}
     … +17 lines (ctrl+r to expand)

⏺ ❌ No bulbs responded to the switch off command. This confirms that expired
  SSL certificates have broken cloud registration, preventing local UDP
  control.

  The bulbs are waiting for successful cloud registration before they'll
  respond to UDP commands on port 9080.

This suggests that UDP command will not work while they cannot connect to Sengled.

I am reviewing: https://www.reddit.com/r/SengledUS/comments/1mky9lz/expired_web_certificate/
However I am not sure that bulbs will suddenly respond in this scenario without re-registration.

## Completed
I am trying to review the SSL certs for all IPs on the Sengled servers and to verify their state. I have seen reports that you can us Home Automation to bypass cert issues. 
