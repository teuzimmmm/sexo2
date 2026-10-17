//! Bounded latest-frame inbox. Invalid, stale or disconnected input never draws.
use serde::{Deserialize, Serialize};
use std::io::{self, BufRead};
use std::time::{Duration, Instant};

pub const MAX_BYTES: usize = 256 * 1024;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Card {
    pub title: String,
    pub lines: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Frame {
    pub v: u8,
    pub seq: u64,
    pub ttl_ms: u64,
    pub active: bool,
    pub preview: bool,
    pub selected: usize,
    pub cards: Vec<Card>,
}

#[derive(Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Stats {
    pub received: u64,
    pub rejected: u64,
    pub draw_callbacks: u64,
    pub visible_callbacks: u64,
    pub hidden_callbacks: u64,
    pub expired_callbacks: u64,
}

#[derive(Default)]
pub struct Inbox {
    pub stats: Stats,
    latest: Option<(Frame, Instant)>,
    seq: u64,
    pub disconnected: bool,
}

impl Inbox {
    pub fn accept(&mut self, bytes: &[u8], now: Instant) -> Result<(), ()> {
        let parsed = if bytes.len() <= MAX_BYTES {
            serde_json::from_slice::<Frame>(bytes).ok()
        } else {
            None
        };
        if let Some(frame) = parsed.filter(|f| valid(f) && f.seq > self.seq) {
            self.seq = frame.seq;
            self.stats.received += 1;
            self.latest = Some((frame, now));
            Ok(())
        } else {
            self.latest = None;
            self.stats.rejected += 1;
            Err(())
        }
    }

    pub fn disconnect(&mut self) {
        self.disconnected = true;
        self.latest = None;
    }

    pub fn draw(&mut self, now: Instant) -> Option<&Frame> {
        self.stats.draw_callbacks += 1;
        let expired = self.latest.as_ref().is_some_and(|(frame, received)| {
            now.saturating_duration_since(*received) >= Duration::from_millis(frame.ttl_ms)
        });
        if expired {
            self.stats.expired_callbacks += 1;
            self.latest = None;
        }
        if self.disconnected || !self.latest.as_ref().is_some_and(|(f, _)| f.active) {
            self.stats.hidden_callbacks += 1;
            return None;
        }
        self.stats.visible_callbacks += 1;
        self.latest.as_ref().map(|(frame, _)| frame)
    }
}

fn valid(frame: &Frame) -> bool {
    fn text(s: &str) -> bool {
        s.chars().count() <= 512 && !s.chars().any(|c| c.is_control()
            || matches!(c, '\u{200b}'..='\u{200f}' | '\u{202a}'..='\u{202e}' | '\u{2060}'..='\u{206f}' | '\u{feff}'))
    }
    frame.v == 1
        && (1..=9_007_199_254_740_991).contains(&frame.seq)
        && (1..=8000).contains(&frame.ttl_ms)
        && frame.cards.len() <= 16
        && frame.selected < frame.cards.len().max(1)
        && (frame.active || (frame.cards.is_empty() && frame.selected == 0))
        && frame
            .cards
            .iter()
            .all(|c| text(&c.title) && c.lines.len() <= 256 && c.lines.iter().all(|s| text(s)))
}

// read_until with a hard limit BEFORE parsing/allocation; a single oversized line
// terminates the stream instead of retaining or draining an unbounded payload.
pub fn read_line(reader: &mut impl BufRead) -> io::Result<Option<Vec<u8>>> {
    let mut line = Vec::new();
    loop {
        let available = reader.fill_buf()?;
        if available.is_empty() {
            return if line.is_empty() {
                Ok(None)
            } else {
                Err(io::ErrorKind::UnexpectedEof.into())
            };
        }
        let end = available.iter().position(|b| *b == b'\n');
        let take = end.map_or(available.len(), |i| i + 1);
        if line.len() + take > MAX_BYTES {
            return Err(io::ErrorKind::InvalidData.into());
        }
        line.extend_from_slice(&available[..take]);
        reader.consume(take);
        if end.is_some() {
            return Ok(Some(line));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    fn frame(seq: u64) -> Vec<u8> {
        format!(r#"{{"v":1,"seq":{seq},"ttlMs":100,"active":true,"preview":true,"selected":0,"cards":[{{"title":"Arena","lines":["12%"]}}]}}"#).into_bytes()
    }

    #[test]
    fn fresh_then_expired_and_disconnected() {
        let now = Instant::now();
        let mut inbox = Inbox::default();
        inbox.accept(&frame(1), now).unwrap();
        assert!(inbox.draw(now).unwrap().preview);
        assert!(inbox.draw(now + Duration::from_millis(100)).is_none());
        assert_eq!(inbox.stats.expired_callbacks, 1);
        inbox.accept(&frame(2), now).unwrap();
        inbox.disconnect();
        assert!(inbox.draw(now).is_none());
    }

    #[test]
    fn invalid_or_reordered_clears_old_data() {
        let now = Instant::now();
        let mut inbox = Inbox::default();
        for invalid in [
            frame(1),
            b"{\"v\":2}".to_vec(),
            b"garbage".to_vec(),
            String::from_utf8(frame(2))
                .unwrap()
                .replace("\"ttlMs\":100", "\"ttlMs\":8001")
                .into_bytes(),
            String::from_utf8(frame(2))
                .unwrap()
                .replace("\"v\":1", "\"v\":1,\"raw\":{}")
                .into_bytes(),
        ] {
            inbox.accept(&frame(1), now).ok();
            assert!(inbox.accept(&invalid, now).is_err());
            assert!(inbox.draw(now).is_none());
        }
    }

    #[test]
    fn bounded_stream_rejects_partial_or_oversized_line() {
        assert!(read_line(&mut Cursor::new(vec![b'x'; MAX_BYTES + 1])).is_err());
        assert!(read_line(&mut Cursor::new(b"{}".to_vec())).is_err());
        assert_eq!(
            read_line(&mut Cursor::new(b"{}\n".to_vec()))
                .unwrap()
                .unwrap(),
            b"{}\n"
        );
        assert!(read_line(&mut Cursor::new(Vec::new())).unwrap().is_none());
    }

    #[test]
    fn schema_and_card_limits_fail_closed() {
        let now = Instant::now();
        let base: serde_json::Value = serde_json::from_slice(&frame(1)).unwrap();
        let mut invalid = Vec::new();
        for (key, value) in [
            ("seq", serde_json::json!(true)),
            ("v", serde_json::json!(2)),
            ("selected", serde_json::json!(1)),
            ("active", serde_json::json!(false)),
            ("ttlMs", serde_json::json!(0)),
        ] {
            let mut row = base.clone();
            row[key] = value;
            invalid.push(row);
        }
        let mut row = base.clone();
        row["cards"] = serde_json::json!(vec![base["cards"][0].clone(); 17]);
        invalid.push(row);
        let mut row = base.clone();
        row["cards"][0]["lines"] = serde_json::json!(vec!["x"; 257]);
        invalid.push(row);
        let mut row = base.clone();
        row["cards"][0]["title"] = serde_json::json!("x".repeat(513));
        invalid.push(row);
        let mut row = base.clone();
        row["cards"][0]["lines"] = serde_json::json!(["invalid\nline"]);
        invalid.push(row);
        for row in invalid {
            let mut inbox = Inbox::default();
            assert!(inbox
                .accept(&serde_json::to_vec(&row).unwrap(), now)
                .is_err());
            assert!(inbox.draw(now).is_none());
        }
    }
}
