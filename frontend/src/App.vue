<template>
  <div id="app-container">
    <!-- 顶部导航栏 -->
    <el-header class="app-header">
      <div class="header-left">
        <el-icon :size="28" color="#00ff88"><Monitor /></el-icon>
        <span class="app-title">AI 漏洞挖掘平台</span>
      </div>
      <div class="header-right">
        <el-tag :type="apiConnected ? 'success' : 'danger'" size="small">
          {{ apiConnected ? 'API 已连接' : 'API 不可达' }}
        </el-tag>
      </div>
    </el-header>

    <el-container class="app-body">
      <!-- 侧边导航 -->
      <el-aside width="220px" class="app-sidebar">
        <el-menu
          :default-active="activeMenu"
          router
          background-color="#1a1d23"
          text-color="#888"
          active-text-color="#00ff88"
        >
          <el-menu-item index="/">
            <el-icon><Upload /></el-icon>
            <span>域名上传</span>
          </el-menu-item>
          <el-menu-item index="/tasks">
            <el-icon><List /></el-icon>
            <span>任务管理</span>
          </el-menu-item>
          <el-menu-item index="/rules">
            <el-icon><Filter /></el-icon>
            <span>筛选规则</span>
          </el-menu-item>
          <el-menu-item index="/agent">
            <el-icon><ChatDotRound /></el-icon>
            <span>Agent 指令</span>
          </el-menu-item>
          <el-menu-item index="/reports">
            <el-icon><DataAnalysis /></el-icon>
            <span>漏洞报告</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区域 -->
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { apiHealth } from "./api";

const route = useRoute();
const activeMenu = computed(() => route.path);
const apiConnected = ref(false);

onMounted(async () => {
  try {
    await apiHealth();
    apiConnected.value = true;
  } catch {
    apiConnected.value = false;
  }
});
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0e1117; color: #e0e0e0; font-family: "Segoe UI", sans-serif; }
#app-container { min-height: 100vh; display: flex; flex-direction: column; }
.app-header {
  background: #1a1d23 !important;
  border-bottom: 1px solid #2a2d33;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px !important;
  height: 56px !important;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.app-title { color: #00ff88; font-size: 18px; font-weight: 600; }
.app-body { flex: 1; }
.app-sidebar { background: #1a1d23; border-right: 1px solid #2a2d33; }
.app-main { background: #0e1117; padding: 24px; }
</style>
