from typing import List

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class LaunchpadPersonResponse(TypedDict):
    self_link: str
    web_link: str
    resource_type_link: str
    recipes_collection_link: str
    latitude: str
    longitude: str
    time_zone: str
    private: str
    is_valid: str
    is_team: str
    visibility: str
    name: str
    display_name: str
    logo_link: str
    is_probationary: str
    id: str
    karma: str
    homepage_content: str
    description: str
    mugshot_link: str
    languages_collection_link: str
    hide_email_addresses: str
    date_created: str
    sshkeys_collection_link: str
    is_ubuntu_coc_signer: str
    gpg_keys_collection_link: str
    wiki_names_collection_link: str
    irc_nicknames_collection_link: str
    jabber_ids_collection_link: str
    social_accounts_collection_link: str
    memberships_details_collection_link: str
    open_membership_invitations_collection_link: str
    confirmed_email_addresses_collection_link: str
    team_owner_link: str
    preferred_email_address_link: str
    mailing_list_auto_subscribe_policy: str
    archive_link: str
    ppas_collection_link: str
    sub_teams_collection_link: str
    super_teams_collection_link: str
    members_collection_link: str
    admins_collection_link: str
    participants_collection_link: str
    deactivated_members_collection_link: str
    expired_members_collection_link: str
    invited_members_collection_link: str
    members_details_collection_link: str
    proposed_members_collection_link: str
    http_etag: str

    def __str__(self):
        return f"Launchpad User: {self.display_name}"


class LaunchpadEmailResponse(TypedDict):
    self_link: str
    web_link: str
    resource_type_link: str
    email: str
    person_link: str
    http_etag: str


class LaunchpadEmailListResponse(TypedDict):
    entries: List[LaunchpadEmailResponse]
    start: int
    total_size: int
    resource_type_link: str


class LaunchpadRequestTokenResponse(TypedDict):
    oauth_token: str
    oauth_token_secret: str
    oauth_token_consumer: str


class LaunchpadAccessTokenResponse(TypedDict):
    oauth_token: str
    oauth_token_secret: str


class AccessTokenSession(TypedDict):
    oauth_token: str
    oauth_token_secret: str


class RequestTokenSession(TypedDict):
    oauth_token: str
    oauth_token_secret: str
    state: str
    redirect_url: str | None


class LaunchpadProfile(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "canonical",
                "emails": ["contact@canonica.com", "contact@ubuntu.com"],
            }
        }
    )
    _id: str
    username: str = Field(..., description="Launchpad username")
    emails: list[str] = Field(..., description="List of verified email addresses")

    def __init__(self, _id: str, **data):
        super().__init__(_id=_id, **data)
        self._id = _id
