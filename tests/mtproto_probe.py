"""Anonymous req_pq_multi roundtrip through MTProxy, without a Telegram account.

Implements https://core.telegram.org/mtproto/mtproto-transports obfuscation and
padded intermediate framing. This is a transport test, not native app acceptance.
OpenSSL supplies AES; no private credentials are printed or written by this tool.
"""
import hashlib
import secrets
import socket
import struct
import subprocess
import time


def probe(server, port, secret, timeout=12, openssl='openssl'):
    key = bytes.fromhex(secret.removeprefix('dd') if len(secret) == 34 else secret)
    assert len(key) == 16
    while True:
        header = bytearray(secrets.token_bytes(64))
        if header[0] != 0xef and header[:4] not in (b'HEAD', b'POST', b'GET ', b'\xee'*4, b'\xdd'*4) and header[4:8] != b'\x00'*4:
            break
    header[56:60] = b'\xdd'*4
    header[60:62] = struct.pack('<h', 2)
    reverse = header[::-1]
    def aes(data, source):
        digest = hashlib.sha256(source[8:40] + key).hexdigest()
        result = subprocess.run([openssl, 'enc', '-aes-256-ctr', '-K', digest, '-iv', source[40:56].hex(), '-nosalt'],
            input=data, capture_output=True)
        if result.returncode:
            raise RuntimeError('AES operation failed')
        return result.stdout
    nonce = secrets.token_bytes(16)
    body = struct.pack('<I', 0xbe7e8ef1) + nonce
    payload = b'\x00'*8 + struct.pack('<QI', int(time.time()*2**32) & ~3, len(body)) + body
    padded = payload + secrets.token_bytes(12)
    encrypted = aes(bytes(header) + struct.pack('<I', len(padded)) + padded, header)
    with socket.create_connection((server, int(port)), timeout=timeout) as conn:
        conn.settimeout(timeout)
        conn.sendall(bytes(header[:56]) + encrypted[56:])
        received = b''
        def read_until(length):
            nonlocal received
            while len(received) < length:
                chunk = conn.recv(length - len(received))
                if not chunk:
                    raise ConnectionError('MTProxy closed the connection')
                received += chunk
        read_until(4)
        length = struct.unpack('<I', aes(received, reverse))[0]
        if not 40 <= length <= 65536:
            raise ConnectionError('Invalid MTProto response frame')
        read_until(4 + length)
        response = aes(received, reverse)[4:]
        if response[:8] != b'\x00'*8 or response[20:24] != struct.pack('<I', 0x05162463) or response[24:40] != nonce:
            raise ConnectionError('Telegram resPQ nonce verification failed')
    return True
