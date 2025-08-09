
import socket
import json
import base64
from Crypto.Cipher import ARC4
import time

class SengledSetupHelper:
    def __init__(self, bulb_ip="192.168.8.1", bulb_port=9080):
        self.bulb_ip = bulb_ip
        self.bulb_port = bulb_port
        
        # RC4 key from the Reddit post (Base64 encoded in app)
        # You'll need to extract this from the decompiled app
        self.rc4_key = "SengledSetupKey123"  # Replace with actual key
        
    def send_udp_command(self, command):
        """Send UDP command to bulb during setup"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        try:
            message = json.dumps(command).encode('utf-8')
            sock.sendto(message, (self.bulb_ip, self.bulb_port))
            
            response, addr = sock.recvfrom(4096)
            return json.loads(response.decode('utf-8'))
        except Exception as e:
            return {"error": str(e)}
        finally:
            sock.close()
    
    def encrypt_setup_params(self, params):
        """Encrypt setup parameters using RC4"""
        # Convert params to JSON string
        params_json = json.dumps(params)
        
        # Encrypt with RC4
        cipher = ARC4.new(self.rc4_key.encode())
        encrypted = cipher.encrypt(params_json.encode())
        
        # Base64 encode the result
        return base64.b64encode(encrypted).decode()
    
    def setup_bulb(self, wifi_ssid, wifi_password, server_ip):
        """Complete bulb setup process"""
        
        print("Step 1: Starting config request...")
        result = self.send_udp_command({
            "name": "startConfigRequest",
            "totalStep": 1,
            "curStep": 1,
            "payload": {"protocol": 1}
        })
        print(f"Result: {result}")
        
        if not result.get('payload', {}).get('result'):
            return {"error": "Failed to start config"}
        
        bulb_mac = result['payload']['mac']
        print(f"Bulb MAC: {bulb_mac}")
        
        print("\nStep 2: Scanning for WiFi networks...")
        self.send_udp_command({
            "name": "scanWifiRequest",
            "totalStep": 1,
            "curStep": 1,
            "payload": {}
        })
        
        time.sleep(3)  # Wait for scan
        
        print("\nStep 3: Getting AP list...")
        ap_result = self.send_udp_command({
            "name": "getAPListRequest",
            "totalStep": 1,
            "curStep": 1,
            "payload": {}
        })
        print(f"Available networks: {ap_result}")
        
        print("\nStep 4: Re-handshake...")
        self.send_udp_command({
            "name": "startConfigRequest",
            "totalStep": 1,
            "curStep": 1,
            "payload": {"protocol": 1}
        })
        
        print("\nStep 5: Setting WiFi parameters...")
        
        # Prepare setup parameters
        setup_params = {
            "userID": "618",
            "appServerDomain": f"http://{server_ip}:80/life2/device/accessCloud.json",
            "jbalancerDomain": f"http://{server_ip}:80/jbalancer/new/bimqtt",
            "timeZone": "America/Chicago",
            "routerInfo": {
                "ssid": wifi_ssid,
                "password": wifi_password
            }
        }
        
        # Encrypt the parameters
        encrypted_params = self.encrypt_setup_params(setup_params)
        
        result = self.send_udp_command({
            "name": "setParamsRequest",
            "totalStep": 1,
            "curStep": 1,
            "payload": encrypted_params
        })
        print(f"Setup params result: {result}")
        
        print("\nStep 6: Ending config...")
        end_result = self.send_udp_command({
            "name": "endConfigRequest",
            "totalStep": 1,
            "curStep": 1,
            "payload": {}
        })
        print(f"End config result: {end_result}")
        
        if end_result.get('payload', {}).get('result'):
            print(f"\n✅ Setup complete! Bulb should reboot and connect to WiFi.")
            print(f"📡 Bulb will call: http://{server_ip}:80/life2/device/accessCloud.json")
            print(f"🏠 After registration, bulb will be controllable via UDP on your main network")
            return {"success": True, "mac": bulb_mac}
        else:
            return {"error": "Setup failed at end config step"}

# Usage example
if __name__ == "__main__":
    setup = SengledSetupHelper()
    
    # Replace with your values
    result = setup.setup_bulb(
        wifi_ssid="YourWiFiName",
        wifi_password="YourWiFiPassword", 
        server_ip="192.168.1.100"  # IP where cloud emulator is running
    )
    
    print(f"\nFinal result: {result}")
