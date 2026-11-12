
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type !== "TRICYPHER_PROTECT") {
        return;
    }

    (async () => {
        try {
            const response = await fetch(
                "http://127.0.0.1:8000/v1/protect",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        text: message.text
                    })
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Protection failed");
            }

            sendResponse({
                success: true,
                protectedText: data.protected_text,
                detectedCount: data.detected_count
            });

        } catch (error) {
            console.error("TriCypher background error:", error);

            sendResponse({
                success: false,
                error: error.message
            });
        }
    })();

    return true;
});
