output "bot_username" {
  value = "cheatsheet_itis_2025_vvot10_bot"
}

output "function_id" {
  value = yandex_function.telegram_bot.id
}

output "function_url" {
  value = "https://functions.yandexcloud.net/${yandex_function.telegram_bot.id}"
}

output "storage_bucket" {
  value = yandex_storage_bucket.instructions_bucket.bucket
}

output "webhook_url" {
  value = "https://functions.yandexcloud.net/${yandex_function.telegram_bot.id}"
}
