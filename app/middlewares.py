from urllib.parse import urlencode

from fastapi import FastAPI, Request


def register_middlewares(app: FastAPI):
    @app.middleware("http")
    async def flatten_query_string_lists(request: Request, call_next):
        """
        FastAPI has support for array query parameters. However only this format is supported:
        `/items?item=foo&item=bar`
        whereas the following format is not supported:
        `/items?item=foo,bar`
        This middleware converts the latter format to the former format.
        """
        flattened = []
        for key, value in request.query_params.multi_items():
            flattened.extend((key, entry) for entry in value.split(","))
        request.scope["query_string"] = urlencode(flattened, doseq=True).encode("utf-8")
        return await call_next(request)

    @app.middleware("http")
    async def query_handle_empty_value(request: Request, call_next):
        """
        FastAPI raises a JSONDecodeError error with status code 500 when a query parameter is empty.
        The unsupported format is `/items?item=`.
        This middleware converts the unsupported format to `/items`.
        """
        cleaned = []
        for key, value in request.query_params.items():
            if value:
                cleaned.append((key, value))

        request.scope["query_string"] = urlencode(cleaned).encode("utf-8")
        return await call_next(request)
