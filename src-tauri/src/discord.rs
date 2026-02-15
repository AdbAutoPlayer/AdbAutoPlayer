use reqwest::blocking::Client;
use serde_json::json;
use std::thread;
use std::time::Duration;

pub fn execute_discord_webhook(webhook_url: String, content: String) {
    if webhook_url.is_empty() {
        return;
    }

    thread::spawn(move || {
        let client = Client::builder()
            .timeout(Duration::from_millis(5000))
            .build()
            .unwrap();

        let payload = json!({
            "content": content,
            "username": "AdbAutoPlayer",
            "avatar_url": "https://raw.githubusercontent.com/AdbAutoPlayer/AdbAutoPlayer/refs/heads/main/app-icon.png",
        });

        let _ = client.post(&webhook_url).json(&payload).send();
    });
}
