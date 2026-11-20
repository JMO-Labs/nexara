"use client";
/**
 * @file components/admin/AIConfigTab.tsx
 * @brief Admin AI tab: provider, Sassybot settings, budget and usage metrics.
 */
import { useEffect, useState } from "react";
import {
  useAdminAIConfig,
  useAdminAIMetrics,
  useTestAIConnection,
  useUpdateAdminAIConfig,
} from "@/hooks/useAdminAI";
import { Button, Switch } from "@/components/ui";
import { Panel, Segmented } from "@/components/ui/page";
import { Progress } from "@/components/ui/shadcn/progress";
import { AdminLoading, AdminNotice } from "./AdminState";
import { AIMetricsChart, usd } from "./AIMetricsChart";

const PROVIDERS = [
  { id: "anthropic", label: "Anthropic" },
  { id: "openai", label: "OpenAI" },
  { id: "ollama", label: "Ollama" },
];
const SASS = [
  "Mild: gentle, friendly teasing.",
  "Moderate: playful roasts with a wink.",
  "Spicy: bold, sharp-tongued banter.",
];
const SASS_NAMES = ["Mild", "Moderate", "Spicy"];
const FEATURE_LABEL: Record<string, string> = {
  ocr: "OCR",
  suggestion: "Suggestions",
  sassybot: "Sassybot",
};

function ProviderSection() {
  const { data } = useAdminAIConfig();
  const test = useTestAIConnection();
  const result = test.data;
  return (
    <Panel title="Provider configuration" className="flex flex-col gap-3">
      {/* Read-only: the provider is set by the server environment. */}
      <Segmented
        label="AI provider"
        options={PROVIDERS.map((p) => ({ value: p.id, label: p.label }))}
        value={data?.provider ?? ""}
        onChange={() => {}}
      />
      <p className="text-sm text-muted">
        Your data is sent to selected provider. OpenAI/Anthropic are
        cloud-based. Ollama runs locally. The provider is set by the server
        environment.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => test.mutate()} disabled={test.isPending}>
          {test.isPending ? "Testing..." : "Test connection"}
        </Button>
        {test.isError && (
          <AdminNotice tone="error">Connection test failed.</AdminNotice>
        )}
        {result && (
          <span
            role="status"
            className={result.success ? "text-ink" : "text-danger"}
          >
            {result.message}
          </span>
        )}
      </div>
    </Panel>
  );
}

function SassybotSection() {
  const { data } = useAdminAIConfig();
  const update = useUpdateAdminAIConfig();
  const [form, setForm] = useState({
    sassybot_enabled: true,
    sass_level: 2,
    probability: 20,
    invoke_only: false,
  });
  useEffect(() => {
    if (data) {
      const { sassybot_enabled, sass_level, probability, invoke_only } = data;
      setForm({ sassybot_enabled, sass_level, probability, invoke_only });
    }
  }, [data]);
  return (
    <Panel title="Sassybot settings" className="flex flex-col gap-4">
      <label className="flex min-h-11 items-center justify-between gap-3">
        Enable Sassybot
        <Switch
          aria-label="Enable Sassybot"
          checked={form.sassybot_enabled}
          onCheckedChange={(v) => setForm({ ...form, sassybot_enabled: v })}
        />
      </label>
      <div className="flex flex-col gap-1">
        <div className="flex justify-between">
          <label htmlFor="sass-level">Sass level</label>
          <span>{SASS_NAMES[form.sass_level - 1]}</span>
        </div>
        <input
          id="sass-level"
          type="range"
          min={1}
          max={3}
          step={1}
          value={form.sass_level}
          aria-valuetext={SASS[form.sass_level - 1]}
          onChange={(e) =>
            setForm({ ...form, sass_level: Number(e.target.value) })
          }
          className="min-h-11 w-full accent-[var(--nx-surface-strong)]"
        />
        <p className="text-sm text-muted">{SASS[form.sass_level - 1]}</p>
      </div>
      <div className="flex flex-col gap-1">
        <div className="flex justify-between">
          <label htmlFor="sass-prob">Probability (chance per post)</label>
          <span>{form.probability}%</span>
        </div>
        <input
          id="sass-prob"
          type="range"
          min={0}
          max={100}
          step={1}
          value={form.probability}
          onChange={(e) =>
            setForm({ ...form, probability: Number(e.target.value) })
          }
          className="min-h-11 w-full accent-[var(--nx-surface-strong)]"
        />
      </div>
      <label className="flex min-h-11 items-center justify-between gap-3">
        Invoke-only mode (only @mention triggers, no auto-commenting)
        <Switch
          aria-label="Invoke-only mode"
          checked={form.invoke_only}
          onCheckedChange={(v) => setForm({ ...form, invoke_only: v })}
        />
      </label>
      <p>{data?.opt_out_count ?? 0} users have opted out of Sassybot</p>
      <p className="text-sm text-muted">
        Sassybot generates witty comments. Users can opt out in settings.
      </p>
      <div className="flex flex-wrap items-center justify-end gap-3">
        <Button onClick={() => update.mutate(form)} disabled={update.isPending}>
          {update.isPending ? "Saving..." : "Save"}
        </Button>
        {update.isSuccess && <span role="status">Settings saved</span>}
        {update.isError && (
          <AdminNotice tone="error">Failed to save settings.</AdminNotice>
        )}
      </div>
    </Panel>
  );
}

function MetricsSection() {
  const { data, isLoading } = useAdminAIMetrics();
  if (isLoading) return <AdminLoading />;
  if (!data)
    return <AdminNotice tone="error">Failed to load metrics.</AdminNotice>;
  const pct = data.daily_budget_cents
    ? Math.round((data.daily_usage_cents / data.daily_budget_cents) * 100)
    : 0;
  return (
    <Panel title="Budget and metrics" className="flex flex-col gap-3">
      <p>
        {`Daily Budget: ${usd(data.daily_usage_cents)} / ${usd(data.daily_budget_cents)} spent (${pct}% used)`}
      </p>
      <Progress
        value={Math.min(100, pct)}
        aria-label="Daily budget used"
        className="h-3"
      />
      {pct > 80 && (
        <AdminNotice tone="error">
          Today&apos;s usage is above 80% of the daily budget.
        </AdminNotice>
      )}
      <AIMetricsChart days={data.last_7_days} />
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Usage by feature today</caption>
        <thead>
          <tr>
            <th scope="col">Feature</th>
            <th scope="col">Calls</th>
            <th scope="col">Cost</th>
          </tr>
        </thead>
        <tbody>
          {data.breakdown.map((b) => (
            <tr key={b.feature}>
              <th scope="row" className="font-normal">
                {FEATURE_LABEL[b.feature] ?? b.feature}
              </th>
              <td>{b.calls}</td>
              <td>{usd(b.cents)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

/**
 * @brief AI configuration admin tab.
 * @return tab content
 */
export function AIConfigTab() {
  const { isLoading, data, error } = useAdminAIConfig();
  if (isLoading) return <AdminLoading />;
  if (error || !data)
    return (
      <AdminNotice tone="error">Failed to load AI configuration.</AdminNotice>
    );
  return (
    <div className="flex flex-col gap-4">
      <ProviderSection />
      <SassybotSection />
      <MetricsSection />
    </div>
  );
}
