<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { DataAnalysis, Files, Monitor, Operation, Promotion } from '@element-plus/icons-vue'
import { api } from './api'

const route = useRoute()
const online = ref(false)
const collapsed = ref(false)
const pageTitle = computed(() => String(route.meta.title || 'Referral Flow Agent'))

onMounted(async () => {
  try { await api.health(); online.value = true } catch { online.value = false }
})
</script>

<template>
  <el-container class="app-shell">
    <el-aside :width="collapsed ? '72px' : '232px'" class="sidebar">
      <div class="brand">
        <div class="brand-mark"><el-icon><Promotion /></el-icon></div>
        <div v-if="!collapsed" class="brand-copy"><strong>Referral Flow</strong><span>Agent Console</span></div>
      </div>
      <el-menu :default-active="route.path" router class="nav-menu" :collapse="collapsed">
        <el-menu-item index="/"><el-icon><Monitor /></el-icon><template #title>系统概览</template></el-menu-item>
        <el-menu-item index="/run"><el-icon><Operation /></el-icon><template #title>Agent 运行</template></el-menu-item>
        <el-menu-item index="/evidence"><el-icon><DataAnalysis /></el-icon><template #title>实验证据</template></el-menu-item>
        <el-menu-item index="/audit"><el-icon><Files /></el-icon><template #title>审计日志</template></el-menu-item>
      </el-menu>
      <button class="collapse-button" type="button" @click="collapsed = !collapsed" :aria-label="collapsed ? '展开导航' : '收起导航'">
        {{ collapsed ? '»' : '« 收起导航' }}
      </button>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div><span class="eyebrow">PE6201 · Problem B</span><h1>{{ pageTitle }}</h1></div>
        <el-tag :type="online ? 'success' : 'danger'" effect="light" round>
          <span class="status-dot" />{{ online ? '后端已连接' : '后端未连接' }}
        </el-tag>
      </el-header>
      <el-main class="main-content"><router-view /></el-main>
    </el-container>
  </el-container>
</template>
