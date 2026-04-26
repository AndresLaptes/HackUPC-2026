// Launches the bundled backend binary (sibling of this executable),
// then connects to its WebSocket and forwards messages to the frontend.

use futures_util::StreamExt;
use tauri::Emitter;
use tauri_plugin_shell::ShellExt;
use tokio_tungstenite::{connect_async, tungstenite::Message};

const WS_URL: &str = "ws://127.0.0.1:8000/ws";

fn spawn_backend() {
    let mut path = match std::env::current_exe() {
        Ok(p) => p,
        Err(e) => { eprintln!("[backend] can't locate self: {e}"); return; }
    };
    path.set_file_name("backend");

    // Kill any leftover backend from a previous session so port 8000 is free
    let _ = std::process::Command::new("pkill")
        .args(["-f", path.to_str().unwrap_or("backend")])
        .status();
    std::thread::sleep(std::time::Duration::from_millis(800));

    match std::process::Command::new(&path).spawn() {
        Ok(_) => eprintln!("[backend] spawned {}", path.display()),
        Err(e) => eprintln!("[backend] failed to spawn {}: {e}", path.display()),
    }
}

async fn ws_task(app: tauri::AppHandle) {
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
        tokio::time::sleep(tokio::time::Duration::from_secs(4)).await;
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            spawn_backend();
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(ws_task(handle));

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
