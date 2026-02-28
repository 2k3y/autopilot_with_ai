import config
import struct
import time
from inavmspapi import MultirotorControl

def build_snake_waypoints(home_lat, home_lon, alt_cm, speed, resume_lat=None, resume_lon=None, recharge_every=7):
    # Теперь берем константы из конфига
    START_LON = config.SNAKE_START_LON
    RIGHT_LON = config.SNAKE_RIGHT_LON
    END_LAT = config.SNAKE_END_LAT
    LAT_STEP = config.SNAKE_LAT_STEP

    if resume_lat is None: resume_lat = config.SNAKE_START_LAT
    if resume_lon is None: resume_lon = config.SNAKE_START_LON

    wps = []
    wp_num = 1
    left_hits = 0
    lat = resume_lat
    on_left = resume_lon == START_LON

    wps.append([wp_num, 1, home_lat, home_lon, alt_cm, speed, 0, 0, 0])
    wp_num += 1
    wps.append([wp_num, 1, resume_lat, resume_lon, alt_cm, speed, 0, 0, 0])
    wp_num += 1

    while lat <= END_LAT:
        if on_left:
            wps.append([wp_num, 1, lat, RIGHT_LON, alt_cm, speed, 0, 0, 0])
            wp_num += 1
            lat += LAT_STEP
            wps.append([wp_num, 1, lat, RIGHT_LON, alt_cm, speed, 0, 0, 0])
            wp_num += 1

            if lat > END_LAT:
                wps.append([wp_num, 1, config.SNAKE_END_LAT, config.SNAKE_END_LON, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, 0, 0, 0, 0, 165])
                return wps, lat, RIGHT_LON, True

            wps.append([wp_num, 1, lat, START_LON, alt_cm, speed, 0, 0, 0])
            wp_num += 1
            left_hits += 1

            if left_hits >= recharge_every:
                wps.append([wp_num, 1, home_lat, home_lon, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, 0, 0, 0, 0, 165])
                return wps, lat + LAT_STEP, START_LON, False

            lat += LAT_STEP
            wps.append([wp_num, 1, lat, START_LON, alt_cm, speed, 0, 0, 0])
            wp_num += 1
            left_hits += 1

            if lat > END_LAT:
                wps.append([wp_num, 1, config.SNAKE_END_LAT, config.SNAKE_END_LON, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, 0, 0, 0, 0, 165])
                return wps, lat, START_LON, True

            if left_hits >= recharge_every:
                wps.append([wp_num, 1, home_lat, home_lon, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, 0, 0, 0, 0, 165])
                return wps, lat, START_LON, False

        else:
            lat += LAT_STEP
            wps.append([wp_num, 1, lat, RIGHT_LON, alt_cm, speed, 0, 0, 0])
            wp_num += 1

            if lat > END_LAT:
                wps.append([wp_num, 1, config.SNAKE_END_LAT, config.SNAKE_END_LON, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, 0, 0, 0, 0, 165])
                return wps, lat, RIGHT_LON, True

            wps.append([wp_num, 1, lat, START_LON, alt_cm, speed, 0, 0, 0])
            wp_num += 1
            left_hits += 1
            on_left = True

            if left_hits >= recharge_every:
                wps.append([wp_num, 1, home_lat, home_lon, alt_cm, speed, 0, 0, 0])
                wp_num += 1
                wps.append([wp_num, 1, home_lat, home_lon, 0, 0, 0, 0, 165])
                return wps, lat + LAT_STEP, START_LON, False

    wps.append([wp_num, 1, config.SNAKE_END_LAT, config.SNAKE_END_LON, alt_cm, speed, 0, 0, 0])
    wp_num += 1
    wps.append([wp_num, 1, home_lat, home_lon, alt_cm, speed, 0, 0, 0])
    wp_num += 1
    wps.append([wp_num, 1, home_lat, home_lon, 0, 0, 0, 0, 165])
    return wps, lat, START_LON, True

def send_waypoints_in_batches(control, waypoints):
    print(f"\nЗАГРУЗКА МАРШРУТА ({len(waypoints)} точек):")
    for wp in waypoints:
        binary_data = struct.pack("<BBIIIHHHB", *wp)
        control.send_RAW_msg(MultirotorControl.MSPCodes["MSP_SET_WP"], binary_data)
        time.sleep(0.5)
        print(f"  WP{wp[0]:2d} | lat={wp[2]} lon={wp[3]} | alt={wp[4]/100:.0f}м | флаг={wp[8]}")