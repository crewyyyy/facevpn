import json
import os
from uuid import uuid4

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

router = Router()

VLESS_HOST = os.getenv("VLESS_HOST", "example.com")
VLESS_PORT = int(os.getenv("VLESS_PORT", "443"))
VLESS_WS_PATH = os.getenv("VLESS_WS_PATH", "/facevpn")
VLESS_SNI = os.getenv("VLESS_SNI", VLESS_HOST)
VLESS_LABEL = os.getenv("VLESS_LABEL", "FaceVPN Test")
VLESS_TRANSPORT = os.getenv("VLESS_TRANSPORT", "ws")
VLESS_FLOW = os.getenv("VLESS_FLOW", "")


@router.message(Command("apitest"))
async def apitest_handler(message: Message):
    profile_id = str(uuid4())

    vless_uri = (
        f"vless://{profile_id}@{VLESS_HOST}:{VLESS_PORT}"
        f"?encryption=none&security=tls&type={VLESS_TRANSPORT}"
        f"&sni={VLESS_SNI}&host={VLESS_SNI}&path={VLESS_WS_PATH}"
        f"&flow={VLESS_FLOW}#{VLESS_LABEL}"
    )

    nekobox_profile = {
        "remark": VLESS_LABEL,
        "type": "VLESS",
        "address": VLESS_HOST,
        "port": VLESS_PORT,
        "id": profile_id,
        "encryption": "none",
        "flow": VLESS_FLOW,
        "udp": True,
        "transport": {
            "type": VLESS_TRANSPORT,
            "path": VLESS_WS_PATH,
            "headers": {"Host": VLESS_SNI},
        },
        "tls": {
            "enabled": True,
            "alpn": ["h2", "http/1.1"],
            "serverName": VLESS_SNI,
            "insecure": False,
        },
    }

    json_payload = json.dumps(nekobox_profile, ensure_ascii=False, indent=2)
    file_payload = BufferedInputFile(
        json_payload.encode("utf-8"),
        filename="nekobox_vless_profile.json",
    )

    await message.answer(
        "✅ Тестовый VLESS профиль создан.\n\n"
        "<b>Ссылка для импорта:</b>\n"
        f"<code>{vless_uri}</code>\n\n"
        "JSON профиль для Nekobox отправлен отдельным файлом.",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await message.answer_document(file_payload)
