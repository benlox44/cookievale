import os

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
templates.env.globals["base_url"] = os.environ["BASE_URL"]
