"""Exercise local network diagnostics and Docker DNS in disposable CI."""
import json
import subprocess
import sys

def run(*args):
    return subprocess.run(args, text=True, capture_output=True, check=False, timeout=20)

healthy = run(sys.executable, 'scripts/netdiag.py', '127.0.0.1', '--port', '8081')
assert healthy.returncode == 0, healthy.stderr
assert json.loads(healthy.stdout)['checks']['http']['status'] == 200

bad_tls = run(sys.executable, 'scripts/netdiag.py', '127.0.0.1', '--port', '8081', '--tls')
assert bad_tls.returncode != 0
checks = json.loads(bad_tls.stdout)['checks']
assert checks['tcp']['ok'] and not checks['tls']['ok']

resolve = run('docker', 'compose', 'exec', '-T', 'api', 'python', '-c',
              "import socket; print(socket.getaddrinfo('db', 5432, type=socket.SOCK_STREAM))")
assert resolve.returncode == 0, resolve.stderr

missing = run('docker', 'compose', 'exec', '-T', 'api', 'python', '-c',
              "import socket; socket.getaddrinfo('missing-db.invalid', 5432, type=socket.SOCK_STREAM)")
assert missing.returncode != 0 and 'gaierror' in missing.stderr
print('Docker DNS, local HTTP and TLS protocol mismatch verified')
