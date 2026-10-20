"use client";
/**
 * @file components/admin/PromptsTab.tsx
 * @brief Admin prompts management tab with master-detail layout.
 *        Left pane: compact list. Right pane: edit form.
 */
import { useState } from "react";
import {
  usePrompts,
  useCreatePrompt,
  useUpdatePrompt,
  useDeletePrompt,
  useSeedBuiltinPrompts,
} from "@/hooks/usePrompts";
import Stack from "@mui/joy/Stack";
import Button from "@mui/joy/Button";
import Input from "@mui/joy/Input";
import Textarea from "@mui/joy/Textarea";
import FormControl from "@mui/joy/FormControl";
import FormLabel from "@mui/joy/FormLabel";
import Select from "@mui/joy/Select";
import Option from "@mui/joy/Option";
import Chip from "@mui/joy/Chip";
import CircularProgress from "@mui/joy/CircularProgress";
import Alert from "@mui/joy/Alert";
import Typography from "@mui/joy/Typography";
import Switch from "@mui/joy/Switch";
import Sheet from "@mui/joy/Sheet";
import Modal from "@mui/joy/Modal";
import ModalDialog from "@mui/joy/ModalDialog";
import ModalClose from "@mui/joy/ModalClose";
import { PlusIcon } from "@heroicons/react/24/outline";
import type { PromptCreate, PromptUpdate } from "@/lib/api/prompts";

const FREQUENCY_COLORS: Record<
  string,
  "warning" | "primary" | "danger" | "neutral" | "success"
> = {
  annual_date: "warning",
  weekly: "primary",
  monthly: "danger",
  custom: "neutral",
  one_time: "success",
};

function getFrequencyColor(frequency: string) {
  return FREQUENCY_COLORS[frequency] || "neutral";
}

export function PromptsTab() {
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newPromptForm, setNewPromptForm] = useState<PromptCreate>({
    title: "",
    body: "",
    frequency: "annual_date",
  });

  const { data: prompts = [], isLoading, error } = usePrompts();
  const updateMutation = useUpdatePrompt();
  const createMutation = useCreatePrompt();
  const deleteMutation = useDeletePrompt();
  const seedMutation = useSeedBuiltinPrompts();

  const selectedPrompt = selectedPromptId
    ? prompts.find((p) => p.id === selectedPromptId)
    : null;

  if (isLoading) {
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ py: 8 }}>
        <CircularProgress />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert color="danger" variant="soft">
        Failed to load prompts
      </Alert>
    );
  }

  if (prompts.length === 0) {
    return (
      <Stack
        alignItems="center"
        justifyContent="center"
        spacing={2}
        sx={{ py: 12 }}
      >
        <Typography level="title-lg">No prompts yet</Typography>
        <Button
          startDecorator={<PlusIcon width={18} height={18} />}
          color="primary"
          variant="solid"
          onClick={() => seedMutation.mutate()}
          loading={seedMutation.isPending}
        >
          Seed builtin library
        </Button>
      </Stack>
    );
  }

  const handleToggleEnabled = (promptId: string, currentEnabled: boolean) => {
    updateMutation.mutate({
      promptId,
      payload: { enabled: !currentEnabled },
    });
  };

  const handleCreatePrompt = () => {
    if (newPromptForm.title.trim() && newPromptForm.body.trim()) {
      createMutation.mutate(newPromptForm);
      setNewPromptForm({
        title: "",
        body: "",
        frequency: "annual_date",
      });
      setIsCreating(false);
    }
  };

  const handleUpdateSelectedPrompt = (update: PromptUpdate) => {
    if (selectedPromptId) {
      updateMutation.mutate({
        promptId: selectedPromptId,
        payload: update,
      });
    }
  };

  const handleDeletePrompt = (promptId: string) => {
    deleteMutation.mutate(promptId);
    if (selectedPromptId === promptId) {
      setSelectedPromptId(null);
    }
  };

  return (
    <Stack
      direction="row"
      spacing={3}
      sx={{
        height: "600px",
        "@media (max-width: 900px)": {
          flexDirection: "column",
          height: "auto",
        },
      }}
    >
      {/* Left Pane: Prompt List */}
      <Stack
        spacing={2}
        sx={{
          width: { xs: "100%", md: "40%" },
          maxWidth: { md: "480px" },
          overflow: "auto",
        }}
      >
        <Stack direction="row" spacing={1} justifyContent="space-between">
          <Typography level="title-md">Prompts</Typography>
          <Button
            size="sm"
            startDecorator={<PlusIcon width={16} height={16} />}
            color="primary"
            variant="solid"
            onClick={() => setIsCreating(true)}
          >
            New
          </Button>
        </Stack>

        <Stack spacing={1}>
          {prompts.map((prompt) => (
            <Sheet
              key={prompt.id}
              variant="outlined"
              onClick={() => setSelectedPromptId(prompt.id)}
              sx={{
                p: 2,
                cursor: "pointer",
                borderRadius: "sm",
                transition: "background-color 0.2s",
                backgroundColor:
                  selectedPromptId === prompt.id
                    ? "action.selected"
                    : undefined,
                "&:hover": {
                  backgroundColor: "action.hover",
                },
              }}
            >
              <Stack spacing={1}>
                <Stack direction="row" spacing={1} alignItems="flex-start">
                  <Switch
                    checked={prompt.enabled}
                    onChange={() =>
                      handleToggleEnabled(prompt.id, prompt.enabled)
                    }
                    onClick={(e) => e.stopPropagation()}
                    slotProps={{
                      input: {
                        "aria-label": `Toggle ${prompt.title}`,
                      },
                    }}
                  />
                  <Stack flex={1} spacing={0.5}>
                    <Typography
                      level="body-sm"
                      sx={{
                        fontWeight: 500,
                        opacity: prompt.enabled ? 1 : 0.6,
                      }}
                    >
                      {prompt.title}
                    </Typography>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip
                        size="sm"
                        variant="soft"
                        color={getFrequencyColor(prompt.frequency)}
                      >
                        {prompt.frequency.replace(/_/g, " ")}
                      </Chip>
                      {prompt.next_fire_at && (
                        <Typography
                          level="body-xs"
                          sx={{ color: "text.tertiary" }}
                        >
                          Soon
                        </Typography>
                      )}
                    </Stack>
                  </Stack>
                </Stack>
              </Stack>
            </Sheet>
          ))}
        </Stack>
      </Stack>

      {/* Right Pane: Edit Form */}
      {selectedPrompt && (
        <Stack
          spacing={2}
          sx={{
            flex: 1,
            overflow: "auto",
            minWidth: 0,
          }}
        >
          <Typography level="title-md">Edit Prompt</Typography>

          <FormControl>
            <FormLabel>Title</FormLabel>
            <Input
              value={selectedPrompt.title}
              onChange={(e) =>
                handleUpdateSelectedPrompt({ title: e.target.value })
              }
              placeholder="Prompt title"
            />
          </FormControl>

          <FormControl>
            <FormLabel>Body</FormLabel>
            <Textarea
              minRows={3}
              value={selectedPrompt.body}
              onChange={(e) =>
                handleUpdateSelectedPrompt({ body: e.target.value })
              }
              placeholder="Prompt body"
            />
          </FormControl>

          <FormControl>
            <FormLabel>Frequency</FormLabel>
            <Select
              value={selectedPrompt.frequency}
              onChange={(_, val) => {
                if (val) {
                  handleUpdateSelectedPrompt({ frequency: val });
                }
              }}
            >
              <Option value="annual_date">Annual Date</Option>
              <Option value="weekly">Weekly</Option>
              <Option value="monthly">Monthly</Option>
              <Option value="custom">Custom</Option>
              <Option value="one_time">One Time</Option>
            </Select>
          </FormControl>

          {selectedPrompt.frequency === "annual_date" && (
            <>
              <FormControl>
                <FormLabel>Month</FormLabel>
                <Select
                  value={String(selectedPrompt.trigger_month || "")}
                  onChange={(_, val) => {
                    if (val) {
                      handleUpdateSelectedPrompt({
                        trigger_month: parseInt(val),
                      });
                    }
                  }}
                >
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                    <Option key={m} value={String(m)}>
                      {new Date(2024, m - 1).toLocaleString("default", {
                        month: "long",
                      })}
                    </Option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Day</FormLabel>
                <Select
                  value={String(selectedPrompt.trigger_day || "")}
                  onChange={(_, val) => {
                    if (val) {
                      handleUpdateSelectedPrompt({
                        trigger_day: parseInt(val),
                      });
                    }
                  }}
                >
                  {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
                    <Option key={d} value={String(d)}>
                      {d}
                    </Option>
                  ))}
                </Select>
              </FormControl>
            </>
          )}

          <FormControl>
            <FormLabel>Prompt Type</FormLabel>
            <Select
              value={selectedPrompt.prompt_type}
              onChange={(_, val) => {
                if (val) {
                  handleUpdateSelectedPrompt({ prompt_type: val });
                }
              }}
            >
              <Option value="standard">Standard</Option>
              <Option value="interest_capture">Interest Capture</Option>
            </Select>
          </FormControl>

          {selectedPrompt.prompt_type === "interest_capture" && (
            <>
              <FormControl>
                <FormLabel>Interest Category Slug</FormLabel>
                <Input
                  value={selectedPrompt.interest_category_slug || ""}
                  onChange={(e) =>
                    handleUpdateSelectedPrompt({
                      interest_category_slug: e.target.value || null,
                    })
                  }
                  placeholder="e.g., cooking, music, books"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Interest Capture Hint</FormLabel>
                <Textarea
                  minRows={2}
                  value={selectedPrompt.interest_capture_hint || ""}
                  onChange={(e) =>
                    handleUpdateSelectedPrompt({
                      interest_capture_hint: e.target.value || null,
                    })
                  }
                  placeholder="Hint for users to capture interests"
                />
              </FormControl>
            </>
          )}

          <Stack direction="row" spacing={2}>
            <Button
              color="danger"
              variant="soft"
              onClick={() => handleDeletePrompt(selectedPrompt.id)}
              loading={deleteMutation.isPending}
            >
              Delete
            </Button>
          </Stack>
        </Stack>
      )}

      {/* New Prompt Modal */}
      <Modal
        aria-labelledby="new-prompt-modal"
        open={isCreating}
        onClose={() => setIsCreating(false)}
      >
        <ModalDialog>
          <ModalClose variant="plain" sx={{ m: 1 }} />
          <Typography
            component="h2"
            id="new-prompt-modal"
            level="inherit"
            fontSize="1.25em"
            mb={2}
          >
            Create New Prompt
          </Typography>

          <FormControl>
            <FormLabel>Title</FormLabel>
            <Input
              value={newPromptForm.title}
              onChange={(e) =>
                setNewPromptForm({ ...newPromptForm, title: e.target.value })
              }
              placeholder="Prompt title"
            />
          </FormControl>

          <FormControl>
            <FormLabel>Body</FormLabel>
            <Textarea
              minRows={3}
              value={newPromptForm.body}
              onChange={(e) =>
                setNewPromptForm({ ...newPromptForm, body: e.target.value })
              }
              placeholder="Prompt body"
            />
          </FormControl>

          <FormControl>
            <FormLabel>Frequency</FormLabel>
            <Select
              value={newPromptForm.frequency}
              onChange={(_, val) => {
                if (val) {
                  setNewPromptForm({ ...newPromptForm, frequency: val });
                }
              }}
            >
              <Option value="annual_date">Annual Date</Option>
              <Option value="weekly">Weekly</Option>
              <Option value="monthly">Monthly</Option>
              <Option value="custom">Custom</Option>
              <Option value="one_time">One Time</Option>
            </Select>
          </FormControl>

          <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
            <Button
              variant="plain"
              color="neutral"
              onClick={() => setIsCreating(false)}
            >
              Cancel
            </Button>
            <Button
              variant="solid"
              color="primary"
              onClick={handleCreatePrompt}
              loading={createMutation.isPending}
            >
              Create
            </Button>
          </Stack>
        </ModalDialog>
      </Modal>
    </Stack>
  );
}
