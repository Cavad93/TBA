package com.homevisit.location;

/**
 * Сколько человек прошёл пешком между машиной и адресами.
 *
 * Это ЛОГИСТИКА: дорога от машины до двери, по лестнице и обратно занимает время, и оно
 * влияет на плановую длительность визита и на то, сколько заказов реально помещается в
 * смену. Ровно как «время в пути» у любого курьерского сервиса.
 *
 * Чего здесь НЕТ и не будет: манеры ходьбы. Ни темпа, ни разброса времени шага, ни
 * ровности. У этих величин нет операционной цели, кроме вывода о физиологическом
 * состоянии человека, а данные, из которых состояние выводится дедукцией, сами
 * становятся специальной категорией персональных данных (152-ФЗ, ст. 10). Назвать
 * коэффициент вариации времени шага «логистикой» не выйдет: проверяющий спросит, зачем
 * логистике разброс шага, и ответить будет нечем.
 *
 * Поэтому и частота датчика остаётся экономной (5 Гц). Чтобы измерить интервалы между
 * шагами, понадобились бы 50 Гц — а чтобы просто понять «идёт, а не едет», хватает
 * дисперсии ускорения. Батарея от этого только выигрывает.
 */
final class WalkDetector {

    /** Дисперсия ускорения выше этой — человек движется сам, а не едет. */
    private static final double MOTION_VARIANCE = 0.35;

    /** Выше этой скорости человек в машине — пешком он так не ходит. */
    private static final double IN_CAR_SPEED_KMH = 12.0;

    /** Тишина дольше этого — прогулка закончилась. */
    private static final double IDLE_SECONDS = 8.0;

    /** Проходы короче отбрасываем: это шаг от двери до багажника, а не дорога. */
    private static final double MIN_BOUT_SECONDS = 20.0;

    private double motionMean = 0;
    private double motionVar = 0;

    private double boutStartS = 0;
    private double lastMotionS = 0;
    private double lastSampleS = 0;

    private int bouts = 0;
    private double totalSeconds = 0;

    /**
     * Один отсчёт акселерометра.
     *
     * @param linear   |вектор ускорения| − g, м/с² (не зависит от того, как телефон
     *                 лежит в кармане)
     * @param seconds  момент отсчёта, секунды
     * @param speedKmh скорость по GPS: в машине ходьбу не ищем
     */
    void onSample(double linear, double seconds, double speedKmh) {
        if (lastSampleS > 0 && seconds <= lastSampleS) {
            return;
        }
        lastSampleS = seconds;

        if (speedKmh >= IN_CAR_SPEED_KMH) {
            closeBout(seconds);
            return;
        }

        double alpha = 0.05;
        double delta = linear - motionMean;
        motionMean += alpha * delta;
        motionVar = (1 - alpha) * (motionVar + alpha * delta * delta);

        if (motionVar >= MOTION_VARIANCE) {
            if (boutStartS <= 0) {
                boutStartS = seconds;
            }
            lastMotionS = seconds;
            return;
        }

        if (boutStartS > 0 && seconds - lastMotionS > IDLE_SECONDS) {
            closeBout(seconds);
        }
    }

    int bouts() {
        return bouts;
    }

    double walkSeconds() {
        return Math.round(totalSeconds * 10.0) / 10.0;
    }

    boolean isEmpty() {
        return bouts <= 0;
    }

    /** Закрыт очередной адрес — начинаем копить дорогу заново. */
    void resetSegment() {
        bouts = 0;
        totalSeconds = 0;
        boutStartS = 0;
        lastMotionS = 0;
    }

    private void closeBout(double seconds) {
        if (boutStartS > 0 && lastMotionS > boutStartS) {
            double duration = lastMotionS - boutStartS;
            if (duration >= MIN_BOUT_SECONDS) {
                bouts += 1;
                totalSeconds += duration;
            }
        }
        boutStartS = 0;
        lastMotionS = 0;
    }
}
