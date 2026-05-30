package com.huiyi.api.ui.screens
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.huiyi.api.core.network.WebSocketManager
import com.huiyi.api.service.HuiYiAccessibilityService
import com.huiyi.api.service.NotificationListener
import com.huiyi.api.ui.components.IosCell
import com.huiyi.api.ui.components.IosToggle
import com.huiyi.api.ui.theme.*
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject lateinit var wsManager: WebSocketManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            HuiYiTheme { MainScreen() }
        }
    }

    @Composable
    fun MainScreen() {
        val wsState by wsManager.connectionState.collectAsState()
        val a11yRunning = HuiYiAccessibilityService.isRunning
        val notifRunning = NotificationListener.isRunning

        Scaffold(
            containerColor = DeepSpace,
            bottomBar = {
                NavigationBar(
                    containerColor = Color(0xDD1A1A2E),
                    tonalElevation = 0.dp,
                ) {
                    NavigationBarItem(selected = true, onClick = {}, icon = { Icon(Icons.Filled.Home, "首页") }, label = { Text("首页") })
                    NavigationBarItem(selected = false, onClick = {}, icon = { Icon(Icons.Filled.Call, "通话") }, label = { Text("通话") })
                    NavigationBarItem(selected = false, onClick = {}, icon = { Icon(Icons.Filled.List, "记录") }, label = { Text("记录") })
                    NavigationBarItem(selected = false, onClick = {}, icon = { Icon(Icons.Filled.Settings, "设置") }, label = { Text("设置") })
                }
            }
        ) { padding ->
            Column(
                modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // 头部 — 呼吸状态
                Box(
                    modifier = Modifier.fillMaxWidth().padding(top = 24.dp, bottom = 16.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("🌙", fontSize = 40.sp)
                        Spacer(Modifier.height(8.dp))
                        Text("HuiYi", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = Color(0xFFCBD5E1))
                        Spacer(Modifier.height(4.dp))
                        Text(
                            when (wsState) {
                                WebSocketManager.ConnectionState.REGISTERED -> "🟢 已连接 · 正在聆听..."
                                WebSocketManager.ConnectionState.CONNECTED -> "🟡 连接中..."
                                else -> "🔴 未连接"
                            },
                            color = Color(0xFF94A3B8),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }

                // 连接卡片
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0x1AFFFFFF)),
                    shape = RoundedCornerShape(20.dp),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text("连接状态", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                        Spacer(Modifier.height(12.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(Modifier.size(10.dp).background(
                                when (wsState) { WebSocketManager.ConnectionState.REGISTERED -> Success else -> TextSecondary },
                                RoundedCornerShape(5.dp)
                            ))
                            Spacer(Modifier.width(8.dp))
                            Text(wsState.name, color = TextPrimary)
                            Spacer(Modifier.weight(1f))
                            Button(
                                onClick = { if (wsState == WebSocketManager.ConnectionState.DISCONNECTED) wsManager.connect() else wsManager.disconnect() },
                                colors = ButtonDefaults.buttonColors(containerColor = Accent),
                                shape = RoundedCornerShape(10.dp),
                            ) {
                                Text(if (wsState == WebSocketManager.ConnectionState.DISCONNECTED) "连接" else "断开")
                            }
                        }
                    }
                }

                // 权限状态组
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0x1AFFFFFF)),
                    shape = RoundedCornerShape(20.dp),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text("权限检查", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                        Spacer(Modifier.height(8.dp))
                        IosCell(
                            title = "无障碍服务",
                            subtitle = if (a11yRunning) "✅ 已启用" else "⚠️ 未启用 — 点击设置",
                            leadingIcon = Icons.Filled.Accessibility,
                            onClick = if (!a11yRunning) {{ startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }} else null
                        )
                        Spacer(Modifier.height(8.dp))
                        IosCell(
                            title = "通知监听",
                            subtitle = if (notifRunning) "✅ 已启用" else "⚠️ 未启用 — 点击设置",
                            leadingIcon = Icons.Filled.Notifications,
                            onClick = if (!notifRunning) {{ startActivity(Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")) }} else null
                        )
                    }
                }

                // 快速操作
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0x1AFFFFFF)),
                    shape = RoundedCornerShape(20.dp),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text("快速操作", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                        Spacer(Modifier.height(8.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            QuickActionButton("截图", Icons.Filled.CameraAlt, Modifier.weight(1f))
                            QuickActionButton("主页", Icons.Filled.Home, Modifier.weight(1f))
                            QuickActionButton("返回", Icons.Filled.ArrowBack, Modifier.weight(1f))
                        }
                    }
                }

                // 底部版本信息
                Text(
                    "HuiYiapi v1.0.0 · 用心打造 · 为每一次对话",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                )
            }
        }
    }

    @Composable
    fun QuickActionButton(label: String, icon: androidx.compose.ui.graphics.vector.ImageVector, modifier: Modifier) {
        Button(
            onClick = {},
            modifier = modifier.height(60.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0x1A7C83FF)),
            shape = RoundedCornerShape(14.dp),
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(icon, contentDescription = null, tint = Accent, modifier = Modifier.size(20.dp))
                Text(label, fontSize = 11.sp, color = Accent)
            }
        }
    }
}
