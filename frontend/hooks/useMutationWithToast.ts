"use client";
/**
 * @file hooks/useMutationWithToast.ts
 * @brief Wrapper around useMutation that auto-handles success/error toasts.
 */
import { useMutation, type UseMutationOptions } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useToasts } from "@/stores/toasts";

interface ToastOpts {
  successKey?: string;
  errorKey?: string;
  silentSuccess?: boolean;
  silentError?: boolean;
}

export function useMutationWithToast<
  TData = unknown,
  TError extends Error = Error,
  TVars = unknown,
  TContext = unknown,
>(
  options: Omit<
    UseMutationOptions<TData, TError, TVars, TContext>,
    "onSuccess" | "onError"
  > &
    ToastOpts & {
      onSuccess?: (data: TData, variables: TVars, context: TContext) => void;
      onError?: (error: TError, variables: TVars, context: TContext) => void;
    },
) {
  const t = useTranslations();
  const push = useToasts((s) => s.push);
  const {
    successKey,
    errorKey,
    silentSuccess,
    silentError,
    onSuccess,
    onError,
    ...rest
  } = options;

  return useMutation<TData, TError, TVars, TContext>({
    ...rest,
    onSuccess: (data, variables, context) => {
      if (!silentSuccess && successKey) {
        push({ variant: "success", message: t(successKey) });
      }
      if (onSuccess) {
        onSuccess(data, variables, context as TContext);
      }
    },
    onError: (error, variables, context) => {
      if (!silentError) {
        const apiError = error as {
          body?: { error?: { message?: string } };
          status?: number;
        };
        const msg =
          apiError?.body?.error?.message ??
          (typeof apiError?.status === "number" && error.message
            ? error.message
            : undefined) ??
          (errorKey ? t(errorKey) : t("toasts.errors.generic"));
        push({ variant: "danger", message: msg });
      }
      if (onError) {
        onError(error, variables, context as TContext);
      }
    },
  });
}
