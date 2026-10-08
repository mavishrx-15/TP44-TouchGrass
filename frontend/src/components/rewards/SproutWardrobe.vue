<script setup lang="ts">
import { computed, ref } from 'vue'
import SproutTree from '@/components/sprout/SproutTree.vue'
import LeafPointsIcon from '@/components/LeafPointsIcon.vue'
import { SPROUT_SKINS, SKIN_COST, getSkin, type SkinId } from '@/data/sproutSkins'
import { useRewardsStore } from '@/stores/rewards'

defineProps<{ compact?: boolean }>()

const rewards = useRewardsStore()
const preview = ref<SkinId>(rewards.equippedSkin)
const selected = computed(() => getSkin(preview.value))
const owned = computed(() => rewards.ownedSkins.includes(preview.value))
const wearing = computed(() => rewards.equippedSkin === preview.value)
const remaining = computed(() => Math.max(0, SKIN_COST - rewards.state.points))
const announcement = ref('')
function selectSkin(id: SkinId) {
  preview.value = id
  announcement.value = ''
}

function unlock() {
  announcement.value = rewards.unlock(preview.value)
    ? `${selected.value.name} unlocked! Sprout is wearing it now.`
    : 'Keep walking to earn enough leaf points for this look.'
}
function wear() {
  rewards.wear(preview.value)
  announcement.value = `Sprout is wearing ${selected.value.name}.`
}
</script>

<template>
  <section class="wardrobe" :class="{ compact }" aria-label="Sprout skins">
    <div class="heading">
      <div>
        <span v-if="!compact" class="eyebrow">A LITTLE SOMETHING FOR YOUR WALKS</span>
        <h2>{{ compact ? 'Sprout skins' : 'Sprout’s wardrobe' }}</h2>
      </div>
      <span v-if="!compact" class="balance"
        ><LeafPointsIcon /> {{ rewards.state.points }} leaf points</span
      >
    </div>
    <div class="preview" :style="{ '--skin-bg': selected.background }">
      <div class="character">
        <span v-if="!compact" class="halo" /><SproutTree
          :skin="preview"
          :size="compact ? 130 : 155"
          :face="compact ? 'happy' : 'excited'"
        />
      </div>
      <div class="details">
        <span v-if="!compact" class="status">{{
          wearing ? 'WEARING NOW' : owned ? 'YOURS TO WEAR' : 'A NEW LOOK TO GROW INTO'
        }}</span>
        <h3>{{ selected.name }}</h3>
        <p>{{ selected.description }}</p>
        <button v-if="!owned" class="action" :disabled="remaining > 0" @click="unlock">
          {{
            remaining > 0
              ? `${remaining} more points to unlock`
              : `Unlock for ${SKIN_COST} leaf points`
          }}
        </button>
        <button v-else-if="!wearing" class="action" @click="wear">Dress Sprout in this skin</button>
        <span v-else class="wearing">{{
          compact ? 'Wearing now' : '✓ Sprout is wearing this skin'
        }}</span>
        <div
          v-if="!owned && !compact"
          class="progress"
          :aria-label="`${rewards.state.points} of ${SKIN_COST} points`"
        >
          <span :style="{ width: `${Math.min(100, (rewards.state.points / SKIN_COST) * 100)}%` }" />
        </div>
        <small v-if="!owned && remaining && !compact"
          >Just {{ Math.ceil(remaining / 5) }} more
          {{ Math.ceil(remaining / 5) === 1 ? 'walk' : 'walks' }}. Every little walk counts.</small
        >
      </div>
    </div>
    <div class="skin-grid" role="group" aria-label="Preview a Sprout skin">
      <button
        v-for="skin in SPROUT_SKINS"
        :key="skin.id"
        class="skin-tile"
        :class="{ selected: preview === skin.id }"
        :aria-pressed="preview === skin.id"
        :aria-label="
          compact
            ? `${skin.name} · ${rewards.ownedSkins.includes(skin.id) ? 'unlocked' : 'locked, 15 points'}`
            : undefined
        "
        :title="compact ? skin.name : undefined"
        @click="selectSkin(skin.id)"
      >
        <span class="mini" :style="{ background: skin.background }"
          ><SproutTree :skin="skin.id" :size="52"
        /></span>
        <strong v-if="!compact">{{ skin.name.replace(' Sprout', '') }}</strong>
        <small v-if="!compact">{{
          rewards.equippedSkin === skin.id
            ? 'Wearing'
            : rewards.ownedSkins.includes(skin.id)
              ? 'Unlocked'
              : `${SKIN_COST} pts`
        }}</small>
        <svg
          v-if="compact && !rewards.ownedSkins.includes(skin.id)"
          class="lock"
          aria-hidden="true"
          viewBox="0 0 16 20"
        >
          <path d="M4 8V5a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" stroke-width="2" />
          <rect
            x="1"
            y="8"
            width="14"
            height="11"
            rx="2"
            fill="#fffdf8"
            stroke="currentColor"
            stroke-width="2"
          />
          <circle cx="8" cy="13" r="1.5" fill="currentColor" />
        </svg>
      </button>
    </div>
    <p class="announcement" role="status">{{ announcement }}</p>
    <p v-if="!compact" class="save-note">
      Your points and looks stay on this device. Classic Sprout is always yours.
    </p>
  </section>
</template>

<style scoped>
.compact {
  padding: 18px;
  border: 1px solid #dfe5d3;
  border-radius: 20px;
  background: #fff;
}
.compact :deep(.tb-grow) {
  animation: none;
}
.compact h2 {
  font-family: 'Figtree', system-ui, sans-serif;
  font-size: 1rem;
}
.compact .preview {
  background: none;
  border: 0;
  padding: 0;
  gap: 18px;
}
.compact .character {
  background: var(--skin-bg);
  border-radius: 16px;
  min-width: 135px;
  min-height: 155px;
}
.compact .details h3 {
  font-size: 1.4rem;
}
.compact .details p {
  margin: 8px 0;
  font-size: 0.82rem;
}
.compact .skin-grid {
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 7px;
}
.compact .skin-tile {
  padding: 4px;
  border-radius: 12px;
  position: relative;
}
.compact .mini {
  width: 100%;
  min-width: 0;
  height: clamp(52px, 18cqi, 80px);
}
.compact .mini :deep(.sprout-tree) {
  width: 100% !important;
  max-width: 52px;
  height: auto !important;
  aspect-ratio: 10 / 11;
}
.compact .mini :deep(.tb-grow) {
  position: absolute;
  inset: 0;
}
.compact .wearing {
  padding: 4px 9px;
  border-radius: 999px;
  background: #e5efdb;
  font-size: 0.73rem;
}
.lock {
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 11px;
  height: 14px;
  color: #294d2a;
}
@container (max-width: 350px) {
  .compact .character {
    min-width: 100px;
    min-height: 130px;
  }
}
.wardrobe {
  font-family: 'Figtree', system-ui, sans-serif;
  color: #1d2a1d;
  container-type: inline-size;
}
.heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.eyebrow,
.status {
  font-size: 0.65rem;
  letter-spacing: 0.12em;
  font-weight: 800;
  color: #53654b;
}
h2,
h3 {
  font-family: 'Fraunces', Georgia, serif;
  margin: 5px 0;
}
h2 {
  font-size: 1.6rem;
}
h3 {
  font-size: 1.7rem;
}
.balance {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #edf4e6;
  border: 1px solid #d6e3cb;
  border-radius: 999px;
  padding: 8px 13px;
  color: #1f5a2c;
  font-weight: 700;
  font-size: 0.8rem;
  white-space: nowrap;
}
.balance svg {
  width: 18px;
  height: 18px;
}
.preview {
  display: flex;
  align-items: center;
  gap: 24px;
  border-radius: 22px;
  padding: 22px;
  background: linear-gradient(125deg, var(--skin-bg), #fffdf8);
  border: 1px solid #e0e3d5;
  transition: background 0.3s;
}
.character {
  min-width: 175px;
  min-height: 195px;
  display: grid;
  place-items: center;
  position: relative;
}
.character :deep(.sprout-tree) {
  position: relative;
  z-index: 1;
}
.halo {
  position: absolute;
  width: 180px;
  height: 180px;
  background: #ffffff75;
  border-radius: 50%;
  border: 1px solid #ffffffb0;
}
.details {
  flex: 1;
  min-width: 0;
}
.details p {
  font-size: 0.9rem;
  line-height: 1.5;
  color: #59634f;
  margin: 8px 0 16px;
}
.action {
  border: 0;
  background: #1f5a2c;
  color: white;
  padding: 12px 18px;
  border-radius: 12px;
  font-family: inherit;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
}
.action:disabled {
  background: #e3e7d9;
  color: #5a6450;
  cursor: default;
}
.wearing {
  display: inline-block;
  color: #1f5a2c;
  font-weight: 700;
  font-size: 0.85rem;
  padding: 10px 0;
}
.progress {
  height: 7px;
  background: #dbe3d2;
  border-radius: 99px;
  overflow: hidden;
  margin: 15px 0 7px;
}
.progress span {
  height: 100%;
  display: block;
  border-radius: inherit;
  background: #62954b;
  transition: width 0.4s;
}
.details small {
  color: #64725b;
  font-size: 0.74rem;
}
.skin-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 16px;
}
.skin-tile {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  border: 2px solid #e7e6dc;
  border-radius: 15px;
  padding: 9px 5px;
  background: #fffdf9;
  cursor: pointer;
  color: inherit;
  font-family: inherit;
  transition:
    border-color 0.2s,
    transform 0.2s;
}
.skin-tile:hover {
  transform: translateY(-2px);
  border-color: #9bb388;
}
.skin-tile.selected {
  border-color: #1f5a2c;
  background: #f4f8ee;
}
.mini {
  display: grid;
  place-items: center;
  width: 68px;
  height: 76px;
  border-radius: 12px;
}
.skin-tile strong {
  font-size: 0.73rem;
}
.skin-tile small {
  font-size: 0.66rem;
  color: #6b766a;
}
.announcement {
  font-size: 0.82rem;
  color: #1f5a2c;
  margin: 10px 0 0;
}
.announcement:empty {
  display: none;
}
.save-note {
  color: #7a8071;
  font-size: 0.72rem;
  margin: 12px 0 0;
}
button:focus-visible {
  outline: 3px solid #a2be80;
  outline-offset: 3px;
}
@container (min-width: 600px) {
  .skin-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}
@container (max-width: 500px) {
  .preview {
    gap: 12px;
    padding: 18px 12px;
  }
  .character {
    min-width: 110px;
    min-height: 150px;
  }
  .character :deep(.sprout-tree) {
    width: 110px !important;
    height: 121px !important;
  }
  .halo {
    width: 112px;
    height: 112px;
  }
  h3 {
    font-size: 1.3rem;
  }
}
@media (max-width: 640px) {
  .preview {
    gap: 12px;
    padding: 18px 12px;
  }
  .character {
    min-width: 110px;
  }
  .character :deep(.sprout-tree) {
    width: 110px !important;
    height: 121px !important;
  }
  .halo {
    width: 112px;
    height: 112px;
  }
  h3 {
    font-size: 1.3rem;
  }
  .skin-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
  }
}
</style>
