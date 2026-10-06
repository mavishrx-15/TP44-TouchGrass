<template>
  <!-- The rolling hills along the bottom of Sprout's scenes (prototype's backdrop). -->
  <svg class="hills" viewBox="0 0 1440 170" preserveAspectRatio="none" aria-hidden="true">
    <path fill="#d3e7bf" d="M0 88 Q90 30 180 78 T360 84 T540 92 T720 76 T900 90 T1080 66 T1260 84 T1440 58 V170 H0Z" />
    <path fill="#abd08a" d="M0 118 Q90 62 180 108 T360 112 T540 122 T720 110 T900 122 T1080 100 T1260 114 T1440 96 V170 H0Z" />
    <path fill="#8dbd6c" d="M0 142 Q120 116 240 136 T480 140 T720 134 T960 142 T1200 132 T1440 138 V170 H0Z" />
  </svg>
</template>

<style scoped>
.hills {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 150px;
  pointer-events: none;
}
</style>
