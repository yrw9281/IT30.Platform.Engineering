using System.Collections.Concurrent;
using System.Diagnostics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);

const string activitySourceName = "Todo.Api";
var serviceName = Environment.GetEnvironmentVariable("OTEL_SERVICE_NAME") ?? "todo-api";
var serviceVersion = Environment.GetEnvironmentVariable("OTEL_SERVICE_VERSION") ?? "0.1.0";
var deploymentEnvironment = Environment.GetEnvironmentVariable("DEPLOYMENT_ENVIRONMENT") ?? "development";
var activitySource = new ActivitySource(activitySourceName);

builder.Services.AddOpenTelemetry()
    .ConfigureResource(resource => resource
        .AddService(serviceName: serviceName, serviceVersion: serviceVersion)
        .AddAttributes([
            new KeyValuePair<string, object>("service.namespace", "todo"),
            new KeyValuePair<string, object>("deployment.environment.name", deploymentEnvironment)
        ]))
    .WithTracing(tracing => tracing
        .AddSource(activitySourceName)
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter());
var app = builder.Build();

var todos = new ConcurrentDictionary<Guid, Todo>();

app.MapGet("/health/live", () => Results.Ok());
app.MapGet("/health/ready", () => Results.Ok());

app.MapGet("/api/todos", () => todos.Values.OrderBy(todo => todo.CreatedAt));

app.MapPost("/api/todos", (CreateTodoRequest request) =>
{
    using var activity = activitySource.StartActivity("todo.create");

    if (string.IsNullOrWhiteSpace(request.Title))
    {
        activity?.SetStatus(ActivityStatusCode.Error, "Todo title is empty.");
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["title"] = ["待辦事項不可空白。"]
        });
    }

    var todo = new Todo(Guid.NewGuid(), request.Title.Trim(), false, DateTimeOffset.UtcNow);
    todos[todo.Id] = todo;
    activity?.SetTag("todo.completed", todo.Completed);
    return Results.Created($"/api/todos/{todo.Id}", todo);
});

app.MapPatch("/api/todos/{id:guid}", (Guid id, UpdateTodoRequest request) =>
{
    if (!todos.TryGetValue(id, out var todo))
    {
        return Results.NotFound();
    }

    var updated = todo with { Completed = request.Completed };
    todos[id] = updated;
    return Results.Ok(updated);
});

app.MapDelete("/api/todos/{id:guid}", (Guid id) =>
    todos.TryRemove(id, out _) ? Results.NoContent() : Results.NotFound());

app.Run();

record Todo(Guid Id, string Title, bool Completed, DateTimeOffset CreatedAt);
record CreateTodoRequest(string? Title);
record UpdateTodoRequest(bool Completed);
