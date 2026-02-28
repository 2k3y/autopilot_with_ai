# --- НАСТРОЙКИ СВЯЗИ ---
INAV_HOST = "192.168.0.172"
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
SNAKE_START_LAT = 454276736
SNAKE_START_LON = 396638176
SNAKE_RIGHT_LON = 396587360
SNAKE_END_LAT = 454412384
SNAKE_END_LON = 396585696
SNAKE_LAT_STEP = 3000
RECHARGE_EVERY = 7

# --- ПАРАМЕТРЫ ПОСАДКИ ---
LANDING_ALT_THRESHOLD = 15.0  # Высота начала точной посадки
BASE_DIST_THRESHOLD = 50.0    # Дистанция до базы для захвата
PID_P_GAIN = 150              # Чувствительность удержания позиции