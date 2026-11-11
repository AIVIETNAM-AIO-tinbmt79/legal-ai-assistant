from pathlib import Path
import shutil
import uuid

from sqlalchemy.orm import Session

from config.settings import settings

from app.database.models.contract import ContractModel
from app.database.repositories.contract import ContractRepository

from indexing.document_indexer import DocumentIndexer


class ContractService:

    def __init__(
        self,
        db: Session,
        document_indexer=None,
    ):
        self.db = db

        self.contract_repository = ContractRepository(
            db
        )

        self.document_indexer = (
            document_indexer
            or DocumentIndexer()
        )

    # ==================================================
    # Upload + Index Contract
    # ==================================================

    def upload_contract(
        self,
        user_id: str,
        original_filename: str,
        source_file_path: str | Path,
    ) -> ContractModel:

        source_file_path = Path(
            source_file_path
        )

        if not source_file_path.exists():
            raise FileNotFoundError(
                f"Source file not found: {source_file_path}"
            )

        # ==================================================
        # 1. Generate contract_id
        # ==================================================

        contract_id = str(
            uuid.uuid4()
        )

        # ==================================================
        # 2. Create contracts directory
        # ==================================================

        contracts_dir = (
            settings.DATA_DIR / "contracts"
        )

        contracts_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ==================================================
        # 3. Create stored filename
        # ==================================================

        stored_filename = (
            f"{contract_id}_"
            f"{source_file_path.name}"
        )

        stored_file_path = (
            contracts_dir / stored_filename
        )

        # ==================================================
        # 4. Copy uploaded file
        # ==================================================

        shutil.copy2(
            source_file_path,
            stored_file_path,
        )

        # ==================================================
        # 5. Create database record
        # ==================================================

        contract = self.contract_repository.create(
            user_id=user_id,
            original_filename=original_filename,
            file_path=str(stored_file_path),
            status="uploaded",
            is_active=False,
        )

        # ==================================================
        # 6. Index document
        # ==================================================

        try:

            self.contract_repository.update_status(
                contract,
                "indexing",
            )

            self.document_indexer.index(
                file_path=stored_file_path,
                contract_id=contract.id,
            )

            # ==================================================
            # 7. Mark as indexed
            # ==================================================

            self.contract_repository.update_status(
                contract,
                "indexed",
            )

        except Exception:

            # ==================================================
            # 8. Mark as failed
            # ==================================================

            self.contract_repository.update_status(
                contract,
                "failed",
            )

            raise

        return contract