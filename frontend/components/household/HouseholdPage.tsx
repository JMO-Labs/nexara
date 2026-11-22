"use client";
/**
 * @file components/household/HouseholdPage.tsx
 * @brief One household member or pet: photo, who they belong to, birthday
 *        and gotcha day, likes/dislikes, care card and photos they're
 *        tagged in.
 */
import * as React from "react";
import Link from "next/link";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Cake, Heart, HeartOff, Images, PawPrint, Pencil } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { PhotoGrid } from "@/components/galleries/PhotoGrid";
import { useHouseholdMember } from "@/hooks/useHousehold";
import { useMemberProfile } from "@/hooks/useMembers";
import { householdPhotos } from "@/lib/api/household";
import { HouseholdMentions } from "./HouseholdMentions";
import { birthdayText } from "@/lib/profile";
import { HouseholdAvatar, householdSubtitle } from "./HouseholdCards";
import { HouseholdEditor } from "./HouseholdEditor";
import { WishlistCards } from "@/components/wishlists/WishlistCards";

function Chips({
  items,
  label,
  icon: Icon,
}: {
  items: string[];
  label: string;
  icon: typeof Heart;
}) {
  if (!items.length) return null;
  return (
    <div>
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-medium">
        <Icon className="size-4" aria-hidden /> {label}
      </h3>
      <ul className="flex flex-wrap gap-1.5">
        {items.map((v) => (
          <li key={v} className="glass-item rounded-full px-3 py-1 text-sm">
            {v}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * @brief Household member page body.
 * @param id member id
 * @return page
 */
export function HouseholdPage({ id }: { id: string }) {
  const { data: m, isLoading, isError } = useHouseholdMember(id);
  const owner = useMemberProfile(m?.owner_id ?? "");
  const [editing, setEditing] = React.useState(false);
  const photos = useInfiniteQuery({
    queryKey: ["household", id, "photos"],
    queryFn: ({ pageParam }) => householdPhotos(id, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_before,
    enabled: !!m,
  });
  const media = photos.data?.pages.flatMap((p) => p.media_ids) ?? [];

  if (isLoading) return <Skeleton height={240} rounded="lg" />;
  if (isError || !m)
    return <EmptyState icon={PawPrint} title="This page isn't available" />;

  const isPet = m.kind === "pet";
  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-6">
      <section className="glass flex flex-col items-center gap-4 rounded-[28px] p-6 text-center sm:flex-row sm:text-left">
        <HouseholdAvatar m={m} className="size-28" />
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold">{m.name}</h1>
          {m.handle && (
            <p className="text-sm text-muted">
              Mention with <span className="font-medium">@{m.handle}</span>
            </p>
          )}
          {householdSubtitle(m) && (
            <p className="text-muted">{householdSubtitle(m)}</p>
          )}
          {owner.data && (
            <p className="mt-1 text-sm text-muted">
              {isPet ? "Pet of " : "Family of "}
              <Link href={`/app/members/${m.owner_id}`} className="underline">
                {owner.data.display_name}
              </Link>
            </p>
          )}
          <div className="mt-2 flex flex-wrap justify-center gap-3 text-sm sm:justify-start">
            {m.birthday && (
              <span className="flex items-center gap-1.5">
                <Cake className="size-4" aria-hidden /> Birthday{" "}
                {birthdayText(m.birthday)}
              </span>
            )}
            {m.gotcha_day && (
              <span className="flex items-center gap-1.5">
                <PawPrint className="size-4" aria-hidden /> Gotcha day{" "}
                {birthdayText(m.gotcha_day)}
              </span>
            )}
          </div>
        </div>
        {m.can_edit && (
          <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
            <Pencil className="size-4" aria-hidden /> Edit
          </Button>
        )}
      </section>
      {(m.bio ||
        m.likes.length > 0 ||
        m.dislikes.length > 0 ||
        m.care_card) && (
        <section className="glass grid gap-5 rounded-[28px] p-6 md:grid-cols-2">
          {m.bio && (
            <p className="whitespace-pre-line md:col-span-2">{m.bio}</p>
          )}
          <Chips items={m.likes} label="Likes" icon={Heart} />
          <Chips items={m.dislikes} label="Dislikes" icon={HeartOff} />
          {m.care_card && (
            <div className="md:col-span-2">
              <h3 className="mb-2 text-sm font-medium">Care card</h3>
              <p className="glass-item rounded-2xl p-4 text-sm whitespace-pre-line">
                {m.care_card}
              </p>
            </div>
          )}
        </section>
      )}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Wishlists</h2>
        <WishlistCards
          query={{ household_id: m.id }}
          canCreate={m.can_edit}
          emptyText={`No wishlists for ${m.name} yet`}
        />
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Photos</h2>
        {photos.isLoading ? (
          <Skeleton height={120} rounded="lg" />
        ) : media.length ? (
          <PhotoGrid mediaIds={media} />
        ) : (
          <EmptyState
            compact
            icon={Images}
            title={`No photos of ${m.name} yet`}
            description="Open any photo and use Tag someone."
          />
        )}
        {photos.hasNextPage && (
          <Button
            variant="ghost"
            size="sm"
            className="self-center"
            loading={photos.isFetchingNextPage}
            onClick={() => void photos.fetchNextPage()}
          >
            Load more
          </Button>
        )}
      </section>
      <HouseholdMentions m={m} />
      {editing && (
        <HouseholdEditor
          member={m}
          kind={m.kind}
          onClose={() => setEditing(false)}
        />
      )}
    </div>
  );
}
