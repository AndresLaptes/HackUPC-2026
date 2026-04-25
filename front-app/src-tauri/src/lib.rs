// Launches the Python backend sidecar, then connects to its WebSocket and
// forwards messages to the frontend as Tauri events.

use futures_util::StreamExt;
use tauri::Emitter;
use tauri_plugin_shell::ShellExt;
use tokio_tungstenite::{connect_async, tungstenite::Message};

const WS_URL: &str = "ws://127.0.0.1:8000/ws";

async fn ws_task(app: tauri::AppHandle) {
    // Give the sidecar a moment to start listening before we try to connect.
    tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;

    loop {
        match connect_async(WS_URL).await {
            Ok((mut stream, _)) => {
                while let Some(Ok(msg)) = stream.next().await {
                    if let Message::Text(text) = msg {
                        if let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) {
                            let event = json.get("type").and_then(|t| t.as_str()).unwrap_or("");
                            let payload = json
                                .get("payload")
                                .cloned()
                                .unwrap_or(serde_json::Value::Null);
                            let _ = app.emit(event, payload);
                        }
                    }
                }
            }
            Err(e) => eprintln!("[ws] connection failed: {e}"),
        }
        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Spawn the Python backend sidecar.
            // The binary must be at src-tauri/binaries/backend-<target-triple>[.exe]
            let _sidecar = app
                .shell()
                .sidecar("backend")
                .expect("backend sidecar not found")
                .spawn()
                .expect("failed to spawn backend sidecar");

            let handle = app.handle().clone();
            tauri::async_runtime::spawn(ws_task(handle));

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
