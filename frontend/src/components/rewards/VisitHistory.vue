<script setup lang="ts">
import { computed } from 'vue'
import LeafPointsIcon from '@/components/LeafPointsIcon.vue'
import { useRewardsStore } from '@/stores/rewards'
import { dayKey } from '@/services/rewards.logic'
import { MOOD_OPTIONS, type Mood } from '@/data/sproutMessages'
import { moodChangeSummary } from '@/data/walkMessages'

const rewards = useRewardsStore()
const recent = computed(() =>
  [...rewards.state.visits].sort((a, b) => b.at.localeCompare(a.at)).slice(0, 8),
)
const week = computed(() => {
  const today = new Date()
  const monday = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate() - ((today.getDay() + 6) % 7),
  )
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + index)
    const key = dayKey(date)
    const count = rewards.state.visits.filter((visit) => visit.date === key).length
    return {
      key,
      day: date.toLocaleDateString('en-AU', { weekday: 'short' }),
      date: date.getDate(),
      count,
      today: key === dayKey(today),
    }
  })
})
function mood(value: Mood | null) {
  return MOOD_OPTIONS.find((option) => option.value === value)
}
function formatDate(at: string) {
  return new Date(at).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })
}
</script>

<template>
  <section class="history" aria-label="Your walks and feeling check-ins">
    <span class="eyebrow">A LITTLE GREENER, ONE DAY AT A TIME</span>
    <div class="title">
      <h2>Your week in leaves</h2>
      <span
        >{{ rewards.state.visits.length }}
        {{ rewards.state.visits.length === 1 ? 'walk' : 'walks' }} logged</span
      >
    </div>
    <div class="week" aria-label="Visits this week">
      <div
        v-for="day in week"
        :key="day.key"
        class="day"
        :class="{ visited: day.count > 0, today: day.today }"
        :aria-label="`${day.day} ${day.date}: ${day.count} walks${day.today ? ', today' : ''}`"
      >
        <small>{{ day.day }}</small
        ><span class="leaf"
          ><LeafPointsIcon v-if="day.count" /><template v-else>{{ day.date }}</template></span
        ><span class="day-note">{{
          day.today ? 'Today' : day.count ? `${day.count} walk${day.count > 1 ? 's' : ''}` : '—'
        }}</span>
      </div>
    </div>
    <p v-if="!recent.length" class="empty">
      Your first little adventure belongs here. Finish a walk to grow your first leaf.
    </p>
    <ol v-else class="visits">
      <li v-for="visit in recent" :key="`${visit.zoneId}-${visit.date}`">
        <div class="visit-top">
          <strong>{{ visit.label ?? 'A tree-dense area' }}</strong
          ><time :datetime="visit.at">{{ formatDate(visit.at) }}</time>
        </div>
        <div class="feelings">
          <span class="mood" :style="{ '--mood-color': mood(visit.before)?.color ?? '#e5e7dc' }"
            >Before · {{ mood(visit.before)?.label ?? 'Not rated' }}</span
          ><span aria-hidden="true">→</span
          ><span class="mood" :style="{ '--mood-color': mood(visit.after)?.color ?? '#e5e7dc' }"
            >After · {{ mood(visit.after)?.label ?? 'Skipped' }}</span
          >
        </div>
        <p v-if="visit.before && visit.after" class="change">
          {{ moodChangeSummary(visit.before, visit.after).text }}
        </p>
      </li>
    </ol>
    <p class="note">
      Check-ins are optional. Every walk counts, whatever kind of day you’re having.
    </p>
  </section>
</template>

<style scoped>
.history {
  color: #1d2a1d;
}
.eyebrow {
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #637357;
}
.title {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
}
h2 {
  font:
    600 1.55rem 'Fraunces',
    Georgia,
    serif;
  margin: 6px 0 18px;
}
.title > span {
  font-size: 0.75rem;
  color: #69775f;
}
.week {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 7px;
  margin-bottom: 20px;
}
.day {
  display: grid;
  gap: 7px;
  justify-items: center;
  padding: 10px 2px;
  background: #f7f6ef;
  border-radius: 13px;
  border: 1px solid #e7e7da;
}
.day small {
  color: #647259;
  font-size: 0.68rem;
}
.leaf {
  border-radius: 50%;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  color: #7e886f;
  font-size: 0.8rem;
}
.visited .leaf {
  background: #1f5a2c;
  color: #fff;
  font-size: 1.5rem;
}
.leaf svg {
  width: 20px;
  height: 20px;
}
.visited {
  background: #edf4e5;
  border-color: #d4e0c8;
}
.today {
  border-color: #799661;
}
.day-note {
  font-size: 0.59rem;
  color: #637357;
}
.visits {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}
.visits li {
  padding: 14px;
  background: #fffdf8;
  border: 1px solid #e9e7dc;
  border-radius: 14px;
}
.visit-top {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: baseline;
}
.visit-top strong {
  font-size: 0.85rem;
}
time {
  font-size: 0.72rem;
  color: #78816d;
  white-space: nowrap;
}
.feelings {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
  flex-wrap: wrap;
  font-size: 0.72rem;
  color: #637357;
}
.mood {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.mood::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--mood-color);
}
.change {
  font-size: 0.75rem;
  color: #426239;
  margin: 9px 0 0;
}
.note,
.empty {
  font-size: 0.75rem;
  color: #727d67;
  line-height: 1.5;
}
.note {
  margin: 16px 0 0;
}
</style>
