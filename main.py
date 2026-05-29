from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from database import engine, Base
from routers import jobs, kanban, answers, cover_letter


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Job Hunter", version="1.0.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(kanban.router, prefix="/api/kanban", tags=["kanban"])
app.include_router(answers.router, prefix="/api/answers", tags=["answers"])
app.include_router(cover_letter.router, prefix="/api/cover-letter", tags=["cover_letter"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
