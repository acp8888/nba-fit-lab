.PHONY: ingest transform lab

ingest:
	uv run nba-fit-ingest bbref data/local/raw/bbref/2026-07-12/*.csv

transform:
	echo "transforming..."

lab:
	echo "doing lab stuff..."