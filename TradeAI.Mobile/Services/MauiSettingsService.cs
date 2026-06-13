using Microsoft.Maui.Storage;
using TradeAI.SharedUI.Services;

namespace TradeAI.Mobile.Services;

public class MauiSettingsService : ISettingsService
{
    private const string ApiUrlKey = "TradeAI_ApiBaseUrl_v2";
    
    // Default depends on platform when first retrieved
    private readonly string _defaultUrl;

    public MauiSettingsService()
    {
        _defaultUrl = DeviceInfo.Platform == DevicePlatform.Android 
            ? "http://10.0.2.2:8050" 
            : "http://localhost:8050";
    }

    public string GetApiUrl()
    {
        return Preferences.Default.Get(ApiUrlKey, _defaultUrl);
    }

    public void SetApiUrl(string url)
    {
        Preferences.Default.Set(ApiUrlKey, url);
    }
}
