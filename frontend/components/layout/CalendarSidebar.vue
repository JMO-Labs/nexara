<!--
  @file components/layout/CalendarSidebar.vue
  @brief Static right-side calendar bar with mini month grid and upcoming events.

  Displays the current month as a compact day grid with today highlighted,
  and a short list of upcoming events (stub data). Sticky-positioned so
  it stays in view while the feed scrolls. Hidden below the lg breakpoint.
-->
<template>
  <aside class="hidden lg:block w-[280px] shrink-0">
    <div class="sticky top-6 space-y-4">
      <!-- Mini calendar card -->
      <div class="rounded-lg border border-border bg-card p-4">
        <div class="mb-3 flex items-center justify-between">
          <button
            class="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            :aria-label="$t('calendar.prevMonth')"
            @click="prevMonth"
          >
            <ChevronLeftIcon class="h-4 w-4" />
          </button>
          <h3 class="text-sm font-semibold text-card-foreground">
            {{ monthLabel }}
          </h3>
          <button
            class="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            :aria-label="$t('calendar.nextMonth')"
            @click="nextMonth"
          >
            <ChevronRightIcon class="h-4 w-4" />
          </button>
        </div>

        <!-- Weekday headers -->
        <div class="grid grid-cols-7 mb-1">
          <span
            v-for="day in weekDays"
            :key="day"
            class="text-center text-[10px] font-medium text-muted-foreground"
          >
            {{ day }}
          </span>
        </div>

        <!-- Day grid -->
        <div class="grid grid-cols-7">
          <span
            v-for="(cell, idx) in calendarCells"
            :key="idx"
            :class="[
              'flex h-8 w-full items-center justify-center text-xs rounded-md transition-colors',
              cell.isCurrentMonth ? 'text-card-foreground' : 'text-muted-foreground/40',
              cell.isToday ? 'bg-primary text-primary-foreground font-bold' : 'hover:bg-accent',
            ]"
          >
            {{ cell.day }}
          </span>
        </div>
      </div>

      <!-- Upcoming events card -->
      <div class="rounded-lg border border-border bg-card p-4">
        <h3 class="mb-3 text-sm font-semibold text-card-foreground">
          {{ $t('calendar.upcoming') }}
        </h3>

        <div v-if="upcomingEvents.length === 0" class="text-center py-4">
          <p class="text-xs text-muted-foreground">{{ $t('calendar.noEvents') }}</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="event in upcomingEvents"
            :key="event.id"
            class="flex gap-3"
          >
            <div class="flex flex-col items-center justify-center rounded-md bg-muted px-2 py-1 min-w-[40px]">
              <span class="text-[10px] font-medium uppercase text-muted-foreground">{{ event.monthShort }}</span>
              <span class="text-sm font-bold text-card-foreground">{{ event.dayNum }}</span>
            </div>
            <div class="min-w-0">
              <p class="truncate text-sm font-medium text-card-foreground">{{ event.title }}</p>
              <p class="text-xs text-muted-foreground">{{ event.time }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * @brief CalendarSidebar logic: month navigation and calendar grid generation.
 */
import { ref, computed } from 'vue'
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/outline'

/** @brief Currently viewed year and month. */
const viewYear = ref(new Date().getFullYear())
const viewMonth = ref(new Date().getMonth())

const weekDays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

interface CalendarCell {
  day: number
  isCurrentMonth: boolean
  isToday: boolean
}

/** @brief Formatted month/year label. */
const monthLabel = computed(() => {
  const date = new Date(viewYear.value, viewMonth.value, 1)
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
})

/** @brief Generate the 6-week calendar grid for the viewed month. */
const calendarCells = computed<CalendarCell[]>(() => {
  const today = new Date()
  const firstDay = new Date(viewYear.value, viewMonth.value, 1)
  const startDow = firstDay.getDay()
  const daysInMonth = new Date(viewYear.value, viewMonth.value + 1, 0).getDate()
  const prevMonthDays = new Date(viewYear.value, viewMonth.value, 0).getDate()

  const cells: CalendarCell[] = []

  for (let i = startDow - 1; i >= 0; i--) {
    cells.push({ day: prevMonthDays - i, isCurrentMonth: false, isToday: false })
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const isToday =
      d === today.getDate() &&
      viewMonth.value === today.getMonth() &&
      viewYear.value === today.getFullYear()
    cells.push({ day: d, isCurrentMonth: true, isToday })
  }

  const remaining = 42 - cells.length
  for (let d = 1; d <= remaining; d++) {
    cells.push({ day: d, isCurrentMonth: false, isToday: false })
  }

  return cells
})

function prevMonth(): void {
  if (viewMonth.value === 0) {
    viewMonth.value = 11
    viewYear.value--
  } else {
    viewMonth.value--
  }
}

function nextMonth(): void {
  if (viewMonth.value === 11) {
    viewMonth.value = 0
    viewYear.value++
  } else {
    viewMonth.value++
  }
}

interface UpcomingEvent {
  id: string
  title: string
  monthShort: string
  dayNum: string
  time: string
}

/**
 * @brief Stub upcoming events. Replaced by API integration later.
 */
const upcomingEvents = ref<UpcomingEvent[]>([
  { id: '1', title: 'Community Standup', monthShort: 'Mar', dayNum: '03', time: '10:00 AM' },
  { id: '2', title: 'Design Review', monthShort: 'Mar', dayNum: '07', time: '2:00 PM' },
  { id: '3', title: 'Town Hall Meeting', monthShort: 'Mar', dayNum: '14', time: '6:00 PM' },
])
</script>
