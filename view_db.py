import psycopg2
import cv2
import numpy as np

# Импортируем настройки из вашего конфига
import config


def view_saved_data():
    print(f"Подключение к базе '{config.DB_NAME}'...")
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASS
        )
        cursor = conn.cursor()

        # Запрашиваем все записи, сортируя по времени (сначала новые)
        cursor.execute("SELECT id, timestamp, lat, lon, confidence, image FROM empty_areas ORDER BY timestamp DESC")
        records = cursor.fetchall()

        if not records:
            print("База данных пока пуста. Запустите автопилот, чтобы дрон нашел пустые участки!")
            return

        print(f"✅ Найдено проблемных участков: {len(records)}\n")
        print("В окне просмотра: нажимайте любую клавишу для перехода к следующему фото.")
        print("Для выхода нажмите ESC.")

        for row in records:
            rec_id, ts, lat, lon, conf, img_bytes = row

            # Выводим инфу в консоль
            print(f"Запись #{rec_id} | Время: {ts} | Координаты: {lat}, {lon} | Уверенность: {conf * 100:.1f}%")

            # Декодируем байты обратно в картинку OpenCV
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is not None:
                # Добавляем подпись прямо на фотографию
                text = f"ID: {rec_id} | EMPTY: {conf * 100:.1f}%"
                cv2.putText(img, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                # Показываем окно
                cv2.imshow("PostgreSQL DB Viewer", img)

                # Ждем нажатия клавиши (27 = ESC)
                key = cv2.waitKey(0)
                if key == 27:
                    break

        cv2.destroyAllWindows()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Ошибка при чтении из БД: {e}")


if __name__ == "__main__":
    view_saved_data()