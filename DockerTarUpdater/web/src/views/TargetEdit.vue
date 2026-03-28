<template>
  <div class="target-edit">
    <div class="toolbar">
      <h2>{{ isEdit ? 'Edit Target' : 'Add Target' }}</h2>
      <el-button @click="$router.push('/targets')">Back</el-button>
    </div>

    <el-card>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="140px">
        <el-form-item label="Container Name" prop="name">
          <el-input v-model="form.name" placeholder="e.g., my-app" />
        </el-form-item>

        <el-form-item label="Tar URL" prop="tar_url">
          <el-input v-model="form.tar_url" placeholder="https://example.com/image.tar" />
        </el-form-item>

        <el-form-item label="Image Tag" prop="image_tag">
          <el-input v-model="form.image_tag" placeholder="myrepo/myapp:latest" />
        </el-form-item>

        <el-form-item label="Schedule Type" prop="schedule_type">
          <el-radio-group v-model="form.schedule_type">
            <el-radio label="interval">Interval</el-radio>
            <el-radio label="cron">Cron</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="Schedule" prop="schedule_value">
          <el-input v-if="form.schedule_type === 'interval'" v-model="form.schedule_value" placeholder="Minutes, e.g., 360">
            <template #append>minutes</template>
          </el-input>
          <el-input v-else v-model="form.schedule_value" placeholder="0 2 * * *">
            <template #append>Cron Expression</template>
          </el-input>
        </el-form-item>

        <el-form-item label="Enabled">
          <el-switch v-model="form.enabled" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submit" :loading="saving">Save</el-button>
          <el-button @click="$router.push('/targets')">Cancel</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { targetsAPI } from '../api'
import { ElMessage } from 'element-plus'

export default {
  name: 'TargetEdit',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const formRef = ref(null)
    const saving = ref(false)

    const isEdit = computed(() => !!route.params.id)

    const form = ref({
      name: '',
      tar_url: '',
      image_tag: '',
      schedule_type: 'interval',
      schedule_value: '360',
      enabled: true
    })

    const rules = {
      name: [{ required: true, message: 'Please enter container name', trigger: 'blur' }],
      tar_url: [{ required: true, message: 'Please enter Tar URL', trigger: 'blur' }],
      image_tag: [{ required: true, message: 'Please enter Image Tag', trigger: 'blur' }],
      schedule_value: [{ required: true, message: 'Please enter schedule value', trigger: 'blur' }]
    }

    const loadTarget = async () => {
      if (!route.params.id) return
      try {
        const res = await targetsAPI.get(route.params.id)
        form.value = {
          name: res.data.name,
          tar_url: res.data.tar_url,
          image_tag: res.data.image_tag,
          schedule_type: res.data.schedule_type,
          schedule_value: res.data.schedule_value,
          enabled: !!res.data.enabled
        }
      } catch (e) {
        ElMessage.error('Failed to load target')
      }
    }

    const submit = async () => {
      try {
        await formRef.value.validate()
        saving.value = true
        if (isEdit.value) {
          await targetsAPI.update(route.params.id, form.value)
          ElMessage.success('Updated')
        } else {
          await targetsAPI.create(form.value)
          ElMessage.success('Created')
        }
        router.push('/targets')
      } catch (e) {
        if (e !== false) ElMessage.error('Failed to save')
      } finally {
        saving.value = false
      }
    }

    onMounted(() => {
      loadTarget()
    })

    return { form, rules, formRef, saving, isEdit, submit }
  }
}
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.toolbar h2 { margin: 0; }
</style>
