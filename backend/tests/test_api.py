import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("FPT_BASE_URL", "https://mkp-api.fptcloud.com/v1")
MODEL_NAME = os.getenv("FPT_MODEL", "gemma-3-27b-it")

if not API_KEY:
    raise ValueError(
        "Không tìm thấy FPT_API_KEY. Hãy kiểm tra file .env trong thư mục backend."
    )

print("=" * 60)
print("TEST FPT API")
print("=" * 60)
print(f"BASE_URL : {BASE_URL}")
print(f"MODEL    : {MODEL_NAME}")
print(f"API KEY  : {API_KEY[:8]}...{API_KEY[-4:]}")
print()

try:
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=120.0,
    )

    print("Đang gửi request...")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "Bạn là trợ lý kiểm tra API. Trả lời ngắn gọn bằng tiếng Việt.",
            },
            {
                "role": "user",
                "content": "API có hoạt động không? Hãy trả lời: API hoạt động bình thường.",
            },
        ],
        temperature=0.2,
    )

    print("\n[OK] API gọi thành công!")
    print("-" * 60)
    print("Response:")
    print(response.choices[0].message.content)
    print("-" * 60)

    if getattr(response, "usage", None):
        print("\nToken usage:")
        print(response.usage)

except Exception as e:
    print("\n[ERROR] API gọi thất bại!")
    print("-" * 60)
    print(f"Loại lỗi: {type(e).__name__}")
    print(f"Chi tiết : {e}")
    print("-" * 60)
