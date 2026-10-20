"use client";
/**
 * @file components/events/event-form/DateTimeFields.tsx
 * @brief All-day toggle plus native date/time inputs for start and end.
 */
import { Input } from "@/components/ui";

export interface DateTimeValue {
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
  allDay: boolean;
}

export interface DateTimeFieldsProps {
  value: DateTimeValue;
  onChange: (next: DateTimeValue) => void;
}

/**
 * @brief Date/time section; end date auto-follows an earlier start date.
 * @param props value and change handler
 * @return section element
 */
export function DateTimeFields({ value, onChange }: DateTimeFieldsProps) {
  const set = (patch: Partial<DateTimeValue>) =>
    onChange({ ...value, ...patch });
  return (
    <div className="flex flex-col gap-4">
      <label className="inline-flex items-center gap-2 text-sm font-semibold">
        <input
          type="checkbox"
          className="size-4"
          checked={value.allDay}
          onChange={(e) => set({ allDay: e.target.checked })}
        />
        All day
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Start date"
          type="date"
          required
          value={value.startDate}
          onChange={(e) => {
            const v = e.target.value;
            set({
              startDate: v,
              endDate: !value.endDate || value.endDate < v ? v : value.endDate,
            });
          }}
        />
        {!value.allDay && (
          <Input
            label="Start time"
            type="time"
            required
            value={value.startTime}
            onChange={(e) => set({ startTime: e.target.value })}
          />
        )}
        <Input
          label="End date"
          type="date"
          required
          value={value.endDate}
          onChange={(e) => set({ endDate: e.target.value })}
        />
        {!value.allDay && (
          <Input
            label="End time"
            type="time"
            required
            value={value.endTime}
            onChange={(e) => set({ endTime: e.target.value })}
          />
        )}
      </div>
    </div>
  );
}

export default DateTimeFields;
