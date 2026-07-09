"""生成历史持久化服务

使用 SQLite 存储生成历史，支持：
- 自动建表
- 记录存取
- 分页查询
- 按 prompt/style/backend 搜索
- 自动清理旧记录（默认保留 500 条）
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.models.schemas import (
    GenerationResponse,
    HistoryListResponse,
    HistoryRecord,
    QualityBreakdown,
)

logger = logging.getLogger(__name__)

DB_PATH = Path("data/history.db")
MAX_RECORDS = 500


class HistoryService:
    """生成历史 SQLite 服务"""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """建表"""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    style TEXT,
                    backend TEXT NOT NULL,
                    best_score REAL,
                    image_count INTEGER NOT NULL,
                    generation_time REAL NOT NULL,
                    refinement_rounds INTEGER NOT NULL DEFAULT 0,
                    best_image_data TEXT NOT NULL,
                    best_seed INTEGER NOT NULL,
                    optimized_prompt_text TEXT NOT NULL,
                    quality_breakdown_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_created
                ON history(created_at DESC)
            """)
        logger.info("历史数据库已初始化: %s", self.db_path)

    def _connect(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, response: GenerationResponse) -> str:
        """保存生成结果到历史"""
        record_id = response.session_id

        breakdown_json = None
        if response.best_image.quality_breakdown:
            breakdown_json = response.best_image.quality_breakdown.model_dump_json()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO history
                    (id, created_at, prompt, style, backend,
                     best_score, image_count, generation_time,
                     refinement_rounds, best_image_data, best_seed,
                     optimized_prompt_text, quality_breakdown_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    datetime.now(timezone.utc).isoformat(),
                    response.optimized_prompt.original,
                    response.optimized_prompt.style.value,
                    response.backend_used,
                    response.best_image.quality_score,
                    len(response.images),
                    response.generation_time,
                    response.refinement_rounds,
                    response.best_image.image_data,
                    response.best_image.seed,
                    response.optimized_prompt.enhanced,
                    breakdown_json,
                ),
            )

            # 自动清理旧记录（必须在 with 块内，否则 DELETE 不会被 commit）
            self._cleanup(conn)
        logger.debug("历史记录已保存: %s", record_id)
        return record_id

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        backend: str | None = None,
    ) -> HistoryListResponse:
        """分页查询历史记录

        Args:
            page: 页码 (1-based)
            page_size: 每页数量
            search: 搜索关键词（匹配 prompt）
            backend: 按后端过滤 ("sd" | "flux")
        """
        conditions = []
        params: list = []

        if search:
            conditions.append("prompt LIKE ?")
            params.append(f"%{search}%")
        if backend:
            conditions.append("backend = ?")
            params.append(backend)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        with self._connect() as conn:
            # 总数
            count_row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM history {where_clause}", params
            ).fetchone()
            total = count_row["cnt"] if count_row else 0

            # 分页数据
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"""
                SELECT * FROM history {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            ).fetchall()

        records = [self._row_to_record(row) for row in rows]
        return HistoryListResponse(
            records=records,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get(self, record_id: str) -> HistoryRecord | None:
        """获取单条记录"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM history WHERE id = ?", (record_id,)
            ).fetchone()

        if row is None:
            return None
        return self._row_to_record(row)

    def delete(self, record_id: str) -> bool:
        """删除单条记录"""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM history WHERE id = ?", (record_id,))
            return cursor.rowcount > 0

    def _row_to_record(self, row: sqlite3.Row) -> HistoryRecord:
        """数据库行 → HistoryRecord"""
        breakdown = None
        if row["quality_breakdown_json"]:
            try:
                breakdown = QualityBreakdown.model_validate_json(
                    row["quality_breakdown_json"]
                )
            except Exception:
                pass

        return HistoryRecord(
            id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            prompt=row["prompt"],
            style=row["style"],
            backend=row["backend"],
            best_score=row["best_score"],
            image_count=row["image_count"],
            generation_time=row["generation_time"],
            refinement_rounds=row["refinement_rounds"],
            best_image_data=row["best_image_data"],
            best_seed=row["best_seed"],
            optimized_prompt_text=row["optimized_prompt_text"],
            quality_breakdown=breakdown,
        )

    def _cleanup(self, conn: sqlite3.Connection) -> None:
        """保留最新 MAX_RECORDS 条，删除旧数据"""
        try:
            conn.execute(
                f"""
                DELETE FROM history WHERE id NOT IN (
                    SELECT id FROM history ORDER BY created_at DESC LIMIT {MAX_RECORDS}
                )
                """
            )
        except Exception as e:
            logger.debug("历史清理异常: %s", e)
