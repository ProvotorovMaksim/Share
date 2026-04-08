# src/redaktorsha/models_base.py
"""
Общий базовый класс для всех моделей БД.
Используется и основным ботом (async), и auth-модулем (sync).
"""
from sqlalchemy.orm import declarative_base

# Единая база для всех моделей — метаданные будут общими
Base = declarative_base()