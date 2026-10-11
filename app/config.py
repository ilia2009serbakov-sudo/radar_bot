from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    database_url: str
    webhook_base_url: str
    webhook_secret: str
    cron_secret: str

    admin_ids: str = ""
    free_topics_limit: int = 5
    premium_topics_limit: int = 20
    free_items_per_digest: int = 5
    premium_items_per_digest: int = 12
    premium_stars: int = 199
    premium_days: int = 30
    timezone_default: str = "Europe/Moscow"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_id_list(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}


settings = Settings()
