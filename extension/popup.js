
const API_URL = "http://127.0.0.1:8000";

const inputText = document.getElementById("inputText");
const protectBtn = document.getElementById("protectBtn");
const resultSection = document.getElementById("resultSection");
const protectedOutput = document.getElementById("protectedOutput");
const detectionCount = document.getElementById("detectionCount");
const copyBtn = document.getElementById("copyBtn");
const message = document.getElementById("message");

protectBtn.addEventListener("click", async () => {
    const text = inputText.value.trim();

    if (!text) {
        message.textContent = "Please enter some text first.";
        resultSection.classList.add("hidden");
        return;
    }

    protectBtn.disabled = true;
    protectBtn.textContent = "Protecting...";
    message.textContent = "";

    try {
        const response = await fetch(`${API_URL}/v1/protect`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ text })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        protectedOutput.textContent = data.protected_text;
        detectionCount.textContent =
            `${data.detected_count} detected`;

        resultSection.classList.remove("hidden");
        message.textContent = "Your prompt has been protected!";

    } catch (error) {
        message.textContent =
            "Could not connect to TriCypher. Is the API running?";
        console.error("TriCypher error:", error);

    } finally {
        protectBtn.disabled = false;
        protectBtn.textContent = "🛡️ Protect My Data";
    }
});

copyBtn.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(
            protectedOutput.textContent
        );

        message.textContent = "Protected text copied!";
    } catch (error) {
        message.textContent = "Could not copy protected text.";
    }
});
