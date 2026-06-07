<template>
  <div class="tasks-page">
    <h2>📋 任务管理</h2>
    <p class="desc">查看所有任务的执行状态和进度，支持取消运行中的任务</p>

    <el-card class="table-card">
      <el-table :data="tasks" style="width: 100%" v-loading="loading" empty-text="暂无任务记录">
        <el-table-column prop="id" label="Task ID" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="100">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="6" />
          </template>
        </el-table-column>
        <el-table-column prop="current_step" label="当前步骤" width="150" />
        <el-table-column prop="domains_count" label="域名" width="70" />
        <el-table-column prop="subdomains_count" label="子域名" width="80" />
        <el-table-column prop="assets_count" label="资产" width="70" />
        <el-table-column prop="vulnerabilities_count" label="漏洞" width="70" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="danger"
              @click="cancel(row.id)"
            >取消</el-button>
            <el-button size="small" @click="$router.push(`/reports?task_id=${row.id}`)">
              查看报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { getTasks, cancelTask } from "../api";

const tasks = ref([]);
const loading = ref(false);

function statusType(status) {
  const map = { running: "warning", completed: "success", failed: "danger", cancelled: "info" };
  return map[status] || "info";
}

async function loadTasks() {
  loading.value = true;
  try {
    const res = await getTasks();
    tasks.value = res.data.tasks || [];
  } finally {
    loading.value = false;
  }
}

async function cancel(id) {
  await cancelTask(id).catch(() => {});
  loadTasks();
}

onMounted(loadTasks);
</script>

<style scoped>
.tasks-page { max-width: 1200px; margin: 0 auto; }
.tasks-page h2 { color: #00ff88; }
.desc { color: #888; margin-bottom: 24px; }
.table-card { background: #1a1d23; border-color: #2a2d33; }
</style>
