"""Compile the own-process composition DLL using installed MSVC and Windows SDK."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def build(source):
    source = Path(source).resolve()
    vswhere = Path(os.environ.get('ProgramFiles(x86)', '')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
    if not vswhere.is_file():
        raise ValueError('MSVC Build Tools and Windows SDK are required.')
    installation = subprocess.run([str(vswhere), '-latest', '-products', '*', '-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'],
        check=True, capture_output=True, text=True).stdout.strip()
    vcvars = Path(installation) / 'VC/Auxiliary/Build/vcvars64.bat'
    if not vcvars.is_file():
        raise ValueError('MSVC x64 toolchain is unavailable.')
    dest = source / 'sexo2/overlay/bin'
    dest.mkdir(parents=True, exist_ok=True)
    output = dest / 'sexo2-overlay-renderer.dll'
    with tempfile.TemporaryDirectory(prefix='sexo2-renderer-') as temporary:
        stage = Path(temporary)
        shutil.copyfile(source / 'native/overlay-renderer/renderer.cpp', stage / 'renderer.cpp')
        # All variable paths are in quoted batch positions. Never interpolate
        # paths containing cmd expansion/metacharacters into executable commands.
        if any(c in str(vcvars) + str(stage) for c in '%!^&|<>\r\n"'):
            raise ValueError('Unsupported toolchain or temporary path.')
        command = stage / 'compile.cmd'
        command.write_text('@echo off\ncall "' + str(vcvars) + '" >nul\n'
            'if errorlevel 1 exit /b 1\n'
            'cl /nologo /LD /O2 /MT /W4 /EHsc /std:c++17 /DUNICODE /D_UNICODE '
            'renderer.cpp /link /OUT:sexo2-overlay-renderer.dll '
            'd3d11.lib dxgi.lib d2d1.lib dwrite.lib dcomp.lib user32.lib ole32.lib\n', encoding='utf-8')
        subprocess.run(['cmd.exe', '/d', '/c', str(command)], cwd=stage, check=True)
        body = (stage / output.name).read_bytes()
        from sexo2.install.packaging import is_pe
        if not is_pe(body) or not 1024 < len(body) < 8 * 1024 * 1024:
            raise ValueError('Invalid composition renderer output.')
        output.write_bytes(body)
    return hashlib.sha256(body).hexdigest()


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    print('Composition renderer SHA-256: ' + build(Path(__file__).resolve().parents[1]))
