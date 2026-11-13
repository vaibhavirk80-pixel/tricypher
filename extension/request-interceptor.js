
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

function requestRestoration(text) {
    return new Promise((resolve, reject) => {
        const requestId = crypto.randomUUID();

        const timeout = setTimeout(() => {
            window.removeEventListener("message", listener);
            reject(new Error("TriCypher restoration timed out."));
        }, 15000);

        function listener(event) {
            if (event.source !== window) return;

            const data = event.data;

            if (
                !data ||
                data.type !== "TRICYPHER_RESTORE_RESULT" ||
                data.requestId !== requestId
            ) {
                return;
            }

            clearTimeout(timeout);
            window.removeEventListener("message", listener);

            if (
                data.success !== true ||
                typeof data.restoredText !== "string"
            ) {
                reject(new Error("TriCypher restoration failed."));
                return;
            }

            resolve(data.restoredText);
        }

        window.addEventListener("message", listener);

        window.postMessage({
            type: "TRICYPHER_RESTORE_REQUEST",
            requestId,
            text
        }, window.location.origin);
    });
}

async function restoreSseResponse(response) {
    const contentType = response.headers.get("content-type") || "";

    if (!contentType.includes("text/event-stream")) {
        return response;
    }

    const originalBody = await response.clone().text();

    const events = originalBody.split(/\r?\n\r?\n/);

    let assistantText = "";

    for (const eventBlock of events) {
        const dataLines = eventBlock
            .split(/\r?\n/)
            .filter(line => line.startsWith("data:"))
            .map(line => line.slice(5).trim());

        if (!dataLines.length) continue;

        try {
            const payload = JSON.parse(dataLines.join("\n"));

            const patches = Array.isArray(payload.v)
                ? payload.v
                : [payload];

            for (const patch of patches) {
                if (
                    patch.p === "/message/content/parts/0" &&
                    typeof patch.v === "string"
                ) {
                    if (
                        patch.o === "append" ||
                        patch.o === "replace"
                    ) {
                        assistantText = patch.o === "replace"
                            ? patch.v
                            : assistantText + patch.v;
                    }
                }
            }
        } catch {
            // Preserve non-JSON SSE events unchanged.
        }
    }

    if (!assistantText || !assistantText.includes("<TC_")) {
        return new Response(originalBody, {
            status: response.status,
            statusText: response.statusText,
            headers: response.headers
        });
    }

    let restoredText;

try {
    console.log("TriCypher: Restored response:", restoredText);
    console.log("TriCypher: Complete assistant text collected.");
    restoredText = await requestRestoration(assistantText);
    console.log(
    "TriCypher: Local restoration successful:",
    restoredText !== assistantText
);
} catch (error) {
    console.error("TriCypher: Response restoration failed.");
    return response;
}

    const replacementEvent =
        "event: delta\n" +
        "data: " + JSON.stringify({
            p: "/message/content/parts/0",
            o: "replace",
            v: restoredText
        }) + "\n\n";

    let insertionIndex = events.findIndex(block =>
        block.includes("message_stream_complete") ||
        block.includes("[DONE]")
    );

    if (insertionIndex === -1) {
        insertionIndex = events.length - 1;
    }

    events.splice(insertionIndex, 0, replacementEvent.trimEnd());

    const headers = new Headers(response.headers);
    headers.delete("content-length");
    headers.delete("content-encoding");

    return new Response(events.join("\n\n") + "\n\n", {
        status: response.status,
        statusText: response.statusText,
        headers
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

            const response = await originalFetch.call(
    this,
    input,
    updatedInit
);

try {
    return await restoreSseResponse(response);
} catch (error) {
    console.error("TriCypher: Response restoration failed.");
    return response;
}

        } catch (error) {
            console.error("TriCypher: Outgoing request blocked.");
            throw new Error("TriCypher blocked an unprotected request.");
        }
    };
})();
