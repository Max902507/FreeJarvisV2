use std::net::SocketAddr;
use std::str::FromStr;

use axum::{
    extract::{ConnectInfo, Request, State},
    http::{header, uri::Authority, Method, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};

pub async fn secure_request(
    State(port): State<u16>,
    request: Request,
    next: Next,
) -> Response {
    let forbidden = || {
        (
            StatusCode::FORBIDDEN,
            Json(serde_json::json!({"error": "Forbidden"})),
        ).into_response()
    };

    // OPTIONS will always be denied. No CORS for now.
    if request.method() == Method::OPTIONS {
        return forbidden();
    }

    let is_local = request
        .extensions()
        .get::<ConnectInfo<SocketAddr>>()
        .map(|ConnectInfo(addr)| addr.ip().is_loopback())
        .unwrap_or(false);
    if !is_local { return forbidden(); }

    // Only localhost or loopback allowed
    let host = match request.headers().get(header::HOST).and_then(|v| v.to_str().ok()) {
        Some(value) => value.trim().to_ascii_lowercase(),
        None => return forbidden(),
    };
    let authority = match Authority::from_str(&host) {
        Ok(value) => value,
        Err(_) => return forbidden(),
    };
    let hostname = authority.host().trim_matches(['[', ']']);
    let valid_host = matches!(hostname, "localhost" | "127.0.0.1" | "::1")
        && authority.port_u16() == Some(port);

    if ! valid_host { return forbidden(); }

    // Verify origin matching host
    if let Some(origin) = request.headers().get(header::ORIGIN) {
        let origin = match origin.to_str() {
            Ok(value) => value.trim().to_ascii_lowercase(),
            Err(_) => return forbidden(),
        };

        let origin_authority = origin
            .split_once("://")
            .map(|(_, rest)| rest.split('/').next().unwrap_or(""))
            .unwrap_or("");

        if origin_authority != host { return forbidden(); }
    }

    // POST requests need X-Jarvis: 1
    if request.method() == Method::POST {
        let valid_token = request
            .headers()
            .get("x-jarvis")
            .and_then(|v| v.to_str().ok()) == Some("1");

        let valid_content_type = request
            .headers()
            .get(header::CONTENT_TYPE)
            .and_then(|v| v.to_str().ok())
            .map(|v| v.to_ascii_lowercase().contains("json"))
            .unwrap_or(false);

        if !valid_token || !valid_content_type {
            return (
                StatusCode::FORBIDDEN,
                Json(serde_json::json!({"error": "Invalid token or content-type."})),
            ).into_response();
        }
    }


    next.run(request).await
}
