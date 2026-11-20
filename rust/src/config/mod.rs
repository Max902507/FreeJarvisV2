pub struct Config {
    pub host: String,
    pub port: u16,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            host: std::env::var("JARVIS_HOST").unwrap_or_else(|_| "127.0.0.1".to_string()),

            port: std::env::var("JARVIS_PORT")
                .ok()
                .and_then(|value| value.parse().ok())
                .unwrap_or(6060),
        }
    }
}
