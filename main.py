from pathlib import Path
import sys

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from cli.main import main  # noqa: E402


if __name__ == "__main__":
    main()
