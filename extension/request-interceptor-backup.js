
(() => {
    console.log("TriCypher: Request interceptor loaded.");

    const originalFetch = window.fetch;

    function isConversationRequest(url) {
    return /\/backend-api\/f\/conversation(?:\?|$)/.test(url);
}

    function requestProtection(text) {
        return new Promise((resolve, reject) => {
            const requestId = crypto.randomUUID();

            const timeout = setTimeout(() => {
                window.removeEventListener("message", listener);
                reject(new Error("TriCypher protection timed out."));
            }, 15000);

            function listener(event) {
                if (event.source !== window) return;

                const data = event.data;

                if (
                    !data ||
                    data.type !== "TRICYPHER_PROTECT_RESULT" ||
                    data.requestId !== requestId
                ) {
                    return;
                }

                clearTimeout(timeout);
                window.removeEventListener("message", listener);

                if (
                    data.success !== true ||
                    typeof data.protectedText !== "string"
                ) {
                    reject(new Error("TriCypher protection failed."));
                    return;
                }

                resolve(data.protectedText);
            }

            window.addEventListener("message", listener);

            window.postMessage({
                type: "TRICYPHER_PROTECT_REQUEST",
                requestId,
                text
            }, window.location.origin);
        });
    }

    window.fetch = async function(input, init) {
        const url = input instanceof Request
            ? input.url
            : String(input);

        if (!isConversationRequest(url)) {
            return originalFetch.apply(this, arguments);
        }

        try {
            if (!init || typeof init.body !== "string") {
                throw new Error("Unsupported conversation request format.");
            }

            const payload = JSON.parse(init.body);

            if (!Array.isArray(payload.messages)) {
                throw new Error("Unexpected conversation payload.");
            }

            const userMessage = [...payload.messages]
                .reverse()
                .find(message => message.author?.role === "user");

            if (!userMessage || !Array.isArray(userMessage.content?.parts)) {
                throw new Error("User message not found.");
            }

            const originalParts = userMessage.content.parts;

            for (let i = 0; i < originalParts.length; i++) {
                if (typeof originalParts[i] === "string") {
                    originalParts[i] = await requestProtection(
                        originalParts[i]
                    );
                }
            }

            const updatedInit = {
                ...init,
                body: JSON.stringify(payload)
            };

            console.log("TriCypher: Outgoing prompt protection completed.");

            return originalFetch.call(this, input, updatedInit);

        } catch (error) {
            console.error("TriCypher: Outgoing request blocked.");
            throw new Error("TriCypher blocked an unprotected request.");
        }
    };
})();
