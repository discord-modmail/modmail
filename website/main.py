from starlette.applications import Starlette
from starlette.routing import Mount, Request, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates


templates = Jinja2Templates(directory="website/templates")


async def homepage(request: Request) -> templates.TemplateResponse:
    """Render us a test homepage."""
    example_server_data = [
        {
            "name": "Modmail",
            "tagline": "The Modmail support server!",
            "invite": " https://discord.gg/HFCJP2K8",
            "icon_url": "https://cdn.discordapp.com/icons/"
            "798235512208490526/447db05557370a52b4c01c9144eff96b.png",
        },
        {
            "name": "Catver",
            "tagline": "This is just test data, don't look too far into it.",
            "invite": "#",
            "icon_url": "https://cdn.discordapp.com/icons/"
            "111218511413551104/62d3f30e68b878ef7f1f729e6d19e2ad.png",
        },
        {
            "name": "Smh Dawn",
            "tagline": "I thought you were going to ask in those servers for stuff :joy:",
            "invite": "#",
            "icon_url": "https://cdn.discordapp.com/icons/"
            "830406883978379264/7608bd774d8467ef81cca61f7f397d9f.png",
        },
    ]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "servers": example_server_data,
        },
    )


routes = [
    Route("/", endpoint=homepage),
    Mount("/static", StaticFiles(directory="website/static"), name="static"),
]

app = Starlette(debug=True, routes=routes)
