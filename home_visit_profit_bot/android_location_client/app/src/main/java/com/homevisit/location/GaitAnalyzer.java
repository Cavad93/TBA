package com.homevisit.location;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Оценка манеры ходьбы по акселерометру.
 *
 * Зачем: походка — самый прямой доступный нам физиологический признак усталости.
 * Уставший человек идёт медленнее, а главное — НЕРОВНЕЕ: разброс времени между шагами
 * растёт. Это устойчивый маркер, в отличие от, например, вариативности скорости
 * вождения, где даже знак связи спорен.
 *
 * Почему не по GPS: точка раз в минуту. Путь от машины до подъезда — это одна-две
 * точки с погрешностью в десятки метров. По ним видно в лучшем случае «шёл / не шёл»,
 * и уж точно не КАК шёл.
 *
 * Почему нужны 50 Гц: шаг человека — это 1,7–2 Гц. На обычной частоте датчика (5 Гц)
 * на шаг приходится 2,5 отсчёта: этого хватает, чтобы понять «идёт», и категорически
 * не хватает, чтобы измерить интервалы между шагами — а именно их разброс нам и нужен.
 * Поэтому частота поднимается только на время ходьбы (см. wantsHighRate).
 *
 * Что НИКОГДА не покидает телефон: сам сигнал. По паттерну походки человека можно
 * опознать — это биометрия. Наружу уходят только агрегаты за отрезок пути.
 *
 * Класс намеренно без зависимостей от Android — чистая арифметика, её можно проверить.
 */
final class GaitAnalyzer {

    /** Шаг человека — 1,2–2,6 Гц. Отсюда границы интервала между шагами. */
    private static final double STEP_MIN_INTERVAL_S = 0.30;   // до 200 шагов/мин
    private static final double STEP_MAX_INTERVAL_S = 1.10;   // от 55 шагов/мин

    /** Пауза дольше этого — человек остановился, отрезок ходьбы закончен. */
    private static final double BOUT_GAP_S = 3.0;

    /** Короткие проходы отбрасываем: на них походку не измерить, только шум поймать. */
    private static final double MIN_BOUT_SECONDS = 30.0;
    private static final int MIN_BOUT_STEPS = 20;

    /** Выше этой скорости человек в машине — ходьбу не ищем. */
    private static final double IN_CAR_SPEED_KMH = 12.0;

    /** Нет шагов столько секунд — возвращаем датчик на экономную частоту. */
    private static final double HIGH_RATE_IDLE_S = 10.0;

    /** Порог «что-то движется» на низкой частоте: повод присмотреться на высокой. */
    private static final double MOTION_VARIANCE = 0.35;

    /** Буфер сигнала для расчёта ровности шага. 60 с при 50 Гц. */
    private static final int MAX_BUFFER = 3000;

    /** Одна прогулка: от машины до подъезда, по лестнице, обратно. */
    static final class Bout {
        final double cadence;      // шагов в минуту
        final double stepCv;       // разброс времени шага, %
        final double regularity;   // ровность шага, 0..1
        final double impact;       // жёсткость приземления, м/с²
        final double seconds;

        Bout(double cadence, double stepCv, double regularity, double impact, double seconds) {
            this.cadence = cadence;
            this.stepCv = stepCv;
            this.regularity = regularity;
            this.impact = impact;
            this.seconds = seconds;
        }
    }

    /** Итог по отрезку пути между адресами: медианы по прогулкам, а не среднее. */
    static final class Summary {
        final int bouts;
        final double walkSeconds;
        final double cadence;
        final double stepCv;
        final double regularity;
        final double impact;

        Summary(int bouts, double walkSeconds, double cadence, double stepCv, double regularity, double impact) {
            this.bouts = bouts;
            this.walkSeconds = walkSeconds;
            this.cadence = cadence;
            this.stepCv = stepCv;
            this.regularity = regularity;
            this.impact = impact;
        }

        boolean isEmpty() {
            return bouts <= 0;
        }
    }

    private final List<Bout> segmentBouts = new ArrayList<>();

    // Текущая прогулка.
    private final List<Double> stepIntervals = new ArrayList<>();
    private final List<Double> stepPeaks = new ArrayList<>();
    private final float[] buffer = new float[MAX_BUFFER];
    private int bufferSize = 0;
    private double boutStartS = 0;
    private double lastStepS = 0;

    // Детектор шага.
    private double smoothed = 0;
    private double previousSmoothed = 0;
    private boolean rising = false;
    private double peakCandidate = 0;
    private double peakAverage = 1.0;

    // Оценка движения на низкой частоте.
    private double motionMean = 0;
    private double motionVar = 0;

    private boolean highRate = false;
    private double lastActivityS = 0;
    private double lastSampleS = 0;

    /**
     * Один отсчёт акселерометра.
     *
     * @param linear    |вектор ускорения| − g, м/с² (не зависит от ориентации телефона —
     *                  а он лежит в кармане как попало)
     * @param seconds   момент отсчёта, секунды
     * @param speedKmh  скорость по GPS: если человек в машине, ходьбу не ищем
     */
    void onSample(double linear, double seconds, double speedKmh) {
        if (lastSampleS > 0 && seconds <= lastSampleS) {
            return;
        }
        lastSampleS = seconds;

        if (speedKmh >= IN_CAR_SPEED_KMH) {
            closeBout(seconds);
            highRate = false;
            return;
        }

        updateMotion(linear);

        if (!highRate) {
            // На экономной частоте шаги не разглядеть — можно только заподозрить
            // движение и попросить поднять частоту.
            if (motionVar >= MOTION_VARIANCE) {
                highRate = true;
                lastActivityS = seconds;
                resetStepDetector();
            }
            return;
        }

        if (detectStep(linear, seconds)) {
            lastActivityS = seconds;
        }

        // Прогулка закончилась — закрываем и решаем, годится ли она.
        if (lastStepS > 0 && seconds - lastStepS > BOUT_GAP_S) {
            closeBout(seconds);
        }
        if (seconds - lastActivityS > HIGH_RATE_IDLE_S) {
            closeBout(seconds);
            highRate = false;
        }

        if (bufferSize < MAX_BUFFER) {
            buffer[bufferSize++] = (float) smoothed;
        }
    }

    /** Сервису: нужна ли сейчас частая выборка (50 Гц) вместо экономной. */
    boolean wantsHighRate() {
        return highRate;
    }

    /** Итог по отрезку пути. Пустой, если человек за него никуда не ходил. */
    Summary snapshot() {
        if (segmentBouts.isEmpty()) {
            return new Summary(0, 0, 0, 0, 0, 0);
        }
        List<Double> cadences = new ArrayList<>();
        List<Double> cvs = new ArrayList<>();
        List<Double> regs = new ArrayList<>();
        List<Double> impacts = new ArrayList<>();
        double seconds = 0;
        for (Bout bout : segmentBouts) {
            cadences.add(bout.cadence);
            cvs.add(bout.stepCv);
            regs.add(bout.regularity);
            impacts.add(bout.impact);
            seconds += bout.seconds;
        }
        // Медиана, а не среднее: одна прогулка по обледенелой лестнице не должна
        // объявлять человека уставшим.
        return new Summary(
                segmentBouts.size(),
                round1(seconds),
                round1(median(cadences)),
                round1(median(cvs)),
                round2(median(regs)),
                round2(median(impacts))
        );
    }

    /** Закрыт очередной адрес — начинаем копить походку заново. */
    void resetSegment() {
        segmentBouts.clear();
    }

    // --- внутреннее ------------------------------------------------------

    private void updateMotion(double linear) {
        double alpha = 0.05;
        double delta = linear - motionMean;
        motionMean += alpha * delta;
        motionVar = (1 - alpha) * (motionVar + alpha * delta * delta);
    }

    /**
     * Детектор шага: сглаживаем сигнал и ищем локальные максимумы выше адаптивного
     * порога, не чаще одного за 0,3 с. Порог адаптивный, потому что человек в куртке
     * с телефоном в глубоком кармане даёт вдвое более слабый сигнал, чем в джинсах.
     */
    private boolean detectStep(double linear, double seconds) {
        previousSmoothed = smoothed;
        smoothed += 0.3 * (Math.abs(linear) - smoothed);

        double threshold = Math.max(0.25, 0.45 * peakAverage);

        if (smoothed > previousSmoothed) {
            rising = true;
            peakCandidate = Math.max(peakCandidate, smoothed);
            return false;
        }
        if (!rising) {
            return false;
        }
        rising = false;

        double peak = peakCandidate;
        peakCandidate = 0;
        if (peak < threshold) {
            return false;
        }

        if (lastStepS > 0) {
            double interval = seconds - lastStepS;
            if (interval < STEP_MIN_INTERVAL_S) {
                return false;  // отражённый пик того же шага
            }
            if (interval <= STEP_MAX_INTERVAL_S) {
                stepIntervals.add(interval);
            } else {
                // Слишком большой разрыв — это уже новая прогулка.
                closeBout(seconds);
            }
        }
        if (boutStartS <= 0) {
            boutStartS = seconds;
        }
        lastStepS = seconds;
        stepPeaks.add(peak);
        peakAverage += 0.2 * (peak - peakAverage);
        return true;
    }

    private void closeBout(double seconds) {
        if (boutStartS > 0 && lastStepS > 0) {
            double duration = lastStepS - boutStartS;
            int steps = stepPeaks.size();
            if (duration >= MIN_BOUT_SECONDS && steps >= MIN_BOUT_STEPS && stepIntervals.size() >= 2) {
                segmentBouts.add(buildBout(duration, steps));
            }
        }
        stepIntervals.clear();
        stepPeaks.clear();
        bufferSize = 0;
        boutStartS = 0;
        lastStepS = 0;
        resetStepDetector();
    }

    private Bout buildBout(double duration, int steps) {
        double meanInterval = mean(stepIntervals);
        double cadence = meanInterval > 0 ? 60.0 / meanInterval : 0;

        // Главный маркер: разброс времени шага. У отдохнувшего человека шаг ровный,
        // у вымотанного — «плавает».
        double sd = stdev(stepIntervals, meanInterval);
        double cv = meanInterval > 0 ? sd / meanInterval * 100.0 : 0;

        // Ровность: насколько один шаг похож на следующий по форме сигнала.
        int lag = (int) Math.round(meanInterval * estimatedHz(duration, steps));
        double regularity = autocorrelation(lag);

        double impact = mean(stepPeaks);

        return new Bout(cadence, cv, regularity, impact, duration);
    }

    /** Частота выборки выводится из данных: у разных телефонов «50 Гц» разные. */
    private double estimatedHz(double duration, int steps) {
        if (duration <= 0 || bufferSize <= 0) {
            return 50.0;
        }
        double hz = bufferSize / duration;
        return hz > 5 && hz < 200 ? hz : 50.0;
    }

    /**
     * Нормированная автокорреляция на лаге в один шаг: 1 — шаги как под метроном,
     * ближе к 0 — каждый шаг сам по себе.
     */
    private double autocorrelation(int lag) {
        if (lag <= 0 || bufferSize <= lag + 10) {
            return 0;
        }
        double mean = 0;
        for (int i = 0; i < bufferSize; i++) {
            mean += buffer[i];
        }
        mean /= bufferSize;

        double numerator = 0;
        double denominator = 0;
        for (int i = 0; i < bufferSize - lag; i++) {
            numerator += (buffer[i] - mean) * (buffer[i + lag] - mean);
        }
        for (int i = 0; i < bufferSize; i++) {
            denominator += (buffer[i] - mean) * (buffer[i] - mean);
        }
        if (denominator <= 0) {
            return 0;
        }
        double value = numerator / denominator * ((double) bufferSize / (bufferSize - lag));
        return Math.max(0.0, Math.min(1.0, value));
    }

    private void resetStepDetector() {
        smoothed = 0;
        previousSmoothed = 0;
        rising = false;
        peakCandidate = 0;
        peakAverage = 1.0;
    }

    private static double mean(List<Double> values) {
        if (values.isEmpty()) {
            return 0;
        }
        double sum = 0;
        for (double value : values) {
            sum += value;
        }
        return sum / values.size();
    }

    private static double stdev(List<Double> values, double mean) {
        if (values.size() < 2) {
            return 0;
        }
        double sum = 0;
        for (double value : values) {
            sum += (value - mean) * (value - mean);
        }
        return Math.sqrt(sum / (values.size() - 1));
    }

    private static double median(List<Double> values) {
        if (values.isEmpty()) {
            return 0;
        }
        List<Double> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        int middle = sorted.size() / 2;
        if (sorted.size() % 2 == 1) {
            return sorted.get(middle);
        }
        return (sorted.get(middle - 1) + sorted.get(middle)) / 2;
    }

    private static double round1(double value) {
        return Math.round(value * 10.0) / 10.0;
    }

    private static double round2(double value) {
        return Math.round(value * 100.0) / 100.0;
    }
}
