import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .api.pdf_routes import router
from .config import Settings
from .services.file_manager import FileManager


def create_app(settings=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        manager = FileManager(settings)
        app.state.manager = manager

        async def cleaner():
            while True:
                await asyncio.sleep(60)
                await run_in_threadpool(manager.cleanup)

        task = asyncio.create_task(cleaner())
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        manager.close()

    app = FastAPI(title="PDF Extraction and Addition", lifespan=lifespan)

    @app.middleware("http")
    async def local_guard(request: Request, call_next):
        # Browser-origin writes must come from this app, even on localhost.
        origin = request.headers.get("origin")
        if request.method == "POST" and origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin uploads are not allowed."}, status_code=403)
        length = request.headers.get("content-length")
        if request.method == "POST" and length:
            try:
                if int(length) > settings.max_upload_bytes + 1024 * 1024:
                    return JSONResponse({"detail": "Request exceeds the configured upload limit."}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid request length."}, status_code=400)
        return await call_next(request)

    app.include_router(router)
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
