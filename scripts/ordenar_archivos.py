"""Orden seguro de candidatos de Bodegas Gestion.
Uso: python scripts\ordenar_archivos.py | --aplicar | --revertir MANIFIESTO
"""
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "historico" / "2026-11-03-orden"
BACKUP = Path(r"E:\_ARCHIVO_FERRETERIA\bodegas-orden-antes_2026-11-03")
EXTS = {".bat", ".py", ".html", ".js", ".json", ".md"}
EXCLUDE_DIRS = {".git", "historico"}


def rel(path):
    return str(path.relative_to(ROOT)).replace("/", "\\")


def all_files():
    for path in ROOT.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file() and path.suffix.lower() in EXTS:
            yield path


def references(name):
    found = []
    for path in all_files():
        try:
            if name.lower() in path.read_text(encoding="utf-8", errors="ignore").lower():
                found.append(rel(path))
        except OSError:
            pass
    return found


def candidates():
    paths = [ROOT / "monitor_sv.log", ROOT / "__pycache__", ROOT / "scripts" / "__pycache__"]
    for pattern in ("*respaldo*", "*backup*", "*copia*", "*.bak"):
        paths.extend(ROOT.glob(pattern))
    seen = set()
    for path in paths:
        if not path.exists() or path in seen:
            continue
        seen.add(path)
        refs = references(path.name)
        yield path, refs


def manifest_path():
    return DEST / "MANIFIESTO.md"


def report(actions):
    print("== INFORME (no mueve nada)")
    for src, refs in actions:
        if refs:
            print(f"BLOQUEADO {rel(src)} referencias: {', '.join(refs[:8])}")
        else:
            print(f"SEGURO {rel(src)}")


def apply(actions):
    movable = [(src, refs) for src, refs in actions if not refs]
    DEST.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Manifiesto orden B1/B2",
        "",
        f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "Revertir: python scripts\\ordenar_archivos.py --revertir "+str(manifest_path()),
        "",
        "| ruta original | ruta nueva | motivo |",
        "|---|---|---|",
    ]
    for src, _ in movable:
        target = DEST / src.name
        if target.exists():
            target = DEST / f"{src.stem}_{time.strftime('%Y%m%d')}{src.suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, BACKUP / src.name) if src.is_file() else shutil.copytree(src, BACKUP / src.name, dirs_exist_ok=True)
        shutil.move(str(src), str(target))
        lines.append(f"| {rel(src)} | {target} | candidato sin referencias |")
    manifest_path().write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Movidos: {len(movable)}; manifiesto: {manifest_path()}")


def revert(manifest):
    count = 0
    for line in Path(manifest).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or "ruta original" in line or line.startswith("|---"):
            continue
        original, target, _ = [part.strip() for part in line.strip("| ").split("|")[:3]]
        src = ROOT / original
        dst = Path(target)
        if dst.exists() and not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
            count += 1
    print(f"Devueltos: {count}")


args = sys.argv[1:]
if args[:1] == ["--revertir"] and len(args) > 1:
    revert(args[1])
else:
    found = list(candidates())
    report(found)
    if "--aplicar" in args:
        apply(found)
