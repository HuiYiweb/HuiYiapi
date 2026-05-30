package com.huiyi.api.viewmodel
import androidx.lifecycle.ViewModel
import com.huiyi.api.core.network.WebSocketManager
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor(val wsManager: WebSocketManager) : ViewModel()
