/**
 * @file tests/components/feed/PollCard.test.ts
 * @brief Tests for the PollCard component.
 *
 * Verifies poll question display, voting, results visibility,
 * anonymous label, after_expiry hidden state, and vote count display.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import PollCard from "~/components/feed/PollCard.vue";

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() }),
}));

const basePoll = {
  id: "poll-1",
  post_id: "post-1",
  poll_type: "single",
  question: "Favorite color?",
  options: [
    { id: "opt-1", label: "Red", image_media_id: null, position: 0, vote_count: 3, voters: [] },
    { id: "opt-2", label: "Blue", image_media_id: null, position: 1, vote_count: 5, voters: [] },
  ],
  is_anonymous: false,
  result_visibility: "after_vote",
  expires_at: null,
  closed: false,
  total_votes: 8,
  user_vote: null,
  created_at: "2026-01-01T00:00:00Z",
};

describe("PollCard", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("renders question and options", () => {
    const wrapper = mount(PollCard, { props: { poll: basePoll } });
    expect(wrapper.text()).toContain("Favorite color?");
    expect(wrapper.text()).toContain("Red");
    expect(wrapper.text()).toContain("Blue");
  });

  it("shows radio inputs for single-choice polls", () => {
    const wrapper = mount(PollCard, { props: { poll: basePoll } });
    expect(wrapper.findAll('input[type="radio"]').length).toBe(2);
  });

  it("shows checkbox inputs for multiple-choice polls", () => {
    const multiPoll = { ...basePoll, poll_type: "multiple" };
    const wrapper = mount(PollCard, { props: { poll: multiPoll } });
    expect(wrapper.findAll('input[type="checkbox"]').length).toBe(2);
  });

  it("shows results after user voted (after_vote visibility)", () => {
    const votedPoll = { ...basePoll, user_vote: ["opt-1"] };
    const wrapper = mount(PollCard, { props: { poll: votedPoll } });
    expect(wrapper.find('[data-testid="poll-results"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="poll-vote-count"]').exists()).toBe(true);
  });

  it("shows anonymous label", () => {
    const anonPoll = { ...basePoll, is_anonymous: true };
    const wrapper = mount(PollCard, { props: { poll: anonPoll } });
    expect(wrapper.text()).toMatch(/anonymous/i);
  });

  it("emits voted event with selected option ids", async () => {
    const wrapper = mount(PollCard, { props: { poll: basePoll } });
    await wrapper.find('input[type="radio"][value="opt-1"]').setValue(true);
    await wrapper.find('[data-testid="poll-vote-btn"]').trigger("click");
    expect(wrapper.emitted("voted")).toBeTruthy();
    expect(wrapper.emitted("voted")![0]).toEqual(["poll-1", ["opt-1"]]);
  });

  it("shows vote-recorded message for after_expiry polls", async () => {
    const futureExpiry = new Date(Date.now() + 86400000).toISOString();
    const afterExpiryPoll = {
      ...basePoll,
      result_visibility: "after_expiry",
      expires_at: futureExpiry,
      total_votes: 0,
      options: basePoll.options.map((o) => ({ ...o, vote_count: 0 })),
    };
    const wrapper = mount(PollCard, { props: { poll: afterExpiryPoll } });

    // Vote on it
    await wrapper.find('input[type="radio"][value="opt-1"]').setValue(true);
    await wrapper.find('[data-testid="poll-vote-btn"]').trigger("click");

    // Should show voted-hidden state, not results
    expect(wrapper.find('[data-testid="poll-voted-hidden"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="poll-results"]').exists()).toBe(false);
  });

  it("shows results for after_expiry polls when closed", () => {
    const closedPoll = {
      ...basePoll,
      result_visibility: "after_expiry",
      closed: true,
      user_vote: ["opt-1"],
    };
    const wrapper = mount(PollCard, { props: { poll: closedPoll } });
    expect(wrapper.find('[data-testid="poll-results"]').exists()).toBe(true);
  });

  it("always shows results when visibility is 'always'", () => {
    const alwaysPoll = { ...basePoll, result_visibility: "always" };
    const wrapper = mount(PollCard, { props: { poll: alwaysPoll } });
    expect(wrapper.find('[data-testid="poll-results"]').exists()).toBe(true);
  });

  it("shows expiry countdown when poll has expires_at", () => {
    const futureExpiry = new Date(Date.now() + 7200000).toISOString();
    const expiringPoll = { ...basePoll, expires_at: futureExpiry };
    const wrapper = mount(PollCard, { props: { poll: expiringPoll } });
    expect(wrapper.find('[data-testid="poll-expiry"]').exists()).toBe(true);
  });

  it("shows closed badge when poll is closed", () => {
    const closedPoll = { ...basePoll, closed: true, user_vote: ["opt-1"] };
    const wrapper = mount(PollCard, { props: { poll: closedPoll } });
    expect(wrapper.find('[data-testid="poll-closed"]').exists()).toBe(true);
  });

  it("shows voter badges on non-anonymous polls with results", () => {
    const pollWithVoters = {
      ...basePoll,
      user_vote: ["opt-1"],
      options: [
        {
          id: "opt-1", label: "Red", image_media_id: null, position: 0, vote_count: 1,
          voters: [{ id: "u1", display_name: "Alice", avatar_url: null }],
        },
        {
          id: "opt-2", label: "Blue", image_media_id: null, position: 1, vote_count: 1,
          voters: [{ id: "u2", display_name: "Bob", avatar_url: null }],
        },
      ],
    };
    const wrapper = mount(PollCard, { props: { poll: pollWithVoters } });
    expect(wrapper.findAll('[data-testid="poll-voters"]').length).toBe(2);
    expect(wrapper.text()).toContain("Alice");
    expect(wrapper.text()).toContain("Bob");
  });

  it("hides voter badges on anonymous polls", () => {
    const anonPoll = {
      ...basePoll,
      is_anonymous: true,
      result_visibility: "always",
      options: [
        {
          id: "opt-1", label: "Red", image_media_id: null, position: 0, vote_count: 1,
          voters: [],
        },
        {
          id: "opt-2", label: "Blue", image_media_id: null, position: 1, vote_count: 1,
          voters: [],
        },
      ],
    };
    const wrapper = mount(PollCard, { props: { poll: anonPoll } });
    expect(wrapper.findAll('[data-testid="poll-voters"]').length).toBe(0);
  });
});
