<template>
  <div class="dashboard">
    <!-- Docker Status -->
    <a-card title="Docker 状态" style="margin-bottom: 24px">
      <a-result
        v-if="dockerStatus.connected"
        status="success"
        title="Docker 已连接"
        :sub-title="`版本: ${dockerStatus.server_version} | 运行中容器: ${dockerStatus.containers_running} | 镜像数: ${dockerStatus.images}`"
      />
      <a-result
        v-else
        status="warning"
        title="Docker 未连接"
        sub-title="请检查 Docker daemon 是否运行"
      />
    </a-card>

    <!-- Quick Stats -->
    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-card>
          <a-statistic title="镜像数" :value="stats.images" :value-style="{ color: '#1890ff' }">
            <template #prefix><PictureOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="项目数" :value="stats.projects" :value-style="{ color: '#52c41a' }">
            <template #prefix><FolderOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="组合数" :value="stats.batches" :value-style="{ color: '#722ed1' }">
            <template #prefix><RocketOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="运行中容器" :value="stats.containers" :value-style="{ color: '#fa8c16' }">
            <template #prefix><ControlOutlined /></template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- Quick Actions -->
    <a-card title="快捷操作">
      <a-space>
        <a-button type="primary" @click="$router.push('/images')">
          <template #icon><PictureOutlined /></template>
          拉取镜像
        </a-button>
        <a-button @click="$router.push('/projects')">
          <template #icon><FolderOutlined /></template>
          管理项目
        </a-button>
        <a-button @click="$router.push('/batches')">
          <template #icon><RocketOutlined /></template>
          执行组合
        </a-button>
      </a-space>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { dockerAPI, imagesAPI, projectsAPI, batchesAPI, containersAPI } from '../api'
import {
  PictureOutlined,
  FolderOutlined,
  RocketOutlined,
  ControlOutlined,
} from '@ant-design/icons-vue'

const dockerStatus = ref({ connected: false })
const stats = ref({
  images: 0,
  projects: 0,
  batches: 0,
  containers: 0,
})

onMounted(async () => {
  try {
    const [health, images, projects, batches, containers] = await Promise.all([
      dockerAPI.health(),
      imagesAPI.list(),
      projectsAPI.list(),
      batchesAPI.list(),
      containersAPI.list(),
    ])
    dockerStatus.value = health.data.data
    stats.value = {
      images: images.data.data.length,
      projects: projects.data.data.length,
      batches: batches.data.data.length,
      containers: containers.data.data.length,
    }
  } catch (e) {
    console.error('Failed to load dashboard data:', e)
  }
})
</script>
