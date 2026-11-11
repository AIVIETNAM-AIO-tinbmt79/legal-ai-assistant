from pathlib import Path
import shutil
import tempfile

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
    get_db,
)

from app.api.schemas.contracts import ContractResponse

from modes.contract_qa.service import ContractService

from app.database.models.user import UserModel
from app.database.repositories.contract import ContractRepository


router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)


# ==================================================
# Upload Contract
# ==================================================

@router.post(
    "/upload",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required.",
        )

    original_filename = Path(
        file.filename
    ).name

    suffix = Path(
        original_filename
    ).suffix

    temp_file_path = None

    try:

        # ==================================================
        # 1. Save uploaded file temporarily
        # ==================================================

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            shutil.copyfileobj(
                file.file,
                temp_file,
            )

            temp_file_path = Path(
                temp_file.name
            )

        # ==================================================
        # 2. Upload + Index
        # ==================================================

        service = ContractService(
            db=db
        )

        contract = service.upload_contract(
            user_id=current_user.id,
            original_filename=original_filename,
            source_file_path=temp_file_path,
        )

        return contract

    except FileNotFoundError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload contract: {str(e)}",
        )

    finally:

        # ==================================================
        # 3. Remove temporary file
        # ==================================================

        if (
            temp_file_path is not None
            and temp_file_path.exists()
        ):
            temp_file_path.unlink()


# ==================================================
# Get User Contracts
# ==================================================

@router.get(
    "",
    response_model=list[ContractResponse],
)
def get_contracts(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):

    repository = ContractRepository(
        db
    )

    contracts = repository.get_by_user_id(
        current_user.id
    )

    return contracts


# ==================================================
# Activate Contract
# ==================================================

@router.post(
    "/{contract_id}/activate",
    response_model=ContractResponse,
)
def activate_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):

    repository = ContractRepository(
        db
    )

    # ==================================================
    # 1. Find contract belonging to current user
    # ==================================================

    contract = repository.get_by_id_and_user(
        contract_id=contract_id,
        user_id=current_user.id,
    )

    if contract is None:

        raise HTTPException(
            status_code=404,
            detail="Contract not found.",
        )

    # ==================================================
    # 2. Contract must be indexed
    # ==================================================

    if contract.status != "indexed":

        raise HTTPException(
            status_code=400,
            detail=(
                "Contract is not ready. "
                f"Current status: {contract.status}"
            ),
        )

    # ==================================================
    # 3. Activate contract
    # ==================================================

    contract = repository.set_active(
        contract
    )

    return contract