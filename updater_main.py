"""Independent helper: signed updates of an existing SEXO2 installation."""

import argparse, json, os, queue, tempfile, threading, sys, zipfile, subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import psutil
from sexo2.update.engine import apply_patch, digest, verify
from sexo2.update.client import check_release, download_asset
from sexo2.update.trust import PUBLIC_KEY
from sexo2.update.lifecycle import stop_installed_app, reopen_app, processes_for

# Only the application being replaced must be stopped. League is independent.
BLOCKED = {"sexo2.exe", "rose.exe"}


def ensure_closed(installation=None):
    if installation is not None:
        if processes_for(installation):
            raise ValueError("O SEXO2 ainda está em uso.")
        return
    for proc in psutil.process_iter(["name"]):
        if (proc.info.get("name") or "").lower() in BLOCKED:
            raise ValueError("Feche apenas o SEXO2 antes de aplicar. O LoL pode permanecer aberto.")


def refresh_shortcuts(installation):
    if os.name != "nt":
        return
    script = r"""$w = New-Object -ComObject WScript.Shell
$root = $env:SEXO2_UPDATE_PATH
$paths = @((Join-Path $w.SpecialFolders('Desktop') 'SEXO2.lnk'), (Join-Path $w.SpecialFolders('Programs') 'SEXO2\SEXO2.lnk'))
foreach ($path in $paths) {
 if (Test-Path -LiteralPath $path) {
  $link = $w.CreateShortcut($path)
  if ($link.TargetPath -ieq (Join-Path $root 'SEXO2.exe')) {
   $link.IconLocation = (Join-Path $root '_internal\assets\sexo2-black-v3.ico') + ',0'
   $link.Save()
  }
 }
}
"""
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "SEXO2_UPDATE_PATH": str(installation)},
        capture_output=True,
        timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=True,
    )
    import ctypes

    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def installed_default():
    if os.name == "nt":
        import winreg

        key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{B876AA51-DB38-448E-BD13-716F1C9DE750}_is1"
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, key) as reg:
                    return winreg.QueryValueEx(reg, "Inno Setup: App Path")[0]
            except OSError:
                pass
    return str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / "SEXO2")


def local_package(installation, folder=None):
    app = Path(installation) / "SEXO2.exe"
    if not app.is_file():
        return ""
    folder = (
        Path(folder)
        if folder is not None
        else (Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent)
    )
    current = digest(app)
    for file in folder.glob("SEXO2-update*.zip"):
        try:
            with zipfile.ZipFile(file) as z:
                data = verify(z.read("manifest.json"), z.read("manifest.sig"), PUBLIC_KEY)
                if data["files"].get("SEXO2.exe", {}).get("old") == current:
                    return str(file)
        except Exception:
            continue
    return ""


def plan_update(installation, selected="", folder=None):
    root = Path(installation)
    if not (root / "SEXO2.exe").is_file():
        raise ValueError("Escolha a pasta onde está o SEXO2.exe que você usa.")
    local = selected or local_package(root, folder)
    if local:
        if not Path(local).is_file():
            raise ValueError("O pacote selecionado não está disponível. Selecione novamente.")
        return root, local
    source = root / "_internal/assets/update-source.json"
    if not source.is_file():
        raise ValueError(
            "Esta versão precisa de um pacote de transição compatível. Extraia todos os arquivos do ZIP juntos e execute o atualizador dessa pasta. Não é necessário reinstalar."
        )
    return root, ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-dir")
    parser.add_argument("--package")
    args = parser.parse_args()
    app = tk.Tk()
    app.title("SEXO2 — Atualização")
    app.geometry("510x280")
    app.resizable(False, False)
    installation = tk.StringVar(value=args.install_dir or installed_default())
    package = tk.StringVar(value=args.package or local_package(installation.get()))
    status = tk.StringVar(
        value="Atualiza a instalação existente e preserva seus dados. O SEXO2 será fechado e aberto automaticamente. O LoL pode permanecer aberto."
    )
    tk.Label(app, text="SEXO2", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=12)
    tk.Label(app, text="Pasta instalada").pack(anchor="w", padx=20)
    row = tk.Frame(app)
    row.pack(fill="x", padx=20)
    tk.Entry(row, textvariable=installation).pack(side="left", fill="x", expand=True)
    tk.Button(
        row, text="Escolher", command=lambda: installation.set(filedialog.askdirectory() or installation.get())
    ).pack(side="right")
    tk.Button(
        app,
        text="Selecionar pacote local",
        command=lambda: package.set(
            filedialog.askopenfilename(filetypes=[("Atualização SEXO2", "*.zip")]) or package.get()
        ),
    ).pack(anchor="w", padx=20, pady=10)
    tk.Label(app, textvariable=status, wraplength=465, justify="left").pack(anchor="w", padx=20)
    events = queue.Queue()
    busy = [False]

    def apply():
        if busy[0]:
            return
        try:
            root, local = plan_update(installation.get(), package.get())
        except ValueError as error:
            status.set(str(error))
            return
        busy[0] = True
        button.config(state="disabled")
        status.set("Verificando pacote e instalação…")

        def work():
            try:
                closed = [False]

                def close_for_update():
                    if closed[0]:
                        ensure_closed(root)
                        return
                    events.put(("progress", "Fechando o SEXO2 para aplicar a atualização…"))
                    stop_installed_app(root)
                    closed[0] = True

                if local:
                    result = apply_patch(local, root, PUBLIC_KEY, close_for_update)
                else:
                    assets = root / "_internal/assets"
                    repo = json.loads((assets / "update-source.json").read_text(encoding="utf-8")).get("repository", "")
                    access = assets / "update-access.json"
                    token = json.loads(access.read_text(encoding="utf-8")).get("token", "") if access.exists() else ""
                    marker = root / "sexo2-release.json"
                    current = (
                        json.loads(marker.read_text(encoding="utf-8")).get("version", "1.4.7")
                        if marker.exists()
                        else "1.4.7"
                    )
                    release = check_release(repo, token, current)
                    if not release.get("available"):
                        raise ValueError(release["message"])
                    with tempfile.TemporaryDirectory(prefix="sexo2-download-") as temp:
                        file = download_asset(repo, token, release["assetId"], Path(temp) / "update.zip")
                        result = apply_patch(file, root, PUBLIC_KEY, close_for_update)
                try:
                    refresh_shortcuts(root)
                except Exception:
                    pass
                try:
                    reopen_app(root)
                    events.put(("success", result))
                except Exception:
                    events.put(("reopen-error", result))
            except Exception as error:
                suffix = ""
                if (
                    "closed" in locals()
                    and closed[0]
                    and not (root / ".sexo2-update/transaction/journal.json").exists()
                ):
                    try:
                        reopen_app(root)
                        suffix = " A versão anterior foi reaberta."
                    except Exception:
                        suffix = " Abra o SEXO2 pelo atalho."
                events.put(("error", str(error) + suffix))

        threading.Thread(target=work, daemon=True, name="SEXO2-Updater").start()

    button = tk.Button(app, text="Aplicar atualização", command=apply)
    button.pack(anchor="e", padx=20, pady=12)

    def poll():
        try:
            kind, value = events.get_nowait()
            if kind == "progress":
                status.set(value)
                app.after(100, poll)
                return
            busy[0] = False
            button.config(state="normal")
            if kind == "success":
                status.set("Atualizado para " + value + ". SEXO2 aberto novamente.")
                messagebox.showinfo("SEXO2", "Atualização concluída; seus dados foram preservados.")
            elif kind == "reopen-error":
                status.set(
                    "Atualizado para " + value + ". Abra o SEXO2 pelo atalho; não foi possível reabrir automaticamente."
                )
            else:
                status.set(value)
        except queue.Empty:
            pass
        app.after(100, poll)

    app.protocol(
        "WM_DELETE_WINDOW",
        lambda: messagebox.showinfo("SEXO2", "Aguarde a atualização terminar.") if busy[0] else app.destroy(),
    )
    poll()
    app.mainloop()


if __name__ == "__main__":
    main()
