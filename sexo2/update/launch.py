"""Run helper from temporary storage so its installed binary can be updated."""
from pathlib import Path
import shutil
import subprocess
import tempfile

def launch_updater(installation):
    executable=Path(installation)/'SEXO2 Update.exe'
    if not executable.is_file():raise ValueError('Atualizador ausente.')
    temp=Path(tempfile.gettempdir())/'SEXO2-updater'
    if temp.exists() and (temp.is_symlink() or temp.is_junction()):raise ValueError('Pasta temporária inválida.')
    temp.mkdir(exist_ok=True)
    helper=temp/executable.name
    shutil.copy2(executable,helper)
    subprocess.Popen([str(helper),'--install-dir',str(installation)],
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
