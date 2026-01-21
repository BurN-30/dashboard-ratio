using hwMonitor.Services;
using System.Text.Json;

// ⚠️ IMPORTANT : Cette application DOIT être exécutée en mode Administrateur
// pour accéder aux capteurs matériels (CPU, GPU, RAM, Stockage).
// Sans droits administrateur, certaines données seront indisponibles.

var builder = WebApplication.CreateBuilder(args);

// Définit une URL par défaut (surchargée si --urls ou ASPNETCORE_URLS est fourni)
builder.WebHost.UseUrls("http://localhost:5056");

// Configuration de la sérialisation JSON (optimisé pour les performances)
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    options.SerializerOptions.WriteIndented = false; // Compact pour réduire la bande passante
});

// Configuration CORS : Restreint l'accès au dashboard public et local
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowDashboard", policy =>
    {
        var dashboardDomain = Environment.GetEnvironmentVariable("DASHBOARD_DOMAIN") ?? "http://localhost:3000";
        policy.WithOrigins(
            dashboardDomain,         // Production
            "http://localhost:3000"  // Développement
        )
        .AllowAnyMethod()
        .AllowAnyHeader();
    });
});

// Enregistrement du service de monitoring en Singleton (instance unique, performant)
builder.Services.AddSingleton<IHardwareMonitorService, HardwareMonitorService>();

// Configuration du logging (production)
if (!builder.Environment.IsDevelopment())
{
    builder.Logging.ClearProviders();
    builder.Logging.AddConsole();
    builder.Logging.SetMinimumLevel(LogLevel.Warning);
}

var app = builder.Build();

// Activation CORS
app.UseCors("AllowDashboard");

// Middleware d'authentification simple
app.Use(async (ctx, next) =>
{
    // Autoriser la route de santé sans authentification pour le monitoring
    if (ctx.Request.Path == "/api/health") 
    { 
        await next(); 
        return; 
    }

    var token = builder.Configuration["HWMONITOR_TOKEN"];
    
    // Si le token n'est pas configuré côté serveur, on bloque tout par sécurité
    if (string.IsNullOrWhiteSpace(token))
    {
        ctx.Response.StatusCode = 500;
        await ctx.Response.WriteAsync("Server Error: HWMONITOR_TOKEN not configured");
        return;
    }

    // Vérification du header X-Api-Key
    if (!ctx.Request.Headers.TryGetValue("X-Api-Key", out var provided) || provided != token)
    {
        ctx.Response.StatusCode = 401;
        await ctx.Response.WriteAsync("Unauthorized");
        return;
    }

    await next();
});

// ========== ROUTES API ==========

/// <summary>
/// Route principale : Récupère les statistiques matérielles en temps réel
/// GET /api/stats
/// Retourne un JSON avec CPU, GPU, RAM et Stockage
/// </summary>
app.MapGet("/api/stats", async (IHardwareMonitorService service) =>
{
    try
    {
        var stats = await service.GetHardwareStatsAsync();
        return Results.Ok(stats);
    }
    catch (Exception ex)
    {
        return Results.Problem(
            detail: ex.Message,
            statusCode: 500,
            title: "Erreur lors de la récupération des statistiques matérielles"
        );
    }
})
.WithName("GetHardwareStats")
.Produces<hwMonitor.Models.HardwareStats>(200)
.Produces(500);

/// <summary>
/// Route de santé : Vérifie que l'API fonctionne
/// GET /api/health
/// </summary>
app.MapGet("/api/health", () => Results.Ok(new
{
    status = "healthy",
    timestamp = DateTime.UtcNow,
    message = "Hardware Monitor API is running"
}))
.WithName("HealthCheck");

// Message d'avertissement au démarrage
app.Lifetime.ApplicationStarted.Register(() =>
{
    var logger = app.Services.GetRequiredService<ILogger<Program>>();
    logger.LogWarning("⚠️  N'oubliez pas d'exécuter cette application en mode ADMINISTRATEUR pour un accès complet aux capteurs matériels.");
});

app.Run();