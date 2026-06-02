"""FastAPI app entry point.

Run with:
    uvicorn alphaagent.api.main:app --reload --port 8000
or via the installed script:
    alphaagent-api
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alphaagent.api.envelope import ok
from alphaagent.api.routers import backtests, screeners, strategies
from alphaagent.api.routers.analysis import company, industry, market

app = FastAPI(title="AlphaAgent API", version="0.1.0")

# Single-user local dev: allow the Vite dev server by default. Tighten for prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(backtests.router, prefix="/api/backtests", tags=["backtests"])
app.include_router(screeners.router, prefix="/api/screeners", tags=["screeners"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(company.router, prefix="/api/analysis/company", tags=["analysis"])
app.include_router(industry.router, prefix="/api/analysis/industry", tags=["analysis"])
app.include_router(market.router, prefix="/api/analysis/market", tags=["analysis"])


@app.get("/api/health")
def health():
    return ok({"status": "ok"})


def run() -> None:  # pragma: no cover - installed-script entry
    import uvicorn

    uvicorn.run(
        "alphaagent.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":  # pragma: no cover
    run()
