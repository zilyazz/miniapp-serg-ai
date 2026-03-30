from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.const import DEEPSEEK_REASONER, GPT_4O, QWEN3_NEXT_80B, QWEN3_VL_32B, YANDEX_GPT_LITE, YANDEXGPT_LITE, YANDEX_GPT_3_5_TURBO, YANDEXGPT_5_LITE

class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_BASE_URL: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    YANDEX_API_KEY: str | None = None
    YANDEX_BASE_URL: str | None = None
    YANDEX_FOLDER_ID: str | None = None

    def validate_api_configs(self) -> bool:
        return (
            (self.DEEPSEEK_API_KEY and self.DEEPSEEK_BASE_URL) or
            (self.OPENAI_API_KEY and self.OPENAI_BASE_URL) or
            (self.YANDEX_API_KEY and self.YANDEX_BASE_URL)
        )

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    def get_model_config(self, model_name: str = '') -> dict[str, str]:
        if not self.validate_api_configs():
            raise ValueError("Необходимо указать хотя бы одну валидную пару API ключа и URL")

        config = {}
        if model_name == DEEPSEEK_REASONER:
            config['api_key'] = self.DEEPSEEK_API_KEY
            config['base_url'] = self.DEEPSEEK_BASE_URL
        elif model_name in {GPT_4O, QWEN3_NEXT_80B, QWEN3_VL_32B}:
            # Модели, использующие OpenAI-совместимый API (Together AI)
            config['api_key'] = self.OPENAI_API_KEY
            config['base_url'] = self.OPENAI_BASE_URL
        elif model_name in {
            YANDEX_GPT_LITE,
            YANDEXGPT_LITE,
            YANDEX_GPT_3_5_TURBO,
            YANDEXGPT_5_LITE,
        }:
            config['api_key'] = self.YANDEX_API_KEY
            config['base_url'] = self.YANDEX_BASE_URL.rstrip('/')
            config['yandex_cloud_folder'] = self.YANDEX_FOLDER_ID

        return config