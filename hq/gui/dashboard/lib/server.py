"""
Backend API for dashboard
"""

from fastapi import FastAPI
import uvicorn
from fastapi.responses import FileResponse
from typing import TypeAlias
from pathlib import Path
from hq.sysbs import find_hq


app = FastAPI()


Response: TypeAlias = dict[str, str]


HQ = find_hq()
HQ_RECIPES = HQ / "etc/kopi/recipes"


@app.get("/")
def read_root():
    """
    Get root of API
    """
    return {"message": "Welcome to My Web App API"}


@app.get("/recipes/{filename}")
def get_recipe(filename: str) -> Response:
    """
    Get a specific recipe by path/name
    """
    # file_path = os.path.join("recipes", filename)
    # if os.path.exists(file_path):
    #     return FileResponse(file_path)
    # return {"error": "File not found"}
    return (
        FileResponse(file_path)
        if (file_path := HQ_RECIPES / filename).exists()
        else {"error": "File not found"}
    )


@app.get("/recipes")
def list_recipes() -> list[Path]:

    return list(HQ_RECIPES.rglob("*"))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
