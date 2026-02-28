import math
from inavmspapi import MultirotorControl

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