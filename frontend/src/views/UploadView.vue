<template>
  <div class="upload-page">
    <h2>📤 上传目标域名</h2>
    <p class="desc">上传文本文件（每行一个域名），启动全自动漏洞挖掘流水线</p>

    <el-card class="upload-card">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        accept=".txt"
        :limit="1"
      >
        <el-icon class="el-icon--upload" :size="48"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处或 <em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 .txt 文件，每行一个根域名</div>
        </template>
      </el-upload>

      <div v-if="previewDomains.length" class="preview-section">
        <el-tag type="info">检测到 {{ previewDomains.length }} 个域名</el-tag>
        <el-input
          type="textarea"
          :rows="8"
          :model-value="previewDomains.slice(0, 20).join('\n') + (previewDomains.length > 20 ? '\n...' : '')"
          readonly
        />
      </div>

      <el-divider>或直接输入</el-divider>

      <el-input
        v-model="manualDomains"
        type="textarea"
        :rows="5"
        placeholder="example.com&#10;test.myapp.cn&#10;api.internal.net"
      />

      <div class="action-bar">
        <el-button type="primary" size="large" @click="launchPipeline" :loading="launching">
          <el-icon><Rocket /></el-icon> 启动扫描流水线
        </el-button>
      </div>

      <el-alert
        v-if="result"
        :title="result.message"
        :type="result.task_id ? 'success' : 'error'"
        show-icon
        closable
      />
    </el-card>

    <el-card class="pipeline-card">
      <template #header>流水线流程</template>
      <el-steps :active="0" align-center>
        <el-step title="子域名发现" description="subfinder" />
        <el-step title="DNS 解析" description="A/AAAA/CNAME" />
        <el-step title="资产筛选" description="规则匹配" />
        <el-step title="Strix 扫描" description="漏洞探测" />
        <el-step title="AI 分析" description="LLM 智能分析" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { uploadDomains, uploadDomainsText } from "../api";

const uploadRef = ref(null);
const fileList = ref([]);
const previewDomains = ref([]);
const manualDomains = ref("");
const launching = ref(false);
const result = ref(null);

function handleFileChange(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const text = e.target.result;
    previewDomains.value = text
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith("#"));
  };
  reader.readAsText(file.raw);
  fileList.value = [file];
}

async function launchPipeline() {
  launching.value = true;
  result.value = null;
  try {
    let res;
    if (previewDomains.value.length) {
      const file = fileList.value[0]?.raw;
      res = await uploadDomains(file);
    } else if (manualDomains.value.trim()) {
      res = await uploadDomainsText(manualDomains.value);
    } else {
      result.value = { message: "请上传文件或输入域名" };
      return;
    }
    result.value = res.data;
  } catch (e) {
    result.value = { message: e.response?.data?.detail || e.message };
  } finally {
    launching.value = false;
  }
}
</script>

<style scoped>
.upload-page { max-width: 800px; margin: 0 auto; }
.upload-page h2 { color: #00ff88; margin-bottom: 8px; }
.desc { color: #888; margin-bottom: 24px; }
.upload-card { margin-bottom: 24px; background: #1a1d23; border-color: #2a2d33; }
.preview-section { margin-top: 16px; }
.preview-section > * { margin-bottom: 8px; }
.action-bar { margin-top: 20px; text-align: center; }
.pipeline-card { background: #1a1d23; border-color: #2a2d33; }
</style>
