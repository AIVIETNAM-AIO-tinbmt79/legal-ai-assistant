
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.database.repositories.contract_repository import ContractRepository
from app.schemas.contract import ContractResponse

import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)

from app.services.contract_service import ContractService

router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"],
)

# backend nằm trong thư mục con của project.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post(
    "/upload",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_contract(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng chọn file hợp đồng.",
        )

    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ chấp nhận file PDF, DOCX hoặc DOC.",
        )

    # Đọc tối đa 20 MB + 1 byte để phát hiện file quá lớn.
    content = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File tải lên đang trống.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Dung lượng file không được vượt quá 20 MB.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Tạo file tạm để chuyển cho pipeline index.
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        service = ContractService(db=db)

        contract = service.upload_contract(
            user_id=user_id,
            original_filename=original_filename,
            source_file_path=temp_path,
        )

        return contract

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Lỗi khi lưu và lập chỉ mục hợp đồng: %s",
            original_filename,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể lưu và lập chỉ mục hợp đồng.",
        )

    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


@router.get(
    "",
    response_model=list[ContractResponse],
)
def get_contracts(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = ContractRepository(db)
    return repository.get_by_user(user_id)


@router.get(
    "/{contract_id}",
    response_model=ContractResponse,
)
def get_contract(
    contract_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = ContractRepository(db)

    contract = repository.get_by_id(
        contract_id=contract_id,
        user_id=user_id,
    )

    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hợp đồng.",
        )

    return contract


@router.patch(
    "/{contract_id}/activate",
    response_model=ContractResponse,
)
def activate_contract(
    contract_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = ContractRepository(db)

    contract = repository.set_active(
        contract_id=contract_id,
        user_id=user_id,
    )

    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hợp đồng.",
        )

    return contract


@router.delete(
    "/{contract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_contract(
    contract_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = ContractRepository(db)

    # Chỉ tìm hợp đồng thuộc tài khoản hiện tại.
    contract = repository.get_by_id(
        contract_id=contract_id,
        user_id=user_id,
    )

    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hợp đồng.",
        )

    file_path = Path(contract.file_path)

    # Xóa bản ghi trong database.
    deleted = repository.delete(
        contract_id=contract_id,
        user_id=user_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hợp đồng.",
        )

    # Chỉ xóa file nằm trong thư mục upload do ứng dụng quản lý.
    try:
        resolved_file = file_path.resolve()
        resolved_upload_dir = UPLOAD_DIR.resolve()

        if (
            resolved_file.is_relative_to(resolved_upload_dir)
            and resolved_file.is_file()
        ):
            resolved_file.unlink()

    except OSError:
        # Bản ghi đã xóa; lỗi dọn file cần được ghi log khi triển khai.
        pass

    return None
