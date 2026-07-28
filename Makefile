.PHONY: ingest transform lab

ingest:
	uv run nba-fit-ingest bbref data/local/raw/bbref/2026-07-08/*.csv
	uv run nba-fit-ingest ctg data/local/raw/ctg/2026-07-08/*.csv
	uv run nba-fit-ingest darko data/local/raw/darko/2026-07-08/*.csv
	uv run nba-fit-ingest pbpstats data/local/raw/pbpstats/2026-07-08/*.csv

transform:
	uv run python transform/run.py

lab:
	echo "doing lab stuff..."