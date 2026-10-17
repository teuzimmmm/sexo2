"""Public test-build identity; no credentials or paths from a manifest are used."""
import json
from pathlib import Path
import re
import sys

MANIFEST = 'sexo2-test-build.json'


def test_identity(installation=None):
    if installation is None:
        if not getattr(sys, 'frozen', False):
            return None
        installation = Path(sys.executable).parent
    path = Path(installation) / MANIFEST
    if not path.exists():
        return None
    if path.is_symlink() or path.stat().st_size > 16384:
        raise ValueError('Identidade da instalação de teste inválida.')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(data, dict) or data.get('schema') != 1 or data.get('app') != 'SEXO2'
                or data.get('channel') != 'test'
                or not re.fullmatch(r'[0-9a-f]{40}', data.get('sourceCommit', ''))
                or not re.fullmatch(r'2\.0\.0\.[1-9][0-9]{0,4}', data.get('version', ''))
                or int(data['version'].rsplit('.', 1)[1]) > 65535):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Identidade da instalação de teste inválida. Reinstale o pacote de teste.') from None
    return data


def display_version(fallback):
    identity = test_identity()
    return identity['version'] + ' (teste)' if identity else fallback
