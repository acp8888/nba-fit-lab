.PHONY: ingest transform notebook

ingest:
	uv run nba-fit-ingest bbref data/local/raw/bbref/2026-07-08/*.csv
	uv run nba-fit-ingest ctg data/local/raw/ctg/2026-07-08/*.csv
	uv run nba-fit-ingest darko data/local/raw/darko/2026-07-08/*.csv
	uv run nba-fit-ingest pbpstats data/local/raw/pbpstats/2026-07-08/*.csv
	# 2024-25 prior-season pull (held-out replication + 2-man/on-off pair synergy)
	uv run nba-fit-ingest bbref data/local/raw/bbref/2025-07-08/*.csv
	uv run nba-fit-ingest darko data/local/raw/darko/2025-07-08/*.csv
	uv run nba-fit-ingest nbastats data/local/raw/nbastats/2025-07-08/*.csv
	uv run nba-fit-ingest pbpstats data/local/raw/pbpstats/2025-07-08/*.csv

transform:
	uv run python transform/run.py

# The single analysis notebook — a per-blog-post walkthrough of the whole series.
notebook:
	uv run marimo edit notebooks/walkthrough.py
