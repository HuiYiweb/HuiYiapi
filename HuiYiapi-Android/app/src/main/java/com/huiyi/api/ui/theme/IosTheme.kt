package com.huiyi.api.ui.theme
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// iOS 色彩系统 — 深空紫夜主题
val DeepSpace = Color(0xFF0D0D1A)
val CardBg = Color(0xFF1A1A2E)
val CardBgAlt = Color(0xFF16213E)
val Accent = Color(0xFF7C83FF)
val Highlight = Color(0xFFA78BFA)
val Success = Color(0xFF34D399)
val Heartbeat = Color(0xFFF472B6)
val TextPrimary = Color(0xFFCBD5E1)
val TextSecondary = Color(0xFF94A3B8)
val SurfaceGlass = Color(0xDD1A1A2E)

private val DarkColorScheme = darkColorScheme(
    primary = Accent,
    secondary = Highlight,
    tertiary = Heartbeat,
    background = DeepSpace,
    surface = CardBg,
    surfaceVariant = CardBgAlt,
    onPrimary = Color.White,
    onSecondary = Color.White,
    onBackground = TextPrimary,
    onSurface = TextPrimary,
    onSurfaceVariant = TextSecondary,
)

@Composable
fun HuiYiTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = IosTypography,
        shapes = IosShapes,
        content = content
    )
}
