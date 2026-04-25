'use client';
/**
 * @file app/app/events/page.tsx
 * @brief Events page; list view + month calendar toggle, create modal.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Button, Tabs, TabList, Tab, TabPanel } from '@/components/ui';
import { EventList } from '@/components/events/EventList';
import { EventCreateModal } from '@/components/events/EventCreateModal';
import { MonthCalendar } from '@/components/events/MonthCalendar';
import { useEventsInRange } from '@/hooks/useEvents';

export default function EventsPage() {
  const [createOpen, setCreateOpen] = React.useState(false);
  const [view, setView] = React.useState<'list' | 'calendar'>('list');
  const [month, setMonth] = React.useState(() => new Date());
  const monthStart = new Date(month.getFullYear(), month.getMonth(), 1);
  const monthEnd = new Date(month.getFullYear(), month.getMonth() + 1, 0, 23, 59, 59);
  const { data: monthData } = useEventsInRange(monthStart, monthEnd);

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: 1200, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 3 }}>
        <Typography level="h2" sx={{ fontFamily: 'var(--font-display)' }}>
          Events
        </Typography>
        <Button onClick={() => setCreateOpen(true)}>New event</Button>
      </Stack>
      <Tabs value={view} onChange={(_e, v) => setView((v as 'list' | 'calendar') ?? 'list')}>
        <TabList>
          <Tab value="list">List</Tab>
          <Tab value="calendar">Calendar</Tab>
        </TabList>
        <TabPanel value="list">
          <EventList />
        </TabPanel>
        <TabPanel value="calendar">
          <MonthCalendar month={month} events={monthData?.items ?? []} onMonthChange={setMonth} />
        </TabPanel>
      </Tabs>
      <EventCreateModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </Box>
  );
}
