<template>
  <div>
    <a-page-header title="编辑部署" @back="$router.back()" style="margin-bottom: 24px" />
    <a-spin :spinning="loading">
      <a-form :model="form" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="部署名称" required>
              <a-input v-model:value="form.name" placeholder="My App" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="类型" required>
              <a-radio-group v-model:value="form.type" :disabled="true">
                <a-radio value="run">Docker Run</a-radio>
                <a-radio value="compose">Docker Compose</a-radio>
              </a-radio-group>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item v-if="form.type === 'run'" label="启动命令" required>
          <a-textarea v-model:value="form.command" :rows="6" placeholder="docker run -d --name myapp -p 80:80 nginx:latest" style="font-family: monospace" />
        </a-form-item>
        <a-form-item v-if="form.type === 'compose'" label="Compose 内容" required>
          <a-textarea v-model:value="form.compose_content" :rows="20" style="font-family: monospace" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="form.description" placeholder="部署描述" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="handleSave" :loading="saving">保存</a-button>
          <a-button style="margin-left: 8px" @click="$router.back()">取消</a-button>
        </a-form-item>
      </a-form>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import { message } from "ant-design-vue"
import { projectsAPI } from "../api"

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const projectId = ref(route.params.id)
const form = ref({ name: "", type: "run", command: "", compose_content: "", description: "" })

onMounted(async () => {
  loading.value = true
  try {
    const res = await projectsAPI.get(projectId.value)
    const p = res.data.data
    form.value = { name: p.name, type: p.type, command: p.command || "", compose_content: p.compose_content || "", description: p.description || "" }
  } catch (e) { message.error("加载失败"); router.back() }
  loading.value = false
})

const handleSave = async () => {
  if (!form.value.name) { message.warning("请输入名称"); return }
  saving.value = true
  try { await projectsAPI.update(projectId.value, form.value); message.success("保存成功"); router.back() } catch (e) { message.error("保存失败") }
  saving.value = false
}
</script>
