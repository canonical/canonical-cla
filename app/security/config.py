private_paths = {
    "/_status/check",
    "/metrics",
}

excluded_paths = {
    "/docs",
    "/",
    "/github/profile",
    "/launchpad/profile",
}

# Only specific paths can be whitelisted to prevent users from bypassing
# rate limiting by sending requests from a GitHub action or similar service.
# Whitelist paths bypass rate limiting if their IP address is private or in the GitHub IPs set
whitelistable_paths = {"/cla/check"}
