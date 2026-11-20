mod routes;
mod middleware;
mod websocket;

use crate::config::Config;
use axum::{
    middleware::from_fn_with_state,
    Router,
};
use std::net::SocketAddr;
use tokio::net::TcpListener;
use tower_http::trace::TraceLayer;

pub async fn run(config: Config) -> Result<(), Box<dyn std::error::Error>> {
    let port = config.port;

    let app = Router::new()
        .merge(routes::routes())
        .layer(from_fn_with_state(port, middleware::secure_request))
        .layer(TraceLayer::new_for_http());

    let address = format!("{}:{}", config.host, config.port);
    let listener = TcpListener::bind(&address).await?;

    tracing::info!("FreeJarvisV2 listening on {address}");

    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await?;

    Ok(())
}
