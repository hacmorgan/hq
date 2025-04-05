#!/usr/bin/env python3


"""
Backend API for dashboard
"""


import json
from fastapi import FastAPI
import uvicorn
from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware
from typing import TypeAlias
from pathlib import Path
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
def get_recipe(filename: str) -> Response:
    """
    Get a specific recipe by path/name

    Args:
        filename: The name of the recipe file, which is the path of the recipe relative
            to hq's recipes directory, with path separators replaced by ".."s (e.g.
            "pourover..clever")

    Returns:
        A dictionary with the recipe name and contents, or an error message if the
        recipe file is not found
    """
    # Reconstruct the path to the recipe file from the request
    filename = filename.replace("..", "/")
    file_path = HQ_RECIPES / filename

    # Return the recipe's name and contents if the file exists
    if file_path.exists():
        return {"name": filename, "recipe": file_path.read_text()}

    # Return an error message if the file does not exist
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
    uvicorn.run(app, port=8000)
