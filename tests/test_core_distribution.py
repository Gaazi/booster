"""Exercise the core without optional server, CDN or codec dependencies."""

import subprocess
import sys

GUARD = '''
import importlib.abc
import sys
class BlockOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'fastapi', 'starlette', 'httpx', 'uvicorn', 'brotli'}:
            raise ModuleNotFoundError(fullname, name=fullname.split('.')[0])
sys.meta_path.insert(0, BlockOptional())
'''


def probe(program: str) -> subprocess.CompletedProcess[str]:
    """Run a fresh interpreter with optional packages unavailable."""
    return subprocess.run([sys.executable, "-c", GUARD + program],
                          capture_output=True, text=True, timeout=10)


def test_core_import_and_gzip_without_optional_libraries() -> None:
    """Core import, memory cache and stdlib compression need no host framework."""
    result = probe('''
import booster
import gzip
cache = booster.FastMemoryCache()
cache.set('key', '/public', 200, [], b'public')
assert cache.get('key').body == b'public'
body, encoding = booster.ResponseCompressor().compress(b'x'*2048, 'text/plain', 'br, gzip')
assert encoding == 'gzip' and gzip.decompress(body) == b'x'*2048
assert not {'fastapi','starlette','httpx','uvicorn'}.intersection(sys.modules)
assert booster.DjangoRocketMiddleware
''')
    assert result.returncode == 0, result.stderr


def test_optional_export_provides_installation_hint() -> None:
    """Requesting the absent proxy explains its optional extra without hiding bugs."""
    result = probe('''
import booster
try:
    booster.SpeedProxyServer
except ImportError as error:
    assert 'booster[server]' in str(error)
else:
    raise AssertionError('Missing optional dependencies were ignored')
try:
    booster.unknown_feature
except AttributeError:
    pass
else:
    raise AssertionError('Unknown export did not raise')
''')
    assert result.returncode == 0, result.stderr


def test_standalone_cli_explains_missing_server_extra() -> None:
    """Core installations fail clearly instead of starting a partial server."""
    result = probe("from booster.cli import main; main()")
    assert result.returncode != 0
    assert "booster[server]" in result.stderr
