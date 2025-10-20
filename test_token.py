import requests
from dotenv import load_dotenv
import os

load_dotenv()

CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
CRYPTOBOT_API_URL = "https://testnet-pay.crypt.bot/api"

headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
response = requests.get(f"{CRYPTOBOT_API_URL}/getMe", headers=headers)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

if response.ok and response.json().get("ok"):
    print("✅ Токен действителен! Информация о приложении:", response.json()["result"])
else:
    print("❌ Токен недействителен или ошибка API. Получите новый через @CryptoTestnetBot /api")