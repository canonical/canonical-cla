import json

from starlette.responses import HTMLResponse


def get_redoc_html() -> HTMLResponse:
    # docs: https://redocly.com/docs/api-reference-docs/configuration/theming
    redoc_theme = {
        "colors": {
            "accent": {"main": "#E85220"},
            "primary": {"main": "#E85220"},
        },
        "typography": {"fontFamily": "Ubuntu, sans-serif"},
    }

    """
    Generate and return the HTML response that loads ReDoc for the alternative
    API docs (normally served at `/redoc`).

    You would only call this function yourself if you needed to override some parts,
    for example the URLs to use to load ReDoc's JavaScript and CSS.

    Read more about it in the
    [FastAPI docs for Custom Docs UI Static Assets (Self-Hosting)](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/).
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>Canonical CLA API</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Ubuntu+Mono:ital,wght@0,400;0,700;1,400;1,700&family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap" rel="stylesheet">
    <link rel="shortcut icon" href="https://assets.ubuntu.com/v1/be7e4cc6-COF-favicon-32x32.png">
    <!--
    ReDoc doesn't change outer page styles
    -->
    <style>
      body {{
        margin: 0;
        padding: 0;
      }}
      .api-info *, .menu-content * {{
        font-family: 'Ubuntu', sans-serif !important;
      }}
      code, pre {{
        font-family: 'Ubuntu Mono', monospace !important;
        font-size: 1.1em !important;
       }}

      .api-content div:has(> h1), .api-content div:has(> h2), .api-content div:has(> h3) {{
        padding-top: 20px !important;
        padding-bottom: 10px !important;
       }}
      div[data-section-id]{{
        padding-top: 0px !important;
        padding-bottom: 0px !important;
       }}

    </style>
    </head>
    <body>
    <noscript>
        ReDoc requires Javascript to function. Please enable it to browse the documentation.
    </noscript>
    <redoc
        spec-url="/openapi.json"
        required-props-first=true
        theme='{json.dumps(redoc_theme)}'
    >
    </redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(html)
