package com.huiyi.api.core.network
import android.util.Log
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object WebSocketManager {
    private const val TAG = "HuiYi_WS"
    private val client = OkHttpClient.Builder().pingInterval(15, TimeUnit.SECONDS).readTimeout(0, TimeUnit.MILLISECONDS).build()
    private var webSocket: WebSocket? = null
    private var wsUrl = "ws://10.0.2.2:8765"
    private var deviceId = ""
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var heartbeatJob: Job? = null
    private var retryCount = 0

    private val _incomingMessages = MutableSharedFlow<JSONObject>(replay = 0)
    val incomingMessages: SharedFlow<JSONObject> = _incomingMessages

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState

    enum class ConnectionState { CONNECTED, CONNECTING, DISCONNECTED, REGISTERED }

    fun configure(url: String, deviceId: String) { this.wsUrl = url; this.deviceId = deviceId }

    fun connect() {
        if (_connectionState.value == ConnectionState.CONNECTING) return
        _connectionState.value = ConnectionState.CONNECTING
        val req = Request.Builder().url(wsUrl).build()
        webSocket = client.newWebSocket(req, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                _connectionState.value = ConnectionState.CONNECTED; retryCount = 0
                send(JSONObject().apply { put("type", "register"); put("device_id", deviceId); put("device_name", android.os.Build.MODEL) })
                startHeartbeat()
            }
            override fun onMessage(ws: WebSocket, text: String) {
                try { scope.launch { _incomingMessages.emit(JSONObject(text)) } } catch (_: Exception) {}
            }
            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                _connectionState.value = ConnectionState.DISCONNECTED; heartbeatJob?.cancel(); scheduleReconnect()
            }
            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                _connectionState.value = ConnectionState.DISCONNECTED; scheduleReconnect()
            }
        })
    }

    fun disconnect() { heartbeatJob?.cancel(); webSocket?.close(1000, "用户断开") }
    fun send(data: JSONObject): Boolean = try { webSocket?.send(data.toString()); true } catch (_: Exception) { false }

    fun sendMessage(app: String, sender: String, content: String, isGroup: Boolean = false, group: String = "") {
        send(JSONObject().apply { put("type","incoming"); put("app",app); put("sender",sender); put("content",content); put("is_group",isGroup); put("group",group) })
    }
    fun sendVoiceText(text: String, callId: String) {
        send(JSONObject().apply { put("type","voice_text"); put("text",text); put("call_id",callId) })
    }
    fun sendToolResult(id: String, success: Boolean, data: Any? = null) {
        send(JSONObject().apply { put("type","tool_result"); put("id",id); put("success",success); if(data!=null) put("result",data) })
    }

    private fun startHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = scope.launch { while (isActive) { delay(15000); send(JSONObject().apply { put("type","heartbeat") }) } }
    }
    private fun scheduleReconnect() {
        scope.launch { val d = minOf(1000L * (1L shl retryCount), 30000L); retryCount++; delay(d); connect() }
    }
}
