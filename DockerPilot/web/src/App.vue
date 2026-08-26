<template>
  <a-config-provider :locale="zhCN">
    <a-layout style="position: fixed; width: 100vw; height: 100vh; overflow: hidden;">
      <!-- Sidebar -->
      <a-layout-sider v-model:collapsed="collapsed" collapsible theme="dark" style="overflow-y: auto;">
        <div class="logo">
          <span v-if="!collapsed">🐳 DockerPilot</span>
          <span v-else>🐳</span>
        </div>
        <a-menu
          v-model:selectedKeys="selectedKeys"
          theme="dark"
          mode="inline"
          @click="handleMenuClick"
        >
          <a-menu-item key="dashboard">
            <template #icon><DashboardOutlined /></template>
            <span>控制台</span>
          </a-menu-item>
          <a-menu-item key="images">
            <template #icon><PictureOutlined /></template>
            <span>镜像管理</span>
          </a-menu-item>
          <a-menu-item key="projects">
            <template #icon><FolderOutlined /></template>
            <span>项目管理</span>
          </a-menu-item>
          <a-menu-item key="batches">
            <template #icon><RocketOutlined /></template>
            <span>批量组合</span>
          </a-menu-item>
          <a-menu-item key="containers">
            <template #icon><ControlOutlined /></template>
            <span>容器管理</span>
          </a-menu-item>
          <a-menu-item key="logs">
            <template #icon><FileTextOutlined /></template>
            <span>执行日志</span>
          </a-menu-item>
          <a-menu-item key="registries">
            <template #icon><CloudOutlined /></template>
            <span>镜像源配置</span>
          </a-menu-item>
          <a-menu-item key="profiles">
            <template #icon><CodeOutlined /></template>
            <span>路径变量方案</span>
          </a-menu-item>
        </a-menu>
      </a-layout-sider>

      <!-- Content -->
      <a-layout style="overflow-y: auto;">
        <a-layout-header style="background: #fff; padding: 0 24px; position: sticky; top: 0; z-index: 10;">
          <h2 style="margin: 0; line-height: 64px">{{ pageTitle }}</h2>
        </a-layout-header>
        <a-layout-content style="margin: 24px 16px; padding: 24px; background: #fff; min-height: calc(100vh - 64px - 48px);">
          <keep-alive>
            <router-view />
          </keep-alive>
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import {
  DashboardOutlined,
  PictureOutlined,
  FolderOutlined,
  RocketOutlined,
  ControlOutlined,
  CloudOutlined,
  CodeOutlined,
  FileTextOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()

const collapsed = ref(false)
const selectedKeys = ref(['dashboard'])

// Sync selectedKeys with route
const pageTitle = computed(() => {
  const titles = {
    dashboard: '控制台',
    images: '镜像管理',
    projects: '项目管理',
    batches: '批量组合',
    containers: '容器管理',
    logs: '执行日志',
    registries: '镜像源配置',
    profiles: '路径变量方案',
    projectEdit: '项目编辑',
  }
  return titles[route.name] || 'DockerPilot'
})

// Update selectedKeys when route changes
router.afterEach((to) => {
  selectedKeys.value = [to.name]
})

const handleMenuClick = ({ key }) => {
  router.push({ name: key })
}
</script>

<style>
body {
  margin: 0;
}
.logo {
  height: 32px;
  margin: 16px;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  text-align: center;
  line-height: 32px;
}
</style>
