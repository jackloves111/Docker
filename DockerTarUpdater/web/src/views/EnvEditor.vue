<template>
  <div class="env-editor-container">
    <iframe src="/env_editor/" frameborder="0" width="100%" height="100%"></iframe>
  </div>
</template>

<script>
export default {
  name: 'EnvEditor'
}
</script>

<style scoped>
.env-editor-container {
  width: 100%;
  height: calc(100vh - 60px); /* 减去顶部 header 的高度 */
  overflow: hidden;
}

iframe {
  border: none;
  display: block;
}
</style>
