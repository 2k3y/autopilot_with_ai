import time
import math
import argparse
import struct
import cv2
import numpy as np
import tensorflow as tf

# Импортируем наш файл настроек
import config

from inavmspapi import MultirotorControl, TCPTransmitter
from agrotechsimapi import SimClient, CaptureType


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ТЕЛЕМЕТРИИ ---
def get_altitude(sim_client):
    try:
        kin_data = sim_client.get_kinametics_data()
        if kin_data and "location" in kin_data:
            return float(kin_data["location"][2])
    except Exception:
        pass
    return None


def get_physics_xy(sim_client):
    try:
        kin_data = sim_client.get_kinametics_data()
        if kin_data and "location" in kin_data:
            return float(kin_data["location"][0]), float(kin_data["location"][1])
    except Exception:
        pass
    return None, None


def get_yaw(sim_client):
    try:
        kin = sim_client.get_kinametics_data()
        qx, qy, qz, qw = kin["orientation"]
        siny_cosp = 2 * (qw * qz + qx * qy)
        cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
        return math.atan2(siny_cosp, cosy_cosp)
    except Exception:
        return 0.0


def get_gps(control):
    try:
        if control.send_RAW_msg(MultirotorControl.MSPCodes["MSP_RAW_GPS"], data=[]):
            dataHandler = control.receive_msg()
            control.process_recv_data(dataHandler)
            lat, lon = control.GPS_DATA["lat"], control.GPS_DATA["lon"]
            if lat != 0 and lon != 0: return lat, lon
    except Exception:
        pass
    return None, None


# --- ML АНАЛИЗ ---
def analyze_frame(frame, model):
    h, w, _ = frame.shape
    min_dim = min(h, w)
    start_x = w // 2 - min_dim // 2
    start_y = h // 2 - min_dim // 2

    cropped_frame = frame[start_y:start_y + min_dim, start_x:start_x + min_dim]
    rgb_frame = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)

    # Используем размер из конфига
    img_resized = cv2.resize(rgb_frame, (config.IMG_SIZE, config.IMG_SIZE))
    img_array = tf.expand_dims(img_resized, 0)

    probability = model.predict(img_array, verbose=0)[0][0]
    return probability, (start_x, start_y, min_dim)


# --- ПОСТРОЕНИЕ МАРШРУТА (ДАННЫЕ ИЗ CONFIG) ---
def build_snake_waypoints(home_lat, home_lon):
    wps = []
    wp_num = 1

    # WP1: база
    wps.append([wp_num, 1, home_lat, home_lon, config.ALT_FLY_CM, config.SPEED, 0, 0, 0])
    wp_num += 1

    # WP2: старт змейки
    wps.append([wp_num, 1, config.START_LAT, config.START_LON, config.ALT_FLY_CM, config.SPEED, 0, 0, 0])
    wp_num += 1

    lat = config.START_LAT
    while lat <= config.END_LAT:
        wps.append([wp_num, 1, lat, config.RIGHT_LON, config.ALT_FLY_CM, config.SPEED, 0, 0, 0])
        wp_num += 1

        lat += config.LAT_STEP
        wps.append([wp_num, 1, lat, config.RIGHT_LON, config.ALT_FLY_CM, config.SPEED, 0, 0, 0])
        wp_num += 1

        if lat > config.END_LAT: break

        wps.append([wp_num, 1, lat, config.START_LON, config.ALT_FLY_CM, config.SPEED, 0, 0, 0])
        wp_num += 1

        lat += config.LAT_STEP
        wps.append([wp_num, 1, lat, config.START_LON, config.ALT_FLY_CM, config.SPEED, 0, 0, 0])
        wp_num += 1

        if lat > config.END_LAT: break

    wps.append([wp_num, 1, home_lat, home_lon, config.ALT_FLY_CM, config.SPEED, 0, 0, 0])
    wp_num += 1
    wps.append([wp_num, 1, home_lat, home_lon, 0, 0, 0, 0, 165])  # Landing
    return wps


def send_waypoints_in_batches(control, waypoints):
    print(f"\nЗАГРУЗКА МАРШРУТА ({len(waypoints)} точек):")
    for wp in waypoints:
        binary_data = struct.pack("<BBIIIHHHB", *wp)
        control.send_RAW_msg(MultirotorControl.MSPCodes["MSP_SET_WP"], binary_data)
        time.sleep(0.2)
        print(f"  WP{wp[0]:2d} | lat={wp[2]} lon={wp[3]} | alt={wp[4] / 100:.0f}м")


def main():
    # Теперь argparse берет значения по умолчанию из конфига
    parser = argparse.ArgumentParser()
    parser.add_argument("--inav_host", type=str, default=config.INAV_HOST)
    parser.add_argument("--inav_port", type=int, default=config.INAV_PORT)
    args = parser.parse_args()

    tcp_transmitter = TCPTransmitter((args.inav_host, args.inav_port))
    tcp_transmitter.connect()
    control = MultirotorControl(tcp_transmitter)
    sim_client = SimClient(address=args.inav_host, port=config.SIM_PORT)

    print("=" * 60 + f"\nСТАРТ МИССИИ ({config.ALTITUDE_M}м)\n" + "=" * 60)

    # 1. Загрузка нейросети
    try:
        model = tf.keras.models.load_model(config.MODEL_PATH)
        problem_points = []
        model.predict(np.zeros((1, config.IMG_SIZE, config.IMG_SIZE, 3)), verbose=0)
        print("  ✅ Модель готова")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return

    # 2. Калибровка
    start_x, start_y = None, None
    for _ in range(10):
        start_x, start_y = get_physics_xy(sim_client)
        if start_x is not None: break
        time.sleep(0.5)

    home_lat, home_lon = None, None
    for _ in range(10):
        home_lat, home_lon = get_gps(control)
        if home_lat is not None: break
        time.sleep(1.0)

    if home_lat is None: return

    # 3. Маршрут
    waypoints = build_snake_waypoints(home_lat, home_lon)
    send_waypoints_in_batches(control, waypoints)

    print("\nВЗЛЁТ...")
    # Шаг 1: Газ на минимум (1000), тумблер Арминга включен (2000)
    control.send_RAW_RC([1500, 1500, 1000, 1500, 2000, 1000, 1000])
    time.sleep(2.0)  # Даем симулятору 2 секунды, чтобы пропеллеры завелись

    # Шаг 2: Моторы работают, даем газ для набора высоты (1900)
    control.send_RAW_RC([1500, 1500, 1900, 1500, 2000, 1000, 1000])

    while True:
        alt = get_altitude(sim_client)
        # Печатаем высоту, чтобы видеть, что дрон реально летит вверх
        if alt is not None:
            print(f"Текущая высота: {alt:.1f}м", end='\r')
            if alt >= (config.ALTITUDE_M - 2):
                print("\nНужная высота достигнута!")
                break
        time.sleep(0.1)

    # 4. Полет
    control.send_RAW_RC([1500, 1500, 1500, 1500, 2000, 1000, 2000])
    mission_start = time.time()
    precise_landing = False

    while True:
        elapsed = time.time() - mission_start
        altitude = get_altitude(sim_client)

        if not precise_landing:
            frame = sim_client.get_camera_capture(1, CaptureType.color)
            if frame is not None:
                prob, bbox = analyze_frame(frame, model)
                bx, by, b_size = bbox

                # Порог из конфига
                if prob > config.CONFIDENCE_THRESHOLD:
                    label, color = f"PLANTED {prob * 100:.0f}%", (0, 255, 0)
                else:
                    label, color = f"EMPTY {(1 - prob) * 100:.0f}%", (0, 0, 255)
                    problem_points.append(elapsed)

                cv2.rectangle(frame, (bx, by), (bx + b_size, by + b_size), color, 3)
                cv2.putText(frame, label, (bx, by - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
                cv2.imshow("LIVE ANALYSIS", frame)
                cv2.waitKey(1)

            curr_x, curr_y = get_physics_xy(sim_client)
            dist = math.hypot(start_x - curr_x, start_y - curr_y) if curr_x else 999

            # Условия посадки из конфига
            if altitude and altitude < config.LANDING_ALT_THRESHOLD and elapsed > 60 and dist < config.BASE_DIST_THRESHOLD:
                print("\nПЕРЕХВАТ: ПОСАДКА...")
                precise_landing = True
                control.send_RAW_RC([1500, 1500, 1500, 1500, 2000, 1000, 1500])
            else:
                print(f"\r  {int(elapsed)}с | Высота: {altitude:.1f}м | База: {dist:.0f}м", end="")
        else:
            curr_x, curr_y = get_physics_xy(sim_client)
            yaw = get_yaw(sim_client)
            if curr_x and curr_y:
                dx, dy = start_x - curr_x, start_y - curr_y
                err_x = math.cos(yaw) * dx + math.sin(yaw) * dy
                err_y = -math.sin(yaw) * dx + math.cos(yaw) * dy

                # Коэффициент P из конфига
                rc_p = int(1500 + err_x * config.PID_P_GAIN)
                rc_r = int(1500 - err_y * config.PID_P_GAIN)

                rc_t = 1250 if altitude > 5.0 else 1320
                control.send_RAW_RC(
                    [max(1350, min(1650, rc_r)), max(1350, min(1650, rc_p)), rc_t, 1500, 2000, 1000, 1500])

            if altitude and altitude <= 0.5: break

        time.sleep(0.05)

    print(f"\nМИССИЯ ЗАВЕРШЕНА! Ошибок: {len(problem_points)}")
    cv2.destroyAllWindows()
    tcp_transmitter.disconnect()


if __name__ == "__main__":
    main()
