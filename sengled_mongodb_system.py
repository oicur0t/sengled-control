
from pymongo import MongoClient
from datetime import datetime, timezone
import threading
import socket
import json
import time
from sengled_cloud_emulator import registered_devices

class SengledMongoDBSystem:
    def __init__(self, mongodb_uri: str, database_name: str = "sengled_home"):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        
        # Collections
        self.devices = self.db.devices
        self.commands = self.db.commands
        self.telemetry = self.db.telemetry
        self.scenes = self.db.scenes
        self.schedules = self.db.schedules
        
        # Active bulb connections
        self.active_bulbs = {}
        
        # Start background discovery
        self.discovery_thread = threading.Thread(target=self._discover_bulbs, daemon=True)
        self.discovery_thread.start()
    
    def _discover_bulbs(self):
        """Background thread to discover and register bulbs"""
        while True:
            try:
                # Check for newly registered devices from cloud emulator
                for device_uuid, device_info in registered_devices.items():
                    if device_uuid not in self.active_bulbs:
                        # Try to find the bulb on the network
                        bulb_ip = self._find_bulb_ip(device_uuid)
                        if bulb_ip:
                            self._register_discovered_bulb(device_uuid, bulb_ip, device_info)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Discovery error: {e}")
                time.sleep(60)
    
    def _find_bulb_ip(self, device_uuid):
        """Scan local network for bulb with specific UUID"""
        # Network scanning logic here
        # This is a simplified version - in practice you'd scan the subnet
        
        import subprocess
        import re
        
        try:
            # Get network range
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'src' in line and '192.168' in line:
                    # Extract network range
                    network = re.search(r'192\.168\.\d+\.0/24', line)
                    if network:
                        # Scan for bulbs on port 9080
                        for i in range(2, 255):
                            ip = f"192.168.1.{i}"  # Adjust for your network
                            if self._test_bulb_connection(ip, device_uuid):
                                return ip
        except Exception as e:
            print(f"Network scan error: {e}")
        
        return None
    
    def _test_bulb_connection(self, ip, expected_uuid):
        """Test if IP has a Sengled bulb with expected UUID"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            
            command = {"func": "get_device_info", "param": {}}
            message = json.dumps(command).encode('utf-8')
            sock.sendto(message, (ip, 9080))
            
            response, addr = sock.recvfrom(1024)
            data = json.loads(response.decode('utf-8'))
            
            # Check if this is our bulb (you'd need to match UUID somehow)
            # This is simplified - real implementation would need MAC mapping
            return True
            
        except:
            return False
        finally:
            sock.close()
    
    def _register_discovered_bulb(self, device_uuid, ip, cloud_info):
        """Register a discovered bulb in MongoDB"""
        
        bulb_doc = {
            "device_uuid": device_uuid,
            "ip_address": ip,
            "mac_address": device_uuid,  # Often the same for Sengled
            "discovered_at": datetime.now(timezone.utc),
            "last_seen": datetime.now(timezone.utc),
            "cloud_registration": cloud_info,
            "status": "active",
            "capabilities": {
                "switch": True,
                "brightness": True,
                "color_temp": True,
                "color": False  # Detect based on model
            }
        }
        
        self.devices.update_one(
            {"device_uuid": device_uuid},
            {"$set": bulb_doc},
            upsert=True
        )
        
        self.active_bulbs[device_uuid] = {
            "ip": ip,
            "last_command": None,
            "last_response": None
        }
        
        print(f"✅ Registered bulb {device_uuid} at {ip}")
    
    def send_command_to_bulb(self, device_uuid, command):
        """Send UDP command to specific bulb and log to MongoDB"""
        
        if device_uuid not in self.active_bulbs:
            return {"error": "Bulb not found"}
        
        bulb_info = self.active_bulbs[device_uuid]
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            message = json.dumps(command).encode('utf-8')
            sock.sendto(message, (bulb_info["ip"], 9080))
            
            response, addr = sock.recvfrom(1024)
            result = json.loads(response.decode('utf-8'))
            
            # Log to MongoDB
            command_doc = {
                "device_uuid": device_uuid,
                "timestamp": datetime.now(timezone.utc),
                "command": command,
                "response": result,
                "success": "error" not in result,
                "ip_address": bulb_info["ip"]
            }
            
            self.commands.insert_one(command_doc)
            
            # Update device last_seen
            self.devices.update_one(
                {"device_uuid": device_uuid},
                {"$set": {"last_seen": datetime.now(timezone.utc)}}
            )
            
            return result
            
        except Exception as e:
            error_doc = {
                "device_uuid": device_uuid,
                "timestamp": datetime.now(timezone.utc),
                "command": command,
                "error": str(e),
                "success": False,
                "ip_address": bulb_info["ip"]
            }
            self.commands.insert_one(error_doc)
            return {"error": str(e)}
        finally:
            sock.close()
    
    def execute_scene(self, scene_name):
        """Execute a scene from MongoDB"""
        scene = self.scenes.find_one({"name": scene_name})
        if not scene:
            return {"error": f"Scene '{scene_name}' not found"}
        
        results = {}
        for action in scene.get("actions", []):
            device_uuid = action["device_uuid"]
            command = action["command"]
            
            result = self.send_command_to_bulb(device_uuid, command)
            results[device_uuid] = result
        
        return results
    
    def get_device_status(self, device_uuid):
        """Get current status of a device"""
        command = {"func": "get_device_info", "param": {}}
        return self.send_command_to_bulb(device_uuid, command)
    
    def create_scene(self, scene_name, actions):
        """Create a new scene in MongoDB"""
        scene_doc = {
            "name": scene_name,
            "actions": actions,
            "created_at": datetime.now(timezone.utc)
        }
        
        self.scenes.update_one(
            {"name": scene_name},
            {"$set": scene_doc},
            upsert=True
        )
        
        return {"success": True}

# Example usage
if __name__ == "__main__":
    # Connect to MongoDB (adjust URI for your Atlas setup)
    system = SengledMongoDBSystem("mongodb://localhost:27017")
    
    # Wait for discovery
    time.sleep(5)
    
    # Test commands
    for device_uuid in system.active_bulbs:
        print(f"Testing bulb {device_uuid}")
        
        # Turn on
        result = system.send_command_to_bulb(device_uuid, {
            "func": "set_device_switch", 
            "param": {"switch": 1}
        })
        print(f"Turn on result: {result}")
        
        time.sleep(1)
        
        # Set brightness
        result = system.send_command_to_bulb(device_uuid, {
            "func": "set_device_brightness", 
            "param": {"brightness": 75}
        })
        print(f"Brightness result: {result}")
