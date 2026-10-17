//! Own-process DX11 laboratory. No DLL, injector, game access or permanent host.
use crate::wire::{read_line, Inbox};
use hudhook::hooks::dx11::ImguiDx11Hooks;
use hudhook::{imgui, Hudhook, ImguiRenderLoop, RenderContext};
use std::io::Write;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use windows::core::w;
use windows::Win32::Foundation::{HMODULE, HWND, LPARAM, LRESULT, WPARAM};
use windows::Win32::Graphics::Direct3D::{
    D3D_DRIVER_TYPE_HARDWARE, D3D_DRIVER_TYPE_WARP, D3D_FEATURE_LEVEL_11_0,
};
use windows::Win32::Graphics::Direct3D11::*;
use windows::Win32::Graphics::Dxgi::Common::*;
use windows::Win32::Graphics::Dxgi::*;
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::UI::WindowsAndMessaging::*;

struct Display {
    inbox: Arc<Mutex<Inbox>>,
    seq: u64,
    index: usize,
    expanded: bool,
}

impl ImguiRenderLoop for Display {
    fn initialize<'a>(&'a mut self, ctx: &mut imgui::Context, _: &'a mut dyn RenderContext) {
        ctx.set_ini_filename(None);
        ctx.set_log_filename(None);
    }

    fn render(&mut self, ui: &mut imgui::Ui) {
        // Parsing and input happen on another thread. Never block the graphics
        // callback or show an old frame when its inbox is unavailable.
        let Ok(mut inbox) = self.inbox.try_lock() else {
            return;
        };
        let Some(frame) = inbox.draw(Instant::now()) else {
            return;
        };
        if self.seq != frame.seq {
            self.seq = frame.seq;
            self.index = frame.selected;
        }
        if ui.is_key_pressed(imgui::Key::F8) {
            self.expanded = !self.expanded;
        }
        if ui.is_key_pressed(imgui::Key::F9) && !frame.cards.is_empty() {
            self.index = (self.index + 1) % frame.cards.len();
        }
        ui.window("SEXO2 - native DX11 laboratory")
            .position([20.0, 20.0], imgui::Condition::FirstUseEver)
            .size([560.0, 480.0], imgui::Condition::FirstUseEver)
            .build(|| {
                ui.text_wrapped("Own-process test. This is not an overlay on League of Legends.");
                if frame.preview {
                    ui.text("Synthetic preview");
                }
                if ui.button(if self.expanded {
                    "Collapse (F8)"
                } else {
                    "Expand (F8)"
                }) {
                    self.expanded = !self.expanded;
                }
                if !self.expanded {
                    return;
                }
                if frame.cards.is_empty() {
                    ui.text("No prepared display cards.");
                    return;
                }
                self.index %= frame.cards.len();
                if ui.button("Next card (F9)") {
                    self.index = (self.index + 1) % frame.cards.len();
                }
                ui.same_line();
                ui.text(format!("{} / {}", self.index + 1, frame.cards.len()));
                let card = &frame.cards[self.index];
                ui.separator();
                ui.text_wrapped(&card.title);
                for line in &card.lines {
                    ui.text_wrapped(line);
                }
            });
    }
}

unsafe extern "system" fn window_proc(hwnd: HWND, msg: u32, wp: WPARAM, lp: LPARAM) -> LRESULT {
    if msg == WM_DESTROY {
        PostQuitMessage(0);
        LRESULT(0)
    } else {
        DefWindowProcW(hwnd, msg, wp, lp)
    }
}

pub fn run() -> Result<(), ()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 2 || args[0] != "--seconds" {
        return Err(());
    }
    let seconds: u64 = args[1].parse().map_err(|_| ())?;
    if !(2..=30).contains(&seconds) {
        return Err(());
    }
    let inbox = Arc::new(Mutex::new(Inbox::default()));
    let input = Arc::clone(&inbox);
    thread::spawn(move || {
        let stdin = std::io::stdin();
        let mut reader = stdin.lock();
        loop {
            match read_line(&mut reader) {
                Ok(Some(bytes)) => {
                    let invalid = input
                        .lock()
                        .unwrap()
                        .accept(&bytes, Instant::now())
                        .is_err();
                    if invalid {
                        break;
                    }
                }
                Ok(None) => break,
                Err(_) => {
                    input.lock().unwrap().stats.rejected += 1;
                    break;
                }
            }
        }
        input.lock().unwrap().disconnect();
    });

    // This host owns the window, device and swapchain. The library hooks only
    // this process; Cargo explicitly disables its injection feature.
    let instance = unsafe { GetModuleHandleW(None).map_err(|_| ())? };
    let class = w!("SEXO2.NativeDX11.Lab");
    let wc = WNDCLASSW {
        lpfnWndProc: Some(window_proc),
        hInstance: instance.into(),
        lpszClassName: class,
        ..Default::default()
    };
    if unsafe { RegisterClassW(&wc) } == 0 {
        return Err(());
    }
    let hwnd = unsafe {
        CreateWindowExW(
            WINDOW_EX_STYLE(0),
            class,
            w!("SEXO2 - DX11 laboratory (not League)"),
            WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_VISIBLE,
            100,
            100,
            800,
            600,
            None,
            None,
            Some(instance.into()),
            None,
        )
        .map_err(|_| ())?
    };
    let desc = DXGI_SWAP_CHAIN_DESC {
        BufferDesc: DXGI_MODE_DESC {
            Width: 800,
            Height: 600,
            Format: DXGI_FORMAT_R8G8B8A8_UNORM,
            RefreshRate: DXGI_RATIONAL {
                Numerator: 60,
                Denominator: 1,
            },
            ..Default::default()
        },
        SampleDesc: DXGI_SAMPLE_DESC {
            Count: 1,
            Quality: 0,
        },
        BufferUsage: DXGI_USAGE_RENDER_TARGET_OUTPUT,
        BufferCount: 1,
        OutputWindow: hwnd,
        Windowed: true.into(),
        SwapEffect: DXGI_SWAP_EFFECT_DISCARD,
        ..Default::default()
    };
    let (mut swap, mut device, mut context) = (None, None, None);
    let mut driver = "hardware";
    for kind in [D3D_DRIVER_TYPE_HARDWARE, D3D_DRIVER_TYPE_WARP] {
        let result = unsafe {
            D3D11CreateDeviceAndSwapChain(
                None,
                kind,
                HMODULE::default(),
                D3D11_CREATE_DEVICE_FLAG(0),
                Some(&[D3D_FEATURE_LEVEL_11_0]),
                D3D11_SDK_VERSION,
                Some(&desc),
                Some(&mut swap),
                Some(&mut device),
                None,
                Some(&mut context),
            )
        };
        if result.is_ok() {
            break;
        }
        driver = "warp";
    }
    let swap: IDXGISwapChain = swap.ok_or(())?;
    let device: ID3D11Device = device.ok_or(())?;
    let context: ID3D11DeviceContext = context.ok_or(())?;
    let buffer: ID3D11Texture2D = unsafe { swap.GetBuffer(0).map_err(|_| ())? };
    let mut target = None;
    unsafe {
        device
            .CreateRenderTargetView(&buffer, None, Some(&mut target))
            .map_err(|_| ())?
    };
    let target = target.ok_or(())?;
    Hudhook::builder()
        .with::<ImguiDx11Hooks>(Display {
            inbox: Arc::clone(&inbox),
            seq: 0,
            index: 0,
            expanded: true,
        })
        .build()
        .apply()
        .map_err(|_| ())?;
    let mut deadline = Instant::now() + Duration::from_secs(seconds);
    let mut ready = false;
    let mut presents = 0_u64;
    while Instant::now() < deadline {
        let mut msg = MSG::default();
        while unsafe { PeekMessageW(&mut msg, None, 0, 0, PM_REMOVE) }.as_bool() {
            if msg.message == WM_QUIT {
                return Err(());
            }
            unsafe {
                let _ = TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
        }
        unsafe {
            context.OMSetRenderTargets(Some(&[Some(target.clone())]), None);
            context.ClearRenderTargetView(&target, &[0.02, 0.02, 0.02, 1.0]);
            swap.Present(1, DXGI_PRESENT(0)).ok().map_err(|_| ())?;
        }
        presents += 1;
        // Only accept the producer's timing test after the first render callback
        // (including lazy shader/font initialization) has actually completed.
        if !ready && inbox.lock().unwrap().stats.draw_callbacks > 0 {
            println!(
                "{}",
                serde_json::json!({"ready":true,"leagueValidated":false})
            );
            std::io::stdout().flush().map_err(|_| ())?;
            ready = true;
            deadline = Instant::now() + Duration::from_secs(seconds);
        }
        thread::sleep(Duration::from_millis(8)); // Bounded even without working VSync.
    }
    // Process-scoped laboratory: exiting removes its own hooks and OS resources.
    // No library is loaded into another process and no injector is compiled.
    println!(
        "{}",
        serde_json::json!({"protocol":1,"engine":"hudhook-dx11",
        "leagueValidated":false,"injectionFeature":false,"driver":driver,
        "presents":presents,"stats":inbox.lock().unwrap().stats})
    );
    unsafe {
        let _ = DestroyWindow(hwnd);
        let _ = UnregisterClassW(class, Some(instance.into()));
    }
    Ok(())
}
