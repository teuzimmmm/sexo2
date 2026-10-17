// Own-process external composition surface. Never loads code into a game.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <d2d1_1.h>
#include <dwrite.h>
#include <dcomp.h>
#include <wrl/client.h>
#include <new>
#include <cwchar>

using Microsoft::WRL::ComPtr;
#define CHECK(call) do { HRESULT result = (call); if (FAILED(result)) return result; } while (0)

struct Apartment {
    HRESULT status = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    ~Apartment() { if (SUCCEEDED(status)) CoUninitialize(); }
};
struct Surface {
    Apartment apartment; // Declared first so COM uninitializes after all members.
    DWORD owner = GetCurrentThreadId();
    bool warp = false;
    UINT width = 0, height = 0;
    ComPtr<ID3D11Device> d3d;
    ComPtr<IDXGISwapChain1> swap;
    ComPtr<ID2D1DeviceContext> draw;
    ComPtr<ID2D1Bitmap1> bitmap;
    ComPtr<IDWriteTextFormat> format;
    ComPtr<ID2D1SolidColorBrush> text, accent;
    ComPtr<IDCompositionDevice> composition;
    ComPtr<IDCompositionTarget> target;
    ComPtr<IDCompositionVisual> visual;

    HRESULT init(HWND hwnd) {
        if (FAILED(apartment.status)) return apartment.status;
        DWORD pid = 0;
        DWORD thread = GetWindowThreadProcessId(hwnd, &pid);
        if (pid != GetCurrentProcessId() || thread != GetCurrentThreadId()) return E_ACCESSDENIED;
        HRESULT result = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr,
            D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0, D3D11_SDK_VERSION,
            d3d.GetAddressOf(), nullptr, nullptr);
        if (FAILED(result)) {
            warp = true;
            CHECK(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr,
                D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0, D3D11_SDK_VERSION,
                d3d.ReleaseAndGetAddressOf(), nullptr, nullptr));
        }
        ComPtr<IDXGIDevice> dxgi;
        CHECK(d3d.As(&dxgi));
        ComPtr<IDXGIAdapter> adapter;
        CHECK(dxgi->GetAdapter(&adapter));
        ComPtr<IDXGIFactory2> factory;
        CHECK(adapter->GetParent(IID_PPV_ARGS(&factory)));
        DXGI_SWAP_CHAIN_DESC1 desc = {};
        desc.Width = 420; desc.Height = 40;
        desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        desc.SampleDesc.Count = 1;
        desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
        desc.BufferCount = 2;
        desc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;
        desc.AlphaMode = DXGI_ALPHA_MODE_PREMULTIPLIED;
        desc.Scaling = DXGI_SCALING_STRETCH;
        CHECK(factory->CreateSwapChainForComposition(d3d.Get(), &desc, nullptr, &swap));
        ComPtr<ID2D1Factory1> d2dFactory;
        CHECK(D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, d2dFactory.GetAddressOf()));
        ComPtr<ID2D1Device> d2d;
        CHECK(d2dFactory->CreateDevice(dxgi.Get(), &d2d));
        CHECK(d2d->CreateDeviceContext(D2D1_DEVICE_CONTEXT_OPTIONS_NONE, &draw));
        ComPtr<IDWriteFactory> write;
        CHECK(DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED, __uuidof(IDWriteFactory),
            reinterpret_cast<IUnknown**>(write.GetAddressOf())));
        CHECK(write->CreateTextFormat(L"Segoe UI", nullptr, DWRITE_FONT_WEIGHT_NORMAL,
            DWRITE_FONT_STYLE_NORMAL, DWRITE_FONT_STRETCH_NORMAL, 14.f, L"pt-BR", &format));
        CHECK(format->SetWordWrapping(DWRITE_WORD_WRAPPING_NO_WRAP));
        CHECK(format->SetLineSpacing(DWRITE_LINE_SPACING_METHOD_UNIFORM, 20.f, 15.f));
        CHECK(draw->CreateSolidColorBrush(D2D1::ColorF(.84f, .90f, .94f), &text));
        CHECK(draw->CreateSolidColorBrush(D2D1::ColorF(.22f, .82f, .74f), &accent));
        CHECK(DCompositionCreateDevice(dxgi.Get(), IID_PPV_ARGS(&composition)));
        CHECK(composition->CreateTargetForHwnd(hwnd, TRUE, &target));
        CHECK(composition->CreateVisual(&visual));
        CHECK(visual->SetContent(swap.Get()));
        CHECK(target->SetRoot(visual.Get()));
        CHECK(composition->Commit());
        return S_OK;
    }

    HRESULT paint(UINT w, UINT h, const wchar_t* header, const wchar_t* body, const wchar_t* footer) {
        if (owner != GetCurrentThreadId()) return RPC_E_WRONG_THREAD;
        if (w < 240 || w > 840 || h < 40 || h > 1140 || !header || !body || !footer)
            return E_INVALIDARG;
        // Bound before DrawText, including malformed direct callers of the ABI.
        const size_t a = wcsnlen_s(header, 8193), b = wcsnlen_s(body, 8193), c = wcsnlen_s(footer, 8193);
        if (a > 8192 || b > 8192 || c > 8192) return E_INVALIDARG;
        if (width != w || height != h || !bitmap) {
            draw->SetTarget(nullptr);
            bitmap.Reset();
            CHECK(swap->ResizeBuffers(2, w, h, DXGI_FORMAT_B8G8R8A8_UNORM, 0));
            ComPtr<IDXGISurface> buffer;
            CHECK(swap->GetBuffer(0, IID_PPV_ARGS(&buffer)));
            D2D1_BITMAP_PROPERTIES1 props = {};
            props.pixelFormat = {DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_PREMULTIPLIED};
            props.dpiX = props.dpiY = 96.f;
            props.bitmapOptions = D2D1_BITMAP_OPTIONS_TARGET | D2D1_BITMAP_OPTIONS_CANNOT_DRAW;
            CHECK(draw->CreateBitmapFromDxgiSurface(buffer.Get(), &props, &bitmap));
            draw->SetTarget(bitmap.Get());
            width = w; height = h;
        }
        draw->BeginDraw();
        draw->Clear(D2D1::ColorF(.035f, .055f, .075f, .98f));
        const D2D1_RECT_F top = D2D1::RectF(14.f, 8.f, float(w)-14.f, 34.f);
        draw->DrawTextW(header, UINT32(a), format.Get(), top, accent.Get(), D2D1_DRAW_TEXT_OPTIONS_CLIP);
        if (h > 40) {
            const D2D1_RECT_F middle = D2D1::RectF(14.f, 42.f, float(w)-14.f, float(h)-38.f);
            const D2D1_RECT_F bottom = D2D1::RectF(14.f, float(h)-28.f, float(w)-14.f, float(h)-4.f);
            draw->DrawTextW(body, UINT32(b), format.Get(), middle, text.Get(), D2D1_DRAW_TEXT_OPTIONS_CLIP);
            draw->DrawTextW(footer, UINT32(c), format.Get(), bottom, accent.Get(), D2D1_DRAW_TEXT_OPTIONS_CLIP);
        }
        CHECK(draw->EndDraw());
        CHECK(swap->Present(0, 0));
        return composition->Commit();
    }
};

extern "C" __declspec(dllexport) HRESULT __cdecl s2_create(HWND hwnd, void** output) noexcept {
    if (!output) return E_POINTER;
    *output = nullptr;
    auto surface = new (std::nothrow) Surface();
    if (!surface) return E_OUTOFMEMORY;
    HRESULT result = surface->init(hwnd);
    if (FAILED(result)) { delete surface; return result; }
    *output = surface;
    return S_OK;
}
extern "C" __declspec(dllexport) HRESULT __cdecl s2_draw(void* state, UINT w, UINT h,
    const wchar_t* header, const wchar_t* body, const wchar_t* footer) noexcept {
    if (!state) return E_POINTER;
    return static_cast<Surface*>(state)->paint(w, h, header, body, footer);
}
extern "C" __declspec(dllexport) int __cdecl s2_driver(void* state) noexcept {
    return state ? (static_cast<Surface*>(state)->warp ? 2 : 1) : 0;
}
extern "C" __declspec(dllexport) void __cdecl s2_destroy(void* state) noexcept {
    delete static_cast<Surface*>(state);
}
