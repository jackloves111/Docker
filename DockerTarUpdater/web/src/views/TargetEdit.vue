<template>
  <div class="target-edit">
    <div class="toolbar">
      <h2>{{ isEdit ? '编辑目标' : '添加目标' }}</h2>
      <el-button @click="$router.push('/targets')">返回</el-button>
    </div>

    <el-alert
      v-if="dockerConnected === false"
      title="Docker 连接失败"
      type="warning"
      description="无法连接到 Docker daemon，请检查容器是否正确映射了 /var/run/docker.sock"
      show-icon
      :closable="false"
      style="margin-bottom: 20px;"
    />

    <el-card>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="140px">
        <el-form-item label="Tar URL" prop="tar_url">
          <el-input v-model="form.tar_url" placeholder="https://example.com/image.tar" />
        </el-form-item>

        <el-form-item label="链接类型" prop="url_type">
          <el-radio-group v-model="form.url_type">
            <el-radio label="direct">直链</el-radio>
            <el-radio label="api">API</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="镜像标签" prop="image_tag">
          <el-input v-model="form.image_tag" placeholder="myrepo/myapp:latest" />
        </el-form-item>

        <el-form-item label="调度类型" prop="schedule_type">
          <el-radio-group v-model="form.schedule_type">
            <el-radio label="interval">间隔</el-radio>
            <el-radio label="cron">Cron</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="调度值" prop="schedule_value">
          <el-input v-if="form.schedule_type === 'interval'" v-model="form.schedule_value" placeholder="分钟数, 例如: 360">
            <template #append>分钟</template>
          </el-input>
          <el-input v-else v-model="form.schedule_value" placeholder="0 2 * * *">
            <template #append>Cron 表达式</template>
          </el-input>
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submit" :loading="saving">保存</el-button>
          <el-button @click="$router.push('/targets')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { targetsAPI, dockerAPI } from '../api'
import { ElMessage } from 'element-plus'

export default {
  name: 'TargetEdit',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const formRef = ref(null)
    const saving = ref(false)
    const dockerConnected = ref(null)

    const isEdit = computed(() => !!route.params.id)

    const form = ref({
      tar_url: '',
      url_type: 'direct',
      image_tag: '',
      schedule_type: 'interval',
      schedule_value: '360',
      enabled: true
    })

    const rules = {
      tar_url: [{ required: true, message: '请输入 Tar URL', trigger: 'blur' }],
      image_tag: [{ required: true, message: '请输入镜像标签', trigger: 'blur' }],
      schedule_value: [{ required: true, message: '请输入调度值', trigger: 'blur' }]
    }

    const loadTarget = async () => {
      if (!route.params.id) return
      try {
        const res = await targetsAPI.get(route.params.id)
        form.value = {
          tar_url: res.data.tar_url,
          url_type: res.data.url_type || 'direct',
          image_tag: res.data.image_tag,
          schedule_type: res.data.schedule_type,
          schedule_value: res.data.schedule_value,
          enabled: !!res.data.enabled
        }
      } catch (e) {
        ElMessage.error('加载目标失败')
      }
    }

    const submit = async () => {
      try {
        await formRef.value.validate()
        saving.value = true
        if (isEdit.value) {
          await targetsAPI.update(route.params.id, form.value)
          ElMessage.success('更新成功')
        } else {
          await targetsAPI.create(form.value)
          ElMessage.success('创建成功')
        }
        router.push('/targets')
      } catch (e) {
        if (e !== false) ElMessage.error('保存失败')
      } finally {
        saving.value = false
      }
    }

    const checkDockerHealth = async () => {
      try {
        const res = await dockerAPI.health()
        dockerConnected.value = res.data.connected
      } catch (e) {
        dockerConnected.value = false
      }
    }

    onMounted(() => {
      loadTarget()
      checkDockerHealth()
    })

    return { form, rules, formRef, saving, isEdit, dockerConnected, submit }
  }
}
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.toolbar h2 { margin: 0; }
</style>
