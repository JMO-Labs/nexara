"use client";
/**
 * @file components/relations/AddRelationDialog.tsx
 * @brief Add a relation: pick a member or one of your household members,
 *        then finish "Ruth is my ...".
 */
import * as React from "react";
import { Button, Input, Modal, Option, Select } from "@/components/ui";
import { useVisibleHousehold } from "@/hooks/useHousehold";
import { useMembersList } from "@/hooks/useMembersList";
import { useRelationActions } from "@/hooks/useRelations";
import { formatApiError } from "@/lib/api/errors";
import type { RelationKind } from "@/lib/api/relations";
import { useSession } from "@/stores/session";
import { useToasts } from "@/stores/toasts";

const KINDS: [RelationKind, string][] = [
  ["parent", "Parent"],
  ["child", "Child"],
  ["spouse", "Spouse"],
  ["partner", "Partner"],
  ["sibling", "Sibling"],
  ["friend", "Friend"],
  ["other", "Other"],
];

/**
 * @param props open flag and close callback
 * @return modal
 */
export function AddRelationDialog({
  open,
  onClose,
  presetUserId,
}: {
  open: boolean;
  onClose: () => void;
  /** Start with this member picked (e.g. from the people strip card). */
  presetUserId?: string;
}) {
  const me = useSession((s) => s.user?.id);
  const members = useMembersList().data ?? [];
  const household = useVisibleHousehold().data ?? [];
  const { request } = useRelationActions();
  const [userId, setUserId] = React.useState(presetUserId ?? "");
  React.useEffect(() => {
    if (open && presetUserId) setUserId(presetUserId);
  }, [open, presetUserId]);
  const [memberId, setMemberId] = React.useState("");
  const [kind, setKind] = React.useState<RelationKind>("parent");
  const [label, setLabel] = React.useState("");

  const people = members.filter((m) => m.id !== me);
  const mine = household.filter(
    (h) => h.owner_id === me && h.kind === "person",
  );
  const name =
    people.find((p) => p.id === userId)?.display_name ??
    mine.find((h) => h.id === memberId)?.name ??
    "They";
  const ready = (userId || memberId) && (kind !== "other" || label.trim());

  const reset = () => {
    setUserId("");
    setMemberId("");
    setKind("parent");
    setLabel("");
  };
  const submit = () =>
    request.mutate(
      {
        ...(userId ? { to_user_id: userId } : { to_member_id: memberId }),
        kind,
        ...(kind === "other" ? { label: label.trim() } : {}),
      },
      {
        onSuccess: () => {
          useToasts.getState().push({
            variant: "success",
            message: userId
              ? `Request sent to ${name}`
              : `${name} added to your family`,
          });
          reset();
          onClose();
        },
        onError: (e) =>
          useToasts
            .getState()
            .push({ variant: "danger", message: formatApiError(e) }),
      },
    );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add a relation"
      description="Members confirm before it shows. People in your household are added right away."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={!ready}
            loading={request.isPending}
            onClick={submit}
          >
            {userId ? "Send request" : "Add"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Select
          label="Member"
          placeholder="Pick a member"
          value={userId}
          onValueChange={(v) => {
            setUserId(v);
            setMemberId("");
          }}
        >
          {people.map((p) => (
            <Option key={p.id} value={p.id}>
              {p.display_name}
            </Option>
          ))}
        </Select>
        {mine.length > 0 && (
          <Select
            label="Or someone in your household"
            placeholder="Or someone in your household"
            value={memberId}
            onValueChange={(v) => {
              setMemberId(v);
              setUserId("");
            }}
          >
            {mine.map((h) => (
              <Option key={h.id} value={h.id}>
                {h.name}
              </Option>
            ))}
          </Select>
        )}
        <p className="text-sm font-medium">{name} is my …</p>
        <Select
          label={`${name} is my`}
          value={kind}
          onValueChange={(v) => setKind(v as RelationKind)}
        >
          {KINDS.map(([k, l]) => (
            <Option key={k} value={k}>
              {l}
            </Option>
          ))}
        </Select>
        {kind === "other" && (
          <Input
            label="How are you related?"
            maxLength={40}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        )}
      </div>
    </Modal>
  );
}
