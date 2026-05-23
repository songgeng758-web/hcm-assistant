<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// ===== 状态 =====
const uploading = ref(false)
const fileList = ref([])
const result = ref(null)
const searchKeyword = ref('')
const issueFilter = ref('all')
const currentPage = ref(1)
const pageSize = ref(15)

// Element Plus 树组件的配置
const treeProps = {
  children: 'children',
  label: 'name',
}

// ===== 计算属性 =====
const filteredIssues = computed(() => {
  if (!result.value) return []
  if (issueFilter.value === 'all') return result.value.issues
  return result.value.issues.filter(i => i.issue_type === issueFilter.value)
})

const pagedIssues = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredIssues.value.slice(start, start + pageSize.value)
})

const gapCount = computed(() =>
  result.value?.issues.filter(i => i.issue_type === 'path_gap').length || 0
)
const emptyCount = computed(() =>
  result.value?.issues.filter(i => i.issue_type === 'empty_root').length || 0
)

// ===== 上传 =====
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

// ===== 解析 =====
const handleParse = async () => {
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
    const res = await axios.post('/api/org/structure/parse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    result.value = res.data
    currentPage.value = 1
    ElMessage.success(
      `解析完成：识别 ${res.data.total_nodes} 个部门节点，最深 ${res.data.max_depth} 级`
    )
  } catch (e) {
    console.error(e)
    ElMessage.error('解析失败：' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

const handleReset = () => {
  fileList.value = []
  result.value = null
  searchKeyword.value = ''
  issueFilter.value = 'all'
  currentPage.value = 1
}

// ===== 树筛选 =====
const filterNode = (value, data) => {
  if (!value) return true
  return data.name.includes(value)
}

const treeRef = ref(null)
const handleSearch = (val) => {
  treeRef.value?.filter(val)
}
</script>

<template>
  <div class="page">
    <!-- ====== 上传卡片 ====== -->
    <el-card shadow="never" class="upload-card">
      <div class="card-title">📊 上传含组织层级的 Excel</div>
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
          <div class="upload-icon">🌲</div>
          <div class="upload-text">拖拽 Excel 到这里，或<em>点击选择文件</em></div>
          <div class="upload-hint">自动识别"岗位_一级组织"~"岗位_十级组织"列</div>
        </div>
      </el-upload>

      <div class="actions">
        <el-button type="primary" :loading="uploading" @click="handleParse" :disabled="fileList.length === 0">
          {{ uploading ? '解析中...' : '开始解析' }}
        </el-button>
        <el-button @click="handleReset" :disabled="!result && fileList.length === 0">
          重置
        </el-button>
      </div>
    </el-card>

    <!-- ====== 结果展示 ====== -->
    <div v-if="result" class="result">
      <!-- 统计卡片 -->
      <el-row :gutter="16" class="stats">
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">数据行数</div>
            <div class="stat-value total">{{ result.total_rows }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">部门节点</div>
            <div class="stat-value nodes">{{ result.total_nodes }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">最深层级</div>
            <div class="stat-value depth">{{ result.max_depth }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="stat-card">
            <div class="stat-label">异常行数</div>
            <div class="stat-value error">{{ result.issues.length }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <!-- 左侧：组织树 -->
        <el-col :span="14">
          <el-card shadow="never" class="tree-card">
            <div class="card-title-row">
              <span class="title">🌲 组织架构树</span>
              <el-input
                v-model="searchKeyword"
                placeholder="搜索部门名称"
                size="small"
                style="width: 200px"
                @input="handleSearch"
                clearable
              />
            </div>

            <div class="tree-wrap">
              <el-tree
                ref="treeRef"
                :data="result.tree"
                :props="treeProps"
                :filter-node-method="filterNode"
                node-key="name"
                default-expand-all
                :indent="20"
              >
                <template #default="{ data }">
                  <span class="node">
                    <span class="node-name">{{ data.name }}</span>
                    <span class="node-meta">
                      <el-tag size="small" type="info">L{{ data.level }}</el-tag>
                      <el-tag size="small" type="success" v-if="data.total_count > 0">
                        {{ data.total_count }} 人
                      </el-tag>
                    </span>
                  </span>
                </template>
              </el-tree>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：异常清单 -->
        <el-col :span="10">
          <el-card shadow="never" class="issues-card">
            <div class="card-title-row">
              <span class="title">⚠️ 异常清单</span>
              <el-radio-group v-model="issueFilter" size="small" @change="currentPage = 1">
                <el-radio-button label="all">全部 ({{ result.issues.length }})</el-radio-button>
                <el-radio-button label="path_gap">断层 ({{ gapCount }})</el-radio-button>
                <el-radio-button label="empty_root">空组织 ({{ emptyCount }})</el-radio-button>
              </el-radio-group>
            </div>

            <div v-if="filteredIssues.length === 0" class="no-issue">
              🎉 此分类下没有异常
            </div>

            <el-table v-else :data="pagedIssues" stripe border size="small">
              <el-table-column prop="row" label="行号" width="70" align="center" />
              <el-table-column prop="employee_id" label="工号" width="100">
                <template #default="{ row }">{{ row.employee_id || '—' }}</template>
              </el-table-column>
              <el-table-column prop="name" label="姓名" width="80">
                <template #default="{ row }">{{ row.name || '—' }}</template>
              </el-table-column>
              <el-table-column prop="issue_type" label="类型" width="90" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.issue_type === 'path_gap' ? 'warning' : 'danger'" size="small">
                    {{ row.issue_type === 'path_gap' ? '断层' : '空组织' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="message" label="问题描述" min-width="200" show-overflow-tooltip />
            </el-table>

            <el-pagination
              v-if="filteredIssues.length > pageSize"
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :total="filteredIssues.length"
              layout="total, prev, pager, next"
              class="pagination"
              background
              small
            />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1400px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
}

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

/* 上传 */
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
.upload-hint { font-size: 12px; color: #94a3b8; margin-top: 6px; }
.actions { display: flex; gap: 10px; }

/* 统计 */
.stats { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-label { font-size: 13px; color: #6b7280; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1; }
.stat-value.total { color: #1f2937; }
.stat-value.nodes { color: #3b82f6; }
.stat-value.depth { color: #8b5cf6; }
.stat-value.error { color: #ef4444; }

/* 树 */
.tree-card { height: 600px; display: flex; flex-direction: column; }
.tree-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.tree-wrap {
  flex: 1;
  overflow: auto;
  padding-right: 8px;
}
.node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  padding-right: 12px;
}
.node-name {
  font-size: 13px;
  color: #1f2937;
}
.node-meta {
  display: flex;
  gap: 4px;
}

/* 异常清单 */
.issues-card { height: 600px; }
.no-issue {
  text-align: center;
  padding: 80px 0;
  color: #94a3b8;
  font-size: 14px;
}
.pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>