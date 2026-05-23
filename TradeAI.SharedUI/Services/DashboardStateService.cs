namespace TradeAI.SharedUI.Services;

public class DashboardStateService
{
    public bool IsConnected { get; set; } = false;
    public string BuyingPower { get; set; } = "$---";
    public bool HasData { get; set; } = false;
    public DateTime LastFetched { get; set; } = DateTime.MinValue;

    public PortfolioSummaryResponse? PortfolioSummary { get; set; }
    public List<AiSuggestion>? AiSuggestions { get; set; }
    public string? SuggestionsGeneratedAt { get; set; }
    public bool SuggestionsAreFresh { get; set; } = false;
}

public class PortfolioSummaryResponse
{
    public decimal total_value { get; set; }
    public decimal today_return_amount { get; set; }
    public decimal today_return_percent { get; set; }
}

public class AiSuggestionResponse
{
    public List<AiSuggestion>? suggestions { get; set; }
    public string? generated_at { get; set; }
    public bool is_fresh { get; set; }
}

public class AiSuggestion
{
    public int id { get; set; }
    public string? symbol { get; set; }
    public string? action { get; set; }
    public string? confidence { get; set; }
    public string? reason { get; set; }
    public bool is_actioned { get; set; }
}
