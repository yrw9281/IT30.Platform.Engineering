using System.Collections.Concurrent;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

var todos = new ConcurrentDictionary<Guid, Todo>();

app.MapGet("/health/live", () => Results.Ok());
app.MapGet("/health/ready", () => Results.Ok());

app.MapGet("/api/todos", () => todos.Values.OrderBy(todo => todo.CreatedAt));

app.MapPost("/api/todos", (CreateTodoRequest request) =>
{
    if (string.IsNullOrWhiteSpace(request.Title))
    {
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["title"] = ["待辦事項不可空白。"]
        });
    }

    var todo = new Todo(Guid.NewGuid(), request.Title.Trim(), false, DateTimeOffset.UtcNow);
    todos[todo.Id] = todo;
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
