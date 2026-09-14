#!/usr/bin/env python3


"""
Backend API for dashboard
"""


import json
import yaml
from fastapi import FastAPI
import uvicorn
from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware
from typing import TypeAlias
from pathlib import Path
from pydantic import BaseModel
from hq.sysbs import find_hq
from hq.emily import relationship_time, why_is_emily_great


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


Response: TypeAlias = dict[str, str]


HQ = find_hq()
HQ_RECIPES = HQ / "etc/kopi/recipes"


@app.get("/")
def read_root() -> Response:
    """
    Get root of API
    """
    return {"message": "Welcome to My Web App API"}


@app.get("/recipes/{filename}")
def get_recipe(filename: str) -> dict:
    """
    Get a specific recipe by path/name

    Recipes are stored as YAML (see ``etc/kopi/RECIPE_FORMAT.md``). This parses the
    YAML and returns it as structured JSON for the UI to render and scale, alongside
    the raw text so the UI can offer raw editing.

    Args:
        filename: The name of the recipe file, which is the path of the recipe relative
            to hq's recipes directory, with path separators replaced by ".."s (e.g.
            "pourover..clever")

    Returns:
        A dictionary with:
            name: the recipe's relative path
            raw: the raw file contents (for the editor)
            recipe: the parsed YAML mapping, or None if it could not be parsed
            parse_error: present only when the YAML could not be parsed into a mapping
        or an error message if the recipe file is not found.
    """
    # Reconstruct the path to the recipe file from the request
    filename = filename.replace("..", "/")
    file_path = HQ_RECIPES / filename

    # Return an error message if the file does not exist
    if not file_path.exists():
        return {"error": f"Recipe not found: {file_path}"}

    raw = file_path.read_text(encoding="utf-8")
    result: dict = {"name": filename, "raw": raw, "recipe": None}
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        result["parse_error"] = str(exc)
        return result

    if isinstance(parsed, dict):
        result["recipe"] = parsed
    elif parsed is not None:
        result["parse_error"] = "Recipe YAML is not a mapping"
    return result


class RecipeUpdate(BaseModel):
    content: str


@app.put("/recipes/{filename}")
def update_recipe(filename: str, update: RecipeUpdate) -> Response:
    """
    Update a recipe's content

    Args:
        filename: The name of the recipe file (same encoding as GET)
        update: New content for the recipe
    """
    filename = filename.replace("..", "/")
    file_path = HQ_RECIPES / filename

    if file_path.exists():
        file_path.write_text(update.content, encoding="utf-8")
        return {"success": f"Recipe updated: {filename}"}

    return {"error": f"Recipe not found: {file_path}"}


@app.get("/recipes")
def list_recipes() -> list[Path]:
    """
    Get all recipes in alphabetical order

    Returns:
        Names of all recipes in hq's recipe directory, sorted alphabetically
    """
    return sorted(
        "/".join(path.relative_to(HQ_RECIPES).parts)
        for path in HQ_RECIPES.rglob("*")
        if not path.is_dir()
    )


@app.get("/relationship_time")
def get_relationship_time() -> Response:
    """
    Compute how long Emily and Hamish have been dating
    """
    relationship_time_string = relationship_time(return_timedelta=False)
    return {"time": relationship_time_string}


@app.get("/why_emily_is_great")
def get_why_emily_is_great() -> Response:
    """
    Get a list of reasons why Emily is great
    """
    return {"reason": why_is_emily_great()}


if __name__ == "__main__":
    uvicorn.run(app, host="192.168.0.247", port=10498)
