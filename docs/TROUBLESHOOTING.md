# Troubleshooting & Maintenance

This guide addresses common issues you might encounter while using or maintaining `llama-manager`.

## Common Issues

### 1. Database Connectivity & Errors
If you see errors related to "Database connection failed" or "Access denied":
*   **Check Environment Variables**: Ensure `LLAMA_DB_HOST`, `LLAMA_DB_USER`, `LLAMA_DB_PASS`, and `LLAMA_DB_NAME` are correctly set.
*   **Verify Database Status**: Ensure your MySQL/MariaDB service is running.
*   **Schema Check**: If you get "Table not found" errors, ensure you have run the schema initialization:
    ```bash
    mysql -h $HOST -u $USER -p llama_configs < schema.sql
    ```

### 2. Server Management Issues
`llama-manager` uses Python's built-in `subprocess.Popen` to manage server processes with PID file tracking in `/tmp/.llama-manager.pid`.

*   **Server Fails to Start**: 
    *   Verify the path to your `llama-server` binary in the `LLAMA_SERVER_BINARY` environment variable.
    *   Try running the generated command manually in your terminal to see if `llama.cpp` reports any errors (e.g., invalid flags or missing model files).
*   **Permission Denied**: Ensure the user running `llama-manager` has permission to execute the `llama-server` binary and write to `/tmp/`.

### 3. Model & Resource Issues
*   **Model Not Found**: Check that the `LLAMA_MODEL_DIR` environment variable points to the correct directory and that your `.gguf` files are located there.
*   **Out of VRAM (OOM)**: If the server crashes or fails to start when loading a model, you likely have too many GPU layers offloaded. 
    *   **Solution**: Decrease the `GPU Layers` parameter in the configuration.
*   **Slow Performance**: If TPS is lower than expected, check if you are utilizing GPU offloading effectively or if your `context_size` is too large for your available memory.

### 4. Application Dependencies
If you encounter `ImportError` or similar:
*   **Missing Packages**: Ensure all dependencies are installed:
    ```bash
    pip install -r requirements.txt
    ```
*   **Benchmarking Errors**: The benchmark service requires `psutil` for CPU monitoring. If it's missing, install it via `pip install psutil`.

---

## Maintenance

### Environment Variables
The application behavior is heavily driven by environment variables. If you change any of these (especially database or binary paths), you must restart the `llama-manager` process for the changes to take effect.

### Logs
If the web interface is unresponsive or behaving unexpectedly, check the following:

1.  **Application Logs**: Check the terminal output where `run.py` was started.
2.  **Server Logs**: `llama-manager` captures the output of the `llama-server` process. You can view these in real-time through the **Live Logs** feature in the web UI.
3.  **System Logs**: If the llama-server process or database is failing, check your system logs (e.g., `journalctl` on Linux).
