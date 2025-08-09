from flask import Flask, request, jsonify
import json
import uuid
from datetime import datetime, timezone
import threading
import time

app = Flask(__name__)

# Store registered devices
registered_devices = {}

@app.route('/life2/device/accessCloud.json', methods=['POST'])
def access_cloud():
    """
    Emulate the Sengled cloud registration endpoint.
    Based on analysis of WebThingsIO/sengled-adapter and ha-sengledapi
    """
    
    request_data = request.get_json()
    print(f"[{datetime.now()}] Device registration request:")
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    device_uuid = request_data.get('deviceUuid')
    user_id = request_data.get('userId')
    product_code = request_data.get('productCode', 'wifielement')
    type_code = request_data.get('typeCode', 'W31-N11')
    
    # Generate a session ID (mimicking real cloud behavior)
    jsession_id = str(uuid.uuid4()).replace('-', '')[:24]
    
    # Standard successful registration response
    # Based on patterns from working Sengled integrations
    response_data = {
        "info": "OK",
        "jsessionId": jsession_id,
        "deviceUuid": device_uuid,
        "userId": user_id,
        "productCode": product_code,
        "typeCode": type_code,
        "status": "online",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "serverTime": int(datetime.now(timezone.utc).timestamp() * 1000)
    }
    
    # Store device info for later reference
    registered_devices[device_uuid] = {
        'registration_time': datetime.now(timezone.utc),
        'last_seen': datetime.now(timezone.utc),
        'user_id': user_id,
        'jsession_id': jsession_id,
        'ip': request.remote_addr
    }
    
    print(f"[{datetime.now()}] Responding with registration success:")
    print(f"Response: {json.dumps(response_data, indent=2)}")
    
    return jsonify(response_data)

@app.route('/jbalancer/new/bimqtt', methods=['GET', 'POST'])
def mqtt_balancer():
    """
    MQTT broker information endpoint.
    The bulb expects to get MQTT server details here.
    """
    
    print(f"[{datetime.now()}] MQTT broker info request")
    
    # Provide local MQTT broker information
    # This tells the bulb where to connect for MQTT commands
    response_data = {
        "info": "OK",
        "inceptionAddr": "ws://192.168.1.100:9001/mqtt",  # Your local MQTT broker
        "mqtt": {
            "host": "192.168.1.100",
            "port": 1883,
            "wsPort": 9001,
            "path": "/mqtt"
        }
    }
    
    print(f"MQTT response: {json.dumps(response_data, indent=2)}")
    return jsonify(response_data)

@app.route('/life2/server/getServerInfo.json', methods=['POST'])
def get_server_info():
    """
    Additional server info endpoint that some bulbs might call.
    Based on WebThingsIO adapter patterns.
    """
    
    response_data = {
        "info": "OK",
        "inceptionAddr": "ws://192.168.1.100:9001/mqtt",
        "serverTime": int(datetime.now(timezone.utc).timestamp() * 1000)
    }
    
    return jsonify(response_data)

@app.route('/api/devices', methods=['GET'])
def list_devices():
    """API endpoint to see all registered devices"""
    return jsonify(registered_devices)

if __name__ == '__main__':
    print("Starting Sengled Cloud Emulator...")
    print("This will respond to bulb registration requests on port 80")
    print("Make sure to point bulbs to this server's IP in the setup process")
    app.run(host='0.0.0.0', port=80, debug=True)
