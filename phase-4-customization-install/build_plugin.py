#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Assemble the plugin from the phase folders and zip it.

    uv run phase-4-customization-install/build_plugin.py

Sources (each phase owns its part):
  phase-2-summarizing-input/skill/article-summary/      -> skills/article-summary/
  phase-3-discussion-memory/skill/discussion-memory/    -> skills/discussion-memory/
  phase-3-discussion-memory/folder-template/            -> folder-template/
  phase-4-customization-install/skill/settings-presets/ -> skills/settings-presets/
  phase-4-customization-install/folder-template/        -> folder-template/
  phase-4-customization-install/plugin-src/             -> plugin root (manifest, hooks)
Output:
  phase-4-customization-install/build/research-assistant/     (unzipped, for --plugin-dir)
  phase-4-customization-install/dist/research-assistant-plugin.zip
"""
import pathlib
import shutil
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
BUILD = HERE / "build" / "research-assistant"
ZIP = HERE / "dist" / "research-assistant-plugin.zip"

PARTS = [
    (HERE / "plugin-src", ""),
    (REPO / "phase-2-summarizing-input/skill/article-summary", "skills/article-summary"),
    (REPO / "phase-3-discussion-memory/skill/discussion-memory", "skills/discussion-memory"),
    (HERE / "skill/settings-presets", "skills/settings-presets"),
    (REPO / "phase-3-discussion-memory/folder-template", "folder-template"),
    (HERE / "folder-template", "folder-template"),
]
REQUIRED = [
    ".claude-plugin/plugin.json",
    "hooks/hooks.json",
    "hooks/session-start.sh",
    "skills/article-summary/SKILL.md",
    "skills/discussion-memory/SKILL.md",
    "skills/settings-presets/SKILL.md",
    "folder-template/CLAUDE.md",
    "folder-template/memory/INDEX.md",
    "folder-template/memory/SETTINGS.md",
]


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    for src, dest in PARTS:
        shutil.copytree(src, BUILD / dest, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"))
    (BUILD / "folder-template" / "articles").mkdir(exist_ok=True)
    (BUILD / "folder-template" / "articles" / "README.md").write_text(
        "Article PDFs go here. Drop them in, or let Claude save the open-access copies it finds.\n")
    missing = [r for r in REQUIRED if not (BUILD / r).is_file()]
    if missing:
        print("missing from build:", missing)
        return 1
    ZIP.parent.mkdir(exist_ok=True)
    if ZIP.exists():
        ZIP.unlink()
    files = sorted(p for p in BUILD.rglob("*") if p.is_file())
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            info = zipfile.ZipInfo(str(p.relative_to(BUILD)), date_time=(2026, 11, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if p.suffix == ".sh" else 0o644) << 16
            z.writestr(info, p.read_bytes())
    print(f"built {ZIP.relative_to(REPO)}: {len(files)} files, {ZIP.stat().st_size} bytes")
    for p in files:
        print("  ", p.relative_to(BUILD))
    return 0


if __name__ == "__main__":
    sys.exit(main())
