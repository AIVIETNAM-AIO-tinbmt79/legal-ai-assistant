
from pathlib import Path

from sqlalchemy.orm import Session

from modes.contract_qa.service import ContractService as ContractIndexService


class ContractService:
    def __init__(self, db: Session):
        self.db = db
        self.index_service = ContractIndexService(db=db)

    def upload_contract(
        self,
        user_id: str,
        original_filename: str,
        source_file_path: str | Path,
    ):
        return self.index_service.upload_contract(
            user_id=user_id,
            original_filename=original_filename,
            source_file_path=source_file_path,
        )
