terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "0.95.0"
    }
    telegram = {
      source  = "yi-jiayu/telegram"
      version = ">= 0.3.0"
    }
  }
}

provider "yandex" {
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  zone      = "ru-central1-a"
  token     = file(var.service_account_key_path)
}

provider "telegram" {
  bot_token = var.tg_bot_key
}

resource "yandex_iam_service_account" "sa" {
  name        = "cheatsheet-sa-vvot10-terraform"
  description = "Service account for Telegram bot created by Terraform"
  folder_id   = var.folder_id
}

resource "yandex_iam_service_account_static_access_key" "sa_static_key" {
  service_account_id = "ajefkte6urcqvndrlfjd"
  description        = "Static access key for object storage"
}

resource "yandex_iam_service_account_api_key" "sa_api_key" {
  service_account_id = "ajefkte6urcqvndrlfjd"
  description        = "API key for Yandex GPT and Vision"
}

resource "yandex_storage_bucket" "instructions_bucket" {
  bucket     = "cheatsheet-instructions-vvot10"
  access_key = yandex_iam_service_account_static_access_key.sa_static_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa_static_key.secret_key
}

resource "yandex_storage_object" "gpt_instruction" {
  bucket     = yandex_storage_bucket.instructions_bucket.bucket
  key        = "gpt_instruction.txt"
  content    = file("${path.module}/gpt_instruction.txt")
  depends_on = [yandex_storage_bucket.instructions_bucket]
}

data "archive_file" "bot_code" {
  type        = "zip"
  output_path = "function.zip"
  
  source {
    content  = file("${path.module}/main.py")
    filename = "main.py"
  }
  
  source {
    content  = file("${path.module}/requirements.txt")
    filename = "requirements.txt"
  }
}

resource "yandex_function" "telegram_bot" {
  name               = "telegram-bot-vvot10"
  description        = "Telegram bot for OS exam questions"
  user_hash          = "telegram-bot-v1"
  runtime            = "python311"
  entrypoint         = "main.handler"
  memory             = 256
  execution_timeout  = 30
  service_account_id = "ajefkte6urcqvndrlfjd"
  
  environment = {
    TG_BOT_TOKEN           = var.tg_bot_key
    YC_FOLDER_ID           = var.folder_id
    YC_API_KEY             = yandex_iam_service_account_api_key.sa_api_key.secret_key
    BUCKET_NAME            = yandex_storage_bucket.instructions_bucket.bucket
    INSTRUCTION_OBJECT_KEY = yandex_storage_object.gpt_instruction.key
  }
  
  content {
    zip_filename = data.archive_file.bot_code.output_path
  }
}

resource "telegram_bot_webhook" "bot_webhook" {
  url = "https://functions.yandexcloud.net/${yandex_function.telegram_bot.id}"
}

resource "null_resource" "remove_webhook" {
  triggers = {
    webhook_url = telegram_bot_webhook.bot_webhook.url
    tg_bot_key  = var.tg_bot_key
  }

  provisioner "local-exec" {
    when    = destroy
    command = "curl -s -X POST \"https://api.telegram.org/bot${self.triggers.tg_bot_key}/deleteWebhook\" > /dev/null 2>&1 || true"
  }

  depends_on = [telegram_bot_webhook.bot_webhook]
}
