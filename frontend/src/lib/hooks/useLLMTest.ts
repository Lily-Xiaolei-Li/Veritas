import { useMutation } from "@tanstack/react-query";
import { testLLMProvider } from "@/lib/api/llm";

export function useTestLLMProvider() {
  return useMutation({
    mutationFn: (args: { provider: string; model?: string | null }) =>
      testLLMProvider(args),
  });
}
