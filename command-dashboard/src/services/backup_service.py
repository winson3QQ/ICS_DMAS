"""
backup_service.py — 指揮部 SQLite 自動備份服務

對應 ROADMAP C3-D；NIST 800-53 CP-9 / CP-10、CIS Controls v8 §11、
個資法 §27 安全維護義務。

設計原則：
- 用 SQLite online backup API（sqlite3.Connection.backup）— 相容 WAL，
  並發寫入時仍能取得 consistent snapshot
- gzip 壓縮 + sha256 校驗 + atomic write（先寫 .tmp 再 rename）
- 30 天 rolling retention（可設定）
- License 無感（per Decision E：法規 / 安全功能不接受 license 控制；
  全 tier 必開）
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import shutil
import sqlite3
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

log = logging.getLogger("ics.backup")

DEFAULT_RETAIN_DAYS = 30
BACKUP_FILENAME_PATTERN = "ics-%Y-%m-%dT%H-%M-%SZ.db.gz"


@dataclass
class BackupResult:
    path: Path
    size_bytes: int
    duration_ms: int
    timestamp: datetime
    sha256: str


@dataclass
class BackupInfo:
    path: Path
    size_bytes: int
    timestamp: datetime  # parsed from filename


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _format_filename(ts: datetime) -> str:
    return ts.strftime(BACKUP_FILENAME_PATTERN)


def _parse_timestamp(filename: str) -> datetime | None:
    try:
        return datetime.strptime(filename, BACKUP_FILENAME_PATTERN).replace(tzinfo=UTC)
    except ValueError:
        return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def create_backup(
    db_path: Path,
    backup_dir: Path,
    *,
    timestamp: datetime | None = None,
) -> BackupResult:
    """產生 SQLite gzipped backup。

    使用 online backup API 取得 consistent snapshot（即使 source DB 正在寫入）。
    寫入採 atomic：先寫 .tmp，校驗後 rename。
    """
    if not db_path.exists():
        raise FileNotFoundError(f"來源 DB 不存在：{db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp or _now_utc()
    final_path = backup_dir / _format_filename(ts)
    tmp_gz = final_path.with_suffix(final_path.suffix + ".tmp")

    started = time.perf_counter()

    with tempfile.NamedTemporaryFile(
        prefix="ics-backup-", suffix=".db", dir=backup_dir, delete=False
    ) as raw_tmp:
        raw_tmp_path = Path(raw_tmp.name)

    try:
        src = sqlite3.connect(str(db_path))
        try:
            dst = sqlite3.connect(str(raw_tmp_path))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()

        with raw_tmp_path.open("rb") as fin, gzip.open(tmp_gz, "wb", compresslevel=6) as fout:
            shutil.copyfileobj(fin, fout)

        digest = _sha256_file(tmp_gz)
        size = tmp_gz.stat().st_size
        tmp_gz.replace(final_path)
        duration_ms = int((time.perf_counter() - started) * 1000)

        log.info(
            "backup_created path=%s size=%d sha256=%s duration_ms=%d",
            final_path,
            size,
            digest,
            duration_ms,
        )
        return BackupResult(
            path=final_path,
            size_bytes=size,
            duration_ms=duration_ms,
            timestamp=ts,
            sha256=digest,
        )
    except Exception:
        if tmp_gz.exists():
            tmp_gz.unlink(missing_ok=True)
        raise
    finally:
        raw_tmp_path.unlink(missing_ok=True)


def list_backups(backup_dir: Path) -> list[BackupInfo]:
    """列出所有 backup（timestamp 由舊到新排序）。"""
    if not backup_dir.exists():
        return []
    out: list[BackupInfo] = []
    for p in backup_dir.iterdir():
        if not p.is_file() or not p.name.endswith(".db.gz"):
            continue
        ts = _parse_timestamp(p.name)
        if ts is None:
            continue
        out.append(BackupInfo(path=p, size_bytes=p.stat().st_size, timestamp=ts))
    out.sort(key=lambda b: b.timestamp)
    return out


def cleanup_old_backups(
    backup_dir: Path,
    retain_days: int = DEFAULT_RETAIN_DAYS,
    *,
    now: datetime | None = None,
) -> list[Path]:
    """刪除超過 retain_days 的 backup，回傳被刪的路徑清單。"""
    cutoff = (now or _now_utc()) - timedelta(days=retain_days)
    deleted: list[Path] = []
    for b in list_backups(backup_dir):
        # 邊界含在內：保留最近 retain_days 天 → 第 retain_days 天當天的備份視為過期
        if b.timestamp <= cutoff:
            b.path.unlink()
            deleted.append(b.path)
            log.info("backup_deleted path=%s age_days=%d", b.path, (cutoff - b.timestamp).days)
    return deleted


def verify_backup(backup_path: Path) -> bool:
    """驗證 backup 是有效 SQLite + schema_migrations 表存在。"""
    if not backup_path.exists() or not backup_path.name.endswith(".db.gz"):
        return False
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with gzip.open(backup_path, "rb") as fin, tmp_path.open("wb") as fout:
            shutil.copyfileobj(fin, fout)
        conn = sqlite3.connect(str(tmp_path))
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            return row is not None
        finally:
            conn.close()
    except (gzip.BadGzipFile, sqlite3.DatabaseError):
        return False
    finally:
        tmp_path.unlink(missing_ok=True)


def restore_backup(
    backup_path: Path,
    target_db_path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """從 backup 還原到 target。

    safety：預設 overwrite=False；如果 target 已存在會 raise。
    要強制還原請明確帶 overwrite=True（playbook 應記錄此操作）。
    """
    if not verify_backup(backup_path):
        raise ValueError(f"backup 無效或損毀：{backup_path}")
    if target_db_path.exists() and not overwrite:
        raise FileExistsError(
            f"目標已存在：{target_db_path}（要覆寫請明確帶 overwrite=True，並先備份當前 DB）"
        )
    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(backup_path, "rb") as fin, target_db_path.open("wb") as fout:
        shutil.copyfileobj(fin, fout)
    log.info("backup_restored from=%s to=%s", backup_path, target_db_path)
    return target_db_path
