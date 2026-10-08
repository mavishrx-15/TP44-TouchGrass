<script setup lang="ts">
import { computed } from 'vue'
import { getSkin, type SkinId } from '@/data/sproutSkins'
import { useRewardsStore } from '@/stores/rewards'

/**
 * Sprout's animated tree character, ported from the approved clickable
 * prototype: the trunk/canopy shape, sway/bounce/blink/grow animations and
 * the five face expressions are the prototype's own SVG and keyframes
 *. `prefers-reduced-motion` turns every animation off, same as
 * the prototype did.
 */
const props = withDefaults(
  defineProps<{
    face?: 'happy' | 'concerned' | 'excited' | 'calm' | 'thirsty' | 'grateful'
    canopy?: 'open' | 'mixed' | 'dense' | null
    size?: number
    wave?: boolean
    skin?: SkinId
  }>(),
  { face: 'happy', canopy: 'mixed', size: 120, wave: false },
)

// Classic skin colours, straight from the prototype's tgSkins().classic.
const rewards = useRewardsStore()
const skinId = computed(() => props.skin ?? rewards.equippedSkin)
const SK = computed(() => {
  const [c0, c1, c2, c3, trunk] = getSkin(skinId.value).colors
  return { c0, c1, c2, c3, trunk }
})

const canopyScale = computed(() => ({ open: 0.8, mixed: 1, dense: 1.12 })[props.canopy ?? 'mixed'])
const showExtraCanopy = computed(() => props.canopy === 'dense')
const bounce = computed(() => props.face === 'excited')
</script>

<template>
  <div class="sprout-tree" :style="{ width: `${size}px`, height: `${size * 1.1}px` }">
    <div class="tb-grow">
      <div class="tb-inner" :class="bounce ? 'tb-bounce' : 'tb-sway'">
        <svg
          viewBox="0 0 200 220"
          width="100%"
          height="100%"
          style="overflow: visible"
          aria-hidden="true"
        >
          <ellipse cx="100" cy="214" rx="46" ry="5" fill="#000000" opacity="0.1" />
          <path d="M90 140 Q88 185 76 212 L124 212 Q112 185 110 140 Z" :fill="SK.trunk" />
          <path
            d="M100 172 Q96 190 92 205"
            stroke="#6f4630"
            stroke-width="3"
            fill="none"
            stroke-linecap="round"
          />
          <g class="can" :style="{ transform: `scale(${canopyScale})` }">
            <g class="extra" :class="showExtraCanopy ? 'extra-on' : 'extra-off'">
              <circle cx="30" cy="90" r="30" :fill="SK.c0" />
              <circle cx="170" cy="90" r="30" :fill="SK.c0" />
              <circle cx="100" cy="14" r="28" :fill="SK.c1" />
            </g>
            <circle cx="58" cy="108" r="40" :fill="SK.c1" />
            <circle cx="142" cy="108" r="40" :fill="SK.c1" />
            <circle cx="100" cy="125" r="48" :fill="SK.c1" />
            <circle cx="70" cy="62" r="40" :fill="SK.c2" />
            <circle cx="130" cy="62" r="40" :fill="SK.c2" />
            <circle cx="100" cy="92" r="58" :fill="SK.c3" />
            <circle cx="76" cy="46" r="10" fill="#ffffff" opacity="0.18" />
            <circle cx="142" cy="72" r="6" fill="#ffffff" opacity="0.18" />
          </g>
          <g v-if="skinId === 'autumn'" class="skin-detail">
            <path d="M78 148 Q100 160 122 148 L121 163 Q100 176 79 163Z" fill="#bd5549" />
            <path d="M105 164 L117 164 L121 190 L108 189Z" fill="#e2a36f" />
            <path
              d="M82 156 L118 156 M111 171 L119 171 M112 179 L120 179"
              stroke="#f4c395"
              stroke-width="2"
            />
          </g>
          <g v-if="skinId === 'blossom'" fill="#f4a7c5" stroke="#ffe6ef" stroke-width="2">
            <g
              v-for="(flower, i) in [
                [48, 65],
                [143, 49],
                [88, 29],
                [163, 102],
                [42, 117],
              ]"
              :key="i"
              :transform="`translate(${flower[0]} ${flower[1]})`"
              class="skin-spark"
              :style="{ animationDelay: `${i * 0.4}s` }"
            >
              <path
                d="M0 -10 Q7 -12 7 -5 Q15 -3 8 3 Q10 12 2 8 Q-5 15 -8 6 Q-16 3 -8 -3 Q-9 -12 0 -10Z"
              />
              <circle r="3" fill="#f9d46a" stroke="none" />
            </g>
          </g>
          <g v-if="skinId === 'wattle'" fill="#f4ca43">
            <g
              v-for="(flower, i) in [
                [43, 79],
                [70, 38],
                [145, 65],
                [153, 112],
                [102, 23],
              ]"
              :key="i"
              :transform="`translate(${flower[0]} ${flower[1]})`"
              class="skin-spark"
              :style="{ animationDelay: `${i * 0.5}s` }"
            >
              <circle r="8" />
              <circle cx="9" cy="5" r="5" />
              <circle cx="-7" cy="6" r="5" />
              <circle cx="1" cy="-2" r="3" fill="#fff1a2" />
            </g>
          </g>
          <g v-if="skinId === 'snowgum'">
            <path
              d="M46 44 Q61 20 82 23 Q103 0 128 27 Q148 26 155 47 Q137 55 126 42 Q106 57 88 40 Q68 55 46 44Z"
              fill="#f4faf9"
            />
            <path
              d="M95 170 Q88 184 93 207 M106 176 L109 195"
              stroke="#af9e8b"
              stroke-width="4"
              fill="none"
            />
          </g>
          <g v-if="skinId === 'night'">
            <path d="M146 31 A15 15 0 1 0 163 52 A16 16 0 0 1 146 31Z" fill="#ffe7a0" />
            <path
              v-for="(star, i) in [
                [52, 57],
                [94, 26],
                [160, 98],
                [37, 123],
              ]"
              :key="i"
              :transform="`translate(${star[0]} ${star[1]})`"
              d="M0 -5 L2 -1 L6 0 L2 2 L0 6 L-2 2 L-6 0 L-2 -1Z"
              fill="#ffeeb6"
              class="skin-spark"
              :style="{ animationDelay: `${i * 0.6}s` }"
            />
          </g>
          <g v-if="skinId === 'autumn' || skinId === 'blossom'">
            <g
              v-for="(point, i) in [
                [27, 68],
                [175, 80],
                [48, 128],
              ]"
              :key="i"
              :transform="`translate(${point[0]} ${point[1]})`"
            >
              <path
                d="M0 0 Q12 -8 9 6 Q4 13 0 0Z"
                :fill="skinId === 'autumn' ? '#dd8539' : '#f4a7c5'"
                class="skin-drift"
                :style="{ animationDelay: `${i * -1.2}s` }"
              />
            </g>
          </g>
          <g v-if="skinId === 'night'" fill="#f8ed9b">
            <g
              v-for="(point, i) in [
                [20, 100],
                [176, 140],
                [41, 171],
              ]"
              :key="i"
              :transform="`translate(${point[0]} ${point[1]})`"
            >
              <circle r="3" class="skin-firefly" :style="{ animationDelay: `${i * -0.8}s` }" />
            </g>
          </g>
        </svg>

        <div v-if="wave" class="tb-wave">
          <svg width="100%" height="100%" viewBox="0 0 50 50" aria-hidden="true">
            <path
              d="M2 48 Q16 34 30 22"
              :stroke="SK.trunk"
              stroke-width="6"
              fill="none"
              stroke-linecap="round"
            />
            <ellipse cx="36" cy="16" rx="12" ry="8" transform="rotate(-35 36 16)" :fill="SK.c3" />
          </svg>
        </div>

        <div class="tb-face">
          <svg
            v-if="face === 'happy'"
            viewBox="0 0 120 70"
            width="100%"
            height="100%"
            aria-hidden="true"
          >
            <circle cx="24" cy="44" r="7" fill="#f2a0a0" opacity="0.75" />
            <circle cx="96" cy="44" r="7" fill="#f2a0a0" opacity="0.75" />
            <ellipse class="tb-eye" cx="38" cy="28" rx="5" ry="7" fill="#2b2118" />
            <ellipse class="tb-eye" cx="82" cy="28" rx="5" ry="7" fill="#2b2118" />
            <circle cx="40" cy="25" r="1.8" fill="#ffffff" />
            <circle cx="84" cy="25" r="1.8" fill="#ffffff" />
            <path
              d="M50 44 Q60 55 70 44"
              stroke="#2b2118"
              stroke-width="3.5"
              fill="none"
              stroke-linecap="round"
            />
          </svg>
          <svg
            v-else-if="face === 'concerned'"
            viewBox="0 0 120 70"
            width="100%"
            height="100%"
            aria-hidden="true"
          >
            <circle cx="24" cy="46" r="7" fill="#f2a0a0" opacity="0.4" />
            <circle cx="96" cy="46" r="7" fill="#f2a0a0" opacity="0.4" />
            <path d="M30 19 L45 14" stroke="#2b2118" stroke-width="3" stroke-linecap="round" />
            <path d="M90 19 L75 14" stroke="#2b2118" stroke-width="3" stroke-linecap="round" />
            <ellipse class="tb-eye" cx="38" cy="30" rx="4.5" ry="6" fill="#2b2118" />
            <ellipse class="tb-eye" cx="82" cy="30" rx="4.5" ry="6" fill="#2b2118" />
            <circle cx="39.5" cy="28" r="1.5" fill="#ffffff" />
            <circle cx="83.5" cy="28" r="1.5" fill="#ffffff" />
            <path
              d="M51 51 Q60 45 69 51"
              stroke="#2b2118"
              stroke-width="3.5"
              fill="none"
              stroke-linecap="round"
            />
          </svg>
          <svg
            v-else-if="face === 'excited'"
            viewBox="0 0 120 70"
            width="100%"
            height="100%"
            aria-hidden="true"
          >
            <circle cx="22" cy="44" r="8" fill="#f28c8c" opacity="0.8" />
            <circle cx="98" cy="44" r="8" fill="#f28c8c" opacity="0.8" />
            <circle class="tb-eye" cx="38" cy="28" r="8" fill="#2b2118" />
            <circle class="tb-eye" cx="82" cy="28" r="8" fill="#2b2118" />
            <circle cx="41" cy="25" r="3" fill="#ffffff" />
            <circle cx="85" cy="25" r="3" fill="#ffffff" />
            <path d="M47 41 Q60 62 73 41 Z" fill="#7a2f2f" />
            <ellipse cx="60" cy="50" rx="6" ry="3" fill="#e07a7a" />
          </svg>
          <svg
            v-else-if="face === 'calm'"
            viewBox="0 0 120 70"
            width="100%"
            height="100%"
            aria-hidden="true"
          >
            <circle cx="24" cy="44" r="7" fill="#f2a0a0" opacity="0.6" />
            <circle cx="96" cy="44" r="7" fill="#f2a0a0" opacity="0.6" />
            <path
              d="M31 28 Q38 34 45 28"
              stroke="#2b2118"
              stroke-width="3"
              fill="none"
              stroke-linecap="round"
            />
            <path
              d="M75 28 Q82 34 89 28"
              stroke="#2b2118"
              stroke-width="3"
              fill="none"
              stroke-linecap="round"
            />
            <path
              d="M54 46 Q60 51 66 46"
              stroke="#2b2118"
              stroke-width="3"
              fill="none"
              stroke-linecap="round"
            />
          </svg>
          <svg
            v-else-if="face === 'thirsty'"
            viewBox="0 0 120 70"
            width="100%"
            height="100%"
            aria-hidden="true"
          >
            <ellipse cx="38" cy="30" rx="5" ry="6" fill="#2b2118" />
            <ellipse cx="82" cy="30" rx="5" ry="6" fill="#2b2118" />
            <path d="M31 26 L45 26" :stroke="SK.c3" stroke-width="6" />
            <path d="M75 26 L89 26" :stroke="SK.c3" stroke-width="6" />
            <path d="M31 29 L45 29" stroke="#2b2118" stroke-width="2.5" stroke-linecap="round" />
            <path d="M75 29 L89 29" stroke="#2b2118" stroke-width="2.5" stroke-linecap="round" />
            <path
              d="M50 49 Q55 45 60 49 Q65 53 70 49"
              stroke="#2b2118"
              stroke-width="3"
              fill="none"
              stroke-linecap="round"
            />
            <path d="M104 6 Q111 17 104 22 Q97 17 104 6 Z" fill="#7fc3ea" />
          </svg>
          <svg
            v-else-if="face === 'grateful'"
            viewBox="0 0 120 70"
            width="100%"
            height="100%"
            aria-hidden="true"
          >
            <circle cx="24" cy="44" r="8" fill="#f28c8c" opacity="0.85" />
            <circle cx="96" cy="44" r="8" fill="#f28c8c" opacity="0.85" />
            <path
              d="M31 31 Q38 21 45 31"
              stroke="#2b2118"
              stroke-width="3.5"
              fill="none"
              stroke-linecap="round"
            />
            <path
              d="M75 31 Q82 21 89 31"
              stroke="#2b2118"
              stroke-width="3.5"
              fill="none"
              stroke-linecap="round"
            />
            <path
              d="M48 42 Q60 57 72 42"
              stroke="#2b2118"
              stroke-width="3.5"
              fill="none"
              stroke-linecap="round"
            />
            <path
              d="M108 14 C108 10 102 10 102 14 C102 18 108 21 108 21 C108 21 114 18 114 14 C114 10 108 10 108 14 Z"
              fill="#e0607a"
            />
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skin-drift {
  animation: skin-drift 4s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}
.skin-firefly {
  animation: skin-firefly 3s ease-in-out infinite;
}
@keyframes skin-drift {
  0% {
    opacity: 0;
    transform: translateY(-10px) rotate(0);
  }
  25% {
    opacity: 0.9;
  }
  100% {
    opacity: 0;
    transform: translate(12px, 35px) rotate(150deg);
  }
}
@keyframes skin-firefly {
  0%,
  100% {
    opacity: 0.2;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-9px);
  }
}
.skin-spark {
  animation: skin-glimmer 3s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}
@keyframes skin-glimmer {
  50% {
    opacity: 0.55;
  }
}
@media (prefers-reduced-motion: reduce) {
  .skin-spark,
  .skin-drift,
  .skin-firefly {
    animation: none;
  }
}
</style>

<style scoped>
@keyframes tbSway {
  0%,
  100% {
    transform: rotate(-1.6deg);
  }
  50% {
    transform: rotate(1.6deg);
  }
}
@keyframes tbBounce {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5%);
  }
}
@keyframes tbBlink {
  0%,
  90%,
  100% {
    transform: scaleY(1);
  }
  94% {
    transform: scaleY(0.1);
  }
}
@keyframes tbGrow {
  0% {
    transform: scale(0);
  }
  70% {
    transform: scale(1.08);
  }
  100% {
    transform: scale(1);
  }
}
@keyframes tbWave {
  0%,
  100% {
    transform: rotate(-18deg);
  }
  50% {
    transform: rotate(22deg);
  }
}
.sprout-tree {
  position: relative;
}
.tb-grow {
  width: 100%;
  height: 100%;
  transform-origin: 50% 100%;
  animation: tbGrow 1.1s cubic-bezier(0.3, 1.4, 0.5, 1) both;
}
.tb-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transform-origin: 50% 100%;
}
.tb-sway {
  animation: tbSway 5s ease-in-out infinite;
}
.tb-bounce {
  animation: tbBounce 1.1s ease-in-out infinite;
}
.tb-eye {
  transform-box: fill-box;
  transform-origin: center;
  animation: tbBlink 4.5s infinite;
}
.can {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  transition: transform 0.7s cubic-bezier(0.3, 1.4, 0.5, 1);
}
.extra {
  transition: opacity 0.6s;
}
.extra-on {
  opacity: 1;
}
.extra-off {
  opacity: 0;
}
.tb-wave {
  position: absolute;
  left: 84%;
  top: 32%;
  width: 25%;
  height: 25%;
  transform-origin: 0% 100%;
  animation: tbWave 0.9s ease-in-out 1.1s 4 both;
}
.tb-face {
  position: absolute;
  left: 20%;
  top: 34%;
  width: 60%;
  height: 31.8%;
}
@media (prefers-reduced-motion: reduce) {
  .tb-grow,
  .tb-sway,
  .tb-bounce,
  .tb-eye,
  .tb-wave,
  .can {
    animation: none;
    transition: none;
  }
}
</style>
