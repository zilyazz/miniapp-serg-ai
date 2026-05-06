from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.const import DEEPSEEK_REASONER, GPT_4O, QWEN3_NEXT_80B, QWEN3_VL_32B, YANDEX_GPT_LITE, YANDEXGPT_LITE, YANDEX_GPT_3_5_TURBO, YANDEXGPT_5_LITE


MODEL_ALIASES = {
    'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8': GPT_4O,
    'Llama-4-Maverick-17B-128E-Instruct-FP8': GPT_4O,
    'meta-llama/llama-4-maverick': GPT_4O,
    'Qwen/Qwen3-Next-80B-A3B-Instruct': QWEN3_NEXT_80B,
    'Qwen3-Next-80B-A3B-Instruct': QWEN3_NEXT_80B,
    'qwen/qwen3-next-80b-a3b-instruct-2509': QWEN3_NEXT_80B,
    'Qwen/Qwen3-VL-32B-Instruct': QWEN3_VL_32B,
    'Qwen3-VL-32B-Instruct': QWEN3_VL_32B,
}


class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_BASE_URL: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    YANDEX_API_KEY: str | None = None
    YANDEX_BASE_URL: str | None = None
    YANDEX_FOLDER_ID: str | None = None

    def validate_api_configs(self) -> bool:
        return (
            (self.DEEPSEEK_API_KEY and self.DEEPSEEK_BASE_URL) or
            (self.OPENROUTER_API_KEY and self.OPENROUTER_BASE_URL) or
            (self.OPENAI_API_KEY and self.OPENAI_BASE_URL) or
            (self.YANDEX_API_KEY and self.YANDEX_BASE_URL)
        )

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    def normalize_model_name(self, model_name: str) -> str:
        normalized = model_name.strip()
        return MODEL_ALIASES.get(normalized, normalized)

    def get_model_config(self, model_name: str = '') -> dict[str, str]:
        if not self.validate_api_configs():
            raise ValueError("Необходимо указать хотя бы одну валидную пару API ключа и URL")

        normalized_model_name = self.normalize_model_name(model_name)
        config = {}
        if normalized_model_name == DEEPSEEK_REASONER:
            config['api_key'] = self.DEEPSEEK_API_KEY
            config['base_url'] = self.DEEPSEEK_BASE_URL
            config['model_name'] = normalized_model_name
        elif normalized_model_name in {GPT_4O, QWEN3_NEXT_80B, QWEN3_VL_32B}:
            config['api_key'] = self.OPENROUTER_API_KEY or self.OPENAI_API_KEY
            config['base_url'] = self.OPENROUTER_BASE_URL or self.OPENAI_BASE_URL
            config['model_name'] = normalized_model_name
        elif normalized_model_name in {
            YANDEX_GPT_LITE,
            YANDEXGPT_LITE,
            YANDEX_GPT_3_5_TURBO,
            YANDEXGPT_5_LITE,
        }:
            config['api_key'] = self.YANDEX_API_KEY
            config['base_url'] = self.YANDEX_BASE_URL.rstrip('/')
            config['yandex_cloud_folder'] = self.YANDEX_FOLDER_ID
            config['model_name'] = normalized_model_name
        elif self.OPENROUTER_API_KEY and self.OPENROUTER_BASE_URL:
            config['api_key'] = self.OPENROUTER_API_KEY
            config['base_url'] = self.OPENROUTER_BASE_URL
            config['model_name'] = normalized_model_name
        elif self.OPENAI_API_KEY and self.OPENAI_BASE_URL:
            config['api_key'] = self.OPENAI_API_KEY
            config['base_url'] = self.OPENAI_BASE_URL
            config['model_name'] = normalized_model_name
        elif self.DEEPSEEK_API_KEY and self.DEEPSEEK_BASE_URL:
            config['api_key'] = self.DEEPSEEK_API_KEY
            config['base_url'] = self.DEEPSEEK_BASE_URL
            config['model_name'] = normalized_model_name

        return config
