// Connects to the FastAPI WebSocket and forwards messages to the frontend as Tauri events

use futures_util::StreamExt;
use tauri::Emitter;
use tokio_tungstenite::{connect_async, tungstenite::Message};

const WS_URL: &str = "ws://127.0.0.1:8000/ws";

async fn ws_task(app: tauri::AppHandle) {
    loop {
        match connect_async(WS_URL).await {
            Ok((mut stream, _)) => {
                while let Some(Ok(msg)) = stream.next().await {
                    if let Message::Text(text) = msg {
                        if let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) {
                            let event = json.get("type").and_then(|t| t.as_str()).unwrap_or("");
                            let payload = json.get("payload").cloned().unwrap_or(serde_json::Value::Null);
                            let _ = app.emit(event, payload);
                        }
                    }
                }
            }
            Err(e) => eprintln!("[ws] connection failed: {e}"),
        }
        // Reconnect after 2 s if the connection drops or the backend is not up yet
        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(ws_task(handle));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
