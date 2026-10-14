using OpenTelemetry.Logs;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);

var serviceName = Environment.GetEnvironmentVariable("OTEL_SERVICE_NAME") ?? "todo-bff";
var serviceVersion = Environment.GetEnvironmentVariable("OTEL_SERVICE_VERSION") ?? "0.1.0";
var deploymentEnvironment = Environment.GetEnvironmentVariable("DEPLOYMENT_ENVIRONMENT") ?? "development";
var todoApiBaseUrl = builder.Configuration["TODO_API_BASE_URL"] ?? "http://todo-api:8080";

builder.Services.AddHttpClient("todo-api", client =>
{
    client.BaseAddress = new Uri(todoApiBaseUrl);
});

builder.Services.AddOpenTelemetry()
    .ConfigureResource(resource => resource
        .AddService(serviceName: serviceName, serviceVersion: serviceVersion)
        .AddAttributes([
            new KeyValuePair<string, object>("service.namespace", "todo"),
            new KeyValuePair<string, object>("deployment.environment.name", deploymentEnvironment)
        ]))
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddOtlpExporter())
    .WithMetrics(metrics => metrics
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter());
builder.Logging.AddOpenTelemetry(logging => logging.AddOtlpExporter());

var app = builder.Build();

app.MapGet("/health/live", () => Results.Ok());
app.MapGet("/health/ready", () => Results.Ok());

app.MapMethods("/api/{**path}", ["GET", "POST", "PATCH", "DELETE"], ForwardToTodoApiAsync);

app.Run();

static async Task<IResult> ForwardToTodoApiAsync(
    HttpContext context,
    IHttpClientFactory httpClientFactory,
    CancellationToken cancellationToken)
{
    using var request = new HttpRequestMessage(
        new HttpMethod(context.Request.Method),
        $"{context.Request.Path}{context.Request.QueryString}");

    if (context.Request.ContentLength is > 0)
    {
        request.Content = new StreamContent(context.Request.Body);

        if (!string.IsNullOrWhiteSpace(context.Request.ContentType))
        {
            request.Content.Headers.ContentType =
                System.Net.Http.Headers.MediaTypeHeaderValue.Parse(context.Request.ContentType);
        }
    }

    using var response = await httpClientFactory
        .CreateClient("todo-api")
        .SendAsync(request, cancellationToken);
    var content = await response.Content.ReadAsStringAsync(cancellationToken);

    return Results.Content(
        content,
        response.Content.Headers.ContentType?.ToString(),
        statusCode: (int)response.StatusCode);
}
