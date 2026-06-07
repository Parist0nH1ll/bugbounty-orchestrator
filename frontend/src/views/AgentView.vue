<template>
  <div class="agent-page">
    <h2>🤖 Agent 指令交互</h2>
    <p class="desc">向 AI Agent 发送自然语言指令，动态调整后续扫描行为</p>

    <el-card class="input-card">
      <el-form>
        <el-form-item label="目标任务">
          <el-input v-model="taskId" placeholder="输入 Task ID" />
        </el-form-item>
        <el-form-item label="指令">
          <el-input
            v-model="prompt"
            type="textarea"
            :rows="4"
            placeholder="例如：忽略所有 Redis 相关的漏洞"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="sendCommand" :loading="sending">
            <el-icon><Promotion /></el-icon> 发送指令
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="response"
        :title="'指令已应用'"
        type="success"
        show-icon
        closable
      >
        <template #default>
          <p>解析出的操作：</p>
          <el-tag v-for="a in response.parsed_actions" :key="a" style="margin: 2px">
            {{ a }}
          </el-tag>
        </template>
      </el-alert>
    </el-card>

    <el-card class="example-card">
      <template #header>示例指令</template>
      <el-row :gutter="12">
        <el-col :span="6" v-for="(ex, i) in examples" :key="i">
          <el-button @click="prompt = ex.prompt" style="width: 100%; height: 100%">
            <small>{{ ex.label }}</small>
          </el-button>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { sendAgentCommand } from "../api";

const taskId = ref("");
const prompt = ref("");
const sending = ref(false);
const response = ref(null);

const examples = [
  { label: "忽略 Redis 漏洞", prompt: "忽略所有 Redis 相关的漏洞" },
  { label: "增加 SQL 注入深度", prompt: "增加 SQL 注入测试深度为 5" },
  { label: "重新分析 + 认证绕过", prompt: "重新分析上次扫描的日志，重点关注认证绕过" },
  { label: "跳过 MySQL", prompt: "忽略 MySQL 相关的漏洞扫描" },
];

async function sendCommand() {
  if (!taskId.value || !prompt.value) return;
  sending.value = true;
  try {
    const res = await sendAgentCommand(taskId.value, prompt.value);
    response.value = res.data;
  } catch (e) {
    response.value = { message: e.response?.data?.detail || e.message };
  } finally {
    sending.value = false;
  }
}
</script>

<style scoped>
.agent-page { max-width: 800px; margin: 0 auto; }
.agent-page h2 { color: #00ff88; }
.desc { color: #888; margin-bottom: 24px; }
.input-card, .example-card { background: #1a1d23; border-color: #2a2d33; margin-bottom: 24px; }
</style>
