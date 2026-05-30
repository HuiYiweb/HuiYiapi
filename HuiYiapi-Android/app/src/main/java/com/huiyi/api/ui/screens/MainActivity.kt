package com.huiyi.api.ui.screens
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.huiyi.api.core.network.WebSocketManager
import com.huiyi.api.service.HuiYiAccessibilityService
import com.huiyi.api.service.NotificationListener
import com.huiyi.api.ui.components.IosCell
import com.huiyi.api.ui.theme.*

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { HuiYiTheme { MainScreen() } }
    }

    @Composable
    fun MainScreen() {
        val wsState by WebSocketManager.connectionState.collectAsState()
        val a11yRunning = HuiYiAccessibilityService.isRunning
        val notifRunning = NotificationListener.isRunning

        Scaffold(
            containerColor = DeepSpace,
            bottomBar = {
                NavigationBar(containerColor = Color(0xDD1A1A2E), tonalElevation = 0.dp) {
                    NavigationBarItem(selected = true, onClick = {}, icon = { Icon(Icons.Filled.Home, "首页") }, label = { Text("首页") })
                    NavigationBarItem(selected = false, onClick = {}, icon = { Icon(Icons.Filled.Call, "通话") }, label = { Text("通话") })
                    NavigationBarItem(selected = false, onClick = {}, icon = { Icon(Icons.Filled.Settings, "设置") }, label = { Text("设置") })
                }
            }
        ) { padding ->
            Column(
                Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // 头部状态
                Column(Modifier.fillMaxWidth().padding(top = 24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("🌙", fontSize = 40.sp)
                    Text("HuiYi", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = TextPrimary)
                    Text(
                        when (wsState) {
                            WebSocketManager.ConnectionState.REGISTERED -> "🟢 已连接"
                            WebSocketManager.ConnectionState.CONNECTED -> "🟡 连接中..."
                            else -> "🔴 未连接"
                        },
                        color = TextSecondary, style = MaterialTheme.typography.bodyMedium
                    )
                }
                // 权限卡片
                Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color(0x1AFFFFFF)), shape = RoundedCornerShape(20.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Text("权限检查", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                        Spacer(Modifier.height(8.dp))
                        IosCell("无障碍服务", if (a11yRunning) "✅ 已启用" else "⚠️ 未启用",
                            leadingIcon = Icons.Filled.Accessibility,
                            onClick = if (!a11yRunning) {{ startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }} else null)
                        IosCell("通知监听", if (notifRunning) "✅ 已启用" else "⚠️ 未启用",
                            leadingIcon = Icons.Filled.Notifications,
                            onClick = if (!notifRunning) {{ startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")) }} else null)
                    }
                }
                // 连接按钮
                Button(
                    onClick = { if (wsState == WebSocketManager.ConnectionState.DISCONNECTED) WebSocketManager.connect() else WebSocketManager.disconnect() },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Accent),
                    shape = RoundedCornerShape(12.dp)
                ) { Text(if (wsState == WebSocketManager.ConnectionState.DISCONNECTED) "连接桥接器" else "断开连接", color = Color.White) }

                Text("HuiYiapi v1.0.0 · 用心打造 · 为每一次对话", style = MaterialTheme.typography.bodySmall, color = TextSecondary, modifier = Modifier.fillMaxWidth().padding(top = 16.dp))
            }
        }
    }
}
