from sqlalchemy.orm import Session

from app.database.models.contract import (
    ContractModel,
)


class ContractRepository:
    """
    Repository for managing contracts.
    """

    def __init__(
        self,
        session: Session,
    ):
        self.session = session

    # ==================================================
    # Create Contract
    # ==================================================

    def create(
        self,
        user_id: str,
        original_filename: str,
        file_path: str,
        status: str = "uploaded",
        is_active: bool = False,
    ) -> ContractModel:

        contract = ContractModel(
            user_id=user_id,
            original_filename=original_filename,
            file_path=file_path,
            status=status,
            is_active=is_active,
        )

        self.session.add(
            contract
        )

        self.session.commit()

        self.session.refresh(
            contract
        )

        return contract

    # ==================================================
    # Get Contract by ID
    # ==================================================

    def get_by_id(
        self,
        contract_id: str,
    ) -> ContractModel | None:

        return (
            self.session
            .query(ContractModel)
            .filter(
                ContractModel.id
                == contract_id
            )
            .first()
        )

    # ==================================================
    # Get Contract by ID and User
    # ==================================================

    def get_by_id_and_user(
        self,
        contract_id: str,
        user_id: str,
    ) -> ContractModel | None:

        return (
            self.session
            .query(ContractModel)
            .filter(
                ContractModel.id
                == contract_id,
                ContractModel.user_id
                == user_id,
            )
            .first()
        )

    # ==================================================
    # Get User Contracts
    # ==================================================

    def get_by_user_id(
        self,
        user_id: str,
    ) -> list[ContractModel]:

        return (
            self.session
            .query(ContractModel)
            .filter(
                ContractModel.user_id
                == user_id
            )
            .order_by(
                ContractModel.created_at.desc()
            )
            .all()
        )

    # ==================================================
    # Get Active Contract
    # ==================================================

    def get_active_by_user(
        self,
        user_id: str,
    ) -> ContractModel | None:

        return (
            self.session
            .query(ContractModel)
            .filter(
                ContractModel.user_id
                == user_id,
                ContractModel.is_active
                == True,
            )
            .first()
        )

    # ==================================================
    # Set Active Contract
    # ==================================================

    def set_active(
        self,
        contract: ContractModel,
    ) -> ContractModel:

        # ----------------------------------------------
        # Deactivate all user's contracts
        # ----------------------------------------------

        (
            self.session
            .query(ContractModel)
            .filter(
                ContractModel.user_id
                == contract.user_id,
                ContractModel.id
                != contract.id,
            )
            .update(
                {
                    ContractModel.is_active: False
                },
                synchronize_session=False,
            )
        )

        # ----------------------------------------------
        # Activate selected contract
        # ----------------------------------------------

        contract.is_active = True

        self.session.commit()

        self.session.refresh(
            contract
        )

        return contract

    # ==================================================
    # Update Status
    # ==================================================

    def update_status(
        self,
        contract: ContractModel,
        status: str,
    ) -> ContractModel:

        contract.status = status

        self.session.commit()

        self.session.refresh(
            contract
        )

        return contract

    # ==================================================
    # Delete Contract
    # ==================================================

    def delete(
        self,
        contract: ContractModel,
    ) -> None:

        self.session.delete(
            contract
        )

        self.session.commit()