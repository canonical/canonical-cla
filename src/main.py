import datetime
from typing import Union

from fastapi import FastAPI

app = FastAPI()

start = datetime.datetime.now()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/healthz")
def health_check():
    return {"status": "OK"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
