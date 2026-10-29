"""Inspect one explicitly selected endpoint without disabling TLS verification."""
import argparse
import json
import socket
import ssl
import sys
import time


def diagnose(host, port, tls=False, path='/health', timeout=5):
    result = {'host': host, 'port': port, 'tls': tls, 'path': path, 'checks': {}}
    if not host or any(c in host for c in '\r\n/\\') or not path.startswith('/') or any(c in path for c in '\r\n'):
        raise ValueError('Invalid host or path')
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        result['checks']['dns'] = {'ok': True, 'addresses': sorted({item[4][0] for item in addresses})}
    except socket.gaierror as exc:
        result['checks']['dns'] = {'ok': False, 'error': type(exc).__name__}
        return result
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            result['checks']['tcp'] = {'ok': True, 'elapsed_ms': round((time.monotonic() - started) * 1000, 2)}
            if tls:
                try:
                    with ssl.create_default_context().wrap_socket(sock, server_hostname=host) as secure:
                        cert = secure.getpeercert()
                        result['checks']['tls'] = {'ok': True, 'protocol': secure.version(), 'not_after': cert.get('notAfter')}
                        result['checks']['http'] = http_status(secure, host, path)
                except ssl.SSLError as exc:
                    result['checks']['tls'] = {'ok': False, 'error': type(exc).__name__}
            else:
                result['checks']['http'] = http_status(sock, host, path)
    except OSError as exc:
        # If TCP already succeeded, this error occurred during TLS/HTTP, not connect.
        stage = 'transport' if result['checks'].get('tcp', {}).get('ok') else 'tcp'
        result['checks'][stage] = {'ok': False, 'error': type(exc).__name__}
    return result


def http_status(connection, host, path):
    connection.sendall(f'GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n'.encode('ascii'))
    response = b''
    while b'\r\n' not in response and len(response) < 4096:
        chunk = connection.recv(1024)
        if not chunk:
            break
        response += chunk
    parts = response.split(b'\r\n', 1)[0].split(b' ', 2)
    if len(parts) < 2 or not parts[0].startswith(b'HTTP/') or not parts[1].isdigit():
        return {'ok': False, 'error': 'invalid_http_response'}
    return {'ok': True, 'status': int(parts[1])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host', help='One endpoint you are authorized to test')
    parser.add_argument('--port', type=int, default=8081)
    parser.add_argument('--tls', action='store_true')
    parser.add_argument('--path', default='/health')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be between 1 and 65535')
    try:
        report = diagnose(args.host, args.port, args.tls, args.path)
    except (ValueError, UnicodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    checks = report['checks']
    return 0 if checks.get('http', {}).get('ok') and (not args.tls or checks.get('tls', {}).get('ok')) else 1


if __name__ == '__main__':
    sys.exit(main())
