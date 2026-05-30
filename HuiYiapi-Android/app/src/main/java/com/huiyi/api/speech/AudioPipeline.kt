package com.huiyi.api.speech
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.util.Log
import com.huiyi.api.core.network.WebSocketManager
import kotlinx.coroutines.*

object AudioPipeline {
    private const val TAG = "HuiYi_Audio"
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var audioRecord: AudioRecord? = null
    private var audioTrack: AudioTrack? = null
    private var isRunning = false
    private val SAMPLE_RATE = 16000
    private val BUFFER_SIZE = AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
    var asrEngine: AsrEngine? = null
    var ttsEngine: TtsEngine? = null

    fun startCapture(callId: String) {
        if (isRunning) return; isRunning = true
        scope.launch {
            try {
                audioRecord = AudioRecord(MediaRecorder.AudioSource.VOICE_COMMUNICATION, SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, BUFFER_SIZE)
                audioRecord?.startRecording()
                val buffer = ShortArray(BUFFER_SIZE)
                while (isRunning) {
                    val read = audioRecord?.read(buffer, 0, BUFFER_SIZE) ?: 0
                    if (read > 0) {
                        val text = asrEngine?.recognize(buffer.copyOf(read))
                        if (!text.isNullOrBlank()) WebSocketManager.sendVoiceText(text, callId)
                    }
                }
            } catch (e: Exception) { Log.e(TAG, "音频捕获异常: ${e.message}") }
        }
    }

    fun playTts(audioData: ByteArray) {
        scope.launch {
            try {
                if (audioTrack == null) {
                    audioTrack = AudioTrack(android.media.AudioAttributes.Builder().setUsage(android.media.AudioAttributes.USAGE_VOICE_COMMUNICATION).setContentType(android.media.AudioAttributes.CONTENT_TYPE_SPEECH).build(),
                        AudioFormat.Builder().setSampleRate(SAMPLE_RATE).setChannelMask(AudioFormat.CHANNEL_OUT_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build(), audioData.size, AudioTrack.MODE_STATIC, android.media.AudioManager.AUDIO_SESSION_ID_GENERATE)
                    audioTrack?.play()
                }
                audioTrack?.write(audioData, 0, audioData.size)
            } catch (e: Exception) { Log.e(TAG, "TTS 播放异常: ${e.message}") }
        }
    }

    fun stop() { isRunning = false; audioRecord?.stop(); audioRecord?.release(); audioRecord = null; audioTrack?.stop(); audioTrack?.release(); audioTrack = null }
}
interface AsrEngine { fun recognize(audioData: ShortArray): String?; fun configure(config: Map<String, Any>) }
interface TtsEngine { fun synthesize(text: String): ByteArray?; fun configure(config: Map<String, Any>) }
