.PHONY: ingest transform lab tour a2 a3 a4 walkthrough

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

lab:
	uv run marimo edit notebooks/10_lineup_explorer.py

tour:
	uv run marimo edit notebooks/00_tour.py

a2:
	uv run marimo edit notebooks/20_a2_scarcity.py

a3:
	uv run marimo edit notebooks/30_a3_opponents.py

a4:
	uv run marimo edit notebooks/40_a4_projection.py

walkthrough:
	uv run marimo edit notebooks/50_data_walkthrough.py
