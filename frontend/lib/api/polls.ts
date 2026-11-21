/**
 * @file lib/api/polls.ts
 * @brief Poll voting (polls are created inline with posts).
 */
import { apiPost, seg } from "./client";

/**
 * @brief Cast (or replace) the caller's vote.
 * @param pollId poll id
 * @param optionIds chosen option ids
 * @return updated counts
 */
export const votePoll = (pollId: string, optionIds: string[]) =>
  apiPost<{ total_votes: number }>(`/api/v1/polls/${seg(pollId)}/vote`, {
    option_ids: optionIds,
  });
