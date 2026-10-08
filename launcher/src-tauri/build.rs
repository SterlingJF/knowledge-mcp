// File: launcher/src-tauri/build.rs
use std::fs;

#[path = "src/ports.rs"]
mod ports;

use ports::{BACKEND_PORT, MCP_PORT};

// The plugin manifest and the MCP server's defaults live in other modules; the root
// `tools/ports/` check compares them with src/ports.rs.

fn main() {
    println!("cargo:rerun-if-changed=tauri.conf.json");
    println!("cargo:rerun-if-changed=src/ports.rs");

    let config: serde_json::Value = serde_json::from_str(
        &fs::read_to_string("tauri.conf.json").expect("tauri.conf.json is unreadable"),
    )
    .expect("tauri.conf.json is not valid JSON");

    check_policies(&config);

    tauri_build::build()
}

fn check_policies(config: &serde_json::Value) {
    let backend = format!("http://127.0.0.1:{BACKEND_PORT}");
    let mcp = format!("http://127.0.0.1:{MCP_PORT}");

    for policy in ["csp", "devCsp"] {
        let value = config["app"]["security"][policy]
            .as_str()
            .unwrap_or_else(|| panic!("app.security.{policy} is missing"));

        assert!(
            value.contains(&backend),
            "app.security.{policy} does not allow {backend}. The shell spawns the backend on port \
             {BACKEND_PORT}, so the policy must name it or every request is refused with no error \
             the window can report."
        );

        assert!(
            !value.contains(&mcp),
            "app.security.{policy} allows {mcp}. That is the model-context server, which agents \
             connect to directly and the window never calls. Remove it: the policy is what keeps \
             the window's reach to the backend alone."
        );
    }
}
