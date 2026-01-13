### Common queries

#### Login via browser

Easiest option is via browser because this will redirect to GitHub or Launchpad and redirect back to the local instance.

- http://127.0.0.1:8000/github/login
- http://127.0.0.1:8000/launchpad/login

Once login flow is done and successful, you should see the GitHub or Launchpad list of emails in JSON format.

You need to grab your session cookie:

1. Toggle web tools view → Application → Cookies → `github_oauth2_session`, `launchpad_oauth2_session`
2. Copy the `Value` column and save it in your terminal session

```sh
export GITHUB_SESSION_COOKIE=...
export LAUNCHPAD_SESSION_COOKIE=...
```

## Individual CLA

### Signing the individual CLA

```sh
curl --location 'http://localhost:8000/cla/individual/sign' \
--header 'Content-Type: application/json' \
--header "Cookie: github_oauth2_session=$GITHUB_SESSION_COOKIE; launchpad_oauth2_session=$LAUNCHPAD_SESSION_COOKIE" \
--data-raw '{
    "first_name": "John",
    "last_name": "Doe",
    "address":"123 Main St",
    "country": "FR",
    "launchpad_email": "john.doe@canonical.com"
}'
# {
#     "message": "Individual Contributor License Agreement (CLA) signed successfully"
# }
```

Note:

`launchpad_email` is the email address of the user you want to sign the CLA for, when provided the cookie `launchpad_oauth2_session` is used to sign the CLA, if `github_email` is provided the cookie `github_oauth2_session` is used to sign the CLA.

### Checking the status of the individual CLA

```sh
curl --location 'http://localhost:8000/cla/check?emails=john.doe@canonical.com'
# { "emails": {"john.doe@canonical.com": true} }
```

## Organization CLA

### Signing organization CLA (for a company)

```sh
curl --location 'http://localhost:8000/cla/organization/sign' \
--header 'Content-Type: application/json' \
--header "Cookie: github_oauth2_session=$GITHUB_SESSION_COOKIE; launchpad_oauth2_session=$LAUNCHPAD_SESSION_COOKIE" \
--data-raw '{
    "name": "ACME Corp",
    "email_domain": "canonical.com",
    "contact_name": "John Doe",
    "contact_email": "user@canonical.com",
    "contact_job_title": "Developer",
    "phone_number": "+1234567890",
    "address": "123 Main St, Paris 75000",
    "country": "FR"
}'

# {
#     "message": "Organization Contributor License Agreement (CLA) signed successfully"
# }
```

### Checking the status of the organization CLA

```sh
curl --location 'http://localhost:8000/cla/check?emails=user1@canonical.com,user2@canonical.com'
# { "emails": {"user1@canonical.com": true, "user2@canonical.com": true} }
```
