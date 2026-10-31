# -*- coding: utf-8 -*-
"""把 skills/ 下的技能安装到 DeepSeek Harness 的技能目录。

默认装到用户级：%USERPROFILE%\\.dsh\\skills（所有会话可见）。
也可以只装到当前工作区：python install.py --project
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills"


def install_one(src: Path, dest_root: Path) -> Path:
    dst = dest_root / src.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for md in dst.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        md.write_text(text.replace("@@TOOL_DIR@@", str(ROOT)), encoding="utf-8")
    return dst


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="安装 subjkit 的 DSH 技能")
    parser.add_argument("--dest", help="技能目录（默认 ~/.dsh/skills）")
    parser.add_argument("--project", action="store_true", help="装到当前目录的 .dsh/skills")
    parser.add_argument("--list", action="store_true", help="只列出技能")
    args = parser.parse_args()

    if not SKILLS.exists():
        print("✘ 找不到 skills/ 目录")
        return 1
    names = sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists())
    if args.list:
        for n in names:
            print(n)
        return 0

    dest = Path(args.dest).expanduser() if args.dest else (
        Path.cwd() / ".dsh" / "skills" if args.project else Path.home() / ".dsh" / "skills"
    )
    dest.mkdir(parents=True, exist_ok=True)
    print(f"安装到：{dest}")
    for name in names:
        path = install_one(SKILLS / name, dest)
        print(f"  ✔ {name} → {path}")
    print("\n完成。新开的 DSH 会话会在技能列表里看到 subjkit；"
          "\n当前已开启的会话如果没看到，新开一个会话即可。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
