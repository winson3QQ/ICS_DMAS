#!/usr/bin/env python3
"""
restore_db.py — CLI entry point for SQLite backup 還原

對應 docs/ops/disaster_recovery.md 情境 A/B 步驟 4。
邏輯實作在 src/services/backup_service.py。

使用方式：
    # 還原到新位置（safe）
    python scripts/restore_db.py --backup data/backups/X.db.gz --target /tmp/test.db

    # 覆寫 production DB（destructive — 必須明確帶 --overwrite）
    python scripts/restore_db.py --backup data/backups/X.db.gz \\
        --target data/ics.db --overwrite

注意：
- 必須先停服務（systemctl stop ics-command）
- 必須先備份當前 DB（cp data/ics.db data/ics.db.suspect.<timestamp>）
- 還原後驗證 schema_migrations + events 計數再啟服務
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from services.backup_service import (  # noqa: E402
    list_backups,
    restore_backup,
    verify_backup,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ICS_DMAS 從 backup 還原 SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--backup", type=Path, required=True, help="backup 檔（.db.gz）")
    parser.add_argument("--target", type=Path, required=True, help="還原目標路徑")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="允許覆寫已存在的 target（destructive — 確認已備份當前 DB）",
    )
    parser.add_argument("--list", action="store_true", help="列出 backup_dir 所有 backup")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=ROOT / "data" / "backups",
        help="backup 目錄（搭配 --list；預設 data/backups/）",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    log = logging.getLogger("ics.restore.cli")

    if args.list:
        backups = list_backups(args.backup_dir)
        if not backups:
            print(f"(no backup in {args.backup_dir})")
            return 0
        for b in backups:
            print(f"{b.timestamp.isoformat()}  {b.size_bytes:>10}  {b.path.name}")
        return 0

    if not verify_backup(args.backup):
        log.error("backup 無效或損毀：%s", args.backup)
        return 1

    if args.target.exists() and not args.overwrite:
        log.error(
            "目標已存在：%s — 確認你已備份當前 DB，再加 --overwrite 重跑",
            args.target,
        )
        return 2

    try:
        restored = restore_backup(args.backup, args.target, overwrite=args.overwrite)
        log.info("restore_done from=%s to=%s size=%d", args.backup, restored, restored.stat().st_size)
        log.info("驗證指令：sqlite3 %s 'SELECT version FROM schema_migrations;'", restored)
        return 0
    except Exception as e:
        log.exception("restore_failed reason=%s", e)
        return 3


if __name__ == "__main__":
    sys.exit(main())
