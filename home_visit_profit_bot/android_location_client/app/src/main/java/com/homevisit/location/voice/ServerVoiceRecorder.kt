package com.homevisit.location.voice

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import java.io.File

/**
 * Короткая запись голоса для серверного ASR (Ф14.4) — фолбэк ТОЛЬКО для телефонов без
 * системного распознавателя (нет Google-сервисов). На телефонах с Google используется
 * `RecognizerIntent` без записи и без этого разрешения.
 *
 * Формат AAC/MPEG-4 (16 кГц) — работает с minSdk 26 (OGG/Opus только с API 29), а
 * faster-whisper на сервере декодирует его через ffmpeg. Запись идёт во ВРЕМЕННЫЙ файл
 * кеша и удаляется сразу после чтения байтов: на устройстве голос не задерживается,
 * на сервере не сохраняется вовсе (152-ФЗ).
 */
class ServerVoiceRecorder(private val context: Context) {
    private var recorder: MediaRecorder? = null
    private var file: File? = null

    val isRecording: Boolean get() = recorder != null

    fun start(): Boolean {
        if (recorder != null) return false
        val target = File.createTempFile("voice_", ".m4a", context.cacheDir)
        val rec = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) MediaRecorder(context) else @Suppress("DEPRECATION") MediaRecorder()
        return try {
            rec.setAudioSource(MediaRecorder.AudioSource.MIC)
            rec.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            rec.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            rec.setAudioSamplingRate(16_000)
            rec.setAudioEncodingBitRate(24_000)
            rec.setOutputFile(target.absolutePath)
            rec.prepare()
            rec.start()
            recorder = rec
            file = target
            true
        } catch (_: Exception) {
            runCatching { rec.release() }
            target.delete()
            false
        }
    }

    /** Остановить и вернуть байты записи (файл удаляется). null — запись не удалась. */
    fun stop(): ByteArray? {
        val rec = recorder ?: return null
        val target = file
        recorder = null
        file = null
        return try {
            rec.stop()
            rec.release()
            val bytes = target?.readBytes()
            target?.delete()
            if (bytes != null && bytes.isNotEmpty()) bytes else null
        } catch (_: Exception) {
            runCatching { rec.release() }
            target?.delete()
            null
        }
    }

    /** Отменить запись без результата (файл удаляется). */
    fun cancel() {
        val rec = recorder
        recorder = null
        val target = file
        file = null
        runCatching { rec?.stop() }
        runCatching { rec?.release() }
        target?.delete()
    }
}
