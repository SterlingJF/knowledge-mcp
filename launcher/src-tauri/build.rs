// File: launcher/src-tauri/build.rs
use std::fs;

#[path = "src/ports.rs"]
mod ports;

use ports::{BACKEND_PORT, MCP_PORT};

const PLUGIN_MANIFEST: &str = "../../mcp/plugin/knowledge-mcp/mcp.json";

fn main() {
    println!("cargo:rerun-if-changed=tauri.conf.json");
    println!("cargo:rerun-if-changed=src/ports.rs");
    println!("cargo:rerun-if-changed={PLUGIN_MANIFEST}");

    let config: serde_json::Value = serde_json::from_str(
        &fs::read_to_string("tauri.conf.json").expect("tauri.conf.json is unreadable"),
    )
    .expect("tauri.conf.json is not valid JSON");

    check_policies(&config);
    check_plugin_manifest();

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

fn check_plugin_manifest() {
    let manifest: serde_json::Value = serde_json::from_str(
        &fs::read_to_string(PLUGIN_MANIFEST)
            .unwrap_or_else(|error| panic!("{PLUGIN_MANIFEST} is unreadable: {error}")),
    )
    .unwrap_or_else(|error| panic!("{PLUGIN_MANIFEST} is not valid JSON: {error}"));

    let url = manifest["mcpServers"]["knowledge-mcp"]["url"]
        .as_str()
        .unwrap_or_else(|| panic!("{PLUGIN_MANIFEST} has no mcpServers.knowledge-mcp.url"));

    let expected = format!("http://127.0.0.1:{MCP_PORT}/mcp");

    assert!(
        url == expected,
        "{PLUGIN_MANIFEST} points an agent host at {url}, and this shell starts the \
         model-context server on {expected}. An agent host would connect to nothing and report \
         only that the server is unavailable. Change one to match the other."
    );
}
