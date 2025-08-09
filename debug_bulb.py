import socket
import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def ping_test(ip):
    """Test if IP responds to ping"""
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '2', ip], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def port_scan(ip, port):
    """Test if specific port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def test_udp_port(ip, port):
    """Test UDP port with simple packet"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        
        # Send a simple test packet
        sock.sendto(b"test", (ip, port))
        
        try:
            response, addr = sock.recvfrom(1024)
            return True, f"Got response: {response[:50]}"
        except socket.timeout:
            return False, "No response (but port might be open)"
        
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        sock.close()

def test_sengled_commands(ip):
    """Try different Sengled command variations"""
    commands_to_try = [
        {"func": "get_device_info", "param": {}},
        {"func": "get_device_status", "param": {}},
        {"cmd": "get_info"},
        {"command": "status"},
        "status",  # Simple string
    ]
    
    ports_to_try = [9080, 8080, 80, 8899, 38899]  # Common IoT ports
    
    print(f"\nTesting various Sengled command formats on {ip}...")
    
    for port in ports_to_try:
        print(f"\n--- Testing port {port} ---")
        
        for i, command in enumerate(commands_to_try):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(2)
                
                if isinstance(command, str):
                    message = command.encode('utf-8')
                else:
                    message = json.dumps(command).encode('utf-8')
                
                print(f"  Command {i+1}: {command}")
                sock.sendto(message, (ip, port))
                
                response, addr = sock.recvfrom(1024)
                result = response.decode('utf-8')
                print(f"  ✅ RESPONSE: {result}")
                return True, port, command, result
                
            except socket.timeout:
                print(f"  ⏱️  Timeout")
            except Exception as e:
                print(f"  ❌ Error: {e}")
            finally:
                sock.close()
    
    return False, None, None, None

def scan_network_for_bulbs():
    """Scan entire local network for potential Sengled bulbs"""
    print("Scanning local network for Sengled bulbs...")
    print("This will take 2-3 minutes...\n")
    
    # Try to detect network range
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True)
        if '192.168.1.' in result.stdout:
            base_ip = "192.168.1."
        elif '192.168.0.' in result.stdout:
            base_ip = "192.168.0."
        else:
            base_ip = "192.168.1."  # Default guess
    except:
        base_ip = "192.168.1."
    
    print(f"Scanning network range: {base_ip}x")
    
    def test_ip_comprehensive(ip):
        """Comprehensive test for Sengled bulb"""
        # First, ping test
        if not ping_test(ip):
            return None
        
        print(f"📍 {ip} responds to ping, testing for Sengled...")
        
        # Test common IoT ports with UDP
        ports = [9080, 8080, 80, 8899, 38899]
        for port in ports:
            udp_result, udp_msg = test_udp_port(ip, port)
            if udp_result:
                print(f"  🔍 UDP port {port} responds: {udp_msg}")
                
                # Try Sengled commands
                success, working_port, working_cmd, response = test_sengled_commands(ip)
                if success:
                    return {
                        'ip': ip, 
                        'port': working_port, 
                        'command': working_cmd, 
                        'response': response
                    }
        
        return None
    
    # Scan in parallel
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i in range(2, 255):
            ip = f"{base_ip}{i}"
            futures.append(executor.submit(test_ip_comprehensive, ip))
        
        found_devices = []
        for future in futures:
            result = future.result()
            if result:
                found_devices.append(result)
                print(f"\n🎉 FOUND SENGLED BULB: {result}")
    
    return found_devices

def debug_specific_ip(ip):
    """Detailed debugging for specific IP"""
    print(f"Detailed debugging for {ip}")
    print("=" * 50)
    
    # 1. Ping test
    print(f"\n1. Ping test...")
    if ping_test(ip):
        print(f"✅ {ip} responds to ping")
    else:
        print(f"❌ {ip} does not respond to ping")
        print("   - Check if device is actually at this IP")
        print("   - Device might be on different network")
        return
    
    # 2. Port scan
    print(f"\n2. Port scanning...")
    common_ports = [80, 443, 8080, 9080, 8899, 38899, 22, 23]
    open_ports = []
    
    for port in common_ports:
        if port_scan(ip, port):
            open_ports.append(port)
            print(f"✅ Port {port} is open (TCP)")
        else:
            print(f"❌ Port {port} is closed/filtered")
    
    if not open_ports:
        print("⚠️  No common ports open - device might not be IoT device")
    
    # 3. UDP tests
    print(f"\n3. UDP testing...")
    success, working_port, working_cmd, response = test_sengled_commands(ip)
    
    if success:
        print(f"\n🎉 SUCCESS! Found working Sengled protocol:")
        print(f"   IP: {ip}")
        print(f"   Port: {working_port}")
        print(f"   Command: {working_cmd}")
        print(f"   Response: {response}")
    else:
        print(f"\n❌ No Sengled protocol detected")
        print("   This might not be a Sengled bulb, or:")
        print("   - Bulb uses different protocol")
        print("   - Bulb not fully set up")
        print("   - Different command format needed")

if __name__ == "__main__":
    print("Sengled Bulb Discovery & Debug Tool")
    print("===================================\n")
    
    # First, test the specific IP you provided
    debug_specific_ip("192.168.1.70")
    
    print("\n" + "="*50)
    response = input("\nWould you like to scan the entire network for Sengled bulbs? (y/n): ")
    
    if response.lower().startswith('y'):
        found_bulbs = scan_network_for_bulbs()
        
        if found_bulbs:
            print(f"\n🎉 SUMMARY: Found {len(found_bulbs)} potential Sengled device(s):")
            for bulb in found_bulbs:
                print(f"  - {bulb['ip']}:{bulb['port']} - {bulb['command']}")
        else:
            print("\n😞 No Sengled bulbs found on network")
            print("\nTroubleshooting:")
            print("- Make sure bulbs are powered on")
            print("- Verify bulbs are connected to WiFi (check router)")
            print("- Ensure bulbs were previously paired with Sengled app")
            print("- Try running this from different device on same network")
