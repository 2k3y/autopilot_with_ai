# --- НАСТРОЙКИ СВЯЗИ ---
INAV_HOST = "127.0.0.1"
INAV_PORT = 5762
SIM_PORT = 8080

# --- НАСТРОЙКИ МОДЕЛИ ---
MODEL_PATH = "agro_cnn_model.keras"
IMG_SIZE = 224
CONFIDENCE_THRESHOLD = 0.5  # Порог уверенности (50%)

# --- ПАРАМЕТРЫ ПОЛЕТА ---
ALTITUDE_M = 50
SPEED = 2000
ALT_FLY_CM = ALTITUDE_M * 100

# --- КООРДИНАТЫ ЗМЕЙКИ ---
START_LAT = 454276736
START_LON = 396638176
RIGHT_LON = 396587360
END_LAT = 454327072
LAT_STEP = 3000

# --- ПАРАМЕТРЫ ПОСАДКИ ---
LANDING_ALT_THRESHOLD = 15.0  # Высота начала точной посадки
BASE_DIST_THRESHOLD = 50.0    # Дистанция до базы для захвата
PID_P_GAIN = 150              # Чувствительность удержания позиции

# --- НАСТРОЙКИ БД PostgreSQL ---
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "db_bsp"
DB_USER = "postgres"  # Ваш пользователь
DB_PASS = "1312"     # Ваш пароль