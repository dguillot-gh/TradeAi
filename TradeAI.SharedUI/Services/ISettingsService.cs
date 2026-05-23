namespace TradeAI.SharedUI.Services;

public interface ISettingsService
{
    string GetApiUrl();
    void SetApiUrl(string url);
}
