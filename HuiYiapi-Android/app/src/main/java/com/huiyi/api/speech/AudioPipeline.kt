package com.huiyi.api.speech
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.util.Log
import com.huiyi.api.core.network.WebSocketManager
import kotlinx.coroutines.*
import java.util.concurrent.ConcurrentLinkedQueue
import javax.inject.*

/**
 * 音频处理管线 — 参考变声器原理
 * - 捕获通话下行音频 → ASR识别 → 发送文本到桥接器
 * - 接收AI回复文本 → TTS合成 → 注入通话上行
 */
@Singleton
class AudioPipeline @Inject constructor(
    private val wsManager: WebSocketManager
) {
    companion object { private const val TAG = "HuiYi_Audio" }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var audioRecord: AudioRecord? = null
    private var audioTrack: AudioTrack? = null
    private var isRunning = false

    private val SAMPLE_RATE = 16000
    private val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
    private val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    private val BUFFER_SIZE = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)

    // ASR/TTS 接口（由具体引擎实现）
    var asrEngine: AsrEngine? = null
    var ttsEngine: TtsEngine? = null

    fun startCapture(callId: String) {
        if (isRunning) return
        isRunning = true

        scope.launch {
            try {
                audioRecord = AudioRecord(
                    MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                    SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT, BUFFER_SIZE
                )
                audioRecord?.startRecording()

                val buffer = ShortArray(BUFFER_SIZE)
                while (isRunning) {
                    val read = audioRecord?.read(buffer, 0, BUFFER_SIZE) ?: 0
                    if (read > 0 && asrEngine != null) {
                        val text = asrEngine?.recognize(buffer.copyOf(read))
                        if (!text.isNullOrBlank()) {
                            wsManager.sendVoiceText(text, callId)
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "音频捕获异常: ${e.message}")
            }
        }
    }

    fun playTts(audioData: ByteArray) {
        scope.launch {
            try {
                if (audioTrack == null) {
                    audioTrack = AudioTrack(
                        android.media.AudioAttributes.Builder()
                            .setUsage(android.media.AudioAttributes.USAGE_VOICE_COMMUNICATION)
                            .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SPEECH)
                            .build(),
                        AudioFormat.Builder()
                            .setSampleRate(SAMPLE_RATE)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .setEncoding(AUDIO_FORMAT)
                            .build(),
                        audioData.size,
                        AudioTrack.MODE_STATIC,
                        android.media.AudioManager.AUDIO_SESSION_ID_GENERATE
                    )
                    audioTrack?.play()
                }
                audioTrack?.write(audioData, 0, audioData.size)
            } catch (e: Exception) {
                Log.e(TAG, "TTS 播放异常: ${e.message}")
            }
        }
    }

    fun stop() {
        isRunning = false
        audioRecord?.stop(); audioRecord?.release(); audioRecord = null
        audioTrack?.stop(); audioTrack?.release(); audioTrack = null
    }
}

interface AsrEngine {
    fun recognize(audioData: ShortArray): String?
    fun configure(config: Map<String, Any>)
}

interface TtsEngine {
    fun synthesize(text: String): ByteArray?
    fun configure(config: Map<String, Any>)
}
