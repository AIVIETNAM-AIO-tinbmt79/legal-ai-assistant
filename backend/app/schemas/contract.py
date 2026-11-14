from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContractResponse(BaseModel):
    id: str
    original_filename: str
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)