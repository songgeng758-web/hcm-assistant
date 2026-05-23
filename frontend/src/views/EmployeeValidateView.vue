<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// ===== 状态 =====
const uploading = ref(false)
const fileList = ref([])
const result = ref(null)        // 校验返回的完整 JSON
const filterLevel = ref('all')  // all / error / warning
const inspectResult = ref(null) // 诊断结果
const inspectDialogVisible = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)

// ===== 计算属性 =====
const filteredIssues = computed(() => {
  if (!result.value) return []
  if (filterLevel.value === 'all') return result.value.issues
  return result.value.issues.filter(i => i.level === filterLevel.value)
})

const pagedIssues = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredIssues.value.slice(start, start + pageSize.value)
})

// ===== 上传前校验 =====
const beforeUpload = (file) => {
  const isExcel = file.name.toLowerCase().endsWith('.xlsx') ||
                  file.name.toLowerCase().endsWith('.xls')
  if (!isExcel) {
    ElMessage.error('仅支持 .xlsx 或 .xls 格式')
    return false
  }
  const sizeMB = file.size / 1024 / 1024
  if (sizeMB > 50) {
    ElMessage.error('文件不能超过 50MB')
    return false
  }
  return true
}

// ===== 提交校验 =====
const handleValidate = async () => {
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
    const res = await axios.post('/api/org/employees/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = res.data
    currentPage.value = 1
    ElMessage.success(`校验完成：共 ${res.data.summary.total_rows} 行，发现 ${res.data.summary.error_count} 个错误`)
  } catch (e) {
    console.error(e)
    ElMessage.error('校验失败：' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

// ===== 诊断字段映射 =====
const handleInspect = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择一个 Excel 文件')
    return
  }
  const rawFile = fileList.value[0].raw
  const formData = new FormData()
  formData.append('file', rawFile)

  try {
    const res = await axios.post('/api/org/employees/inspect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    inspectResult.value = res.data
    inspectDialogVisible.value = true
  } catch (e) {
    ElMessage.error('诊断失败：' + (e.response?.data?.detail || e.message))
  }
}

// ===== 下载报告 =====
const handleDownload = () => {
  if (!result.value?.report_file) return
  window.open('http://localhost:8000' + result.value.report_file, '_blank')
}

// ===== 重置 =====
const handleReset = () => {
  fileList.value = []
  result.value = null
  inspectResult.value = null
  currentPage.value = 1
  filterLevel.value = 'all'
}

// ===== 文件变化 =====
const handleFileChange = (file) => {
  fileList.value = [file]
}

const handleFileRemove = () => {
  fileList.value = []
}
</script>

<template>
  <div class="page">
    <!-- ====== 上传卡片 ====== -->
    <el-card shadow="never" class="upload-card">
      <div class="card-title">
        <span class="title">📤 上传员工档案 Excel</span>
        <el-tooltip content="支持中英文字段名自动识别，包括浪潮 HCM 标准模板">
          <el-icon class="info-icon"><svg viewBox="0 0 1024 1024" width="14" height="14"><path fill="#94a3b8" d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 800c-194.4 0-352-157.6-352-352s157.6-352 352-352 352 157.6 352 352-157.6 352-352 352z"/><path fill="#94a3b8" d="M512 624c17.7 0 32-14.3 32-32V352c0-17.7-14.3-32-32-32s-32 14.3-32 32v240c0 17.7 14.3 32 32 32zm0 96c-22.1 0-40 17.9-40 40s17.9 40 40 40 40-17.9 40-40-17.9-40-40-40z"/></svg></el-icon>
        </el-tooltip>
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
          <div class="upload-icon">📂</div>
          <div class="upload-text">拖拽 Excel 到这里，或<em>点击选择文件</em></div>
          <div class="upload-hint">支持 .xlsx / .xls，单文件不超过 50MB</div>
        </div>
      </el-upload>

      <div class="actions">
        <el-button type="primary" :loading="uploading" @click="handleValidate" :disabled="fileList.length === 0">
          {{ uploading ? '校验中...' : '开始校验' }}
        </el-button>
        <el-button @click="handleInspect" :disabled="fileList.length === 0">
          🔍 诊断字段映射
        </el-button>
        <el-button @click="handleReset" :disabled="!result && fileList.length === 0">
          重置
        </el-button>
      </div>
    </el-card>

    <!-- ====== 结果总览 ====== -->
    <div v-if="result" class="result-section">
      <el-row :gutter="16" class="stats">
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">总行数</div>
            <div class="stat-value total">{{ result.summary.total_rows }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">合法行数</div>
            <div class="stat-value valid">{{ result.summary.valid_rows }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">错误数</div>
            <div class="stat-value error">{{ result.summary.error_count }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">警告数</div>
            <div class="stat-value warning">{{ result.summary.warning_count }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 重复工号提醒 -->
      <el-alert
        v-if="result.summary.duplicate_employee_ids?.length"
        type="warning"
        :closable="false"
        class="dup-alert"
      >
        <template #title>
          发现 {{ result.summary.duplicate_employee_ids.length }} 个重复工号：
          {{ result.summary.duplicate_employee_ids.slice(0, 10).join('、') }}
          {{ result.summary.duplicate_employee_ids.length > 10 ? '...' : '' }}
        </template>
      </el-alert>

      <!-- ====== 异常明细 ====== -->
      <el-card shadow="never" class="issues-card">
        <div class="card-title">
          <span class="title">📋 异常明细</span>
          <div class="card-actions">
            <el-radio-group v-model="filterLevel" size="small" @change="currentPage = 1">
              <el-radio-button label="all">全部 ({{ result.issues.length }})</el-radio-button>
              <el-radio-button label="error">错误 ({{ result.summary.error_count }})</el-radio-button>
              <el-radio-button label="warning">警告 ({{ result.summary.warning_count }})</el-radio-button>
            </el-radio-group>
            <el-button type="success" size="small" @click="handleDownload" :disabled="!result.report_file">
              📥 下载 Excel 报告
            </el-button>
          </div>
        </div>

        <el-table
          :data="pagedIssues"
          stripe
          border
          empty-text="未发现异常 🎉"
          size="small"
          style="width: 100%"
        >
          <el-table-column prop="row" label="行号" width="80" align="center" />
          <el-table-column prop="employee_id" label="工号" width="120">
            <template #default="{ row }">{{ row.employee_id || '—' }}</template>
          </el-table-column>
          <el-table-column prop="name" label="姓名" width="120">
            <template #default="{ row }">{{ row.name || '—' }}</template>
          </el-table-column>
          <el-table-column prop="field" label="字段" width="120" />
          <el-table-column prop="level" label="级别" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.level === 'error' ? 'danger' : 'warning'" size="small">
                {{ row.level === 'error' ? '错误' : '警告' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="问题描述" min-width="240" show-overflow-tooltip />
          <el-table-column prop="suggestion" label="修复建议" min-width="200" show-overflow-tooltip />
        </el-table>

        <el-pagination
          v-if="filteredIssues.length > pageSize"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredIssues.length"
          layout="total, prev, pager, next, jumper"
          class="pagination"
          background
        />
      </el-card>
    </div>

    <!-- ====== 诊断结果弹窗 ====== -->
    <el-dialog v-model="inspectDialogVisible" title="🔍 字段诊断结果" width="700px">
      <div v-if="inspectResult">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="总列数">{{ inspectResult.total_columns }}</el-descriptions-item>
          <el-descriptions-item label="识别到的字段">
            <div v-if="Object.keys(inspectResult.recognized).length === 0" class="muted">无</div>
            <el-tag
              v-for="(actual, std) in inspectResult.recognized"
              :key="std"
              class="mapping-tag"
              type="success"
            >
              {{ std }} → {{ actual }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="缺失的重要字段">
            <span v-if="!inspectResult.missing_important_fields?.length" class="muted">无（关键字段齐全）</span>
            <el-tag
              v-for="m in inspectResult.missing_important_fields"
              :key="m"
              type="danger"
              class="mapping-tag"
            >
              {{ m }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="未识别的列">
            <span v-if="!inspectResult.unrecognized_columns?.length" class="muted">无</span>
            <div v-else class="unrec-cols">
              <el-tag
                v-for="c in inspectResult.unrecognized_columns"
                :key="c"
                type="info"
                class="mapping-tag"
              >
                {{ c }}
              </el-tag>
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1300px;
}

.card-title {
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

.card-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.info-icon {
  margin-left: 6px;
  cursor: help;
}

/* ===== 上传 ===== */
.upload-card {
  margin-bottom: 20px;
}

.uploader {
  margin-bottom: 16px;
}

.uploader :deep(.el-upload-dragger) {
  padding: 32px 0;
}

.upload-inner {
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 14px;
  color: #4b5563;
}

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
}

.actions {
  display: flex;
  gap: 10px;
}

/* ===== 结果统计 ===== */
.result-section {
  margin-top: 20px;
}

.stats {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.stat-value.total { color: #1f2937; }
.stat-value.valid { color: #10b981; }
.stat-value.error { color: #ef4444; }
.stat-value.warning { color: #f59e0b; }

.dup-alert {
  margin-bottom: 16px;
}

/* ===== 异常明细 ===== */
.issues-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* ===== 诊断弹窗 ===== */
.mapping-tag {
  margin: 2px 4px 2px 0;
}

.unrec-cols {
  max-height: 200px;
  overflow-y: auto;
}

.muted {
  color: #94a3b8;
  font-size: 13px;
}
</style>