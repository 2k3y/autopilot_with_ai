import cv2
import tensorflow as tf
import config

def analyze_frame(frame, model):
    """
    Обрезает кадр по центру, меняет размер под нейросеть
    и возвращает вероятность наличия объекта.
    """
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