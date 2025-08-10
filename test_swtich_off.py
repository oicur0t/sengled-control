#!/usr/bin/env python3
"""
Send switch off command to all bulb IPs. This uses my IP addresses, update to use your known bulb IPs.
"""

import socket
import json

def send_switch_command(ip, switch_value):
    """Send switch command to bulb"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        
        command = {"func": "set_device_switch", "param": {"switch": switch_value}}
        message = json.dumps(command).encode('utf-8')
        
        print(f"Sending to {ip}: {command}")
        sock.sendto(message, (ip, 9080))
        
        try:
            response, addr = sock.recvfrom(1024)
            response_text = response.decode('utf-8', errors='ignore')
            print(f"✅ {ip}: {response_text}")
            return True, response_text
        except socket.timeout:
            print(f"❌ {ip}: No response (timeout)")
            return False, "timeout"
            
    except Exception as e:
        print(f"❌ {ip}: Error - {e}")
        return False, str(e)
    finally:
        sock.close()

def main():
    bulb_ips = [
        "192.168.1.78",
        "192.168.1.67", 
        "192.168.1.70"
    ]
    
    print("🔴 SENDING SWITCH OFF COMMAND TO ALL BULBS")
    print("=" * 50)
    print('Command: {"func": "set_device_switch", "param": {"switch": 0}}')
    print("Port: 9080 UDP")
    print()
    
    results = {}
    
    for ip in bulb_ips:
        success, response = send_switch_command(ip, 0)
        results[ip] = (success, response)
    
    print(f"\n📊 RESULTS SUMMARY")
    print("=" * 20)
    
    working = [ip for ip, (success, _) in results.items() if success]
    
    if working:
        print(f"✅ Responded: {working}")
    else:
        print("❌ No bulbs responded to switch command")
        print("💡 This confirms bulbs need cloud registration first")
        print("   Run: python3 sengled_cloud_rescue.py")

if __name__ == "__main__":
    main()
