<template>
  <header class="page-head rise">
    <div class="page-head__main">
      <div class="eyebrow">{{ kicker }}</div>
      <h1 class="page-head__title">{{ title }}</h1>
      <p v-if="description" class="page-head__desc">{{ description }}</p>
    </div>
    <div class="page-head__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ title: string; kicker: string; description?: string }>()
</script>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 16px;
}
.page-head__title {
  font-size: clamp(19px, 2.1vw, 26px);
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-top: 3px;
}
.page-head__desc {
  font-size: 12px;
  color: var(--ink-faint);
  margin-top: 5px;
  max-width: 62ch;
}
.page-head__actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}
@media (max-width: 860px) {
  .page-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .page-head__actions {
    justify-content: flex-start;
  }
}
</style>
