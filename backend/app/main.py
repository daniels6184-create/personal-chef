"""Application entry point: API routers, security middleware and the built PWA."""
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from . import auth, export, profile
from .config import get_settings
from .security import SECURITY_HEADERS, csrf_guard

log = logging.getLogger("personal_chef")


def create_app() -> FastAPI:
    app = FastAPI(title="Personal Chef", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            try:
                csrf_guard(request)
            except HTTPException as e:
                return JSONResponse({"detail": e.detail}, status_code=e.status_code)
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if get_settings().cookie_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Report what was wrong without echoing the submitted values back (or into logs).
        problems = [{"field": ".".join(str(p) for p in e.get("loc", [])[1:]), "problem": e.get("msg", "")}
                    for e in exc.errors()]
        return JSONResponse({"detail": "Some values are not valid.", "problems": problems}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        # Log the type and path only: never the request body.
        log.error("Unhandled %s on %s %s", type(exc).__name__, request.method, request.url.path)
        return JSONResponse({"detail": "Something went wrong on the server."}, status_code=500)

    @app.get("/healthz")
    def healthz():
        # Deliberately does not touch the database, so health checks never wake Neon.
        return {"ok": True}

    app.include_router(auth.router)
    app.include_router(profile.router)
    app.include_router(export.router)

    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def api_not_found(rest: str):
        raise HTTPException(404, "Not found.")

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    root = get_settings().frontend_dir
    if not root:
        return
    dist = Path(root).resolve()
    index = dist / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = (dist / path).resolve()
        # Serve real files only from inside dist; everything else is the app shell.
        if path and target.is_file() and dist in target.parents:
            if path.startswith("assets/"):
                headers = {"Cache-Control": "public, max-age=31536000, immutable"}
            else:
                headers = {"Cache-Control": "no-cache"}
            return FileResponse(target, headers=headers)
        if not index.is_file():
            raise HTTPException(404, "Frontend not built.")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
