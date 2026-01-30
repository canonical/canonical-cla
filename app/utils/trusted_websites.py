from typing import Annotated

TRUSTED_WEBSITES: Annotated[
    set[str],
    "Trusted websites used to validate open redirects and to add CORS headers.",
] = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "*.ubuntu.com",
    "*.canonical.com",
    "*.demos.haus",
}
