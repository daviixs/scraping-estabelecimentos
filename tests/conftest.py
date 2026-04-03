from pathlib import Path
import uuid

import pytest


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
