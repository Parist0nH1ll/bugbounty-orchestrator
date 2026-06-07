<template>
  <div class="rules-page">
    <h2>📏 筛选规则配置</h2>
    <p class="desc">配置域名筛选规则，匹配到的域名标记为重点资产</p>

    <el-card class="table-card">
      <el-table :data="rules" v-loading="loading" empty-text="暂无规则">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" width="180" />
        <el-table-column prop="rule_type" label="类型" width="80" />
        <el-table-column prop="pattern" label="模式" />
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column label="启用" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="toggleRule(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="removeRule(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="add-card">
      <template #header>添加规则</template>
      <el-form :inline="true">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="keyword:admin" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.rule_type">
            <el-option label="关键词" value="keyword" />
            <el-option label="正则" value="regex" />
          </el-select>
        </el-form-item>
        <el-form-item label="模式">
          <el-input v-model="form.pattern" placeholder="admin" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="1" :max="10" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="addRule">添加</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { getRules, createRule, updateRule, deleteRule } from "../api";

const rules = ref([]);
const loading = ref(false);
const form = reactive({ name: "", rule_type: "keyword", pattern: "", priority: 1 });

async function loadRules() {
  loading.value = true;
  try {
    const res = await getRules();
    rules.value = res.data;
  } finally {
    loading.value = false;
  }
}

async function addRule() {
  if (!form.name || !form.pattern) return;
  await createRule({ ...form, enabled: true });
  form.name = "";
  form.pattern = "";
  loadRules();
}

async function toggleRule(rule) {
  await updateRule(rule.id, { enabled: !rule.enabled });
  loadRules();
}

async function removeRule(id) {
  await deleteRule(id);
  loadRules();
}

onMounted(loadRules);
</script>

<style scoped>
.rules-page { max-width: 1000px; margin: 0 auto; }
.rules-page h2 { color: #00ff88; }
.desc { color: #888; margin-bottom: 24px; }
.table-card, .add-card { background: #1a1d23; border-color: #2a2d33; margin-bottom: 24px; }
</style>
