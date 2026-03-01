import os
import psycopg2
from psycopg2 import Binary
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import cv2
import config

def init_db():
    os.environ["PGCLIENTENCODING"] = "utf-8"
    try:
        setup_conn = psycopg2.connect(
            host=config.DB_HOST, port=config.DB_PORT, dbname="postgres",
            user=config.DB_USER, password=config.DB_PASS
        )
        setup_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        setup_cursor = setup_conn.cursor()

        setup_cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{config.DB_NAME}'")
        if not setup_cursor.fetchone():
            print(f"  ⏳ Создаем новую базу данных '{config.DB_NAME}'...")
            setup_cursor.execute(f"CREATE DATABASE {config.DB_NAME}")

        setup_cursor.close()
        setup_conn.close()
    except Exception as e:
        print(f"  ❌ Ошибка при создании БД: {e}")
        return None

    try:
        conn = psycopg2.connect(
            host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
            user=config.DB_USER, password=config.DB_PASS
        )
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empty_areas (
                id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                lat DOUBLE PRECISION, lon DOUBLE PRECISION, confidence REAL, image BYTEA
            )
        """)
        cursor.execute("TRUNCATE TABLE empty_areas RESTART IDENTITY;")
        conn.commit()
        print(f"  ✅ БД '{config.DB_NAME}' подключена, старые данные очищены")
        return conn
    except Exception as e:
        print(f"  ❌ Ошибка подключения к рабочей БД: {e}")
        return None

def save_empty_area(db_conn, lat, lon, prob, frame):
    if db_conn is None: return
    _, buffer = cv2.imencode('.jpg', frame)
    try:
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO empty_areas (lat, lon, confidence, image)
            VALUES (%s, %s, %s, %s)
        """, (lat, lon, float(1 - prob), Binary(buffer.tobytes())))
        db_conn.commit()
        print(f"\n[БД] Сохранен пустой участок: {lat}, {lon}")
    except Exception as e:
        print(f"\n[БД] Ошибка записи: {e}")
        db_conn.rollback()