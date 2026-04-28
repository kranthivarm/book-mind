from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from db.database import init_db, close_db
from routers import upload, query, chats, auth, quiz
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="BookMind API", lifespan=lifespan)

#   CORS must be added FIRST before any other middleware  
# If CORS middleware is added after other middleware, error responses
# (4xx, 5xx) won't have CORS headers → browser shows "CORS error"
# even though the real problem is something else entirely.
ALLOWED_ORIGINS = [
    "http://bookmind-frontend.s3-website.eu-north-1.amazonaws.com",
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,   # Using Bearer tokens, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


#   Custom exception handlers that include CORS headers
# FastAPI's default error responses bypass CORS middleware.
# These handlers manually add the CORS header so browser can read the error.

def add_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    origin = request.headers.get("origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGINS[0]
    response.headers["Access-Control-Allow-Credentials"] = "false"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    return add_cors_headers(request, response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    response = JSONResponse(
        status_code=422,
        content={"detail": str(exc.errors())},
    )
    return add_cors_headers(request, response)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )
    return add_cors_headers(request, response)


app.include_router(auth.router,   prefix="/api")
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(query.router,  prefix="/api", tags=["Query"])
app.include_router(chats.router,  prefix="/api", tags=["Chats"])
app.include_router(quiz.router,   prefix="/api", tags=["Quiz"])


@app.get("/")
async def root():
    return {"status": "ok", "docs": "/docs"}