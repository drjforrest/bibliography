#!/usr/bin/env python3
"""
Test SSH tunnel by trying to connect and see what we actually get.
Also test if local PostgreSQL is intercepting.
"""
import socket
import sys

def test_port_connection(host, port):
    """Test raw TCP connection to see what's listening"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_postgres_protocol(host, port):
    """Try to initiate PostgreSQL handshake"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((host, port))
        
        # Send PostgreSQL startup message
        # Protocol version 3.0, database name test
        startup_msg = bytearray([0, 0, 0, 0])
        sock.send(startup_msg)
        
        # Try to read response
        sock.settimeout(1)
        try:
            response = sock.recv(1024)
            if response:
                print(f"  Response: {response[:50]}")
                if b'PostgreSQL' in response:
                    version = response.split(b'\x00')[0].decode('utf-8', errors='ignore')
                    print(f"  PostgreSQL version in response: {version[:50]}")
                    sock.close()
                    return True
        except socket.timeout:
            pass
        
        sock.close()
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

print("="*60)
print("SSH TUNNEL DIAGNOSTICS")
print("="*60)

print("\n1. Testing port 5433 (SSH tunnel)...")
if test_port_connection('127.0.0.1', 5433):
    print("  ✓ Port 5433 is open")
    print("  Testing PostgreSQL protocol...")
    test_postgres_protocol('127.0.0.1', 5433)
else:
    print("  ✗ Port 5433 is NOT accessible")
    print("  SSH tunnel may not be working")

print("\n2. Testing port 5432 (local PostgreSQL)...")
if test_port_connection('127.0.0.1', 5432):
    print("  ✓ Port 5432 is open (local PostgreSQL)")
else:
    print("  ✗ Port 5432 is NOT accessible")

print("\n3. Recommendation:")
print("  If both ports are open, the SSH tunnel may not be forwarding correctly.")
print("  Try restarting the tunnel:")
print("    pkill -f 'ssh.*5433'")
print("    ssh -L 5433:localhost:5432 mac-mini -N")

