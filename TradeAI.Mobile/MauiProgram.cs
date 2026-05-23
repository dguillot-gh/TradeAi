using Microsoft.Extensions.Logging;

namespace TradeAI.Mobile;

public static class MauiProgram
{
	public static MauiApp CreateMauiApp()
	{
		var builder = MauiApp.CreateBuilder();
		builder
			.UseMauiApp<App>()
			.ConfigureFonts(fonts =>
			{
				fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
			});

		builder.Services.AddMauiBlazorWebView();

        // Register Settings Service
        builder.Services.AddSingleton<TradeAI.SharedUI.Services.ISettingsService, TradeAI.Mobile.Services.MauiSettingsService>();
        
        // Register Dashboard State Service
        builder.Services.AddScoped<TradeAI.SharedUI.Services.DashboardStateService>();

        builder.Services.AddScoped(sp => 
        {
            var settings = sp.GetRequiredService<TradeAI.SharedUI.Services.ISettingsService>();
            return new HttpClient { BaseAddress = new Uri(settings.GetApiUrl()) };
        });

#if DEBUG
		builder.Services.AddBlazorWebViewDeveloperTools();
		builder.Logging.AddDebug();
#endif

		return builder.Build();
	}
}
