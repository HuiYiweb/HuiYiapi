package com.huiyi.api.model
data class Message(val id: String, val app: String, val sender: String, val content: String, val isGroup: Boolean = false, val groupName: String = "", val timestamp: Long = System.currentTimeMillis())
data class SpeechConfig(val asrModel: String = "cloud", val ttsModel: String = "cloud", val voice: String = "gentle_female", val speed: Float = 1f, val pitch: Float = 1f, val autoAnswer: Boolean = false, val answerDelay: Int = 3)
data class DeviceState(val online: Boolean = false, val batteryLevel: Int = -1, val currentApp: String = "")
