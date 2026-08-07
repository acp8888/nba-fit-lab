import sys
from pathlib import Path
from nba_fit.ingest import upload_files


def main():
    source = sys.argv[1]
    files = [Path(p) for p in sys.argv[2:]]
    upload_files(source, files)


if __name__ == "__main__":
    main()
