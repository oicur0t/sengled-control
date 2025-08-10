#!/usr/bin/env python3
"""
Sengled Cloud Service Rescue
===========================
Emergency replacement for down Sengled cloud services.

This will:
1. Intercept requests to dead Sengled servers
2. Provide the responses bulbs need to function
3. Enable local UDP control once bulbs are "satisfied"
"""

import json
import time
import threading
import socket
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

# Store intercepted requests and bulb info
intercepted_requests = []
active_bulbs = {}

class SengledCloudRescue:
    def __init__(self):
        self.app = app
        self.setup_routes()
        
    def setup_routes(self):
        """Set up all the cloud endpoints that bulbs might call"""
        
        @app.route('/life2/device/accessCloud.json', methods=['POST', 'GET'])
        def access_cloud():
            """Main cloud registration endpoint"""
            data = request.get_json() if request.method == 'POST' else {}
            
            log_request("accessCloud", data)
            
            # Standard success response based on working integrations
            response = {
                "info": "OK",
                "jsessionId": f"rescue_{int(time.time())}",
                "deviceUuid": data.get('deviceUuid', 'unknown'),
                "userId": data.get('userId', '618'),
                "productCode": data.get('productCode', 'wifielement'),
                "typeCode": data.get('typeCode', 'W31-N11'),
                "status": "active",
                "timestamp": int(time.time() * 1000),
                "serverTime": int(time.time() * 1000),
                "result": True,
                "code": 0,
                "message": "Device registered successfully"
            }
            
            # Track this bulb
            device_uuid = data.get('deviceUuid')
            if device_uuid:
                active_bulbs[device_uuid] = {
                    'registration_time': datetime.now(),
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'last_seen': datetime.now()
                }
                
                print(f"🎉 RESCUED BULB: {device_uuid} from {request.remote_addr}")
            
            return jsonify(response)
        
        @app.route('/jbalancer/new/bimqtt', methods=['POST', 'GET'])
        def mqtt_balancer():
            """MQTT broker information"""
            data = request.get_json() if request.method == 'POST' else {}
            log_request("mqtt_balancer", data)
            
            # Point to local MQTT broker (we'll set one up)
            response = {
                "info": "OK", 
                "inceptionAddr": f"ws://{get_local_ip()}:9001/mqtt",
                "mqttServer": {
                    "host": get_local_ip(),
                    "port": 1883,
                    "wsPort": 9001,
                    "path": "/mqtt"
                }
            }
            
            return jsonify(response)
        
        @app.route('/life2/server/getServerInfo.json', methods=['POST'])
        def get_server_info():
            """Server info endpoint"""
            data = request.get_json()
            log_request("getServerInfo", data)
            
            response = {
                "info": "OK",
                "inceptionAddr": f"ws://{get_local_ip()}:9001/mqtt",
                "serverTime": int(time.time() * 1000)
            }
            
            return jsonify(response)
        
        @app.route('/user/app/customer/v2/AuthenCross.json', methods=['POST'])
        def authen_cross():
            """Authentication endpoint"""
            data = request.get_json()
            log_request("AuthenCross", data)
            
            response = {
                "jsessionId": f"auth_{int(time.time())}",
                "info": "OK",
                "userId": data.get('user', 'rescued_user'),
                "timestamp": int(time.time() * 1000)
            }
            
            return jsonify(response)
        
        @app.route('/user/app/customer/isSessionTimeout.json', methods=['POST'])
        def session_timeout():
            """Session timeout check"""
            data = request.get_json()
            log_request("sessionTimeout", data)
            
            # Never timeout
            response = {
                "info": "OK",
                "timeout": False
            }
            
            return jsonify(response)
        
        @app.route('/life2/device/list.json', methods=['POST'])
        def device_list():
            """Device list endpoint"""
            data = request.get_json()
            log_request("deviceList", data)
            
            # Return list of rescued bulbs
            devices = []
            for uuid, info in active_bulbs.items():
                devices.append({
                    "deviceUuid": uuid,
                    "productCode": "wifielement",
                    "typeCode": "W31-N11",
                    "status": "online",
                    "attributes": {
                        "switch": 1,
                        "brightness": 100,
                        "colorTemperature": 4000
                    }
                })
            
            response = {
                "info": "OK",
                "deviceList": devices
            }
            
            return jsonify(response)
        
        @app.route('/api/status', methods=['GET'])
        def status():
            """Status page for monitoring"""
            return jsonify({
                "service": "Sengled Cloud Rescue",
                "status": "active",
                "rescued_bulbs": len(active_bulbs),
                "uptime": time.time(),
                "intercepted_requests": len(intercepted_requests)
            })
        
        @app.route('/api/bulbs', methods=['GET'])
        def list_bulbs():
            """List all rescued bulbs"""
            return jsonify(active_bulbs)
        
        @app.route('/', methods=['GET', 'POST'])
        def catch_all():
            """Catch any other requests"""
            data = request.get_json() if request.method == 'POST' else request.args
            log_request("unknown_endpoint", data, request.path)
            
            # Generic OK response
            return jsonify({"info": "OK", "status": "rescued"})

def log_request(endpoint, data, path=None):
    """Log all requests for analysis"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "path": path or request.path,
        "data": data,
        "ip": request.remote_addr,
        "user_agent": request.headers.get('User-Agent', ''),
        "method": request.method
    }
    
    intercepted_requests.append(entry)
    
    print(f"📡 [{datetime.now().strftime('%H:%M:%S')}] {endpoint}: {request.remote_addr}")
    if data:
        print(f"    Data: {json.dumps(data, indent=2)}")

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a dummy address to find local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "192.168.1.79"  # sooke-srv

def start_udp_test_server():
    """Background UDP server to test bulb responses"""
    def udp_server():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 9080))
        sock.settimeout(1)
        
        print("🔧 UDP test server started on port 9080")
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8')
                print(f"📨 UDP from {addr}: {message}")
                
                # Try to parse as JSON command
                try:
                    command = json.loads(message)
                    response = {"result": {"ret": 0}, "rescued": True}
                    sock.sendto(json.dumps(response).encode('utf-8'), addr)
                    print(f"📤 UDP response sent to {addr}")
                except:
                    # Send generic response
                    sock.sendto(b'{"result":{"ret":0}}', addr)
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"UDP server error: {e}")
    
    thread = threading.Thread(target=udp_server, daemon=True)
    thread.start()

def test_rescued_bulbs():
    """Test UDP control on rescued bulbs"""
    print("\n🧪 Testing rescued bulbs with UDP commands...")
    
    for device_uuid, info in active_bulbs.items():
        bulb_ip = info['ip']
        print(f"\nTesting {device_uuid} at {bulb_ip}...")
        
        commands = [
            {"func": "get_device_info", "param": {}},
            {"func": "set_device_switch", "param": {"switch": 1}},
            {"func": "set_device_brightness", "param": {"brightness": 50}},
        ]
        
        for command in commands:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(3)
                
                message = json.dumps(command).encode('utf-8')
                sock.sendto(message, (bulb_ip, 9080))
                
                response, addr = sock.recvfrom(1024)
                result = response.decode('utf-8')
                print(f"  ✅ {command['func']}: {result}")
                
            except Exception as e:
                print(f"  ❌ {command['func']}: {e}")
            finally:
                sock.close()

def main():
    print("🚨 SENGLED CLOUD RESCUE SERVICE")
    print("=" * 50)
    print("Emergency replacement for down Sengled cloud services")
    print("This will intercept bulb requests and provide needed responses")
    print()
    
    local_ip = get_local_ip()
    print(f"🌐 Local IP: {local_ip}")
    print(f"🔧 Cloud rescue server will run on: http://{local_ip}")
    print()
    print("📋 SETUP INSTRUCTIONS:")
    print("1. Configure your router/DNS to redirect Sengled domains to this IP:")
    print("   - ucenter.cloud.sengled.com")
    print("   - life2.cloud.sengled.com") 
    print("   - us-mqtt.cloud.sengled.com")
    print()
    print("2. Or use network interception/firewall rules")
    print("3. Watch for bulb rescue messages below")
    print("4. Once rescued, bulbs should respond to UDP commands")
    print()
    
    # Start background services
    start_udp_test_server()
    
    # Run the Flask app
    rescue = SengledCloudRescue()
    
    try:
        print(f"🚀 Starting rescue service on {local_ip}:8080...")
        app.run(host='0.0.0.0', port=80, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Rescue service stopped")
        
        if active_bulbs:
            print(f"\n📊 RESCUE SUMMARY:")
            print(f"Rescued {len(active_bulbs)} bulbs:")
            for uuid, info in active_bulbs.items():
                print(f"  • {uuid} at {info['ip']}")
            
            test_rescued_bulbs()

if __name__ == "__main__":
    main()
