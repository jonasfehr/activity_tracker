function sendActiveTab() {
    browser.tabs.query({ active: true, currentWindow: true }).then(tabs => {
        if (tabs.length === 0) return;
        const tab = tabs[0];
        const title = tab.title;
        const url = tab.url;

        // Send to local server
        fetch("http://127.0.0.1:5000/tab", {
            method: "POST",
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title, url: url })
        }).catch(err => console.log("Cannot reach local server:", err));
    });
}

const SEND_INTERVAL_MS = 10000;

// Send active tab data every 10 seconds
setInterval(sendActiveTab, SEND_INTERVAL_MS);
