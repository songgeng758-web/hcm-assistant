<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// ===== 输入表单 =====
const form = ref({
  base_salary: 15000,
  performance: 3000,
  position_allowance: 500,
  overtime_pay: 0,
  other_allowance: 200,
  social_insurance_base: null,
  housing_fund_rate: 0.07,
  special_deduction: 1500,
  other_deduction: 0,
})

const loading = ref(false)
const result = ref(null)

// ===== 计算 =====
const handleCalculate = async () => {
  loading.value = true
  result.value = null
  try {
    const res = await axios.post('/api/payroll/calculate', form.value)
    result.value = res.data
    ElMessage.success('计算完成')
  } catch (e) {
    console.error(e)
    ElMessage.error('计算失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// ===== 重置 =====
const handleReset = () => {
  form.value = {
    base_salary: 0,
    performance: 0,
    position_allowance: 0,
    overtime_pay: 0,
    other_allowance: 0,
    social_insurance_base: null,
    housing_fund_rate: 0.07,
    special_deduction: 0,
    other_deduction: 0,
  }
  result.value = null
}

// ===== 格式化数字 =====
const fmt = (v) => {
  if (v == null) return '—'
  return Number(v).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const fmtPercent = (v) => {
  if (v == null) return '—'
  return (Number(v) * 100).toFixed(1) + '%'
}
</script>

<template>
  <div class="page">
    <el-row :gutter="20">
      <!-- ====== 左侧：输入表单 ====== -->
      <el-col :span="10">
        <el-card shadow="never" class="form-card">
          <div class="card-title">💵 薪酬要素</div>

          <el-form :model="form" label-width="120px" label-position="left" size="default">
            <el-divider content-position="left">应发组成</el-divider>

            <el-form-item label="基本工资">
              <el-input-number v-model="form.base_salary" :min="0" :step="100" controls-position="right" style="width: 100%" />
            </el-form-item>
            <el-form-item label="绩效工资">
              <el-input-number v-model="form.performance" :min="0" :step="100" controls-position="right" style="width: 100%" />
            </el-form-item>
            <el-form-item label="岗位津贴">
              <el-input-number v-model="form.position_allowance" :min="0" :step="100" controls-position="right" style="width: 100%" />
            </el-form-item>
            <el-form-item label="加班费">
              <el-input-number v-model="form.overtime_pay" :min="0" :step="100" controls-position="right" style="width: 100%" />
            </el-form-item>
            <el-form-item label="其他补贴">
              <el-input-number v-model="form.other_allowance" :min="0" :step="100" controls-position="right" style="width: 100%" />
            </el-form-item>

            <el-divider content-position="left">五险一金</el-divider>

            <el-form-item label="社保基数">
              <el-input-number v-model="form.social_insurance_base" :min="0" :step="100" controls-position="right" style="width: 100%" placeholder="留空则用应发工资" />
            </el-form-item>
            <el-form-item label="公积金费率">
              <el-slider v-model="form.housing_fund_rate" :min="0.05" :max="0.12" :step="0.005" :format-tooltip="(v) => (v*100).toFixed(1) + '%'" show-input :show-input-controls="false" />
            </el-form-item>

            <el-divider content-position="left">扣除项</el-divider>

            <el-form-item label="专项附加扣除">
              <el-input-number v-model="form.special_deduction" :min="0" :step="100" controls-position="right" style="width: 100%" />
            </el-form-item>
            <el-form-item label="其他扣款">
              <el-input-number v-model="form.other_deduction" :min="0" :step="100" controls-position="right" style="width: 100%" />
            </el-form-item>

            <div class="form-actions">
              <el-button type="primary" :loading="loading" @click="handleCalculate" style="width: 100%">
                {{ loading ? '计算中...' : '开始计算' }}
              </el-button>
              <el-button @click="handleReset" style="width: 100%; margin-top: 8px; margin-left: 0">
                重置
              </el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <!-- ====== 右侧：结果展示 ====== -->
      <el-col :span="14">
        <!-- 未计算时的占位 -->
        <el-card v-if="!result" shadow="never" class="empty-card">
          <div class="empty-inner">
            <div class="empty-icon">💼</div>
            <div class="empty-text">填写左侧薪酬要素，点击"开始计算"</div>
            <div class="empty-hint">所有金额按月度计算 · 个税采用月度税率表</div>
          </div>
        </el-card>

        <!-- 计算结果 -->
        <div v-else>
          <!-- 实发工资 - 主卡片 -->
          <el-card shadow="never" class="net-card">
            <div class="net-label">实发工资</div>
            <div class="net-value">¥ {{ fmt(result.net_salary) }}</div>
            <div class="net-breakdown">
              应发 {{ fmt(result.gross_salary) }} − 五险一金 {{ fmt(result.social_insurance_total) }} − 个税 {{ fmt(result.income_tax) }}
              <span v-if="result.other_deduction > 0"> − 其他扣款 {{ fmt(result.other_deduction) }}</span>
            </div>
          </el-card>

          <!-- 三大块明细 -->
          <el-row :gutter="12" class="detail-row">
            <!-- 应发明细 -->
            <el-col :span="8">
              <el-card shadow="never" class="detail-card">
                <div class="detail-title">📈 应发明细</div>
                <div class="detail-list">
                  <div v-for="(v, k) in result.income_breakdown" :key="k" class="detail-item">
                    <span>{{ k }}</span>
                    <span class="value">{{ fmt(v) }}</span>
                  </div>
                  <div class="detail-item total">
                    <span>合计</span>
                    <span class="value">{{ fmt(result.gross_salary) }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>

            <!-- 五险一金 -->
            <el-col :span="8">
              <el-card shadow="never" class="detail-card">
                <div class="detail-title">🏥 五险一金</div>
                <div class="detail-list">
                  <div class="detail-item">
                    <span>养老 (8%)</span>
                    <span class="value">{{ fmt(result.pension) }}</span>
                  </div>
                  <div class="detail-item">
                    <span>医疗 (2%)</span>
                    <span class="value">{{ fmt(result.medical) }}</span>
                  </div>
                  <div class="detail-item">
                    <span>失业 (0.5%)</span>
                    <span class="value">{{ fmt(result.unemployment) }}</span>
                  </div>
                  <div class="detail-item">
                    <span>公积金 ({{ fmtPercent(form.housing_fund_rate) }})</span>
                    <span class="value">{{ fmt(result.housing_fund) }}</span>
                  </div>
                  <div class="detail-item total">
                    <span>合计</span>
                    <span class="value">{{ fmt(result.social_insurance_total) }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>

            <!-- 个税 -->
            <el-col :span="8">
              <el-card shadow="never" class="detail-card">
                <div class="detail-title">📑 个人所得税</div>
                <div class="detail-list">
                  <div class="detail-item">
                    <span>应纳税所得额</span>
                    <span class="value">{{ fmt(result.taxable_income) }}</span>
                  </div>
                  <div class="detail-item">
                    <span>适用税率</span>
                    <span class="value">{{ fmtPercent(result.tax_rate) }}</span>
                  </div>
                  <div class="detail-item">
                    <span>速算扣除数</span>
                    <span class="value">{{ fmt(result.quick_deduction) }}</span>
                  </div>
                  <div class="detail-item total">
                    <span>应缴个税</span>
                    <span class="value">{{ fmt(result.income_tax) }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 计算过程 -->
          <el-card shadow="never" class="notes-card">
            <div class="detail-title">📝 计算过程</div>
            <el-steps direction="vertical" :active="result.notes.length" :space="50" class="steps">
              <el-step v-for="(n, idx) in result.notes" :key="idx" :title="n" />
            </el-steps>
          </el-card>
        </div>
      </el-col>
    </el-row>
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

/* ===== 表单 ===== */
.form-card {
  position: sticky;
  top: 0;
}

.form-actions {
  margin-top: 24px;
}

/* ===== 占位 ===== */
.empty-card {
  height: 100%;
  min-height: 500px;
}

.empty-inner {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  color: #4b5563;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: #94a3b8;
}

/* ===== 实发主卡片 ===== */
.net-card {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
  border: none;
  margin-bottom: 16px;
}

.net-card :deep(.el-card__body) {
  padding: 32px;
}

.net-label {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.net-value {
  font-size: 42px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 12px;
  font-family: monospace;
}

.net-breakdown {
  font-size: 13px;
  opacity: 0.85;
}

/* ===== 明细卡片 ===== */
.detail-row {
  margin-bottom: 16px;
}

.detail-card {
  height: 100%;
}

.detail-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.detail-list {
  font-size: 13px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  color: #6b7280;
}

.detail-item .value {
  font-family: monospace;
  color: #1f2937;
}

.detail-item.total {
  border-top: 1px solid #f1f5f9;
  margin-top: 4px;
  padding-top: 8px;
  font-weight: 600;
  color: #1f2937;
}

/* ===== 步骤 ===== */
.notes-card {
  margin-bottom: 20px;
}

.steps {
  padding: 8px 4px;
}

.steps :deep(.el-step__title) {
  font-size: 13px;
  line-height: 1.6;
  font-family: monospace;
}
</style>