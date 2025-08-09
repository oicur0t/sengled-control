#!/bin/bash
# Sengled App Key Extraction Methods
## THIS IS THEORITICAL ONLY - NOT VERIFIED ##

echo "🔑 SENGLED APP KEY EXTRACTION GUIDE"
echo "=================================="
echo

echo "METHOD 1: APK Static Analysis (Android - Easiest)"
echo "================================================="

echo "1. Download Sengled Home APK:"
echo "   - From APKMirror: https://www.apkmirror.com/apk/sengled/"
echo "   - Or extract from your phone: adb pull /data/app/com.sengled.life2/base.apk"
echo

echo "2. Decompile APK with jadx:"
echo "   # Install jadx"
echo "   sudo apt install jadx"
echo "   # Or download from: https://github.com/skylot/jadx/releases"
echo
echo "   # Decompile APK"
echo "   jadx sengled_home.apk"
echo

echo "3. Search for RC4/encryption keys:"
echo "   cd sengled_home/sources"
echo "   grep -r \"RC4\" ."
echo "   grep -r \"encrypt\" ."
echo "   grep -r \"Base64\" . | grep -i key"
echo "   grep -r \"setParamsRequest\" ."
echo

echo "4. Look for Base64 strings in setup/config classes:"
echo "   find . -name \"*.java\" | xargs grep -l \"startConfigRequest\\|setParamsRequest\""
echo

echo "METHOD 2: Dynamic Analysis with Frida (Android)"
echo "==============================================="

cat << 'EOF'
# Install Frida
pip install frida-tools

# Connect to device/emulator
frida-ps -U

# Hook encryption functions
frida -U -f com.sengled.life2 -l hook_encryption.js

# hook_encryption.js content:
Java.perform(function() {
    // Hook RC4 cipher creation
    var Cipher = Java.use("javax.crypto.Cipher");
    Cipher.getInstance.overload("java.lang.String").implementation = function(transformation) {
        console.log("[+] Cipher.getInstance called: " + transformation);
        if (transformation.includes("RC4")) {
            console.log("[!] RC4 cipher detected!");
        }
        return this.getInstance(transformation);
    };

    // Hook Base64 encoding
    var Base64 = Java.use("android.util.Base64");
    Base64.encodeToString.overload("[B", "int").implementation = function(input, flags) {
        var result = this.encodeToString(input, flags);
        console.log("[+] Base64.encodeToString: " + result);
        return result;
    };

    // Hook setParamsRequest specifically
    // You'll need to find the exact class name from jadx output
    try {
        var ConfigClass = Java.use("com.sengled.life2.config.SetupHelper"); // Adjust class name
        ConfigClass.setParamsRequest.implementation = function(params) {
            console.log("[!] setParamsRequest called with: " + params);
            return this.setParamsRequest(params);
        };
    } catch (e) {
        console.log("[-] Could not hook setParamsRequest: " + e);
    }
});
EOF

echo

echo "METHOD 3: Network Traffic Analysis"
echo "================================="

echo "1. Set up packet capture:"
echo "   # On router/gateway"
echo "   tcpdump -i any -w sengled_setup.pcap host 192.168.8.1"
echo
echo "   # Or use Wireshark with WiFi monitor mode"
echo

echo "2. Perform bulb setup while capturing traffic"
echo "3. Analyze captured packets for:"
echo "   - UDP traffic to 192.168.8.1:9080"
echo "   - Look for setParamsRequest payload"
echo "   - Compare encrypted vs unencrypted versions"
echo

echo "METHOD 4: iOS App Analysis (More Complex)"
echo "========================================="

echo "1. Jailbroken device required"
echo "2. Extract IPA file:"
echo "   # Using 3uTools or similar"
echo "   # Or Clutch if jailbroken"
echo

echo "3. Analyze with Hopper Disassembler:"
echo "   # Look for RC4, encrypt, setParams strings"
echo "   # Find Base64 encoded constants"
echo

echo "METHOD 5: Firmware Analysis (Nuclear Option)"
echo "============================================"

echo "1. Extract firmware from bulb:"
echo "   # Connect to bulb's serial/UART pins"
echo "   # Or dump SPI flash chip directly"
echo

echo "2. Analyze firmware:"
echo "   binwalk firmware.bin"
echo "   strings firmware.bin | grep -i rc4"
echo "   strings firmware.bin | grep -i encrypt"
echo

echo "EXPECTED KEY PATTERNS:"
echo "====================="
echo "Based on the Reddit post, look for:"
echo "- Base64 encoded string (likely 16-32 chars)"
echo "- Used in RC4 cipher initialization"
echo "- Referenced in setParamsRequest function"
echo "- Might be named like: SETUP_KEY, RC4_KEY, ENCRYPT_KEY"
echo

echo "QUICK TEST SCRIPT:"
echo "=================="

cat << 'EOF'
# test_keys.py - Test extracted keys
import base64
from Crypto.Cipher import ARC4
import json

def test_key(potential_key, test_payload):
    """Test if a key can decrypt known payload"""
    try:
        # Try as direct string
        cipher = ARC4.new(potential_key.encode())
        encrypted = cipher.encrypt(test_payload.encode())
        b64_encrypted = base64.b64encode(encrypted).decode()
        print(f"Key '{potential_key}' -> {b64_encrypted}")
        
        # Try as base64 decoded
        decoded_key = base64.b64decode(potential_key)
        cipher2 = ARC4.new(decoded_key)
        encrypted2 = cipher2.encrypt(test_payload.encode())
        b64_encrypted2 = base64.b64encode(encrypted2).decode()
        print(f"Key '{potential_key}' (b64 decoded) -> {b64_encrypted2}")
        
    except Exception as e:
        print(f"Key '{potential_key}' failed: {e}")

# Test with sample payload
test_payload = json.dumps({
    "userID": "618",
    "timeZone": "America/Chicago",
    "routerInfo": {"ssid": "test", "password": "test"}
})

# Test potential keys found in app
test_keys = [
    "SengledSetupKey123",  # Example - replace with actual findings
    "your_extracted_key_here",
]

for key in test_keys:
    test_key(key, test_payload)
EOF

echo

echo "AUTOMATION SCRIPT:"
echo "=================="

cat << 'EOF'
#!/bin/bash
# auto_extract.sh - Automated key extraction

APK_FILE="sengled_home.apk"

echo "🔍 Automated Sengled key extraction..."

if [ ! -f "$APK_FILE" ]; then
    echo "❌ APK file not found. Download from APKMirror first."
    exit 1
fi

echo "📱 Decompiling APK..."
jadx -d extracted/ "$APK_FILE"

echo "🔑 Searching for encryption keys..."
cd extracted/sources

echo "Base64 strings that might be keys:"
grep -r "Base64" . | grep -E "(key|Key|encrypt|Encrypt)" | head -10

echo
echo "RC4 related code:"
grep -r "RC4" . | head -5

echo
echo "Setup/Config related files:"
find . -name "*.java" | xargs grep -l "setParamsRequest\|startConfigRequest" | head -5

echo
echo "🎯 Manual review required. Check the files above for hardcoded Base64 strings."
EOF
