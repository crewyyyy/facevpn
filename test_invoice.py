import requests
from dotenv import load_dotenv
import os

load_dotenv()

CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
CRYPTOBOT_API_URL = "https://testnet-pay.crypt.bot/api"

headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
data = {
    "asset": "USDT",
    "amount": 2.5,  # Число, не строка
    "description": "Тестовый инвойс для FaceVPN"
}

response = requests.post(f"{CRYPTOBOT_API_URL}/createInvoice", headers=headers, json=data)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

if response.ok:
    resp_data = response.json()
    if resp_data.get("ok"):
        result = resp_data["result"]
        print(f"✅ Инвойс создан! ID: {result['invoice_id']}, Pay URL: {result['pay_url']}")
    else:
        print(f"❌ API ошибка: {resp_data.get('error', 'No error details')}")
else:
    print(f"❌ HTTP ошибка: {response.status_code}")