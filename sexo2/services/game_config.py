"""Explicit, backed-up import of the bundled game settings (no account data)."""

import configparser
import io
import json
import os
import tempfile
from pathlib import Path

import psutil

from config import get_config_option
from utils.core.paths import get_assets_dir, get_user_data_dir


def game_running():
    return any(
        (process.info.get("name") or "").lower() == "league of legends.exe" for process in psutil.process_iter(["name"])
    )


def config_directory():
    game = get_config_option("General", "leaguePath", "") or ""
    client = get_config_option("General", "clientPath", "") or ""
    if game:
        candidate = Path(game).parent / "Config"
    elif client:
        candidate = Path(client) / "Config"
    else:
        candidate = None
        for process in psutil.process_iter(["name", "exe"]):
            if (process.info.get("name") or "").lower() == "leagueclient.exe" and process.info.get("exe"):
                candidate = Path(process.info["exe"]).parent / "Config"
                break
    if candidate is None or not candidate.is_dir():
        raise ValueError("Confira a pasta do LoL (Game) nas configurações antes de importar.")
    return candidate


def _atomic_write(path, content):
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def import_default(*, confirmed, directory=None, profile_path=None, backup_root=None, running=game_running):
    if confirmed is not True:
        raise ValueError("Confirme a importação da configuração de jogo padrão.")
    if running():
        raise ValueError("Saia da partida antes de importar a configuração de jogo padrão.")
    directory = Path(directory) if directory is not None else config_directory()
    profile_path = profile_path or get_assets_dir() / "game-config-default.json"
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8-sig"))
    if profile.get("version") != 1 or set(profile.get("files", {})) != {"game.cfg", "input.ini"}:
        raise ValueError("A configuração de jogo padrão está inválida.")
    names = ("game.cfg", "input.ini", "PersistedSettings.json")
    originals = {name: (directory / name).read_bytes() if (directory / name).exists() else None for name in names}
    persisted = (
        json.loads(originals["PersistedSettings.json"].decode("utf-8-sig")) if originals[names[2]] else {"files": []}
    )
    # Keep destination-only options and top-level metadata belonging to this account.
    result = {}
    for name, sections in profile["files"].items():
        ini = configparser.ConfigParser(interpolation=None, strict=False)
        ini.optionxform = str
        if originals[name] is not None:
            ini.read_string(originals[name].decode("utf-8-sig"))
        file = next((f for f in persisted["files"] if f["name"].lower() == name.lower()), None)
        if file is None:
            file = {"name": name, "sections": []}
            persisted["files"].append(file)
        for section_name, settings in sections.items():
            if not ini.has_section(section_name):
                ini.add_section(section_name)
            section = next((s for s in file["sections"] if s["name"] == section_name), None)
            if section is None:
                section = {"name": section_name, "settings": []}
                file["sections"].append(section)
            for key, value in settings.items():
                ini.set(section_name, key, value)
                setting = next((s for s in section["settings"] if s["name"] == key), None)
                if setting is None:
                    section["settings"].append({"name": key, "value": value})
                else:
                    setting["value"] = value
        stream = io.StringIO()
        ini.write(stream, space_around_delimiters=False)
        result[name] = stream.getvalue().encode("utf-8")
    result[names[2]] = (json.dumps(persisted, ensure_ascii=False, indent=4) + "\n").encode("utf-8")
    backup_root = Path(backup_root) if backup_root else get_user_data_dir() / "game-config-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="before-import-", dir=backup_root))
    for name, content in originals.items():
        if content is not None:
            (backup / name).write_bytes(content)
    (backup / "manifest.json").write_text(
        json.dumps({"destination": str(directory), "missing": [n for n, v in originals.items() if v is None]}),
        encoding="utf-8",
    )
    if running():
        raise ValueError("Saia da partida antes de importar a configuração de jogo padrão.")
    written = []
    try:
        for name, content in result.items():
            _atomic_write(directory / name, content)
            written.append(name)
    except OSError as error:
        try:
            for name in reversed(written):
                if originals[name] is None:
                    (directory / name).unlink(missing_ok=True)
                else:
                    _atomic_write(directory / name, originals[name])
        except OSError:
            raise ValueError(f"A importação falhou. Restaure a cópia de segurança em {backup}.") from error
        raise ValueError("Não foi possível importar. A configuração anterior foi preservada.") from error
    return {"success": True, "backup": str(backup)}
