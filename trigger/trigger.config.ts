import { defineConfig } from "@trigger.dev/sdk";

// Trigger.dev v4 config. The project ref comes from the dashboard
// (Project Settings) — set TRIGGER_PROJECT_REF in .env or pass
// `--project-ref` to the CLI. See trigger/README.md.
export default defineConfig({
  project: process.env.TRIGGER_PROJECT_REF ?? "proj_REPLACE_ME",
  dirs: ["./src"],
  maxDuration: 300, // seconds — hard wall-clock per task (M4: raise for real ccx)
  retries: {
    enabledInDev: true,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 1_000,
      maxTimeoutInMs: 30_000,
      factor: 2,
      randomize: true,
    },
  },
});
