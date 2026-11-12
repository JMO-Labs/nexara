"use client";
/**
 * @file components/admin/prompts-tab/PromptEditor.tsx
 * @brief Edit form for the selected prompt; saves each change immediately.
 */
import { Button, Input, Option, Select, Textarea } from "@/components/ui";
import type { PromptResponse, PromptUpdate } from "@/lib/api/prompts";
import { FREQUENCIES } from "./constants";

interface Props {
  prompt: PromptResponse;
  deleting: boolean;
  onChange: (update: PromptUpdate) => void;
  onDelete: () => void;
}

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);
const DAYS = Array.from({ length: 31 }, (_, i) => i + 1);

/**
 * @brief Right pane of the prompts tab.
 * @param props selected prompt and callbacks
 * @return edit form
 */
export function PromptEditor({ prompt, deleting, onChange, onDelete }: Props) {
  return (
    <div className="flex min-w-0 flex-col gap-4">
      <h2 className="text-lg font-semibold">Edit prompt</h2>
      <Input
        label="Title"
        value={prompt.title}
        onChange={(e) => onChange({ title: e.target.value })}
        placeholder="Prompt title"
      />
      <Textarea
        label="Body"
        rows={3}
        value={prompt.body}
        onChange={(e) => onChange({ body: e.target.value })}
        placeholder="Prompt body"
      />
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-semibold">Frequency</span>
        <Select
          label="Frequency"
          value={prompt.frequency}
          onValueChange={(v) => onChange({ frequency: v })}
        >
          {FREQUENCIES.map((f) => (
            <Option key={f.value} value={f.value}>
              {f.label}
            </Option>
          ))}
        </Select>
      </div>
      {prompt.frequency === "annual_date" && (
        <>
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold">Month</span>
            <Select
              label="Month"
              value={String(prompt.trigger_month || "")}
              onValueChange={(v) => onChange({ trigger_month: parseInt(v) })}
            >
              {MONTHS.map((m) => (
                <Option key={m} value={String(m)}>
                  {new Date(2024, m - 1).toLocaleString("default", {
                    month: "long",
                  })}
                </Option>
              ))}
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold">Day</span>
            <Select
              label="Day"
              value={String(prompt.trigger_day || "")}
              onValueChange={(v) => onChange({ trigger_day: parseInt(v) })}
            >
              {DAYS.map((d) => (
                <Option key={d} value={String(d)}>
                  {d}
                </Option>
              ))}
            </Select>
          </div>
        </>
      )}
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-semibold">Prompt type</span>
        <Select
          label="Prompt type"
          value={prompt.prompt_type}
          onValueChange={(v) => onChange({ prompt_type: v })}
        >
          <Option value="standard">Standard</Option>
          <Option value="interest_capture">Interest capture</Option>
        </Select>
      </div>
      {prompt.prompt_type === "interest_capture" && (
        <>
          <Input
            label="Interest category slug"
            value={prompt.interest_category_slug || ""}
            onChange={(e) =>
              onChange({ interest_category_slug: e.target.value || null })
            }
            placeholder="e.g., cooking, music, books"
          />
          <Textarea
            label="Interest capture hint"
            rows={2}
            value={prompt.interest_capture_hint || ""}
            onChange={(e) =>
              onChange({ interest_capture_hint: e.target.value || null })
            }
            placeholder="Hint for users to capture interests"
          />
        </>
      )}
      <div>
        <Button variant="destructive" onClick={onDelete} loading={deleting}>
          Delete
        </Button>
      </div>
    </div>
  );
}
