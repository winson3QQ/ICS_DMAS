#!/usr/bin/env python3
"""
backup_db.py — CLI entry point for SQLite 自動備份

systemd timer 直接呼叫此腳本（每日 03:00）。
邏輯實作在 src/services/backup_service.py。

使用方式：
    python scripts/backup_db.py                # 用預設路徑
    python scripts/backup_db.py --retain-days 60
    python scripts/backup_db.py --verify-only  # 只驗證最新 backup，不新建
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 加入 src 到 path（讓 systemd 從 command-dashboard/ 啟動時可 import）
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from services.backup_service import (  # noqa: E402
    DEFAULT_RETAIN_DAYS,
    cleanup_old_backups,
    create_backup,
    list_backups,
    verify_backup,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="ICS_DMAS 指揮部 SQLite backup")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=ROOT / "data" / "ics.db",
        help="來源 DB 路徑（預設 data/ics.db）",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=ROOT / "data" / "backups",
        help="backup 輸出目錄（預設 data/backups/）",
    )
    parser.add_argument(
        "--retain-days",
        type=int,
        default=DEFAULT_RETAIN_DAYS,
        help=f"保留天數（預設 {DEFAULT_RETAIN_DAYS} 天）",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="只驗證最新 backup，不新建",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="跳過過期 backup 清理",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    log = logging.getLogger("ics.backup.cli")

    if args.verify_only:
        backups = list_backups(args.backup_dir)
        if not backups:
            log.error("no backup found in %s", args.backup_dir)
            return 1
        latest = backups[-1]
        ok = verify_backup(latest.path)
        if ok:
            log.info("verify_ok path=%s size=%d", latest.path, latest.size_bytes)
            return 0
        log.error("verify_failed path=%s", latest.path)
        return 2

    try:
        result = create_backup(args.db_path, args.backup_dir)
        log.info(
            "backup_done path=%s size=%d sha256=%s duration_ms=%d",
            result.path,
            result.size_bytes,
            result.sha256,
            result.duration_ms,
        )
    except FileNotFoundError as e:
        log.error("backup_skip reason=db_missing %s", e)
        return 3
    except Exception as e:
        log.exception("backup_failed reason=%s", e)
        return 4

    if not args.no_cleanup:
        deleted = cleanup_old_backups(args.backup_dir, retain_days=args.retain_days)
        if deleted:
            log.info("cleanup_done deleted=%d retain_days=%d", len(deleted), args.retain_days)

    backups = list_backups(args.backup_dir)
    log.info(
        "backup_summary total=%d oldest=%s newest=%s",
        len(backups),
        backups[0].timestamp.isoformat() if backups else None,
        backups[-1].timestamp.isoformat() if backups else None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
