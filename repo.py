"""Clonado de repositorios GitHub en el workspace local.

Migrado desde el notebook del TP1 (celda 6). En el notebook el workspace era
/content/workspace (Colab); acá es ./workspace en el root del proyecto.
"""

import os
import shutil
import subprocess
from pathlib import Path

WORKSPACE = Path(os.getenv("AGENT_WORKSPACE", "./workspace")).resolve()


def clone_repo(repo_url, chdir=True):
    """Clona (shallow) un repo en el workspace y opcionalmente hace chdir.

    Args:
        repo_url (str): URL del repositorio a clonar.
        chdir (bool): si True, cambia el cwd al repo clonado.

    Returns:
        Path | None: ruta al repo clonado, o None si falló.
    """
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    repo_path = WORKSPACE / repo_name

    WORKSPACE.mkdir(parents=True, exist_ok=True)

    if repo_path.exists():
        print(f"⚠️  Removing existing repo at {repo_path}")
        shutil.rmtree(repo_path)

    print(f"Cloning {repo_url} ...")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )

    if result.returncode != 0:
        print("❌ Clone failed:")
        print(result.stderr)
        return None

    print(f"✅ Repo cloned to: {repo_path}")
    print("\n📂 Repository contents:")
    for item in sorted(repo_path.iterdir()):
        marker = "📁" if item.is_dir() else "📄"
        print(f"  {marker} {item.name}")

    if chdir:
        os.chdir(repo_path)
        print(f"\n Working directory: {os.getcwd()}")

    return repo_path
