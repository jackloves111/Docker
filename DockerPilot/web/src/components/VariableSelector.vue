<template>
  <div>
    <a-form layout="vertical">
      <a-form-item label="选择路径变量方案">
        <a-select
          v-model:value="selectedProfileId"
          placeholder="选择方案"
          allowClear
          @change="handleProfileChange"
        >
          <a-select-option v-for="p in profiles" :key="p.id" :value="p.id">
            {{ p.name }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="自定义变量（覆盖方案值）">
        <div v-for="(v, idx) in overrides" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px;">
          <a-input
            v-model:value="v.name"
            placeholder="变量名"
            style="width: 150px"
          />
          <a-input
            v-model:value="v.value"
            placeholder="值"
            style="flex: 1"
          />
          <a-button danger @click="removeOverride(idx)">删除</a-button>
        </div>
        <a-button type="dashed" block @click="addOverride">
          + 添加变量
        </a-button>
      </a-form-item>
    </a-form>

    <!-- 变量检查结果 -->
    <a-divider v-if="varCheck.length > 0">变量检查</a-divider>
    <div v-for="(item, idx) in varCheck" :key="item.name" style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
      <a-tag :color="item.status === 'ok' ? 'success' : item.status === 'override' ? 'processing' : 'warning'">
        {{ item.status === 'ok' ? '✅' : item.status === 'override' ? '🔧' : '⚠️' }}
      </a-tag>
      <span style="font-family: monospace; min-width: 120px;">{{ item.name }}</span>
      <a-input
        v-if="item.status === 'missing'"
        v-model:value="item.inputValue"
        :placeholder="`请输入 ${item.name} 的值`"
        style="flex: 1"
        @input="handleVarInput(idx)"
      />
      <span v-else style="color: #666; flex: 1;">= {{ item.value }}</span>
    </div>

    <a-alert
      v-if="varCheck.some(v => v.status === 'missing' && !v.inputValue)"
      type="warning"
      showIcon
      style="margin-top: 12px"
    >
      <template #message>
        有变量未填写，执行将失败
      </template>
      <template #description>
        请在上方输入框中填写所有 ⚠️ 标记的变量值。
      </template>
    </a-alert>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { profilesAPI } from '../api'

const props = defineProps({
  // Required variables extracted from command/compose
  requiredVars: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:profileId', 'update:overrides', 'update:valid'])

const profiles = ref([])
const selectedProfileId = ref(null)
const overrides = ref([])
const varCheck = ref([])

// Load profiles
const loadProfiles = async () => {
  try {
    const res = await profilesAPI.list()
    profiles.value = res.data.data || []
  } catch (e) {
    console.error('Failed to load profiles:', e)
  }
}

// Handle profile selection change
const handleProfileChange = () => {
  checkVariables()
  emit('update:profileId', selectedProfileId.value)
}

// Add custom override
const addOverride = () => {
  overrides.value.push({ name: '', value: '' })
}

// Remove custom override
const removeOverride = (idx) => {
  overrides.value.splice(idx, 1)
  checkVariables()
}

// Handle variable input in check area
const handleVarInput = (idx) => {
  const item = varCheck.value[idx]
  if (!item) return

  // Sync to overrides
  const existingIdx = overrides.value.findIndex(o => o.name === item.name)
  if (item.inputValue) {
    if (existingIdx >= 0) {
      overrides.value[existingIdx].value = item.inputValue
    } else {
      overrides.value.push({ name: item.name, value: item.inputValue })
    }
    item.status = 'override'
    item.value = item.inputValue
  } else {
    if (existingIdx >= 0) {
      overrides.value.splice(existingIdx, 1)
    }
    item.status = 'missing'
    item.value = ''
  }
  emitUpdate()
}

// Check variables
const checkVariables = () => {
  // Get profile variables
  const profileVars = {}
  if (selectedProfileId.value) {
    const profile = profiles.value.find(p => p.id === selectedProfileId.value)
    if (profile && profile.variables) {
      profile.variables.forEach(v => { profileVars[v.var_name] = v.var_value })
    }
  }

  // Get override variables
  const overrideVars = {}
  overrides.value.forEach(v => {
    if (v.name) overrideVars[v.name] = v.value
  })

  // Build check result
  varCheck.value = props.requiredVars.map(name => {
    const value = overrideVars[name] || profileVars[name]
    if (overrideVars[name] !== undefined) {
      return { name, value: overrideVars[name], status: 'override', inputValue: overrideVars[name] }
    } else if (profileVars[name] !== undefined) {
      return { name, value: profileVars[name], status: 'ok', inputValue: '' }
    } else {
      return { name, value: '', status: 'missing', inputValue: '' }
    }
  })

  emitUpdate()
}

// Emit update event
const emitUpdate = () => {
  const overridesObj = {}
  overrides.value.forEach(v => {
    if (v.name) overridesObj[v.name] = v.value
  })
  emit('update:overrides', overridesObj)
  emit('update:valid', !varCheck.value.some(v => v.status === 'missing' && !v.inputValue))
}

// Watch overrides changes
watch(overrides, () => {
  checkVariables()
}, { deep: true })

// Watch requiredVars changes
watch(() => props.requiredVars, () => {
  checkVariables()
}, { deep: true })

onMounted(() => {
  loadProfiles().then(() => {
    checkVariables()
  })
})
</script>
