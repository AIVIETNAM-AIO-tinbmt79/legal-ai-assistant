from datetime import datetime

from pydantic import BaseModel


class ContractResponse(BaseModel):

    id: str

    original_filename: str

    file_path: str

    status: str

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = {
        "from_attributes": True
    }