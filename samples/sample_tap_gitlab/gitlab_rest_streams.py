"""Sample tap stream test for tap-gitlab."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from singer_sdk.authenticators import SimpleAuthenticator
from singer_sdk.pagination import SimpleHeaderPaginator
from singer_sdk.streams.rest import RESTStream
from singer_sdk.typing import (
    ArrayType,
    DateTimeType,
    IntegerType,
    PropertiesList,
    Property,
    StringType,
)

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")

DEFAULT_URL_BASE = "https://gitlab.com/api/v4"


class GitlabStream(RESTStream[str]):
    """Sample tap test for gitlab."""

    _LOG_REQUEST_METRIC_URLS = True

    @property
    def url_base(self) -> str:
        """Return the base GitLab URL."""
        return self.config.get("api_url", DEFAULT_URL_BASE)

    @property
    def authenticator(self) -> SimpleAuthenticator:
        """Return an authenticator for REST API requests."""
        return SimpleAuthenticator(
            stream=self, auth_headers={"Private-Token": self.config.get("auth_token")}
        )

    def get_url_params(
        self, context: dict | None, next_page_token: str | None
    ) -> dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        if next_page_token:
            params["page"] = next_page_token
        if self.replication_key:
            params["sort"] = "asc"
            params["order_by"] = self.replication_key
        return params

    def get_new_paginator(self) -> SimpleHeaderPaginator:
        """Return a new paginator for GitLab API endpoints.

        Returns:
            A new paginator.
        """
        return SimpleHeaderPaginator("X-Next-Page")


class ProjectBasedStream(GitlabStream):
    """Base class for streams that are keys based on project ID."""

    @property
    def partitions(self) -> list[dict]:
        """Return a list of partition key dicts (if applicable), otherwise None."""
        if "{project_id}" in self.path:
            return [
                {"project_id": id} for id in cast(list, self.config.get("project_ids"))
            ]
        if "{group_id}" in self.path:
            if "group_ids" not in self.config:
                raise ValueError(
                    f"Missing `group_ids` setting which is required for the "
                    f"'{self.name}' stream."
                )
            return [{"group_id": id} for id in cast(list, self.config.get("group_ids"))]
        raise ValueError(
            "Could not detect partition type for Gitlab stream "
            f"'{self.name}' ({self.path}). "
            "Expected a URL path containing '{project_id}' or '{group_id}'. "
        )


class ProjectsStream(ProjectBasedStream):
    """Gitlab Projects stream."""

    name = "projects"
    path = "/projects/{project_id}?statistics=1"
    primary_keys = ["id"]
    replication_key = "last_activity_at"
    is_sorted = True
    schema_filepath = SCHEMAS_DIR / "projects.json"


class ReleasesStream(ProjectBasedStream):
    """Gitlab Releases stream."""

    name = "releases"
    path = "/projects/{project_id}/releases"
    primary_keys = ["project_id", "commit_id", "tag_name"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "releases.json"


class IssuesStream(ProjectBasedStream):
    """Gitlab Issues stream."""

    name = "issues"
    path = "/projects/{project_id}/issues?scope=all&updated_after={start_date}"
    primary_keys = ["id"]
    replication_key = "updated_at"
    is_sorted = True
    schema_filepath = SCHEMAS_DIR / "issues.json"


class CommitsStream(ProjectBasedStream):
    """Gitlab Commits stream."""

    name = "commits"
    path = (
        "/projects/{project_id}/repository/commits?since={start_date}&with_stats=true"
    )
    primary_keys = ["id"]
    replication_key = "created_at"
    is_sorted = False
    schema_filepath = SCHEMAS_DIR / "commits.json"


class EpicsStream(ProjectBasedStream):
    """Gitlab Epics stream.

    This class shows an example of inline `schema` declaration rather than referencing
    a raw json input file.
    """

    name = "epics"
    path = "/groups/{group_id}/epics?updated_after={start_date}"
    primary_keys = ["id"]
    replication_key = "updated_at"
    is_sorted = True
    schema = PropertiesList(
        Property("id", IntegerType, required=True),
        Property("iid", IntegerType, required=True),
        Property("group_id", IntegerType, required=True),
        Property("parent_id", IntegerType),
        Property("title", StringType),
        Property("description", StringType),
        Property("state", StringType),
        Property("author_id", IntegerType),
        Property("start_date", DateTimeType),
        Property("end_date", DateTimeType),
        Property("due_date", DateTimeType),
        Property("created_at", DateTimeType),
        Property("updated_at", DateTimeType),
        Property("labels", ArrayType(StringType)),
        Property("upvotes", IntegerType),
        Property("downvotes", IntegerType),
    ).to_dict()

    # schema_filepath = SCHEMAS_DIR / "epics.json"

    def get_child_context(self, record: dict, context: dict | None) -> dict:
        """Perform post processing, including queuing up any child stream types."""
        # Ensure child state record(s) are created
        return {
            "group_id": record["group_id"],
            "epic_id": record["id"],
            "epic_iid": record["iid"],
        }


class EpicIssuesStream(GitlabStream):
    """EpicIssues stream class."""

    name = "epic_issues"
    path = "/groups/{group_id}/epics/{epic_iid}/issues"
    primary_keys = ["id"]
    replication_key = None
    schema_filepath = SCHEMAS_DIR / "epic_issues.json"
    parent_stream_type = EpicsStream  # Stream should wait for parents to complete.

    def get_url_params(
        self, context: dict | None, next_page_token: str | None
    ) -> dict[str, Any]:
        """Return a dictionary of values to be used in parameterization."""
        result = super().get_url_params(context, next_page_token)
        if not context or "epic_id" not in context:
            raise ValueError("Cannot sync epic issues without already known epic IDs.")
        return result
