<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// ===== 状态 =====
const uploading = ref(false)
const fileList = ref([])
const result = ref(null)
const filterStatus = ref('all')
const currentPage = ref(1)
const pageSize = ref(20)

// ===== 计算属性 =====
const filteredRows = computed(() => {
  if (!result.value) return []
  if (filterStatus.value === 'all') return result.value.rows
  if (filterStatus.value === 'success') return result.value.rows.filter(r => r.success)
  return result.value.rows.filter(r => !r.success)
})

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

// ===== 工具函数 =====
const fmt = (v) => {
  if (v == null) return '—'
  return Number(v).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

// ===== 上传校验 =====
const beforeUpload = (file) => {
  const isExcel = file.name.toLowerCase().endsWith('.xlsx') ||
                  file.name.toLowerCase().endsWith('.xls')
  if (!isExcel) {
    ElMessage.error('仅支持 .xlsx 或 .xls 格式')
    return false
  }
  return true
}

const handleFileChange = (file) => { fileList.value = [file] }
const handleFileRemove = () => { fileList.value = [] }

// ===== 下载模板 =====
const handleDownloadTemplate = () => {
  window.open('http://localhost:8000/api/payroll/batch/template', '_blank')
}

// ===== 批量计算 =====
const handleCalculate = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择一个 Excel 文件')
    return
  }
  const rawFile = fileList.value[0].raw
  const formData = new FormData()
  formData.append('file', rawFile)

  uploading.value = true
  result.value = null
  try {
    const res = await axios.post('/api/payroll/batch/calculate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = res.data
    currentPage.value = 1
    ElMessage.success(
      `计算完成：成功 ${res.data.summary.success_rows} 人，失败 ${res.data.summary.failed_rows} 人`
    )
  } catch (e) {
    console.error(e)
    ElMessage.error('计算失败：' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

// ===== 下载结果 =====
const handleDownloadReport = () => {
  if (!result.value?.report_file) return
  window.open('http://localhost:8000' + result.value.report_file, '_blank')
}

// ===== 重置 =====
const handleReset = () => {
  fileList.value = []
  result.value = null
  filterStatus.value = 'all'
  currentPage.value = 1
}
</script>

<template>
  <div class="page">
    <!-- ====== 上传卡片 ====== -->
    <el-card shadow="never" class="upload-card">
      <div class="card-title-row">
        <span class="title">💰 批量上传薪酬要素 Excel</span>
        <el-button size="small" type="primary" plain @click="handleDownloadTemplate">
          📥 下载标准模板
        </el-button>
      </div>

      <el-upload
        class="uploader"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :before-upload="beforeUpload"
        :file-list="fileList"
        :limit="1"
        accept=".xlsx,.xls"
      >
        <div class="upload-inner">
          <div class="upload-icon">📊</div>
          <div class="upload-text">拖拽 Excel 到这里，或<em>点击选择文件</em></div>
          <div class="upload-hint">
            必需列：工号、姓名、基本工资 ·
            可选列：绩效、津贴、加班费、社保基数、公积金费率、专项扣除等
          </div>
        </div>
      </el-upload>

      <div class="actions">
        <el-button type="primary" :loading="uploading" @click="handleCalculate" :disabled="fileList.length === 0">
          {{ uploading ? '计算中...' : '开始批量计算' }}
        </el-button>
        <el-button @click="handleReset" :disabled="!result && fileList.length === 0">
          重置
        </el-button>
      </div>
    </el-card>

    <!-- ====== 结果展示 ====== -->
    <div v-if="result" class="result">
      <!-- 总览统计 -->
      <el-row :gutter="16" class="stats">
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">总人数</div>
            <div class="stat-value total">{{ result.summary.total_rows }}</div>
            <div class="stat-sub">
              成功 <span class="text-success">{{ result.summary.success_rows }}</span> ·
              失败 <span class="text-danger">{{ result.summary.failed_rows }}</span>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">应发总额</div>
            <div class="stat-value gross">¥ {{ fmt(result.summary.total_gross) }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">五险一金 + 个税</div>
            <div class="stat-value deduct">
              ¥ {{ fmt(result.summary.total_si + result.summary.total_tax) }}
            </div>
            <div class="stat-sub">
              社保 {{ fmt(result.summary.total_si) }} ·
              税 {{ fmt(result.summary.total_tax) }}
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card highlight">
            <div class="stat-label">实发总额</div>
            <div class="stat-value net">¥ {{ fmt(result.summary.total_net) }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 工资条明细 -->
      <el-card shadow="never" class="rows-card">
        <div class="card-title-row">
          <span class="title">📋 工资条明细</span>
          <div class="actions-right">
            <el-radio-group v-model="filterStatus" size="small" @change="currentPage = 1">
              <el-radio-button label="all">全部 ({{ result.rows.length }})</el-radio-button>
              <el-radio-button label="success">成功 ({{ result.summary.success_rows }})</el-radio-button>
              <el-radio-button label="failed">失败 ({{ result.summary.failed_rows }})</el-radio-button>
            </el-radio-group>
            <el-button type="success" size="small" @click="handleDownloadReport" :disabled="!result.report_file">
              📥 下载完整工资条 Excel
            </el-button>
          </div>
        </div>

        <el-table
          :data="pagedRows"
          stripe
          border
          empty-text="没有数据"
          size="small"
          style="width: 100%"
        >
          <el-table-column prop="row" label="行号" width="70" align="center" />
          <el-table-column prop="employee_id" label="工号" width="100">
            <template #default="{ row }">{{ row.employee_id || '—' }}</template>
          </el-table-column>
          <el-table-column prop="name" label="姓名" width="90">
            <template #default="{ row }">{{ row.name || '—' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.success" type="success" size="small">成功</el-tag>
              <el-tag v-else type="danger" size="small">失败</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="应发" align="right" min-width="100">
            <template #default="{ row }">
              <span v-if="row.success" class="num">{{ fmt(row.gross_salary) }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="五险一金" align="right" min-width="100">
            <template #default="{ row }">
              <span v-if="row.success" class="num">{{ fmt(row.social_insurance_total) }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="个税" align="right" min-width="90">
            <template #default="{ row }">
              <span v-if="row.success" class="num">{{ fmt(row.income_tax) }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="实发" align="right" min-width="110">
            <template #default="{ row }">
              <span v-if="row.success" class="num net-amount">{{ fmt(row.net_salary) }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="错误原因" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="!row.success" class="error-msg">{{ row.error }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="filteredRows.length > pageSize"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredRows.length"
          layout="total, prev, pager, next, jumper"
          class="pagination"
          background
        />
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1400px; }

.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

/* ===== 上传 ===== */
.upload-card { margin-bottom: 20px; }
.uploader { margin-bottom: 16px; }
.uploader :deep(.el-upload-dragger) { padding: 32px 0; }
.upload-inner { text-align: center; }
.upload-icon { font-size: 48px; margin-bottom: 8px; }
.upload-text { font-size: 14px; color: #4b5563; }
.upload-text em {
  color: #3b82f6;
  font-style: normal;
  font-weight: 500;
  margin: 0 4px;
}
.upload-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 6px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}
.actions { display: flex; gap: 10px; }

/* ===== 统计 ===== */
.stats { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-card.highlight {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
  border: none;
}
.stat-card.highlight .stat-label { color: #d1fae5; }
.stat-card.highlight .stat-value { color: #fff; }
.stat-label { font-size: 13px; color: #6b7280; margin-bottom: 8px; }
.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  font-family: monospace;
}
.stat-value.total { color: #1f2937; }
.stat-value.gross { color: #3b82f6; }
.stat-value.deduct { color: #f59e0b; }
.stat-value.net { color: #10b981; }
.stat-sub { font-size: 12px; color: #94a3b8; margin-top: 8px; }
.text-success { color: #10b981; font-weight: 600; }
.text-danger { color: #ef4444; font-weight: 600; }

/* ===== 明细表格 ===== */
.rows-card { margin-bottom: 20px; }
.actions-right {
  display: flex;
  gap: 12px;
  align-items: center;
}
.num { font-family: monospace; color: #1f2937; }
.net-amount {
  font-weight: 600;
  color: #10b981;
}
.muted { color: #cbd5e1; }
.error-msg { color: #ef4444; font-size: 12px; }

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>