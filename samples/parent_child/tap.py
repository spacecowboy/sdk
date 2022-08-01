"""A tap with parent and child streams."""

from singer_sdk import Stream, Tap


class Parent(Stream):
    """A parent stream."""

    name = "parent"
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "tenant": {"type": "string"},
        },
    }

    def get_child_context(self, record: dict, context: dict) -> dict:
        """Create context for children streams."""
        return {
            "pid": record["id"],
        }

    def get_records(self, context: dict):
        """Get dummy records."""
        yield {"id": 1, "tenant": "tenant1"}
        yield {"id": 2, "tenant": "tenant1"}
        yield {"id": 3, "tenant": "tenant1"}


class Child(Stream):
    """A child stream."""

    name = "child"
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "pid": {"type": "integer"},
            "tenant": {"type": "string"},
        },
    }
    parent_stream_type = Parent
    state_partitioning_keys = ["pid", "tenant"]

    def get_records(self, context: dict):
        """Get dummy records."""
        yield {"id": 1, "pid": context["pid"], "tenant": "tenant1"}
        yield {"id": 2, "pid": context["pid"], "tenant": "tenant1"}
        yield {"id": 3, "pid": context["pid"], "tenant": "tenant1"}


class ParentChildTap(Tap):
    """A tap with streams having a parent-child relationship."""

    name = "my-tap"
    config_jsonschema = {"properties": {}}

    def discover_streams(self):
        """Discover streams."""
        return [Parent(self), Child(self)]


if __name__ == "__main__":
    ParentChildTap.cli()
