from pathlib import Path
import sys
import uuid

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture(scope="function")
def temp_db_path():
    base_dir = Path("tests") / ".tmp_db"
    base_dir.mkdir(exist_ok=True)
    db_path = base_dir / f"{uuid.uuid4().hex}.db"
    yield db_path
    try:
        if db_path.exists():
            db_path.unlink()
    except PermissionError:
        pass
