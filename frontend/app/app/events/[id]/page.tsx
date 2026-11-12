"use client";
/**
 * @file app/app/events/[id]/page.tsx
 * @brief Standalone event route; delegates to EventPage.
 */
import { useParams } from "next/navigation";
import { EventPage } from "@/components/events/EventPage";

export default function Page() {
  const params = useParams<{ id: string }>();
  return <EventPage id={params.id} />;
}
