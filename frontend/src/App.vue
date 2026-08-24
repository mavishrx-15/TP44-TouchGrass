<script setup lang="ts"></script>

<template>
  <main class="shell">
    <header class="bar">
      <h1>TouchGrass</h1>
      <nav><RouterLink to="/">Home</RouterLink></nav>
    </header>
    <RouterView />
  </main>
</template>

<style>
:root {
  font-family: system-ui, sans-serif;
  color: #1c2b1f;
  background: #fbfaf5;
}
body {
  margin: 0;
}
.shell {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px;
}
.bar {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  border-bottom: 1px solid #d8ded4;
  padding-bottom: 12px;
}
.bar h1 {
  font-size: 20px;
  margin: 0;
}
a {
  color: #2f6b3f;
}
</style>
