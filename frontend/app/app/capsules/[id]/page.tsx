/**
 * @file app/app/capsules/[id]/page.tsx
 * @brief One time capsule (sealed placeholder or opened message).
 */
"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui";
import { CapsuleView } from "@/components/capsules/CapsuleView";
import { deleteCapsule, getCapsule } from "@/lib/api/capsules";
import { useSession } from "@/stores/session";

export default function CapsuleRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const me = useSession((s) => s.user?.id);
  const router = useRouter();
  const qc = useQueryClient();
  const { data, isError } = useQuery({
    queryKey: ["capsules", id],
    queryFn: () => getCapsule(id),
    retry: false,
  });
  const del = useMutation({
    mutationFn: () => deleteCapsule(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["capsules"] });
      router.push("/app/capsules");
    },
  });
  if (isError) return <p role="alert">This capsule is not available.</p>;
  if (!data) return null;
  const mine = data.author.id === me;
  return (
    <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4 pb-8">
      <CapsuleView capsule={data} mine={mine} />
      {mine && (
        <Button
          variant="ghost"
          className="self-start"
          onClick={() => del.mutate()}
          loading={del.isPending}
        >
          Delete capsule
        </Button>
      )}
    </div>
  );
}
