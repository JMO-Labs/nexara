"use client";
/**
 * @file app/app/chat/page.tsx
 * @brief Chat root: editorial masthead + channel list / empty thread pane.
 */
import Box from "@mui/joy/Box";
import { ChatLayout } from "@/components/chat/ChatLayout";
import { PageMasthead } from "@/components/layout/PageMasthead";
import { useChannels, useDmThreads } from "@/hooks/useChat";

export default function ChatIndexPage() {
  const { data: channels } = useChannels();
  const { data: dms } = useDmThreads();
  const channelCount = (channels ?? []).filter(
    (c) => c.channel_type !== "direct",
  ).length;
  const count = channelCount + (dms?.length ?? 0);

  return (
    <Box
      sx={{
        flex: 1,
        width: "100%",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
        px: { xs: 1.5, md: 4, lg: 6 },
      }}
    >
      <Box
        sx={{
          flexShrink: 0,
          mx: { xs: -1.5, md: -4, lg: -6 },
          px: { xs: 1.5, md: 4, lg: 6 },
        }}
      >
        <PageMasthead
          title="Chat"
          size="md"
          meta={`${count} ${count === 1 ? "conversation" : "conversations"} open`}
        />
      </Box>
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          mx: { xs: -1.5, md: -4, lg: -6 },
        }}
      >
        <ChatLayout activeId={null} />
      </Box>
    </Box>
  );
}
