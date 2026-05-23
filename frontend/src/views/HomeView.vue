<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const backendStatus = ref('checking')
const apiVersion = ref('')

const features = [
  {
    icon: '👥',
    title: '组织人事',
    desc: '员工档案批量校验、身份证解析、组织架构树解析',
    items: ['员工档案校验', '组织架构解析'],
    path: '/org/employee-validate',
    color: 'org',
    enabled: true,
  },
  {
    icon: '💰',
    title: '薪酬计算',
    desc: '单人工资试算 + Excel 批量算薪，含五险一金与个税',
    items: ['工资计算器', '批量算薪'],
    path: '/payroll/calculate',
    color: 'payroll',
    enabled: true,
  },
  {
    icon: '🔧',
    title: '通用能力',
    desc: '字段映射、规则库、操作日志追溯',
    items: ['规划中'],
    path: null,
    color: 'common',
    enabled: false,
  },
]

onMounted(async () => {
  try {
    const res = await axios.get('/')
    backendStatus.value = 'ok'
    apiVersion.value = res.data.version
  } catch (e) {
    backendStatus.value = 'fail'
  }
})
</script>

<template>
  <div class="home">
    <!-- 欢迎横幅 -->
    <el-card shadow="never" class="welcome">
      <div class="welcome-title">欢迎使用 HCM 实施助手 👋</div>
      <div class="welcome-desc">
        面向 HCM 实施顾问的 Web 端数据迁移与校验工具，
        让 Excel 清洗、字段校验、薪酬计算不再痛苦。
      </div>
      <div class="welcome-tags">
        <el-tag class="w-tag">FastAPI</el-tag>
        <el-tag class="w-tag">Vue 3</el-tag>
        <el-tag class="w-tag">Element Plus</el-tag>
        <el-tag class="w-tag">pandas</el-tag>
        <el-tag class="w-tag">pytest</el-tag>
      </div>
    </el-card>

    <!-- 三大模块 -->
    <el-row :gutter="20" class="cards">
      <el-col v-for="f in features" :key="f.title" :span="8">
        <el-card shadow="hover" class="feature-card" :class="f.color">
          <div class="feature-icon">{{ f.icon }}</div>
          <div class="feature-title">{{ f.title }}</div>
          <div class="feature-desc">{{ f.desc }}</div>
          <div class="feature-items">
            <el-tag
              v-for="item in f.items"
              :key="item"
              size="small"
              :type="f.enabled ? 'success' : 'info'"
              class="item-tag"
            >
              {{ item }}
            </el-tag>
          </div>
          <el-button
            v-if="f.enabled"
            type="primary"
            plain
            @click="$router.push(f.path)"
          >
            立即体验
          </el-button>
          <el-button v-else disabled>规划中</el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统状态 -->
    <el-card shadow="never" class="status">
      <div class="status-title">系统状态</div>
      <div class="status-row">
        <span class="status-label">后端服务：</span>
        <el-tag v-if="backendStatus === 'ok'" type="success">运行中</el-tag>
        <el-tag v-else-if="backendStatus === 'fail'" type="danger">未连接</el-tag>
        <el-tag v-else type="info">检测中...</el-tag>
        <span v-if="apiVersion" class="status-version">v{{ apiVersion }}</span>
      </div>
      <div class="status-row">
        <span class="status-label">API 文档：</span>
        <a href="http://localhost:8000/docs" target="_blank" class="link">
          http://localhost:8000/docs ↗
        </a>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.home {
  max-width: 1200px;
}

/* 欢迎横幅 */
.welcome {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
  color: #fff;
  border: none;
}

.welcome :deep(.el-card__body) {
  padding: 32px;
}

.welcome-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
}

.welcome-desc {
  font-size: 14px;
  opacity: 0.9;
  line-height: 1.6;
  margin-bottom: 16px;
}

.welcome-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.w-tag {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
}

/* 三大模块 */
.cards {
  margin-bottom: 20px;
}

.feature-card {
  height: 260px;
  display: flex;
  flex-direction: column;
}

.feature-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.feature-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.feature-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

.feature-desc {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
  margin-bottom: 12px;
}

.feature-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
  flex: 1;
}

.item-tag {
  font-size: 12px;
}

/* 系统状态 */
.status {
  background: #fff;
}

.status-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 12px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
}

.status-row:last-child {
  margin-bottom: 0;
}

.status-version {
  color: #94a3b8;
  font-family: monospace;
}

.link {
  color: #3b82f6;
  font-family: monospace;
}

.link:hover {
  text-decoration: underline;
}
</style>