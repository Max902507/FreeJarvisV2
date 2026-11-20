use axum::{
    extract::ws::{Message, WebSocket, WebSocketUpgrade},
    response::Response,
};

pub async fn handler(ws: WebSocketUpgrade) -> Response {
    ws.on_upgrade(handle_socket)
}

async fn handle_socket(mut socket: WebSocket) {
    while let Some(Ok(message)) = socket.recv().await {
        match message {
            Message::Text(msg) => {
                if socket
                    .send(Message::Text(format!("Echo: {msg}").into()))
                    .await
                    .is_err()
                {
                    break;
                }
            }

            Message::Close(_) => break,
            _ => {}
        }
    }
}
