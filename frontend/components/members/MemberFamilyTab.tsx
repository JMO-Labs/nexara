"use client";
/**
 * @file components/members/MemberFamilyTab.tsx
 * @brief Profile "Family" tab: the member's household and pets the viewer
 *        may see.
 */
import { PawPrint } from "lucide-react";
import { EmptyState, Skeleton } from "@/components/ui";
import { HouseholdCards } from "@/components/household/HouseholdCards";
import { useUserHousehold } from "@/hooks/useHousehold";

/**
 * @brief Family tab body.
 * @param userId profile owner
 * @param name first name for the empty state
 * @return cards
 */
export function MemberFamilyTab({
  userId,
  name,
}: {
  userId: string;
  name: string;
}) {
  const { data, isLoading } = useUserHousehold(userId);
  if (isLoading) return <Skeleton height={96} rounded="lg" />;
  if (!data?.length)
    return (
      <EmptyState
        compact
        icon={PawPrint}
        title={`No family or pets shared by ${name}`}
      />
    );
  return <HouseholdCards items={data} />;
}
