// Check if API is running and update status
async function checkStatus() {
    try {
        const response = await fetch('/health', { timeout: 2000 });
        if (response.ok) {
            const data = await response.json();
            document.querySelector('.status').innerHTML = `
                <span class="status-dot" style="background: var(--success)"></span>
                <span>Online | ${data.gpu_count} GPUs | ${data.model_loaded} models loaded</span>
            `;
        }
    } catch (e) {
        // API not running, that's fine for static docs
    }
}
checkStatus();
