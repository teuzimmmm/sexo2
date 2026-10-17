#[cfg(windows)]
mod windows_host;
mod wire;

fn main() {
    #[cfg(windows)]
    if windows_host::run().is_err() {
        // Never print API error details, payloads, local paths or environment.
        eprintln!("Native DX11 host failed; League was not tested.");
        std::process::exit(1);
    }
    #[cfg(not(windows))]
    {
        eprintln!("The native DX11 host requires Windows. Protocol tests are portable.");
        std::process::exit(2);
    }
}
