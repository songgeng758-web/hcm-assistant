<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// 当前激活的菜单项 = 当前路由
const activeMenu = computed(() => route.path)

const handleMenuSelect = (path) => {
  router.push(path)
}
</script>

<template>
  <el-container class="layout">
    <!-- 左侧导航 -->
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <span class="logo-icon">🛠</span>
        <div>
          <div class="logo-title">HCM 实施助手</div>
          <div class="logo-subtitle">v0.1.0</div>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :router="false"
        class="menu"
        background-color="#1f2937"
        text-color="#cbd5e1"
        active-text-color="#60a5fa"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/">
          <el-icon><i class="icon">🏠</i></el-icon>
          <span>首页</span>
        </el-menu-item>

        <el-sub-menu index="org">
          <template #title>
            <el-icon><i class="icon">👥</i></el-icon>
            <span>组织人事</span>
          </template>
          <el-menu-item index="/org/employee-validate">员工档案校验</el-menu-item>
          <el-menu-item index="/org/structure">组织架构解析</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="payroll">
          <template #title>
            <el-icon><i class="icon">💰</i></el-icon>
            <span>薪酬计算</span>
          </template>
          <el-menu-item index="/payroll/calculate">工资计算器</el-menu-item>
          <el-menu-item index="/payroll/batch">批量算薪</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="common">
          <template #title>
            <el-icon><i class="icon">🔧</i></el-icon>
            <span>通用能力</span>
          </template>
          <el-menu-item index="/common/placeholder" disabled>规划中...</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <!-- 右侧内容区 -->
    <el-container>
      <el-header class="header">
        <div class="header-title">
          {{ route.meta.title || '欢迎' }}
        </div>
        <div class="header-right">
          <el-tag size="small" type="success">后端已连接</el-tag>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}

.sidebar {
  background-color: #1f2937;
  color: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid #374151;
}

.logo-icon {
  font-size: 28px;
}

.logo-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.logo-subtitle {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}

.menu {
  border-right: none;
  flex: 1;
}

.icon {
  font-style: normal;
  margin-right: 4px;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.main {
  background-color: #f8fafc;
  padding: 24px;
}
</style>