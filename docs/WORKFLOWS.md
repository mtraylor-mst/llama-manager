# Core Workflows

This guide describes the primary ways to interact with `llama-manager` to manage your `llama.cpp` server instances.

## 1. Importing Configurations

One of the most powerful features of `llama-manager` is its ability to "capture" a running server's configuration. If you have already started a `llama-server` manually via the terminal, you can import its exact settings into the manager.

### How to Import
1.  **Start your server**: Ensure your `llama-server` is running in a terminal.
2.  **Click "Import Config"**: In the top navigation bar, click the **Import Config** button.
3.  **Name your config**: Provide a name for the new configuration.
4.  **Review**: The system will parse the command-line flags and create a new configuration entry. If the settings are identical to an existing version, the system will notify you.

**Benefit**: This eliminates the need to manually re-enter dozens of complex command-line flags.

---

## 2. Managing Versions & Iteration

`llama-manager` treats configurations as evolving entities. Instead of overwriting settings, it creates new **versions**, allowing you to experiment safely.

### Navigating History
*   **Config View**: When viewing a configuration, you can see its latest settings and a summary of its version history.
*   **History Page**: Click on the configuration name to view the full list of all versions ever created for that model.

### Editing and Experimenting
There are three main ways to change your settings:

*   **Edit Latest**: Quickly adjust the parameters of the most recent version.
*   **Forking (Creating a New Version)**: If you want to try a new idea (e.g., "What if I increase the context size?") without losing your current setup, use the **Fork** option. This creates a new version based on the existing one.
*   **Duplicating**: Create an exact copy of a version to serve as a starting point for a new experiment.
*   **Deleting**: Remove a version that is no longer needed. You cannot delete the currently running version — stop it first.

### Parameter Organization
Settings are organized into logical categories to make tuning easier:
*   **Model Loading**: Paths, URLs, and LoRA adapters.
*   **GPU / Device**: Layers to offload, device selection, and flash attention.
*   **Sampling**: Temperature, Top-P, Top-K, and other generation controls.
*   **Context & Batching**: Context size, batch size, and parallel processing.
*   **Server**: Host, port, and API settings.

---

## 3. Server Lifecycle & Monitoring

Once a configuration is set, you can use the manager to control the actual server processes.

### Launching and Stopping
*   **Start**: From the configuration view or the main dashboard, click **Start** on the desired version. The server runs as a background subprocess with PID tracking (`/tmp/.llama-manager.pid`).
*   **Stop**: Click **Stop** to terminate the current running session.

### Real-Time Monitoring
*   **Live Logs**: Instead of switching back to your terminal, you can view the server's output directly in the web interface via the live log stream.
*   **Status Tracking**: The UI provides real-time feedback on whether a server is currently `Running` or `Stopped`, and which specific version is active.

### Benchmarking
To evaluate how a change affects performance:
1.  Select a version.
2.  Run the **Benchmark** command.
3.  The system will track metrics such as **Tokens Per Second (TPS)**, VRAM usage (MB), peak CPU %, and request duration, which are then stored in the version's history for comparison.

### Benchmark Comparison

View benchmarks across all versions of a single config from the config's benchmark page, or compare multiple configs side-by-side using the cross-config benchmark comparison view.

### Command Diff

To see exactly how two versions differ, use the command diff feature. It compares the generated command lines between two versions and shows which flags were added, removed, or changed. Accessible via the API at `/api/benchmarks/diff?v1=<id>&v2=<id>`.

### Common Options

Frequently-used parameters can be pinned to a **common options** panel that appears at the top of every version edit form. Toggle fields in and out of common options, reorder them via drag-and-drop, and customize their display labels.

---

## 4. Pre-Launch Validation

Before starting a server, you can validate a version's configuration to catch issues early:

1.  **Navigate to a version**: Open the edit form for any version.
2.  **Click Validate**: The system checks for missing model files, invalid parameter values, and VRAM fit estimates.
3.  **Review results**: Hard errors (e.g., missing model file) block launch. Warnings (e.g., low VRAM margin) are advisory only.

Validation runs automatically when you click **Start**, surfacing errors before the process is spawned.

---

## 5. Server Health Monitoring

The nav bar displays real-time server health:

*   **Response time badge**: When a server is running and healthy, the status shows response time (e.g., `Running (2ms)`).
*   **Unresponsive indicator**: If the llama-server HTTP API doesn't respond within 1 second, the badge shows `(Unresponsive)`.
*   **Dedicated health endpoint**: Visit `/server/health` for a JSON health report with detailed error information.

---

## 6. VRAM Safety Analysis

Estimate whether your configuration will fit in available GPU memory before launching:

1.  **Navigate to a version**: Open any version's view page.
2.  **View VRAM safety**: The page displays a color-coded estimate:
    *   **Green**: Comfortable margin — the config should run without OOM.
    *   **Yellow**: Tight margin — consider reducing `gpu_layers` or `ctx_size`.
    *   **Red**: Likely to exceed VRAM — adjust settings before launching.
3.  **First launch required**: The estimate requires cached model metadata. Run a server once to populate it, then check again.

---

## 7. VRAM Stress Testing

Find the maximum context size your hardware supports for a given configuration:

1.  **Navigate to the stress test page**: Visit `/vram-stress-test`.
2.  **Select a version**: Choose from versions marked as `working`.
3.  **Start the test**: The system performs binary search, launching llama-server at increasing context sizes until OOM.
4.  **Monitor progress**: Poll the test status to see phases (`initial_probe`, `binary_search`, `completed`) and data points.
5.  **Review results**: Once complete, the test reports the maximum safe context size and VRAM usage curve.

**Note**: Stress tests run in background threads and manage their own llama-server processes. Do not run other servers during a stress test.

---

## 8. Usage Analytics

Track which configs are used most and how they perform over time:

1.  **Navigate to analytics**: Visit `/usage-analytics`.
2.  **Review stats**: See per-config launch counts, average runtime, unique versions launched, and exit reason breakdowns.
3.  **Recent sessions**: View the 50 most recent launch/stop sessions with timestamps and exit reasons.

Usage data is recorded automatically when you start or stop a server through the manager interface. Sessions are tracked in the `config_usage` table.

---

## 9. Config Templates

Create reusable, parameterized presets from existing configurations:

1.  **Create from version**: From any version, save it as a template.
2.  **Define variables**: Mark fields (e.g., model path, context size) as templatable with `{{variable}}` placeholders.
3.  **Instantiate**: Create new configs from a template by filling in variable values.

Templates are stored in the `config_templates` and `template_variables` tables, and are useful for deploying similar configurations across multiple models.
