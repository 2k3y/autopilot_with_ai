import time
import math
import cv2
import config

from agrotechsimapi import CaptureType
from modules.telemetry import get_altitude, get_physics_xy, get_yaw, get_gps
from modules.ai_logic import analyze_frame
from modules.navigation import build_snake_waypoints, send_waypoints_in_batches

# --- ДОБАВЛЕНО: Импортируем нашу функцию для сохранения в БД ---
from modules.database import save_empty_area


# --- ДОБАВЛЕНО: db_conn в параметрах ---
def run_full_mission(sim_client, control, tcp_transmitter, model, recharge_every, db_conn):
    """
    Выполняет полную миссию: калибровка, полет по змейке с дозарядками и анализ ИИ.
    """
    # 1. Калибровка физики и базы
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

    if home_lat is None:
        print("  ❌ Не удалось получить GPS. Выход.")
        return

    problem_points = []
    resume_lat, resume_lon = None, None
    segment_num = 1

    # --- ДОБАВЛЕНО: Глобальный таймер для БД ---
    last_db_save = 0

    # 2. Главный цикл миссии (с перезарядками)
    while True:
        print(f"\n{'=' * 60}\nСЕГМЕНТ #{segment_num} | Возобновление: lat={resume_lat}, lon={resume_lon}\n{'=' * 60}")

        control.send_RAW_RC([1500, 1500, 1000, 1500, 1000, 1000, 1000])
        time.sleep(1.0)

        waypoints, next_lat, next_lon, finished = build_snake_waypoints(
            home_lat, home_lon, config.ALT_FLY_CM, config.SPEED, resume_lat, resume_lon, recharge_every
        )
        send_waypoints_in_batches(control, waypoints)

        print("\nВЗЛЁТ...")
        control.send_RAW_RC([1500, 1500, 1000, 1500, 2000, 1000, 1000])
        time.sleep(2.0)
        control.send_RAW_RC([1500, 1500, 1900, 1500, 2000, 1000, 1000])

        takeoff_start = time.time()
        while time.time() - takeoff_start < 30:
            alt = get_altitude(sim_client)
            if alt and alt >= (config.ALTITUDE_M - 2): break
            time.sleep(0.1)

        print("\nЗАПУСК МИССИИ...")
        control.send_RAW_RC([1500, 1500, 1500, 1500, 2000, 1000, 2000])
        mission_start = time.time()

        precise_landing = False
        mission_complete = False

        while not mission_complete:
            elapsed = time.time() - mission_start
            altitude = get_altitude(sim_client)

            if not precise_landing:
                # --- ИИ АНАЛИЗ ---
                frame = sim_client.get_camera_capture(1, CaptureType.color)
                if frame is not None:
                    prob, bbox = analyze_frame(frame, model)
                    bx, by, b_size = bbox
                    if prob > config.CONFIDENCE_THRESHOLD:
                        label, color = f"PLANTED {prob * 100:.0f}%", (0, 255, 0)
                    else:
                        label, color = f"EMPTY {(1 - prob) * 100:.0f}%", (0, 0, 255)
                        problem_points.append(elapsed)

                        # --- ДОБАВЛЕНО: Магия сохранения в PostgreSQL ---
                        if db_conn and (elapsed - last_db_save > 3.0):
                            last_db_save = elapsed
                            lat, lon = get_gps(control)
                            lat = lat if lat else 0.0
                            lon = lon if lon else 0.0

                            # Отправляем фото и данные в БД
                            save_empty_area(db_conn, lat, lon, prob, frame)

                    cv2.rectangle(frame, (bx, by), (bx + b_size, by + b_size), color, 3)
                    cv2.putText(frame, label, (bx, by - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
                    cv2.imshow("LIVE ANALYSIS", frame)
                    cv2.waitKey(1)

                curr_x, curr_y = get_physics_xy(sim_client)
                dist = math.hypot(start_x - curr_x, start_y - curr_y) if curr_x else 999

                if altitude and altitude < config.LANDING_ALT_THRESHOLD and elapsed > 20 and dist < config.BASE_DIST_THRESHOLD:
                    print("\nПЕРЕХВАТ: ПОСАДКА...")
                    precise_landing = True
                    control.send_RAW_RC([1500, 1500, 1500, 1500, 2000, 1000, 1500])
                    time.sleep(0.5)
            else:
                # --- ТОЧНАЯ ПОСАДКА ---
                curr_x, curr_y = get_physics_xy(sim_client)
                yaw = get_yaw(sim_client)
                if curr_x and curr_y:
                    dx, dy = start_x - curr_x, start_y - curr_y
                    err_x = math.cos(yaw) * dx + math.sin(yaw) * dy
                    err_y = -math.sin(yaw) * dx + math.cos(yaw) * dy

                    rc_p = int(1500 + err_x * config.PID_P_GAIN)
                    rc_r = int(1500 - err_y * config.PID_P_GAIN)
                    dist_to_center = math.hypot(dx, dy)

                    rc_t = 1250 if dist_to_center < 0.5 and altitude and altitude > 5.0 else 1320 if dist_to_center < 0.5 else 1500
                    control.send_RAW_RC(
                        [max(1350, min(1650, rc_r)), max(1350, min(1650, rc_p)), rc_t, 1500, 2000, 1000, 1500])

                if altitude and altitude <= 0.5:
                    print(f"\n  ПРИЗЕМЛИЛСЯ! Высота: {altitude:.2f}м")
                    mission_complete = True

            time.sleep(0.05)

        if finished:
            print("\n" + "=" * 60 + "\nВСЯ ЗМЕЙКА ЗАВЕРШЕНА!")
            break

        resume_lat, resume_lon = next_lat, next_lon
        segment_num += 1

    print(f"\nМИССИЯ ЗАВЕРШЕНА! Ошибок (пустых лунок): {len(problem_points)}")
    for _ in range(5):
        control.send_RAW_RC([1500, 1500, 900, 1500, 1000, 1000, 1000])
        time.sleep(0.5)

    cv2.destroyAllWindows()
    tcp_transmitter.disconnect()