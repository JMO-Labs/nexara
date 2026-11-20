"use client";
/**
 * @file components/settings/AccountTab.tsx
 * @brief Account settings tab: email change form.
 */
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { SettingsRow, Input, Button } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useUpdateEmail } from "@/hooks/useSettings";
import { DataExportSection } from "./DataExportSection";

const Schema = z.object({
  email: z.string().email("Invalid email address"),
});
type FormData = z.infer<typeof Schema>;

/**
 * @brief Email change form.
 * @return account tab content
 */
export function AccountTab() {
  const [initialEmail] = useState("");
  const { mutate, isPending } = useUpdateEmail();
  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(Schema),
    defaultValues: { email: initialEmail },
  });

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Email address">
        <form onSubmit={handleSubmit((d) => mutate(d.email))} noValidate>
          <SettingsRow
            label="Email"
            description="Your account email address used for login and recovery."
          >
            <Input
              type="email"
              label="Email address"
              placeholder="name@example.com"
              autoComplete="email"
              error={formState.errors.email?.message}
              {...register("email")}
            />
          </SettingsRow>
          <div className="mt-4">
            <Button type="submit" loading={isPending} disabled={isPending}>
              Update email
            </Button>
          </div>
        </form>
      </Panel>
      <DataExportSection />
    </div>
  );
}
