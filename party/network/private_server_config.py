"""Parse and persist shared-server links. Tokens are kept out of logs."""
import os
import re
from urllib.parse import urlsplit, urlunsplit, parse_qs
from config import get_config_option, set_config_option
from .relay_config import RELAY_URL

TOKEN_PATTERN = re.compile(r'^[A-Za-z0-9_-]{32,128}$')

def parse_server_link(link):
    raw = str(link or '').strip()
    if not raw:
        return RELAY_URL.rstrip('/'), ''
    parts = urlsplit(raw)
    if parts.scheme not in ('https', 'wss') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Cole o endereço https:// da sala, sem usuário ou senha no endereço.')
    if parts.path not in ('', '/') or parts.query:
        raise ValueError('Use o endereço completo copiado pelo Rose Sala.')
    if parts.port not in (None,443):
        raise ValueError('O endereço da sala deve usar a conexão segura padrão.')
    token = parse_qs(parts.fragment).get('rose', [''])[0]
    if parts.fragment and not TOKEN_PATTERN.fullmatch(token):
        raise ValueError('A chave da sala está incompleta. Copie o endereço novamente.')
    endpoint = urlunsplit(('wss',parts.netloc.lower(),'','',''))
    return endpoint, token

def save_server_link(link):
    endpoint, token = parse_server_link(link)
    # One write of the whole file through the shared config writer, under the config
    # lock and in the ANSI code page core.dll reads: a host never mixes with another token.
    from config import set_config_options
    set_config_options({'Party': {'relay_url': endpoint, 'relay_access': token}}, strict=True)
    return endpoint

def relay_settings():
    endpoint = os.environ.get('ROSE_RELAY_URL') or get_config_option('Party','relay_url',RELAY_URL) or RELAY_URL
    token = get_config_option('Party','relay_access','') or ''
    return endpoint.rstrip('/'), token
