use axum::{Json, Router, routing::get};
use serde::Serialize;

use super::websocket;

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
    version: &'static str,
}

pub fn routes() -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/ws", get(websocket::handler))
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        version: env!("CARGO_PKG_VERSION"),
    })
}
