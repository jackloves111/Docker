<template>
  <div class="env-editor">
    <el-card shadow="hover">
      <div class="editor-header">
        <div class="header-left">
          <el-select v-model="currentPath" placeholder="选择文件" @change="loadEnv" :disabled="loading">
            <el-option v-for="f in files" :key="f" :label="f" :value="f" />
          </el-select>
        </div>
        <div class="header-right">
          <el-switch v-model="autoUpdateDesired" active-text="自动更新" inactive-text="" />
          <el-switch v-model="advancedMode" active-text="高级" inactive-text="" />
        </div>
      </div>

      <div class="action-bar">
        <el-button type="primary" @click="saveEnv" :loading="saving">保存</el-button>
        <el-button @click="reloadEnv">重新加载</el-button>
        <span class="status-text" :class="statusClass">{{ status }}</span>
      </div>

      <div class="hint-text" v-if="hint">{{ hint }}</div>

      <el-table :data="nonAdvancedEntries" border class="env-table" v-loading="loading">
        <el-table-column label="Key" width="180" min-width="180">
          <template #default="{ row }">
            <code class="key-code">{{ row.key }}</code>
          </template>
        </el-table-column>
        <el-table-column label="说明" min-width="150">
          <template #default="{ row }">
            <span v-if="isImportant(row.key)" class="badge bg-danger me-1">重要</span>
            <span :class="isImportant(row.key) ? 'text-danger' : 'text-secondary'">{{ row.desc }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Value" min-width="300">
          <template #default="{ row }">
            <template v-if="isAutoUpdateKey(row.key)">
              <span class="text-secondary">{{ row.value }}</span>
            </template>
            <template v-else-if="specialOptions[row.key]">
              <div class="value-select-input">
                <el-select v-model="row.editingValue" @change="onSpecialChange(row)">
                  <el-option v-for="opt in specialOptions[row.key]" :key="opt.val" :label="opt.label" :value="opt.val" />
                  <el-option label="自定义" value="__custom__" />
                </el-select>
                <el-input v-if="row.showCustomInput" v-model="row.customValue" class="custom-input" placeholder="自定义值" />
              </div>
            </template>
            <template v-else-if="isBoolValue(row.value)">
              <el-switch v-model="row.boolValue" />
            </template>
            <template v-else>
              <el-input v-model="row.editingValue" />
            </template>
          </template>
        </el-table-column>
      </el-table>

      <div class="section-divider" v-if="advancedEntries.length">
        <span class="divider-text">高级配置</span>
      </div>

      <el-table :data="advancedEntries" border class="env-table" v-loading="loading">
        <el-table-column label="Key" width="180" min-width="180">
          <template #default="{ row }">
            <code class="key-code">{{ row.key }}</code>
          </template>
        </el-table-column>
        <el-table-column label="说明" min-width="150">
          <template #default="{ row }">
            <span :class="isImportant(row.key) ? 'text-danger' : 'text-secondary'">{{ row.desc }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Value" min-width="300">
          <template #default="{ row }">
            <template v-if="isAutoUpdateKey(row.key)">
              <span class="text-secondary">{{ row.value }}</span>
            </template>
            <template v-else-if="specialOptions[row.key]">
              <div class="value-select-input">
                <el-select v-model="row.editingValue" @change="onSpecialChange(row)" :disabled="!advancedMode">
                  <el-option v-for="opt in specialOptions[row.key]" :key="opt.val" :label="opt.label" :value="opt.val" />
                  <el-option label="自定义" value="__custom__" />
                </el-select>
                <el-input v-if="row.showCustomInput" v-model="row.customValue" class="custom-input" placeholder="自定义值" />
              </div>
            </template>
            <template v-else-if="isBoolValue(row.value)">
              <el-switch v-model="row.boolValue" :disabled="!advancedMode" />
            </template>
            <template v-else>
              <el-input v-model="row.editingValue" :disabled="!advancedMode" />
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showWarning" title="⚠️ 警告" width="400px" :close-on-click-modal="false" :show-close="false">
      <div class="warning-content">
        警告：请勿修改不熟悉的配置【请勿开启高级配置】，否则可能导致系统错误或数据损失，相关后果需自行承担。
      </div>
      <template #footer>
        <el-button type="danger" @click="showWarning = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { envEditorAPI } from '../api'

const IMPORTANT_KEYS = new Set(['GITHUB_PROXY', 'PIP_PROXY'])
const AUTO_UPDATE_KEYS = new Set(['MOVIEPILOT_AUTO_UPDATE', 'AUTO_UPDATE_RESOURCE'])
const ADVANCED_KEYS = new Set([
  'API_TOKEN', 'SEARCH_MULTIPLE_NAME', 'COOKIECLOUD_HOST', 'DEBUG',
  'SUBSCRIBE_SEARCH', 'LOCAL_EXISTS_SEARCH', 'COOKIECLOUD_KEY',
  'COOKIECLOUD_PASSWORD', 'ANIME_GENREIDS', 'SITEDATA_REFRESH_INTERVAL',
  'SITE_MESSAGE', 'COOKIECLOUD_ENABLE_LOCAL'
])

const SPECIAL_OPTIONS = {
  'SEARCH_SOURCE': [
    { val: 'themoviedb', label: 'themoviedb（TMDB）' },
    { val: 'douban', label: 'douban（豆瓣-不建议）' },
    { val: 'bangumi', label: 'bangumi（bangumi-不建议）' }
  ],
  'WALLPAPER': [
    { val: 'tmdb', label: 'tmdb（TMDB）' },
    { val: 'bing', label: 'bing（必应）' },
    { val: 'mediaserver', label: 'mediaserver（媒体服务器）' }
  ],
  'TMDB_IMAGE_DOMAIN': [
    { val: 'image.tmdb.org', label: 'image.tmdb.org（TMDB）' },
    { val: 'tmdb.nastool.work', label: 'tmdb.nastool.work（代理-不建议）' }
  ],
  'TMDB_API_DOMAIN': [
    { val: 'api.themoviedb.org', label: 'api.themoviedb.org（TMDB）' },
    { val: 'api.tmdb.org', label: 'api.tmdb.org（TMDB）' },
    { val: 'api.nastool.work', label: 'api.nastool.work（代理-不建议）' }
  ],
  'GITHUB_PROXY': [
    { val: 'https://ghfast.top/', label: 'https://ghfast.top/' }
  ],
  'PIP_PROXY': [
    { val: 'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple', label: 'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple' },
    { val: 'https://pypi.mirrors.ustc.edu.cn/simple', label: 'https://pypi.mirrors.ustc.edu.cn/simple' },
    { val: 'https://mirrors.pku.edu.cn/pypi/web/simple', label: 'https://mirrors.pku.edu.cn/pypi/web/simple' },
    { val: 'https://mirrors.aliyun.com/pypi/simple', label: 'https://mirrors.aliyun.com/pypi/simple' },
    { val: 'https://mirrors.cloud.tencent.com/pypi/simple', label: 'https://mirrors.cloud.tencent.com/pypi/simple' },
    { val: 'https://mirrors.163.com/pypi/simple', label: 'https://mirrors.163.com/pypi/simple' },
    { val: 'https://pypi.doubanio.com/simple', label: 'https://pypi.doubanio.com/simple' },
    { val: 'https://mirrors.hust.edu.cn/pypi/web/simple', label: 'https://mirrors.hust.edu.cn/pypi/web/simple' },
    { val: 'https://mirrors.bfsu.edu.cn/pypi/web/simple', label: 'https://mirrors.bfsu.edu.cn/pypi/web/simple' }
  ]
}

export default {
  name: 'EnvEditor',
  setup() {
    const files = ref([])
    const currentPath = ref('')
    const entries = ref([])
    const loading = ref(false)
    const saving = ref(false)
    const status = ref('')
    const hint = ref('')
    const advancedMode = ref(false)
    const autoUpdateDesired = ref(false)
    const showWarning = ref(true)
    const specialOptions = SPECIAL_OPTIONS

    const statusClass = computed(() => {
      return status.value && status.value.includes('失败') ? 'text-danger' : 'text-secondary'
    })

    const nonAdvancedEntries = computed(() => {
      return entries.value.filter(e => !isAdvanced(e.key))
    })

    const advancedEntries = computed(() => {
      return entries.value.filter(e => isAdvanced(e.key))
    })

    const isImportant = (key) => IMPORTANT_KEYS.has(key)
    const isAutoUpdateKey = (key) => AUTO_UPDATE_KEYS.has(key)
    const isAdvanced = (key) => ADVANCED_KEYS.has(key)
    const isBoolValue = (val) => {
      const lower = (val || '').toLowerCase()
      return lower === 'true' || lower === 'false'
    }

    const computeAutoUpdateMode = () => {
      const e1 = entries.value.find(e => e.key === 'MOVIEPILOT_AUTO_UPDATE')
      const e2 = entries.value.find(e => e.key === 'AUTO_UPDATE_RESOURCE')
      if (!e1 && !e2) return 'missing'
      const v1 = (e1?.value || '').toLowerCase()
      const v2 = (e2?.value || '').toLowerCase()
      const on1 = v1 === 'release'
      const off1 = v1 === 'false'
      const on2 = v2 === 'true'
      const off2 = v2 === 'false'
      if (e1 && e2 && on1 && on2) return 'on'
      if (e1 && e2 && off1 && off2) return 'off'
      return 'mixed'
    }

    const loadFiles = async () => {
      loading.value = true
      status.value = '加载文件列表...'
      try {
        const res = await envEditorAPI.files()
        files.value = res.files || []
        if (res.rootExists === false) {
          hint.value = `映射目录不存在：${res.root}。请启动容器时挂载目录到 ${res.root}`
          status.value = ''
          return
        }
        if (files.value.length) {
          currentPath.value = files.value[0]
          await loadEnv()
        } else {
          hint.value = `未找到 app.env 文件（会递归查找子目录）`
          status.value = ''
        }
      } catch (e) {
        status.value = '加载失败'
        console.error(e)
      } finally {
        loading.value = false
      }
    }

    const loadEnv = async () => {
      if (!currentPath.value) return
      loading.value = true
      status.value = '加载中...'
      try {
        const res = await envEditorAPI.env(currentPath.value)
        entries.value = (res.entries || []).map(e => {
          const entry = {
            ...e,
            editingValue: e.value,
            boolValue: e.value === 'True' || e.value === 'true',
            showCustomInput: false,
            customValue: ''
          }
          if (SPECIAL_OPTIONS[e.key]) {
            const matched = SPECIAL_OPTIONS[e.key].find(opt => opt.val === e.value)
            entry.showCustomInput = !matched
            entry.customValue = matched ? '' : e.value
          }
          return entry
        })
        const mode = computeAutoUpdateMode()
        autoUpdateDesired.value = mode === 'on'
        hint.value = `当前文件：${currentPath.value}，共 ${entries.value.length} 条变量`
        status.value = ''
      } catch (e) {
        status.value = '加载失败'
        console.error(e)
      } finally {
        loading.value = false
      }
    }

    const onSpecialChange = (row) => {
      if (row.editingValue === '__custom__') {
        row.showCustomInput = true
        row.customValue = ''
      } else {
        row.showCustomInput = false
        row.customValue = ''
        row.editingValue = row.editingValue
      }
    }

    const saveEnv = async () => {
      if (!currentPath.value) return
      saving.value = true
      status.value = '保存中...'
      try {
        const payloadEntries = entries.value.map(e => ({
          id: e.id,
          value: e.value === 'True' || e.value === 'true' ? (e.boolValue ? 'True' : 'False') : e.editingValue,
          quote: e.quote || 'none'
        }))
        const upserts = autoUpdateDesired.value
          ? [
              { key: 'MOVIEPILOT_AUTO_UPDATE', value: 'release', quote: 'single' },
              { key: 'AUTO_UPDATE_RESOURCE', value: 'true', quote: 'single' }
            ]
          : [
              { key: 'MOVIEPILOT_AUTO_UPDATE', value: 'false', quote: 'single' },
              { key: 'AUTO_UPDATE_RESOURCE', value: 'false', quote: 'single' }
            ]
        await envEditorAPI.save(currentPath.value, payloadEntries, upserts)
        status.value = '已保存'
        ElMessage.success('保存成功')
        await loadEnv()
        setTimeout(() => { status.value = '' }, 1200)
      } catch (e) {
        status.value = '保存失败'
        ElMessage.error('保存失败')
      } finally {
        saving.value = false
      }
    }

    const reloadEnv = async () => {
      await loadEnv()
    }

    onMounted(() => {
      loadFiles()
    })

    return {
      files,
      currentPath,
      entries,
      loading,
      saving,
      status,
      statusClass,
      hint,
      advancedMode,
      autoUpdateDesired,
      showWarning,
      specialOptions,
      nonAdvancedEntries,
      advancedEntries,
      isImportant,
      isAutoUpdateKey,
      isAdvanced,
      isBoolValue,
      onSpecialChange,
      loadEnv,
      saveEnv,
      reloadEnv
    }
  }
}
</script>

<style scoped>
.env-editor {
  padding: 0;
}
.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.header-left {
  flex: 1;
  min-width: 200px;
}
.header-right {
  display: flex;
  gap: 20px;
  align-items: center;
}
.action-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}
.status-text {
  margin-left: auto;
  font-size: 13px;
}
.text-danger { color: #f56c6c; }
.text-secondary { color: #909399; }
.hint-text {
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
}
.env-table {
  width: 100%;
}
.key-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: #409eff;
}
.badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}
.bg-danger {
  background-color: #f56c6c;
  color: white;
}
.text-danger {
  color: #f56c6c;
  font-weight: 600;
}
.value-select-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.custom-input {
  max-width: 300px;
}
.section-divider {
  display: flex;
  align-items: center;
  margin: 20px 0 12px;
  gap: 12px;
}
.section-divider::before,
.section-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #dcdfe6;
}
.divider-text {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .editor-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .header-right {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>