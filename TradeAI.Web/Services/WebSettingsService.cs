using TradeAI.SharedUI.Services;

namespace TradeAI.Web.Services;

public class WebSettingsService : ISettingsService
{
    private string _apiUrl = "http://localhost:8050";

    public string GetApiUrl()
    {
        return _apiUrl;
    }

    public void SetApiUrl(string url)
    {
        _apiUrl = url;
    }
}
