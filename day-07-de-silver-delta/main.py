import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from silver.__main__ import main  # noqa: E402

raise SystemExit(main())
