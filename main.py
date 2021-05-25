from starlette.applications import Starlette
from starlette.routing import Mount, Request, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates


templates = Jinja2Templates(directory="templates")


async def homepage(request: Request) -> templates.TemplateResponse:
    """Render us a test homepage."""
    return templates.TemplateResponse("index.html", {"request": request})


routes = [
    Route("/", endpoint=homepage),
    Mount("/static", StaticFiles(directory="static"), name="static"),
]

app = Starlette(debug=True, routes=routes)
