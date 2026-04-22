from pathlib import Path
from typing import Final

SEARCH_INDEX_OUTPUT_FILENAME: Final[str] = "organizations.json"
ENCRYPTED_ENDPOINTS_OUTPUT_FILENAME: Final[str] = "endpoints.json"
SEARCH_INDEX_OUTPUT_DIR: Final[Path] = Path("static/search")
SEARCH_INDEX_TEMP_DIR: Final[Path] = Path("tmp/search_index")
