"""Test path setup. 让主仓库根目录运行 pytest 时能导入 test-debug-agent 的 src 包。"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
