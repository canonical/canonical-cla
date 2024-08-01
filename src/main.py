from fastapi import FastAPI

from connect_db import test_db_connection

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/healthz")
def health_check():
    return {"status": "OK"}


print(test_db_connection())
