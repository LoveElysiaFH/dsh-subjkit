#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""subjkit —— 学科材料排版与图示工具。

用法：
    python subjkit.py --help
    python subjkit.py doctor
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from subjkit.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
