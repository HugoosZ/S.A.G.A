"""
Script para compilar SAGA como ejecutable usando PyInstaller.

Uso:
    python build.py

Genera:
    - dist/SAGA.exe         (Windows)
    - dist/SAGA             (macOS / Linux)
"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "SAGA"


def build():
    # Asegurarse de que PyInstaller esté instalado
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller no está instalado. Instalando…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"]
        )

    # Limpiar builds anteriores
    for d in ["build", "dist", f"{NAME}.spec"]:
        path = ROOT / d
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()

    # Detectar carpeta de CustomTkinter para incluir sus assets
    import customtkinter
    ctk_path = Path(customtkinter.__file__).parent

    # Argumentos de PyInstaller
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", NAME,
        "--onedir",            # Cambia a --onefile si se prefiere un solo ejecutable
        "--windowed",          # Sin consola (importante en Windows)
        "--clean",
        "--noconfirm",
        f"--add-data={ctk_path}{_sep()}customtkinter",
        "--collect-all", "customtkinter",
        "main.py",
    ]

    print("Ejecutando PyInstaller...")
    print(" ".join(args))
    subprocess.check_call(args)

    print()
    print("─" * 60)
    print(f"  Compilación completada.")
    print(f"  Ejecutable generado en: dist/{NAME}/")
    print("─" * 60)


def _sep():
    """Separador requerido por PyInstaller para --add-data."""
    return ";" if sys.platform.startswith("win") else ":"


if __name__ == "__main__":
    build()
