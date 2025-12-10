import os
import json
import logging
import requests
import base64
from flask import Flask, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get('TG_BOT_TOKEN')
YC_FOLDER_ID = os.environ.get('YC_FOLDER_ID')
YC_API_KEY = os.environ.get('YC_API_KEY')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
OBJECT_KEY = os.environ.get('INSTRUCTION_OBJECT_KEY')

class YandexGPTClient:
    def __init__(self, folder_id, api_key):
        self.folder_id = folder_id
        self.api_key = api_key
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
    def get_instruction(self):
        return """
        Ты - эксперт по операционным системам, помогающий студентам подготовиться к экзамену.
        Отвечай строго по учебной программе, будь точным и структурированным.
        
        Структура ответа:
        1. Определение и основные понятия
        2. Принципы работы и механизмы
        3. Примеры и практическое применение
        
        Будь лаконичным, но информативным. Ответ должен быть 200-300 слов.
        """
    
    def classify_question(self, text):
        try:
            prompt = {
                "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.1,
                    "maxTokens": 50
                },
                "messages": [
                    {
                        "role": "system",
                        "text": "Определи, является ли текст экзаменационным вопросом по операционным системам. Отвечай только 'yes' или 'no'."
                    },
                    {
                        "role": "user",
                        "text": f"Текст: {text[:500]}"
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.url, json=prompt, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            classification = result['result']['alternatives'][0]['message']['text'].strip().lower()
            
            return 'yes' in classification
        except Exception as e:
            logger.error(f"Ошибка классификации: {e}")
            return True
    
    def generate_answer(self, question):
        """Генерация ответа на вопрос"""
        try:
            instruction = self.get_instruction()
            
            prompt = {
                "modelUri": f"gpt://{self.folder_id}/yandexgpt",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.3,
                    "maxTokens": 1000
                },
                "messages": [
                    {
                        "role": "system",
                        "text": instruction
                    },
                    {
                        "role": "user",
                        "text": f"Вопрос: {question}\n\nДай развернутый ответ на этот экзаменационный вопрос по операционным системам."
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.url, json=prompt, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            answer = result['result']['alternatives'][0]['message']['text']
            
            return answer
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return "Я не смог подготовить ответ на экзаменационный вопрос."

class YandexVisionClient:
    def __init__(self, api_key, folder_id):
        self.api_key = api_key
        self.folder_id = folder_id
        self.url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
    
    def recognize_text(self, image_data):
        try:
            request_body = {
                "folderId": self.folder_id,
                "analyze_specs": [{
                    "content": image_data,
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "text_detection_config": {
                            "language_codes": ["ru", "en"]
                        }
                    }]
                }]
            }
            
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info("Отправка запроса в Yandex Vision...")
            response = requests.post(self.url, json=request_body, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Vision response received")

            def extract_text(obj):
                if isinstance(obj, dict):
                    text_parts = []
                    for key, value in obj.items():
                        if key == 'text':
                            text_parts.append(str(value))
                        else:
                            text_parts.extend(extract_text(value))
                    return text_parts
                elif isinstance(obj, list):
                    text_parts = []
                    for item in obj:
                        text_parts.extend(extract_text(item))
                    return text_parts
                else:
                    return []
            
            all_text = extract_text(result)
            recognized_text = ' '.join(all_text).strip()
            
            if recognized_text:
                logger.info(f"Recognized text: {recognized_text[:200]}...")
                return recognized_text
            else:
                logger.warning("No text found in response")
                return None
            
        except Exception as e:
            logger.error(f"Ошибка распознавания текста: {e}", exc_info=True)
            return None

gpt_client = YandexGPTClient(YC_FOLDER_ID, YC_API_KEY)
vision_client = YandexVisionClient(YC_API_KEY, YC_FOLDER_ID)

def send_telegram_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False

def handle_start(chat_id):
    message = "Я помогу ответить на экзаменационный вопрос по «Операционным системам».\nПрисылайте вопрос — фото или текстом."
    send_telegram_message(chat_id, message)

def handle_help(chat_id):
    message = "Я помогу ответить на экзаменационный вопрос по «Операционным системам».\nПрисылайте вопрос — фото или текстом."
    send_telegram_message(chat_id, message)

def handle_text(chat_id, text):
    logger.info(f"Обработка текста: {text}")
    
    if not gpt_client.classify_question(text):
        send_telegram_message(
            chat_id,
            "Я не могу понять вопрос.\nПришлите экзаменационный вопрос по «Операционным системам» — фото или текстом."
        )
        return
    
    answer = gpt_client.generate_answer(text)
    send_telegram_message(chat_id, answer)

def handle_photo(chat_id, photo_info):
    logger.info(f"Обработка фото, info: {photo_info}")
    
    if not photo_info:
        send_telegram_message(chat_id, "Я не могу обработать эту фотографию.")
        return
    
    try:
        file_id = photo_info[-1]['file_id']
        logger.info(f"File ID: {file_id}")
        
        file_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
        file_response = requests.post(file_url, json={'file_id': file_id}, timeout=10)
        file_response.raise_for_status()
        
        file_data = file_response.json()
        logger.info(f"File data: {file_data}")
        
        if 'result' not in file_data or 'file_path' not in file_data['result']:
            send_telegram_message(chat_id, "Не удалось получить информацию о файле.")
            return
            
        file_path = file_data['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        logger.info(f"Download URL: {download_url}")
        
        image_response = requests.get(download_url, timeout=30)
        image_response.raise_for_status()
        
        image_base64 = base64.b64encode(image_response.content).decode('utf-8')
        logger.info(f"Image encoded, size: {len(image_base64)}")
        
        send_telegram_message(chat_id, "Распознаю текст с фотографии...")
        recognized_text = vision_client.recognize_text(image_base64)
        
        if not recognized_text:
            send_telegram_message(chat_id, "Не удалось распознать текст на фотографии. Попробуйте другое фото.")
            return
        
        logger.info(f"Распознанный текст: {recognized_text}")
        
        send_telegram_message(chat_id, f"Распознанный вопрос:\n{recognized_text}")
        
        send_telegram_message(chat_id, "Генерирую ответ...")
        answer = gpt_client.generate_answer(recognized_text)
        
        send_telegram_message(chat_id, answer)
            
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}", exc_info=True)
        send_telegram_message(chat_id, f"Ошибка обработки фотографии: {str(e)}")

def handle_other(chat_id):
    send_telegram_message(chat_id, "Я могу обработать только текстовое сообщение или фотографию.")

@app.route('/', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        logger.info(f"Received update type: {update.keys() if update else 'empty'}")
        
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            
            if 'text' in message:
                text = message['text']
                
                if text.startswith('/start'):
                    handle_start(chat_id)
                elif text.startswith('/help'):
                    handle_help(chat_id)
                else:
                    handle_text(chat_id, text)
            
            elif 'photo' in message:
                handle_photo(chat_id, message['photo'])
            
            else:
                handle_other(chat_id)
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

def handler(event, context):
    """Обработчик для Yandex Cloud Functions"""
    try:
        if 'httpMethod' in event:
            body = json.loads(event['body']) if event.get('body') else {}
            with app.test_client() as client:
                response = client.post('/', json=body)
                return {
                    'statusCode': response.status_code,
                    'body': response.get_data(as_text=True),
                    'headers': {'Content-Type': 'application/json'}
                }
        else:
            return {'status': 'Function is ready'}
            
    except Exception as e:
        logger.error(f"Ошибка в handler: {e}", exc_info=True)
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
