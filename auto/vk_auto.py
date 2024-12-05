from flask import Flask, request, redirect, jsonify

app = Flask(__name__)

# VK callback
@app.route('/callback', methods=['GET'])
def vk_callback():
    access_token = request.args.get('access_token')
    if not access_token:
        return jsonify({"error": "Access token not provided"}), 400

    # Связываем пользователя с Telegram через ваш бот
    # Например, сохраняем токен или отправляем сообщение боту
    # Здесь вы можете использовать Telegram Bot API
    user_id = "TELEGRAM_USER_ID"  # Нужно получить из контекста
    send_message_to_bot(user_id, access_token)

    return "Авторизация завершена!"

def send_message_to_bot(user_id, token):
    import requests
    BOT_TOKEN = "ВАШ_TOKEN"
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    message = f"Пользователь успешно авторизован через VK. Access token: {token}"
    payload = {"chat_id": user_id, "text": message}
    requests.post(TELEGRAM_API_URL, data=payload)

if __name__ == '__main__':
    app.run(debug=True)
