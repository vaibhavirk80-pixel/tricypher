
(() => {
    console.log("TriCypher: Protection bridge loaded.");

    const pendingRequests = new Set();

    window.addEventListener("message", async (event) => {
        if (event.source !== window) return;
        if (event.origin !== window.location.origin) return;

        const message = event.data;

        const allowedTypes = [
            "TRICYPHER_PROTECT_REQUEST",
            "TRICYPHER_RESTORE_REQUEST"
        ];

        if (
            !message ||
            !allowedTypes.includes(message.type) ||
            typeof message.requestId !== "string" ||
            typeof message.text !== "string"
        ) {
            return;
        }

        const { requestId, text, type } = message;

        if (pendingRequests.has(requestId)) return;
        pendingRequests.add(requestId);

        const isRestore = type === "TRICYPHER_RESTORE_REQUEST";

        try {
            const response = await chrome.runtime.sendMessage({
                type: isRestore
                    ? "TRICYPHER_RESTORE"
                    : "TRICYPHER_PROTECT",
                text
            });

            if (!response || !response.success) {
                throw new Error("Local operation failed.");
            }

            window.postMessage({
                type: isRestore
                    ? "TRICYPHER_RESTORE_RESULT"
                    : "TRICYPHER_PROTECT_RESULT",
                requestId,
                success: true,
                protectedText: response.protectedText,
                restoredText: response.restoredText
            }, window.location.origin);

        } catch (error) {
            window.postMessage({
                type: isRestore
                    ? "TRICYPHER_RESTORE_RESULT"
                    : "TRICYPHER_PROTECT_RESULT",
                requestId,
                success: false
            }, window.location.origin);

            console.error("TriCypher: Local operation failed.");
        } finally {
            pendingRequests.delete(requestId);
        }
    });

    console.log("TriCypher: Protection and restoration bridge ready.");
})();
