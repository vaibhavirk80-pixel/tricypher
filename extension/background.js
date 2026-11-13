
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {

    // PROTECT: Send original text to the local privacy engine.
    if (message.type === "TRICYPHER_PROTECT") {
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

                if (!response.ok) {
                    throw new Error("Protection failed.");
                }

                const data = await response.json();

                if (typeof data.protected_text !== "string") {
                    throw new Error("Invalid protection response.");
                }

                sendResponse({
                    success: true,
                    protectedText: data.protected_text,
                    detectedCount: data.detected_count,
                    detectedTypes: data.detected_types,
                    tokenMap: data.token_map
                });

            } catch (error) {
                console.error("TriCypher: Protection failed.");

                sendResponse({
                    success: false,
                    error: "Local protection failed."
                });
            }
        })();

        return true;
    }

    // RESTORE: Restore tokens using the local privacy engine.
    if (message.type === "TRICYPHER_RESTORE") {
        (async () => {
            try {
                const response = await fetch(
                    "http://127.0.0.1:8000/v1/restore",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            protected_text: message.text
                        })
                    }
                );

                if (!response.ok) {
                    throw new Error("Restoration failed.");
                }

                const data = await response.json();

                if (typeof data.restored_text !== "string") {
                    throw new Error("Invalid restoration response.");
                }

                sendResponse({
                    success: true,
                    restoredText: data.restored_text
                });

            } catch (error) {
                console.error("TriCypher: Restoration failed.");

                sendResponse({
                    success: false,
                    error: "Local restoration failed."
                });
            }
        })();

        return true;
    }
});
