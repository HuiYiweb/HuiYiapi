# HuiYiapi ProGuard Rules
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.huiyi.api.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
