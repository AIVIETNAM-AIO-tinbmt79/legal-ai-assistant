
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.contract import ContractModel


class ContractRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
    self,
    user_id: str,
    original_filename: str,
    file_path: str,
    status: str = "uploaded",
    is_active: bool = False,
):
        now = datetime.now(timezone.utc)

        contract = ContractModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            original_filename=original_filename,
            file_path=file_path,
            status=status,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )

        try:
            self.db.add(contract)
            self.db.commit()
            self.db.refresh(contract)
            return contract
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, contract_id: str, user_id: str):
        statement = select(ContractModel).where(
            ContractModel.id == contract_id,
            ContractModel.user_id == user_id,
        )
        return self.db.scalar(statement)

    def get_by_user(self, user_id: str):
        statement = (
            select(ContractModel)
            .where(ContractModel.user_id == user_id)
            .order_by(ContractModel.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def update_status(
    self,
    contract_id: str,
    user_id: str,
    status: str,
):
        contract = self.get_by_id(
            contract_id=contract_id,
            user_id=user_id,
        )

        if contract is None:
            return None

        try:
            contract.status = status
            contract.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(contract)
            return contract

        except Exception:
            self.db.rollback()
            raise

    def set_active(self, contract_id: str, user_id: str):
        contract = self.get_by_id(contract_id, user_id)

        if contract is None:
            return None

        try:
            # Chỉ cho phép một hợp đồng active
            # trên mỗi người dùng.
            contracts = self.db.scalars(
                select(ContractModel).where(
                    ContractModel.user_id == user_id
                )
            ).all()

            now = datetime.now(timezone.utc)

            for item in contracts:
                item.is_active = item.id == contract_id

            contract.updated_at = now

            self.db.commit()
            self.db.refresh(contract)
            return contract
        except Exception:
            self.db.rollback()
            raise

    def delete(self, contract_id: str, user_id: str):
        contract = self.get_by_id(contract_id, user_id)

        if contract is None:
            return False

        try:
            self.db.delete(contract)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
