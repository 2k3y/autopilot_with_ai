import argparse
import numpy as np
import tensorflow as tf

# Настройки проекта
import config

# Модуль с главным циклом миссии
from modules.mission import run_full_mission

# Импортируем нашу базу данных из новой папки модулей
from modules.database import init_db

# API симулятора
from inavmspapi import MultirotorControl, TCPTransmitter
from agrotechsimapi import SimClient

def main():
    # 1. Парсинг аргументов
    parser = argparse.ArgumentParser()
    parser.add_argument("--inav_host", type=str, default=config.INAV_HOST)
    parser.add_argument("--inav_port", type=int, default=config.INAV_PORT)
    parser.add_argument("--recharge_every", type=int, default=config.RECHARGE_EVERY) # Видимо, друг добавил функцию подзарядки!
    args = parser.parse_args()

    # 2. Подключение к симулятору
    tcp_transmitter = TCPTransmitter((args.inav_host, args.inav_port))
    tcp_transmitter.connect()
    control = MultirotorControl(tcp_transmitter)
    sim_client = SimClient(address=args.inav_host, port=config.SIM_PORT)

    print("=" * 60 + f"\nСТАРТ МИССИИ ({config.ALTITUDE_M}м)\n" + "=" * 60)

    # Инициализируем нашу БД
    db_conn = init_db()

    # 3. Загрузка нейросети
    try:
        model = tf.keras.models.load_model(config.MODEL_PATH)
        # Прогревочный прогон для ускорения первого кадра
        model.predict(np.zeros((1, config.IMG_SIZE, config.IMG_SIZE, 3)), verbose=0)
        print("  ✅ ИИ Модель готова")
    except Exception as e:
        print(f"  ❌ Ошибка загрузки модели: {e}")
        return

    # 4. Передаем управление в модуль миссии
    # Добавляем db_conn в конец списка аргументов, чтобы миссия могла сохранять фото!
    run_full_mission(sim_client, control, tcp_transmitter, model, args.recharge_every, db_conn)

if __name__ == "__main__":
    main()