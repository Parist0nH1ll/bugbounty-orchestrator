<template>
  <div class="report-page">
    <h2>📊 漏洞报告</h2>
    <p class="desc">查看漏洞扫描结果和 AI 分析报告</p>

    <el-card class="select-card">
      <el-form :inline="true">
        <el-form-item label="选择任务">
          <el-input v-model="taskId" placeholder="输入 Task ID" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadReport" :loading="loading">查看报告</el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="exportCsv" :disabled="!report">导出 CSV</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <template v-if="report">
      <el-row :gutter="16" class="stats-row">
        <el-col :span="6">
          <el-statistic title="高危漏洞" :value="highCount">
            <template #suffix><span style="color:#f56c6c">🔴</span></template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="中危漏洞" :value="mediumCount">
            <template #suffix><span style="color:#e6a23c">🟧</span></template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="低危漏洞" :value="lowCount">
            <template #suffix><span style="color:#67c23a">🟩</span></template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="总计" :value="report.vulnerabilities.length">
            <template #suffix>📋</template>
          </el-statistic>
        </el-col>
      </el-row>

      <el-card class="table-card">
        <template #header>漏洞列表</template>
        <el-table :data="report.vulnerabilities" v-loading="loading" empty-text="无漏洞记录">
          <el-table-column label="严重度" width="80">
            <template #default="{ row }">
              <el-tag :type="sevType(row.risk_score)">{{ sevLabel(row.risk_score) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="cve_id" label="CVE" width="150" />
          <el-table-column prop="risk_score" label="评分" width="80" sortable />
          <el-table-column prop="domain" label="域名" width="200" />
          <el-table-column prop="affected_component" label="组件" width="150" />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column prop="remediation" label="修复建议" min-width="200" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card class="summary-card">
        <template #header>AI 分析摘要</template>
        <el-alert :title="report.summary" type="info" :closable="false" show-icon />
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { getReport, exportReportCsv } from "../api";

const route = useRoute();
const taskId = ref(route.query.task_id || "");
const report = ref(null);
const loading = ref(false);

const highCount = computed(() =>
  report.value?.vulnerabilities.filter((v) => (v.risk_score || 0) >= 7).length || 0
);
const mediumCount = computed(() =>
  report.value?.vulnerabilities.filter((v) => (v.risk_score || 0) >= 4 && (v.risk_score || 0) < 7).length || 0
);
const lowCount = computed(() =>
  report.value?.vulnerabilities.filter((v) => (v.risk_score || 0) < 4).length || 0
);

function sevType(score) {
  if (score >= 7) return "danger";
  if (score >= 4) return "warning";
  return "success";
}
function sevLabel(score) {
  if (score >= 7) return "高危";
  if (score >= 4) return "中危";
  return "低危";
}

async function loadReport() {
  if (!taskId.value) return;
  loading.value = true;
  try {
    const res = await getReport(taskId.value);
    report.value = res.data;
  } finally {
    loading.value = false;
  }
}

async function exportCsv() {
  if (!taskId.value) return;
  const res = await exportReportCsv(taskId.value);
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = `report_${taskId.value}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
}

onMounted(() => {
  if (taskId.value) loadReport();
});
</script>

<style scoped>
.report-page { max-width: 1200px; margin: 0 auto; }
.report-page h2 { color: #00ff88; }
.desc { color: #888; margin-bottom: 24px; }
.select-card, .table-card, .summary-card { background: #1a1d23; border-color: #2a2d33; margin-bottom: 24px; }
.stats-row { margin-bottom: 24px; }
.stats-row .el-statistic { background: #1a1d23; padding: 16px; border-radius: 8px; border: 1px solid #2a2d33; }
</style>
