"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # 品牌与业务
    brand: str = "newssweep"
    org_name: str = "澄明品牌公关 · 舆情值班组"
    org_size: str = "10 人 · 6 个消费品牌"
    seed_now: str = "2026-11-12T18:00:00+08:00"

    # 数据库
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "newssweep"
    db_user: str = "newssweep"
    db_password: str = "newssweep_pw_2026"
    db_schema: str = "newssweep"

    # 安全
    jwt_secret: str = "newssweep-jwt-secret-change-me-2026"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    seed_demo: bool = True
    rate_limit_collect_per_minute: int = 6
    rate_limit_detect_per_minute: int = 8
    rate_limit_default_per_minute: int = 240

    # 情感算法阈值（前端只展示后端回传值，绝不硬编码）
    sentiment_pos_threshold: float = 0.2
    sentiment_neg_threshold: float = -0.2
    sentiment_normalizer: float = 1.85
    negation_window: int = 3
    degree_lookback: int = 4
    negation_damping: float = 0.85
    exclaim_step: float = 0.05
    exclaim_cap: int = 4
    rhetoric_penalty: float = 0.32
    rhetoric_cap: int = 2

    # 爆发检测阈值
    burst_baseline_days: int = 7
    burst_z_threshold: float = 3.0
    burst_min_count: int = 5
    burst_ratio: float = 2.0
    burst_sigma_floor: float = 1.0
    burst_alert_z: float = 4.0
    burst_critical_z: float = 6.0

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
