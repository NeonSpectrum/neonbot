from __future__ import annotations

from datetime import datetime

from beanie import Document


class MigrationModel(Document):
    name: str
    applied_at: datetime

    class Settings:
        name = 'migrations'
