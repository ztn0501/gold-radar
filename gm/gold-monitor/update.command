#!/bin/bash
cd "$(dirname "$0")"
echo "============================================"
echo "  黄金盯盘台 - 一键更新数据"
echo "============================================"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[失败] 未找到 python3，请先安装 Python 3"
  read -n 1 -s -r -p "按任意键关闭..."
  exit 1
fi
python3 update.py || { read -n 1 -s -r -p "更新失败，按任意键关闭..."; exit 1; }
open "index.html"
