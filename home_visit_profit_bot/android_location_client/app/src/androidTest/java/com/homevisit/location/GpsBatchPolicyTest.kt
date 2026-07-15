package com.homevisit.location

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Правило флаша очереди GPS (Фаза 3.7): не в движении — шлём немедленно (встал/визит,
 * алерт должен успеть); в движении — копим пачкой (экономия батареи). Проверяем чистую
 * логику LocationUploadService.shouldFlush без сети и датчиков.
 */
class GpsBatchPolicyTest {

    @Test
    fun emptyQueueNeverFlushes() {
        assertFalse(LocationUploadService.shouldFlush(false, 0, 999_999L))
        assertFalse(LocationUploadService.shouldFlush(true, 0, 999_999L))
    }

    @Test
    fun stoppedFlushesImmediately() {
        // Встал/визит: даже одна точка уходит сразу — по ней нужен живой ответ.
        assertTrue(LocationUploadService.shouldFlush(false, 1, 0L))
    }

    @Test
    fun movingAccumulatesUntilLimits() {
        // Едешь, очередь мала и время не вышло — копим.
        assertFalse(LocationUploadService.shouldFlush(true, 3, 10_000L))
        // Набралось 10 точек — флаш.
        assertTrue(LocationUploadService.shouldFlush(true, 10, 10_000L))
        // Прошло 5 минут — флаш даже при малой очереди.
        assertTrue(LocationUploadService.shouldFlush(true, 2, 5 * 60 * 1000L))
    }
}
