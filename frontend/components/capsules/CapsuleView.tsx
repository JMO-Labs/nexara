/**
 * @file components/capsules/CapsuleView.tsx
 * @brief One capsule: sealed placeholder, or the opened message with photos.
 */
import { Hourglass, Lock } from "lucide-react";
import { mediaFileUrl } from "@/lib/api/media";
import {
  isOpen,
  type CapsuleOpen,
  type CapsuleSealed,
} from "@/lib/api/capsules";
import { fmtDate } from "./SealedCard";

/**
 * @param capsule sealed or full capsule
 * @param mine viewer is the author
 * @return article
 */
export function CapsuleView({
  capsule,
  mine,
}: {
  capsule: CapsuleSealed | CapsuleOpen;
  mine: boolean;
}) {
  const open = isOpen(capsule);
  return (
    <article className="glass flex flex-col gap-4 rounded-3xl p-5">
      <header className="flex items-start gap-3">
        {open && capsule.opened_at ? (
          <Hourglass aria-hidden className="size-5" />
        ) : (
          <Lock aria-hidden className="text-muted size-5" />
        )}
        <div>
          <h1 className="text-xl font-semibold">{capsule.title}</h1>
          <p className="text-muted text-sm">
            From {capsule.author.display_name} · To {capsule.recipients_summary}
          </p>
        </div>
      </header>
      {open ? (
        <>
          {mine && !capsule.opened_at && (
            <p className="text-sm" role="status">
              Sealed until {fmtDate(capsule.open_at)}. Only you can read this
              until then.
            </p>
          )}
          <p className="whitespace-pre-wrap">{capsule.body}</p>
          {capsule.media.length > 0 && (
            <ul className="m-0 grid list-none grid-cols-2 gap-2 p-0 sm:grid-cols-3">
              {capsule.media.map((id) => (
                // eslint-disable-next-line @next/next/no-img-element
                <li key={id}>
                  <img
                    src={mediaFileUrl(id)}
                    alt="Photo from the capsule"
                    className="aspect-square w-full rounded-xl object-cover"
                  />
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <p role="status">
          This capsule is sealed. It opens on {fmtDate(capsule.open_at)}.
        </p>
      )}
    </article>
  );
}
