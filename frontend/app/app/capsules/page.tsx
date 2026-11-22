/**
 * @file app/app/capsules/page.tsx
 * @brief Time capsules: Sealed (for me) / Opened / Sent by me.
 */
"use client";

import * as React from "react";
import Link from "next/link";
import { Hourglass } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  EmptyState,
  Tab,
  TabList,
  TabPanel,
  Tabs,
} from "@/components/ui";
import { PageHeader } from "@/components/ui/page";
import { CapsuleComposer } from "@/components/capsules/CapsuleComposer";
import { SealedCard, fmtDate } from "@/components/capsules/SealedCard";
import { useFeature } from "@/hooks/useFeature";
import { listCapsules, type CapsuleOpen } from "@/lib/api/capsules";

function Row({ c, prefix }: { c: CapsuleOpen; prefix: string }) {
  return (
    <Link
      href={`/app/capsules/${c.id}`}
      className="glass-item focus-visible:outline-accent flex flex-col rounded-2xl p-4 focus-visible:outline-2"
    >
      <span className="font-semibold">{c.title}</span>
      <span className="text-muted text-sm">
        {prefix} · {fmtDate(c.open_at)}
      </span>
    </Link>
  );
}

const none = (t: string) => <EmptyState compact icon={Hourglass} title={t} />;

export default function CapsulesRoute() {
  const on = useFeature("time_capsules");
  const [compose, setCompose] = React.useState(false);
  const { data } = useQuery({ queryKey: ["capsules"], queryFn: listCapsules });
  if (!on) return null;
  return (
    <div className="mx-auto flex w-full max-w-[800px] flex-col gap-6 pb-8">
      <PageHeader
        title="Time capsules"
        description="Messages sealed now and opened on a date you choose."
        actions={
          <Button onClick={() => setCompose(true)}>Seal a capsule</Button>
        }
      />
      <Tabs defaultValue="sealed">
        <TabList aria-label="Capsules">
          <Tab value="sealed">Sealed</Tab>
          <Tab value="opened">Opened</Tab>
          <Tab value="mine">Sent by me</Tab>
        </TabList>
        <TabPanel value="sealed" className="flex flex-col gap-2 pt-4">
          {data?.sealed.map((c) => (
            <SealedCard key={c.id} capsule={c} />
          ))}
          {data &&
            data.sealed.length === 0 &&
            none("Nothing sealed for you yet")}
        </TabPanel>
        <TabPanel value="opened" className="flex flex-col gap-2 pt-4">
          {data?.opened.map((c) => (
            <Row key={c.id} c={c} prefix={`From ${c.author.display_name}`} />
          ))}
          {data && data.opened.length === 0 && none("No opened capsules yet")}
        </TabPanel>
        <TabPanel value="mine" className="flex flex-col gap-2 pt-4">
          {data?.mine.map((c) => (
            <Row
              key={c.id}
              c={c}
              prefix={c.opened_at ? "Opened" : "Sealed until"}
            />
          ))}
          {data &&
            data.mine.length === 0 &&
            none("You have not sealed any capsules")}
        </TabPanel>
      </Tabs>
      {compose && <CapsuleComposer open onClose={() => setCompose(false)} />}
    </div>
  );
}
