// HuiYiapi-Android — 项目级构建脚本
// 使用 Kotlin DSL + Jetpack Compose

plugins {
    id("com.android.application") version "8.2.0" apply false
    id("org.jetbrains.kotlin.android") version "1.9.21" apply false
}

tasks.register("clean", Delete::class) {
    delete(rootProject.layout.buildDirectory)
}
