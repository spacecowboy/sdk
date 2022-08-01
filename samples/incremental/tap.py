"""A sample tap."""

from datetime import datetime, timedelta

import singer_sdk.typing as th
from singer_sdk import Stream, Tap
from singer_sdk.helpers._classproperty import classproperty
from singer_sdk.helpers.capabilities import TapCapabilities


class IncrementalStream(Stream):
    """A stream with incremental sync capabilities."""

    name = "incremental_stream"
    is_sorted = True
    replication_key = "repl"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType),
        th.Property("repl", th.DateTimeType),
    ).to_dict()

    partitions = [{"partition": 1}, {"partition": 2}]

    def get_records(self, context):
        """Get records."""
        for batch in range(5):
            sts = self.get_starting_timestamp(context)
            ts = sts or datetime.now()
            for i in range(1 + 10 * batch, 6 + 10 * batch):
                yield {
                    "id": i,
                    "partition": context["partition"],
                    "repl": ts + timedelta(days=i),
                }


class IncrementalTap(Tap):
    """A tap with incremental streams."""

    name = "incremental_tap"
    config_jsonschema = {"properties": {"key": {"type": "string"}}}

    def discover_streams(self):
        """Discover streams."""
        return [IncrementalStream(self)]
