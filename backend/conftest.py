# pytest 环境隔离：必须在导入 app 之前设置（强制离线，避免测试消耗 API）
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="riskcite-test-")
os.environ["DATA_DIR"] = _TMP
os.environ["CHROMA_DIR"] = os.path.join(_TMP, "chroma")
os.environ["UPLOAD_DIR"] = os.path.join(_TMP, "uploads")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP, "app.db")
os.environ["LLM_API_KEY"] = ""
os.environ["EMBEDDING_PROVIDER"] = "offline"
os.environ["EMBEDDING_API_KEY"] = ""
os.environ["RERANKER_API_KEY"] = ""
