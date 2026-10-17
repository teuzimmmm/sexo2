"""Build an unsigned functional-test installer on Windows; never publish/sign.

Only allowlisted native binaries are restored from an existing baseline. Source
plugins come from this checkout, never from the baseline. No user config, token,
datastore or signing key is copied to the clean staging directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sexo2.install.identity import MANIFEST, test_identity
from sexo2.install.packaging import restore_native, snapshot_source, validate_version, is_pe


def compiler_path(explicit=None):
    if explicit:
        return Path(explicit).resolve() if Path(explicit).is_file() else None
    executable = shutil.which('ISCC.exe')
    if executable:
        return Path(executable)
    for variable in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
        prefix = os.environ.get(variable)
        if prefix:
            parent = Path(prefix) / ('Programs' if variable == 'LOCALAPPDATA' else '')
            candidate = parent / 'Inno Setup 6' / 'ISCC.exe'
            if candidate.is_file():
                return candidate
    return None


def git_commit():
    for options in (['diff', '--quiet'], ['diff', '--cached', '--quiet']):
        if subprocess.run(['git', *options], cwd=ROOT, check=False).returncode:
            raise ValueError('Registre as alterações rastreadas no Git antes de compilar.')
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
                            capture_output=True, text=True).stdout.strip()
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Identificador do código inválido.')
    return commit


def write_identity(app, version, commit):
    identity = {'schema': 1, 'app': 'SEXO2', 'channel': 'test',
                'version': validate_version(version), 'sourceCommit': commit}
    (app / MANIFEST).write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')
    test_identity(app)
    return identity


def run(command, *, cwd):
    subprocess.run([str(p) for p in command], cwd=cwd, check=True)


def build(base, version, output, iscc):
    commit = git_commit()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    name = f'SEXO2-{version}-Teste-{commit[:8]}'
    installer = output / (name + '.exe')
    if installer.exists():
        raise ValueError('Este instalador já existe; use outro número de edição ou pasta de saída.')
    # A private temporary snapshot prevents personal ignored files entering
    # PyInstaller's broad assets/runtime globs. The working checkout stays intact.
    with tempfile.TemporaryDirectory(prefix='sexo2-test-build-') as temporary:
        stage = Path(temporary) / 'source'
        snapshot_source(ROOT, stage)
        native = restore_native(base, stage)
        assets = stage / 'assets'
        (assets / 'update-source.json').write_text(
            json.dumps({'repository': '', 'channel': 'test', 'private': True}), encoding='utf-8')
        version_file = assets / 'sexo2-version.txt'
        metadata = version_file.read_text(encoding='utf-8')
        metadata = re.sub(r'(filevers|prodvers)=\([^)]*\)',
                          lambda m: m[1] + '=(' + version.replace('.', ',') + ')', metadata)
        metadata = re.sub(r"(StringStruct\('(?:FileVersion|ProductVersion)',')[^']+('\))",
                          lambda m: m[1] + version + m[2], metadata)
        version_file.write_text(metadata, encoding='utf-8')
        spec = stage / 'installer-sexo2.iss'
        spec.write_text(spec.read_text(encoding='utf-8-sig'), encoding='utf-8-sig')
        from scripts.build_offer_reader import build as build_offer_reader
        offer_reader_hash = build_offer_reader(stage)
        run([sys.executable, '-m', 'PyInstaller', 'SEXO2.spec', '--noconfirm',
             '--distpath', 'dist-test', '--workpath', 'build-test'], cwd=stage)
        app = stage / 'dist-test' / 'SEXO2'
        # The existing package assembly adds the user-supplied patcher after
        # PyInstaller filters it; keep that same behavior for this private test.
        for name_part in ('ltk_patcher_host.exe', 'ltk_patcher_dll.dll'):
            shutil.copyfile(stage / 'injection' / 'tools' / name_part,
                            app / '_internal' / 'injection' / 'tools' / name_part)
        identity = write_identity(app, version, commit)
        for source, target in [
            ('LICENSE', 'LICENSE-Rose.txt'),
            ('vendor/PenguLoader-1.1.6/LICENSE', 'LICENSE-PenguLoader.txt'),
            ('hosting-tools/LICENSE-cloudflared.txt', '_internal/hosting-tools/LICENSE-cloudflared.txt'),
            ('hosting-tools/provenance.json', '_internal/hosting-tools/provenance.json'),
        ]:
            shutil.copyfile(stage / source, app / target)
        run([sys.executable, 'audit_frozen.py', app], cwd=stage)
        run([iscc, '/DSourceDir=' + str(app), '/DOutputDir=' + str(output),
             '/DBuildVersion=' + version, '/DOutputName=' + name, spec], cwd=stage)
        body = installer.read_bytes()
        if not is_pe(body):
            raise ValueError('O compilador não gerou um instalador Windows válido.')
        digest = hashlib.sha256(body).hexdigest()
        (output / (installer.name + '.sha256')).write_text(
            digest + '  ' + installer.name + '\n', encoding='ascii')
        report = dict(identity, installer=installer.name, sha256=digest, nativeFiles=native,
                      offerReaderSha256=offer_reader_hash,
                      legacyCleanup=False, legacyDataCompatibility=True,
                      stableUpdates=False, nativeLeagueValidation=False)
        (output / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Instalador de teste gerado: ' + str(installer))
    return installer


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True,
                        help='SEXO2 baseline ZIP or existing application folder (read-only)')
    parser.add_argument('--version', default='2.0.0.4')
    parser.add_argument('--output', type=Path, default=ROOT / 'build-test-installer' / 'output')
    parser.add_argument('--iscc', type=Path)
    args = parser.parse_args(argv)
    try:
        validate_version(args.version)
        if sys.platform != 'win32':
            raise ValueError('A compilação exige Windows x64; PyInstaller não gera executáveis Windows neste Linux.')
        if sys.version_info[:2] != (3, 14):
            raise ValueError('Use Python 3.14 com requirements.txt instalados para este build.')
        iscc = compiler_path(args.iscc)
        if iscc is None:
            raise ValueError('Instale Inno Setup 6 ou informe --iscc com o caminho de ISCC.exe.')
        build(args.base.resolve(), args.version, args.output, iscc)
    except (ValueError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print('Build não concluído: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
