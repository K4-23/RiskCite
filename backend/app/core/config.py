# 读仓库根目录的 env
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]          # backend/
REPO_ROOT = BACKEND_DIR.parent                            # 仓库根
load_dotenv(REPO_ROOT / "env")
load_dotenv(BACKEND_DIR / ".env", override=False)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass
class Settings:
    """全局配置。密钥类只从 env 文件读入服务端内存，接口响应不回显。"""
    app_name: str = _env("APP_NAME", "知险有据")
    app_env: str = _env("APP_ENV", "development")
    host: str = _env("APP_HOST", "127.0.0.1")
    port: int = int(_env("APP_PORT", "8000") or 8000)

    # 模型可不填
    llm_model: str = _env("LLM_MODEL", "qwen3-vl-plus")
    llm_api_key: str = _env("LLM_API_KEY", "")
    llm_base_url: str = _env("LLM_BASE_URL", "")

    embedding_provider: str = _env("EMBEDDING_PROVIDER", "dashscope")
    embedding_model: str = _env("EMBEDDING_MODEL", "")
    embedding_api_key: str = _env("EMBEDDING_API_KEY", "") or _env("DASHSCOPE_API_KEY", "")
    embedding_base_url: str = _env("EMBEDDING_BASE_URL", "")

    reranker_model: str = _env("RERANKER_MODEL", "")
    reranker_api_key: str = _env("RERANKER_API_KEY", "") or _env("DASHSCOPE_API_KEY", "")
    reranker_base_url: str = _env("RERANKER_BASE_URL", "")

    chroma_dir: str = _env("CHROMA_DIR", str(BACKEND_DIR / ".chroma"))
    data_dir: str = _env("DATA_DIR", str(BACKEND_DIR / ".data"))
    database_url: str = _env("DATABASE_URL", "")
    upload_dir: str = _env("UPLOAD_DIR", "")

    rerank_top_n: int = int(_env("RERANK_TOP_N", "8") or 8)
    evidence_top_n: int = int(_env("EVIDENCE_TOP_N", "8") or 8)

    # 模型不支持 tool calling 时回退 JSON 循环
    tool_calling: bool = _env("TOOL_CALLING", "1").strip().lower() not in {"0", "false", "off", "no"}

    material_text_limit: int = int(_env("MATERIAL_TEXT_LIMIT", "60000") or 60000)
    material_slice_limit: int = int(_env("MATERIAL_SLICE_LIMIT", "5000") or 5000)

    @property
    def db_path(self) -> Path:
        return Path(self.database_url.replace("sqlite:///", "")) if self.database_url else Path(self.data_dir) / "app.db"

    @property
    def uploads_path(self) -> Path:
        return Path(self.upload_dir) if self.upload_dir else Path(self.data_dir) / "uploads"

    @property
    def logs_path(self) -> Path:
        return Path(self.data_dir) / "logs"

    def ensure_dirs(self) -> None:
        for p in (Path(self.chroma_dir), Path(self.data_dir), self.uploads_path, self.logs_path):
            p.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
