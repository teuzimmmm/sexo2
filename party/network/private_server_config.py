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
    # One atomic configuration write to prevent mixing one host with another token.
    from config import get_config_file_path
    import configparser
    from utils.core.atomic_file import atomic_write
    path = get_config_file_path()
    parser = configparser.ConfigParser(interpolation=None)
    from config import read_config_file
    if path.exists(): read_config_file(parser,path)
    if not parser.has_section('Party'): parser.add_section('Party')
    parser.set('Party','relay_url',endpoint)
    parser.set('Party','relay_access',token)
    with atomic_write(path,mode='w',encoding='utf-8') as stream:
        parser.write(stream)
    return endpoint

def relay_settings():
    endpoint = os.environ.get('ROSE_RELAY_URL') or get_config_option('Party','relay_url',RELAY_URL) or RELAY_URL
    token = get_config_option('Party','relay_access','') or ''
    return endpoint.rstrip('/'), token
