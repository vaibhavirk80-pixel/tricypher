
(() => {
    console.log("TriCypher: Protection script loaded.");

    let isProtecting = false;
    let allowNextSend = false;

    const SEND_SELECTOR = 'button[aria-label="Send"]';
    const EDITOR_SELECTOR =
        'div[role="textbox"][aria-label="Ask ChatGPT"]';

    function getPromptBox() {
        return document.querySelector(EDITOR_SELECTOR);
    }

    function getPromptText(editor) {
        return editor.innerText.trim();
    }

    function setPromptText(editor, text) {
    editor.focus();

    const selection = window.getSelection();
    const range = document.createRange();

    range.selectNodeContents(editor);
    selection.removeAllRanges();
    selection.addRange(range);

    const inserted = document.execCommand(
        "insertText",
        false,
        text
    );
    console.log("TriCypher: Insert result:", inserted);
console.log("TriCypher: Editor after insertion:", editor.innerText);
console.log("TriCypher: Expected protected text:", text);

    const normalize = (value) =>
        value.replace(/\s+/g, " ").trim();

    const actualText = normalize(editor.innerText);
    const expectedText = normalize(text);

    if (!inserted || actualText !== expectedText) {
        throw new Error("Could not safely replace the prompt.");
    }
}

    function protectWithBackground(originalText) {
        return new Promise((resolve, reject) => {
            chrome.runtime.sendMessage(
                {
                    type: "TRICYPHER_PROTECT",
                    text: originalText
                },
                (response) => {
                    if (chrome.runtime.lastError) {
                        reject(
                            new Error(chrome.runtime.lastError.message)
                        );
                        return;
                    }

                    if (!response || !response.success) {
                        reject(
                            new Error(
                                response?.error || "Protection failed."
                            )
                        );
                        return;
                    }

                    resolve(response);
                }
            );
        });
    }

    
document.addEventListener("click", async (event) => {
    if (!(event.target instanceof Element)) return;

    const sendButton = event.target.closest(SEND_SELECTOR);
    if (!sendButton) return;

    // Ignore our own synthetic click.
    if (allowNextSend && event.isTrusted === false) {
        allowNextSend = false;
        return;
    }

    if (isProtecting) {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
    }

    const editor = getPromptBox();
    if (!editor) return;

    const originalText = getPromptText(editor);
    if (!originalText) return;

    // Cancel the original user submission.
    event.preventDefault();
    event.stopImmediatePropagation();

    isProtecting = true;
    sendButton.disabled = true;

    console.log("TriCypher: Intercepted original submission.");

    try {
        const result = await protectWithBackground(originalText);

        console.log("TriCypher: Detected entities:", result.detectedCount);

        setPromptText(editor, result.protectedText);

        console.log("TriCypher: Protected prompt inserted.");

        // Re-enable the button before triggering submission.
        sendButton.disabled = false;

        // Allow one synthetic click to submit the protected prompt.
        allowNextSend = true;
        sendButton.click();

    } catch (error) {
        console.error("TriCypher protection error:", error);

        alert(
            "TriCypher could not protect this prompt. " +
            "Your original prompt was not sent."
        );

        sendButton.disabled = false;

    } finally {
        isProtecting = false;
    }
}, true);
    console.log("TriCypher: Send interception is ready.");
})();
