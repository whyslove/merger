from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    rabbitmq_password: str = Field(..., env="RABBITMQ_PASSWORD")
    rabbitmq_name: str = Field(..., env="RABBITMQ_NAME")
    rabbitmq_host: str = Field(..., env="RABBITMQ_HOST")
    rabbitmq_port: str = Field(..., env="RABBITMQ_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings(_env_file="../.env")
