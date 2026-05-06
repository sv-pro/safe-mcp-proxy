# `demos/product/dashboard/`

Dashboard and API demo entry points.

## `demo.py`

Generates ten audit decisions, then verifies:

- `GET /stats`
- `GET /worlds/current`
- `GET /dashboard`

Run:

```bash
python -m demos.product.dashboard.demo
```

## `web_launcher.py`

Starts the FastAPI app and opens the dashboard in a browser.

Run:

```bash
python -m demos.product.dashboard.web_launcher
```

Legacy command:

```bash
python run_demo.py
```

The top-level `run_demo.py` is now only a compatibility wrapper around this
launcher.
