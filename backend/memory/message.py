from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Message:
    role: str
    content: str
    created_at: datetime | None = None

    def __post_init__(self):

        if self.created_at is None:

            self.created_at = datetime.now(
                timezone.utc
            )