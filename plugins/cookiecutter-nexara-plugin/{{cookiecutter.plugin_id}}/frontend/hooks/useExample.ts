import { useQuery } from "@tanstack/react-query";

/** Example TanStack Query hook. Replace the fetch with your plugin API call. */
export function useExample() {
  return useQuery({
    queryKey: ["{{cookiecutter.plugin_id}}", "hello"],
    queryFn: async (): Promise<{ message: string }> => {
      const res = await fetch("/api/v1/plugins/{{cookiecutter.plugin_id}}/hello");
      return res.json();
    },
  });
}
