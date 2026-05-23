using TradeAI.Web.Components;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();
    
builder.Services.AddScoped<TradeAI.SharedUI.Services.ISettingsService, TradeAI.Web.Services.WebSettingsService>();
builder.Services.AddScoped<TradeAI.SharedUI.Services.DashboardStateService>();

builder.Services.AddScoped(sp => 
{
    var settings = sp.GetRequiredService<TradeAI.SharedUI.Services.ISettingsService>();
    return new HttpClient { BaseAddress = new Uri(settings.GetApiUrl()) };
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}
app.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true);
app.UseHttpsRedirection();

app.UseAntiforgery();

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode()
    .AddAdditionalAssemblies(typeof(TradeAI.SharedUI.Pages.Home).Assembly);

app.Run();
