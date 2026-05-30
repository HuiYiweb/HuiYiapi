package com.huiyi.api.device
import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import javax.inject.*

@Singleton
class DeviceController @Inject constructor() {
    private var service: AccessibilityService? = null
    fun setService(s: AccessibilityService?) { service = s }
    fun isAvailable() = service != null

    fun tap(x: Int, y: Int) = performGesture(GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(Path().apply { moveTo(x.toFloat(), y.toFloat()) }, 0, 1)).build())
    fun doubleTap(x: Int, y: Int) = tap(x, y) && tap(x, y)
    fun longPress(x: Int, y: Int, dur: Long = 800) = performGesture(GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(Path().apply { moveTo(x.toFloat(), y.toFloat()) }, 0, dur)).build())
    fun swipe(x1: Int, y1: Int, x2: Int, y2: Int, dur: Long = 300) = performGesture(GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(Path().apply { moveTo(x1.toFloat(),y1.toFloat()); lineTo(x2.toFloat(),y2.toFloat()) }, 0, dur)).build())

    fun typeText(text: String): Boolean {
        val s = service ?: return false
        val root = s.rootInActiveWindow ?: return false
        val f = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) ?: return false
        val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text) }
        return f.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    fun getUiTree(): String? {
        val s = service ?: return null
        val root = s.rootInActiveWindow ?: return null
        val sb = StringBuilder()
        nodeToJson(root, sb)
        root.recycle()
        return sb.toString()
    }

    fun findAndClick(text: String? = null, resourceId: String? = null, contentDesc: String? = null, index: Int = 0): Boolean {
        val nodes = findElements(text, resourceId, contentDesc)
        if (index < nodes.size) { val r = nodes[index].performAction(AccessibilityNodeInfo.ACTION_CLICK); nodes.forEach { it.recycle() }; return r }
        return false
    }

    fun findAndSetText(text: String, hintText: String? = null): Boolean {
        val nodes = findElements(hintText, null, null)
        for (n in nodes) {
            if (n.isEditable) {
                val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text) }
                val r = n.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args); nodes.forEach { it.recycle() }; return r
            }
        }
        nodes.forEach { it.recycle() }; return false
    }

    fun scrollToFind(text: String, max: Int = 10): Boolean {
        for (i in 0 until max) {
            if (findElements(text).isNotEmpty()) return true
            swipe(540, 1800, 540, 600, 200); Thread.sleep(500)
        }; return false
    }

    fun pressKey(key: String): Boolean {
        val s = service ?: return false
        return s.performGlobalAction(when(key.lowercase()) {
            "home" -> AccessibilityService.GLOBAL_ACTION_HOME
            "back" -> AccessibilityService.GLOBAL_ACTION_BACK
            "recent" -> AccessibilityService.GLOBAL_ACTION_RECENTS
            else -> return false
        })
    }

    private fun findElements(text: String? = null, resourceId: String? = null, contentDesc: String? = null): MutableList<AccessibilityNodeInfo> {
        val s = service ?: return mutableListOf()
        val root = s.rootInActiveWindow ?: return mutableListOf()
        val r = mutableListOf<AccessibilityNodeInfo>()
        findRecursive(root, text, resourceId, contentDesc, r); root.recycle(); return r
    }

    private fun findRecursive(node: AccessibilityNodeInfo, text: String?, rid: String?, cd: String?, results: MutableList<AccessibilityNodeInfo>) {
        var match = true
        if (text != null && node.text?.contains(text, true) != true) match = false
        if (rid != null && node.viewIdResourceName?.contains(rid, true) != true) match = false
        if (cd != null && node.contentDescription?.contains(cd, true) != true) match = false
        if (match && (text != null || rid != null || cd != null)) results.add(AccessibilityNodeInfo.obtain(node))
        for (i in 0 until node.childCount) { val c = node.getChild(i) ?: continue; findRecursive(c, text, rid, cd, results); c.recycle() }
    }

    private fun performGesture(g: GestureDescription): Boolean {
        val s = service ?: return false
        return s.dispatchGesture(g, null, null)
    }

    private fun nodeToJson(node: AccessibilityNodeInfo, sb: StringBuilder) {
        val bounds = Rect(); node.getBoundsInScreen(bounds)
        sb.append("""{"class":"${node.className}","text":"${node.text}","rid":"${node.viewIdResourceName}","bounds":[${bounds.left},${bounds.top},${bounds.right},${bounds.bottom}],""")
        sb.append(""""click":${node.isClickable},"editable":${node.isEditable},"children":[""")
        for (i in 0 until node.childCount) { if (i > 0) sb.append(","); val c = node.getChild(i); if (c != null) { nodeToJson(c, sb); c.recycle() } }
        sb.append("]}")
    }
}
