package com.huiyi.api.ui.components
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.huiyi.api.ui.theme.TextSecondary

@Composable
fun IosCell(
    title: String,
    subtitle: String? = null,
    leadingIcon: ImageVector? = null,
    leadingText: String? = null,
    trailingText: String? = null,
    trailingIcon: Boolean = true,
    onClick: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    Surface(
        color = Color(0x1AFFFFFF),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
        modifier = modifier.then(
            if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier
        )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (leadingIcon != null) {
                Icon(leadingIcon, contentDescription = null, tint = Color(0xFF7C83FF), modifier = Modifier.size(24.dp))
                Spacer(Modifier.width(12.dp))
            }
            if (leadingText != null) {
                Text(leadingText, color = Color(0xFF7C83FF), style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.width(12.dp))
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.bodyLarge, color = Color(0xFFCBD5E1))
                if (subtitle != null) {
                    Text(subtitle, style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                }
            }
            if (trailingText != null) {
                Text(trailingText, color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                Spacer(Modifier.width(4.dp))
            }
            if (trailingIcon) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = Color(0xFF475569), modifier = Modifier.size(20.dp))
            }
        }
    }
}
