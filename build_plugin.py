#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Assemble the plugin from plugin/ and zip it.

    uv run build_plugin.py

Source: plugin/ (skills/, manifest, folder-template/). plugin/merge-in/ is not part of
the build. Output:
  build/research-assistant/                  (unzipped, for --plugin-dir; gitignored)
  dist/research-assistant-plugin.zip

The plugin has no hooks (research/live-trial.md, "The trial's answer").
"""
import json
import pathlib
import shutil
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE
PLUGIN = HERE / "plugin"
BUILD = HERE / "build" / "research-assistant"
ZIP = HERE / "dist" / "research-assistant-plugin.zip"
REQUIRED = [
    ".claude-plugin/plugin.json",
    "skills/article-summary/SKILL.md",
    "skills/article-summary/scripts/quotes.py",
    "skills/discussion-memory/SKILL.md",
    "skills/settings-presets/SKILL.md",
    "folder-template/CLAUDE.md",
    "folder-template/memory/INDEX.md",
    "folder-template/memory/SETTINGS.md",
]


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    shutil.copytree(PLUGIN, BUILD,
                    ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "merge-in"))
    (BUILD / "folder-template" / "articles").mkdir(exist_ok=True)
    (BUILD / "folder-template" / "articles" / "README.md").write_text(
        "Article PDFs go here. Drop them in, or let Claude save the open-access copies it finds.\n")
    # The folder template is also written into the discussion-memory skill, so Claude can
    # create the files even where it cannot read the plugin's own folder.
    tpl = BUILD / "folder-template"
    block = "\n\n".join(
        f"`{name}`:\n\n````\n{(tpl / name).read_text().rstrip()}\n````"
        for name in ("memory/INDEX.md", "memory/SETTINGS.md", "CLAUDE.md"))
    skill = BUILD / "skills/discussion-memory/SKILL.md"
    text = skill.read_text()
    if "{{FOLDER_TEMPLATE}}" not in text:
        print("discussion-memory/SKILL.md has no {{FOLDER_TEMPLATE}} marker")
        return 1
    skill.write_text(text.replace("{{FOLDER_TEMPLATE}}", block))
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
