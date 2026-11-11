import os

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000"
).rstrip("/")

TIMEOUT = 60


class APIError(Exception):
    """Lỗi khi gọi hoặc xử lý phản hồi từ backend."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _request(method, path, token=None, **kwargs):
    """Gửi request tới FastAPI và xử lý lỗi chung."""

    url = f"{API_BASE_URL}{path}"

    headers = kwargs.pop("headers", {})

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            timeout=TIMEOUT,
            **kwargs
        )
    except requests.RequestException as exc:
        raise APIError(
                f"Lỗi khi gọi backend: {type(exc).__name__}: {exc}"
            ) from exc

    if response.status_code == 401:
        raise APIError(
            "Phiên đăng nhập không hợp lệ hoặc đã hết hạn. "
            "Vui lòng đăng nhập lại.",
            status_code=401,
        )

    if response.status_code == 403:
        raise APIError(
            "Bạn không có quyền thực hiện thao tác này.",
            status_code=403,
    )

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok:
        detail = data.get(
            "detail",
            data.get("message", response.text)
        )

        if isinstance(detail, list):
            detail = "; ".join(
                str(item.get("msg", item))
                if isinstance(item, dict)
                else str(item)
                for item in detail
            )

        raise APIError(
             f"API trả về lỗi {response.status_code}: {detail}",
            status_code=response.status_code,
        )

    return data


def check_health():
    """Kiểm tra tình trạng backend."""

    return _request("GET", "/health")


# -------------------------
# Xác thực tài khoản
# -------------------------

def register_account(username, email, password):
    return _request(
        "POST",
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )


def login_account(email, password):
    return _request(
        "POST",
        "/api/auth/login",
        json={
            "email": email,
            "password": password
        }
    )


def get_current_user(token):
    return _request(
        "GET",
        "/api/auth/me",
        token=token
    )


# -------------------------
# Hỏi đáp hợp đồng
# -------------------------

def ask_contract_question(
    token,
    question,
    contract_id=None
):
    return _request(
        "POST",
        "/api/qa/chat",
        token=token,
        json={
            "query": question,
            "contract_id": contract_id
        }
    )


def get_qa_history(token):
    return _request(
        "GET",
        "/api/qa/history",
        token=token
    )


# -------------------------
# Đánh giá rủi ro
# -------------------------

def assess_contract_risk(token, contract_id):
    return _request(
        "POST",
        "/api/risk/assess",
        token=token,
        json={
            "contract_id": contract_id
        }
    )


def get_risk_history(token):
    return _request(
        "GET",
        "/api/risk-assessment/history",
        token=token
    )


# -------------------------
# Quản lý hợp đồng
# -------------------------

def get_contracts(token):
    return _request(
        "GET",
        "/api/contracts",
        token=token
    )


def activate_contract(token, contract_id):
    return _request(
        "POST",
        f"/api/contracts/{contract_id}/activate",
        token=token,
    )

def upload_contract(token, uploaded_file):
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream"
        )
    }

    return _request(
        "POST",
        "/api/contracts/upload",
        token=token,
        files=files
    )


def delete_contract(token, contract_id):
    return _request(
        "DELETE",
        f"/api/contracts/{contract_id}",
        token=token
    )