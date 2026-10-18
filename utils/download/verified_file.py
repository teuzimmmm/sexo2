"""Do not expose an interrupted or corrupt download as a usable skin."""

from pathlib import Path
import zipfile
from utils.core.atomic_file import atomic_write


def write_download(response, destination, chunk_size=65536):
    path = Path(destination)
    with atomic_write(path, "w+b") as output:
        count = 0
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                output.write(chunk)
                count += len(chunk)
        output.flush()
        length = response.headers.get("Content-Length")
        if length and not response.headers.get("Content-Encoding") and count != int(length):
            raise ValueError("Download incompleto. O arquivo anterior foi preservado.")
        if not count:
            raise ValueError("Download vazio.")
        if path.suffix.lower() == ".zip":
            output.seek(0)
            with zipfile.ZipFile(output) as archive:
                if not archive.infolist() or archive.testzip() is not None:
                    raise ValueError("Arquivo da skin corrompido.")
