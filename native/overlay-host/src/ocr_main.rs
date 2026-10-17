//! Local OCR only. Input is three bounded in-memory title crops, never a path.
use base64::{engine::general_purpose::STANDARD, Engine};
use serde::Deserialize;
use std::io::BufRead;
#[cfg(windows)]
use std::io::Write;

const MAX_BYTES: usize = 4 * 1024 * 1024;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Image {
    width: u32,
    height: u32,
    bgra: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    v: u8,
    seq: u64,
    images: Vec<Image>,
}

fn decode(image: &Image) -> Result<Vec<u8>, ()> {
    if image.width == 0 || image.width > 768 || image.height == 0 || image.height > 240 {
        return Err(());
    }
    let expected = image.width as usize * image.height as usize * 4;
    if image.bgra.len() > expected.div_ceil(3) * 4 {
        return Err(());
    }
    let bytes = STANDARD.decode(&image.bgra).map_err(|_| ())?;
    if bytes.len() != expected {
        return Err(());
    }
    Ok(bytes)
}

fn read(reader: &mut impl BufRead) -> Result<Option<Request>, ()> {
    let mut bytes = Vec::new();
    loop {
        let available = reader.fill_buf().map_err(|_| ())?;
        if available.is_empty() {
            return if bytes.is_empty() { Ok(None) } else { Err(()) };
        }
        let end = available.iter().position(|b| *b == b'\n');
        let count = end.map_or(available.len(), |i| i + 1);
        if bytes.len() + count > MAX_BYTES {
            return Err(());
        }
        bytes.extend_from_slice(&available[..count]);
        reader.consume(count);
        if end.is_some() {
            let request: Request = serde_json::from_slice(&bytes).map_err(|_| ())?;
            if request.v != 1 || request.seq == 0 || request.images.len() != 3 {
                return Err(());
            }
            return Ok(Some(request));
        }
    }
}

#[cfg(windows)]
fn run() -> Result<(), ()> {
    use windows::{
        core::HSTRING,
        Globalization::Language,
        Graphics::Imaging::{BitmapPixelFormat, SoftwareBitmap},
        Media::Ocr::OcrEngine,
        Storage::Streams::DataWriter,
        Win32::System::WinRT::{RoInitialize, RO_INIT_MULTITHREADED},
    };
    unsafe {
        RoInitialize(RO_INIT_MULTITHREADED).map_err(|_| ())?;
    }
    let engine = OcrEngine::TryCreateFromUserProfileLanguages()
        .or_else(|_| {
            OcrEngine::TryCreateFromLanguage(&Language::CreateLanguage(&HSTRING::from("en-US"))?)
        })
        .map_err(|_| ())?;
    let stdin = std::io::stdin();
    let mut input = stdin.lock();
    let mut stdout = std::io::stdout().lock();
    let mut last = 0;
    while let Some(request) = read(&mut input)? {
        if request.seq <= last {
            return Err(());
        }
        last = request.seq;
        let mut titles = Vec::new();
        for image in request.images {
            let bytes = decode(&image)?;
            let writer = DataWriter::new().map_err(|_| ())?;
            writer.WriteBytes(&bytes).map_err(|_| ())?;
            let buffer = writer.DetachBuffer().map_err(|_| ())?;
            let bitmap = SoftwareBitmap::CreateCopyFromBuffer(
                &buffer,
                BitmapPixelFormat::Bgra8,
                image.width as i32,
                image.height as i32,
            )
            .map_err(|_| ())?;
            let result = engine
                .RecognizeAsync(&bitmap)
                .map_err(|_| ())?
                .join()
                .map_err(|_| ())?;
            let value = result.Text().map_err(|_| ())?.to_string();
            // Fail this title closed; never truncate a longer string into a known name.
            let title = if value.chars().count() <= 256 {
                value.split_whitespace().collect::<Vec<_>>().join(" ")
            } else {
                String::new()
            };
            titles.push(title);
            let _ = bitmap.Close();
            let _ = writer.Close();
        }
        writeln!(
            stdout,
            "{}",
            serde_json::json!({"v":1,"seq":request.seq,"status":"ok","titles":titles})
        )
        .map_err(|_| ())?;
        stdout.flush().map_err(|_| ())?;
    }
    Ok(())
}

fn main() {
    #[cfg(windows)]
    if run().is_err() {
        std::process::exit(1);
    }
    #[cfg(not(windows))]
    std::process::exit(2);
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_invalid_images_and_schema() {
        assert!(decode(&Image {
            width: 769,
            height: 1,
            bgra: String::new()
        })
        .is_err());
        assert!(decode(&Image {
            width: 1,
            height: 1,
            bgra: "AA==".into()
        })
        .is_err());
        assert!(read(&mut std::io::Cursor::new(b"{\"v\":2}\n")).is_err());
        assert!(read(&mut std::io::Cursor::new(vec![b'x'; MAX_BYTES + 1])).is_err());
    }
}
