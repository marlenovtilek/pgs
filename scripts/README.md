# scripts/

Operational / performance checks that need a real PostgreSQL backend, so
they live here instead of the SQLite-based pytest suite. Each script builds
its own isolated data (a dedicated floor) and removes it afterwards.

Run them inside the stack (the `scripts/` dir is mounted, like `tests/`):

```bash
# Sequential throughput: 1800 spots, ingest + worst-case recalc
docker compose run --rm -v ./scripts:/app/scripts pgs-api python -m scripts.load_test

# Smaller / custom size
docker compose run --rm -v ./scripts:/app/scripts pgs-api \
  python -m scripts.load_test --zones 50 --spots-per-zone 6

# Race handling: concurrent auto-create + dedup (exit code != 0 on failure)
docker compose run --rm -v ./scripts:/app/scripts pgs-api python -m scripts.concurrency_test
```

`concurrency_test` exits non-zero if any scenario is wrong, so it is safe to
wire into CI as a gate. `load_test` only reports throughput numbers.
