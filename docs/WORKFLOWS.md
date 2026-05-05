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
*   **Start**: From the configuration view or the main dashboard, click **Start** on the desired version. The server will run in a background `screen` session.
*   **Stop**: Click **Stop** to terminate the current running session.

### Real-Time Monitoring
*   **Live Logs**: Instead of switching back to your terminal, you can view the server's output directly in the web interface via the live log stream.
*   **Status Tracking**: The UI provides real-time feedback on whether a server is currently `Running` or `Stopped`, and which specific version is active.

### Benchmarking
To evaluate how a change affects performance:
1.  Select a version.
2.  Run the **Benchmark** command.
3.  The system will track metrics such as **Tokens Per Second (TPS)**, load time, and VRAM usage, which are then stored in the version's history for comparison.
