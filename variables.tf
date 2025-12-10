variable "cloud_id" {
  type        = string
  description = "Yandex Cloud ID"
  sensitive   = true
}

variable "folder_id" {
  type        = string
  description = "Yandex Folder ID"
  sensitive   = true
}

variable "tg_bot_key" {
  type        = string
  description = "Telegram Bot API Key"
  sensitive   = true
}

variable "service_account_key_path" {
  type        = string
  description = "Path to service account key file"
  default     = "~/.yc-keys/key.json"
}
