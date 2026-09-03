// File: launcher/src-tauri/src/lib.rs
//! Menu-bar shell supervising engine and MCP sidecars. Window calls engine over loopback HTTP.

use std::net::{Shutdown, SocketAddr, TcpStream};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use serde::Serialize;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{
    AppHandle, Emitter, Listener, Manager, RunEvent, State, WebviewWindowBuilder, WindowEvent,
};
use tauri_plugin_autostart::MacosLauncher;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

mod ports;

use ports::{BACKEND_PORT, MCP_PORT};

const BACKEND_SIDECAR: &str = "km-server";
const MCP_SIDECAR: &str = "km-mcp";

/// Fixed-size settings window (tauri.conf.json).
const SETTINGS_WINDOW: &str = "main";

/// A process is ready when its socket accepts a connection.
const READY_POLL_INTERVAL: Duration = Duration::from_millis(100);
const READY_PROBE_TIMEOUT: Duration = Duration::from_millis(200);
const READY_MAX_TICKS: u32 = 300;

const SHUTDOWN_GRACE: Duration = Duration::from_millis(1500);

/// Window reads name, state, and port (launcher/src/App.tsx).
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProcessStatus {
    name: String,
    port: u16,
    pid: Option<u32>,
    state: &'static str,
    detail: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProcessLog {
    name: String,
    stream: &'static str,
    line: String,
}

#[derive(Default)]
struct Processes {
    children: Mutex<Vec<CommandChild>>,
    status: Mutex<Vec<ProcessStatus>>,
    paused: Mutex<bool>,
}

fn is_listening(port: u16) -> bool {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    match TcpStream::connect_timeout(&address, READY_PROBE_TIMEOUT) {
        Ok(stream) => {
            let _ = stream.shutdown(Shutdown::Both);
            true
        }
        Err(_) => false,
    }
}

fn publish(app: &AppHandle, status: ProcessStatus) {
    if let Some(processes) = app.try_state::<Processes>() {
        let mut recorded = processes.status.lock().expect("process status lock");
        recorded.retain(|existing| existing.name != status.name);
        recorded.push(status.clone());
    }
    let _ = app.emit("process-status", status);
}

/// Forwards environment overrides, normally absent under Finder. Engine reads its config when absent.
fn backend_arguments() -> Vec<String> {
    let mut arguments = vec![
        "--port".to_string(),
        BACKEND_PORT.to_string(),
        "--parent-pid".to_string(),
        std::process::id().to_string(),
    ];

    for (variable, flag) in [
        ("KM_STORE_ROOT", "--store-root"),
        ("KM_PRINCIPAL_ID", "--principal-id"),
    ] {
        if let Ok(value) = std::env::var(variable) {
            if !value.is_empty() {
                arguments.push(flag.to_string());
                arguments.push(value);
            }
        }
    }

    arguments
}

fn mcp_arguments() -> Vec<String> {
    vec![
        "--port".to_string(),
        MCP_PORT.to_string(),
        "--parent-pid".to_string(),
        std::process::id().to_string(),
        "--api-origin".to_string(),
        format!("http://127.0.0.1:{BACKEND_PORT}/api/v1"),
    ]
}

fn spawn_process(app: &AppHandle, name: &'static str, port: u16, arguments: Vec<String>) {
    if is_listening(port) {
        publish(
            app,
            ProcessStatus {
                name: name.to_string(),
                port,
                pid: None,
                state: "occupied",
                detail: format!(
                    "127.0.0.1:{port} already has a listener, so {name} was not started. \
                     Find it with: lsof -nP -iTCP:{port} -sTCP:LISTEN"
                ),
            },
        );
        return;
    }

    let spawned = app
        .shell()
        .sidecar(name)
        .and_then(|command| command.args(&arguments).spawn());

    let (mut events, child) = match spawned {
        Ok(pair) => pair,
        Err(error) => {
            publish(
                app,
                ProcessStatus {
                    name: name.to_string(),
                    port,
                    pid: None,
                    state: "exited",
                    detail: format!("{name} could not be started: {error}"),
                },
            );
            return;
        }
    };

    let pid = child.pid();
    app.state::<Processes>()
        .children
        .lock()
        .expect("process child lock")
        .push(child);

    publish(
        app,
        ProcessStatus {
            name: name.to_string(),
            port,
            pid: Some(pid),
            state: "spawned",
            detail: format!("Started, waiting for 127.0.0.1:{port} to accept."),
        },
    );

    // Readiness poll runs off the window thread.
    let probe_app = app.clone();
    thread::spawn(move || {
        for tick in 1..=READY_MAX_TICKS {
            if is_listening(port) {
                publish(
                    &probe_app,
                    ProcessStatus {
                        name: name.to_string(),
                        port,
                        pid: Some(pid),
                        state: "listening",
                        detail: format!("Accepting after about {} ms.", tick * 100),
                    },
                );
                return;
            }
            thread::sleep(READY_POLL_INTERVAL);
        }
        publish(
            &probe_app,
            ProcessStatus {
                name: name.to_string(),
                port,
                pid: Some(pid),
                state: "timeout",
                detail: format!("Nothing accepted on 127.0.0.1:{port} within 30 seconds."),
            },
        );
    });

    let log_app = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim_end().to_string();
                    println!("[{name}] {line}");
                    let _ = log_app.emit(
                        "process-log",
                        ProcessLog {
                            name: name.to_string(),
                            stream: "stdout",
                            line,
                        },
                    );
                }
                CommandEvent::Stderr(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim_end().to_string();
                    eprintln!("[{name}] {line}");
                    let _ = log_app.emit(
                        "process-log",
                        ProcessLog {
                            name: name.to_string(),
                            stream: "stderr",
                            line,
                        },
                    );
                }
                CommandEvent::Terminated(payload) => {
                    publish(
                        &log_app,
                        ProcessStatus {
                            name: name.to_string(),
                            port,
                            pid: Some(pid),
                            state: "exited",
                            detail: format!(
                                "Stopped with code {:?} and signal {:?}.",
                                payload.code, payload.signal
                            ),
                        },
                    );
                    return;
                }
                _ => {}
            }
        }
    });
}

fn spawn_all(app: &AppHandle) {
    // Start order does not matter.
    spawn_process(app, BACKEND_SIDECAR, BACKEND_PORT, backend_arguments());
    spawn_process(app, MCP_SIDECAR, MCP_PORT, mcp_arguments());
}

/// Stop every child by pid. Children share this process group.
fn stop_processes(processes: State<'_, Processes>) {
    let mut children = processes.children.lock().expect("process child lock");
    let pids: Vec<u32> = children.iter().map(CommandChild::pid).collect();

    for pid in &pids {
        // Frozen bootloader forwards SIGTERM. SIGKILL bypasses it.
        unsafe { libc::kill(*pid as libc::pid_t, libc::SIGTERM) };
    }

    if !pids.is_empty() {
        thread::sleep(SHUTDOWN_GRACE);
    }

    for child in children.drain(..) {
        let _ = child.kill();
    }
}

/// Recreates settings window after OS-level close.
fn show_settings_window(app: &AppHandle) {
    if let Some(existing) = app.get_webview_window(SETTINGS_WINDOW) {
        let _ = existing.unminimize();
        let _ = existing.show();
        let _ = existing.set_focus();
        return;
    }

    let config = app
        .config()
        .app
        .windows
        .iter()
        .find(|window| window.label == SETTINGS_WINDOW)
        .cloned();

    if let Some(config) = config {
        if let Err(error) =
            WebviewWindowBuilder::from_config(app, &config).and_then(|builder| builder.build())
        {
            eprintln!("the settings window could not be reopened: {error}");
        }
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_autostart::init(
            MacosLauncher::LaunchAgent,
            None,
        ))
        .manage(Processes::default())
        .setup(|app| {
            // Menu-bar app: no Dock icon.
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Accessory);

            let handle = app.handle().clone();

            // Window mounts after startup. ui-ready triggers a replay.
            let replay_handle = handle.clone();
            app.listen("ui-ready", move |_| {
                let recorded = replay_handle
                    .state::<Processes>()
                    .status
                    .lock()
                    .expect("process status lock")
                    .clone();
                for status in recorded {
                    let _ = replay_handle.emit("process-status", status);
                }
            });

            // Webview names the path. Shell performs the reveal.
            let reveal_handle = handle.clone();
            app.listen("reveal-vault", move |event| {
                #[derive(serde::Deserialize)]
                struct RevealVault {
                    path: String,
                }
                match serde_json::from_str::<RevealVault>(event.payload()) {
                    Ok(payload) => {
                        use tauri_plugin_opener::OpenerExt;
                        if let Err(error) =
                            reveal_handle.opener().reveal_item_in_dir(&payload.path)
                        {
                            eprintln!("the vault folder could not be revealed: {error}");
                        }
                    }
                    Err(error) => eprintln!("reveal-vault carried no path: {error}"),
                }
            });

            let open_item =
                MenuItem::with_id(app, "open-settings", "Open Settings", true, None::<&str>)?;
            let pause_item =
                MenuItem::with_id(app, "toggle-serving", "Pause Serving", true, None::<&str>)?;
            let quit_item =
                MenuItem::with_id(app, "quit", "Quit Knowledge MCP", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open_item, &pause_item, &quit_item])?;

            let pause_handle = pause_item.clone();
            TrayIconBuilder::with_id("knowledge-mcp-tray")
                // Bare KM mark. Menu bar renders template icons from alpha.
                .icon(tauri::image::Image::from_bytes(include_bytes!(
                    "../icons/tray-template@2x.png"
                ))?)
                .icon_as_template(true)
                .menu(&menu)
                .show_menu_on_left_click(true)
                .on_menu_event(move |app, event| match event.id().as_ref() {
                    "open-settings" => show_settings_window(app),
                    "toggle-serving" => {
                        let processes = app.state::<Processes>();
                        let was_paused = { *processes.paused.lock().expect("paused lock") };
                        if was_paused {
                            spawn_all(app);
                            *processes.paused.lock().expect("paused lock") = false;
                            let _ = pause_handle.set_text("Pause Serving");
                        } else {
                            stop_processes(processes);
                            *app.state::<Processes>().paused.lock().expect("paused lock") =
                                true;
                            let _ = pause_handle.set_text("Resume Serving");
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;

            spawn_all(&handle);
            Ok(())
        })
        // Closing the window keeps the app serving from the tray.
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("the shell could not be built")
        .run(|app, event| match event {
            RunEvent::ExitRequested { api, code, .. } if code.is_none() => {
                api.prevent_exit();
            }
            // Finder reactivation shows a missing window.
            #[cfg(target_os = "macos")]
            RunEvent::Reopen {
                has_visible_windows,
                ..
            } if !has_visible_windows => {
                show_settings_window(app);
            }
            RunEvent::Exit => {
                stop_processes(app.state::<Processes>());
            }
            _ => {}
        });
}
