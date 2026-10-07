require "base64"
require "json"
require "net/http"
require "uri"
require "yaml"

base = URI(ENV.fetch("BACKSTAGE_URL", "http://127.0.0.1:7007"))
raise "Use the local port-forward for this guest-only check" unless
  base.scheme == "http" && %w[127.0.0.1 localhost].include?(base.host)
digest = ARGV.fetch(0, "a" * 64)
raise "Expected a 64-character lowercase hex digest" unless digest.match?(/\A[0-9a-f]{64}\z/)
root = File.expand_path(__dir__)

def request(base, path, token: nil, body: nil, expected: 200)
  uri = URI.join(base.to_s, path)
  req = body ? Net::HTTP::Post.new(uri) : Net::HTTP::Get.new(uri)
  req["Authorization"] = "Bearer #{token}" if token
  if body
    req["Content-Type"] = "application/json"
    req.body = JSON.generate(body)
  end
  http = Net::HTTP.new(uri.host, uri.port, nil)
  http.open_timeout = 5
  http.read_timeout = 90
  response = http.request(req)
  raise "#{path} returned HTTP #{response.code}, expected #{expected}" unless
    response.code.to_i == expected
  JSON.parse(response.body)
end

auth = request(base, "/api/auth/guest/refresh?env=development")
token = auth.fetch("backstageIdentity").fetch("token")
files = %w[microservice.yaml kustomization.yaml].map do |name|
  {
    "path" => "skeleton/#{name}",
    "base64Content" => Base64.strict_encode64(
      File.binread(File.join(root, "todo-api-dev/skeleton", name)))
  }
end

%w[todo-api-dev-preview todo-api-dev-pr-preview].each do |name|
  entity = request(base, "/api/catalog/entities/by-name/template/default/#{name}", token: token)
  raise "Preview template UI must use English: #{name}" unless JSON.generate(entity).ascii_only?
  actions = entity.fetch("spec").fetch("steps").map { |step| step.fetch("action") }
  raise "Refusing to run a template that can write externally" unless
    actions == ["fetch:template", "debug:log"]

  body = {"template" => entity, "values" => {"digest" => digest}, "directoryContents" => files}
  result = request(base, "/api/scaffolder/v2/dry-run", token: token, body: body)
  rendered = result.fetch("directoryContents").find { |item| item.fetch("path") == "microservice.yaml" }
  raise "Dry run did not produce microservice.yaml" unless rendered
  resource = YAML.safe_load(Base64.strict_decode64(rendered.fetch("base64Content")))
  raise "Digest was not actually rendered" unless
    resource.dig("spec", "image") == "ghcr.io/yrw9281/it30-todo-api@sha256:#{digest}"
  raise "Rendered resource differs from Todo contract" unless
    resource.values_at("apiVersion", "kind") == ["platform.example.io/v1alpha1", "Microservice"] &&
    resource.dig("metadata", "name") == "todo-api" &&
    resource.dig("metadata", "namespace") == "todo" &&
    resource.fetch("spec").keys.sort == %w[image port] &&
    resource.dig("spec", "port") == 8080
  kustomization = result.fetch("directoryContents").find { |item| item.fetch("path") == "kustomization.yaml" }
  raise "Dry run did not produce kustomization.yaml" unless kustomization
  raise "Kustomization does not include the Microservice" unless
    YAML.safe_load(Base64.strict_decode64(kustomization.fetch("base64Content"))) ==
      YAML.load_file(File.join(root, "todo-api-dev/skeleton/kustomization.yaml"))

  ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "sha256:#{digest}"].each do |invalid|
    request(base, "/api/scaffolder/v2/dry-run", token: token,
            body: body.merge("values" => {"digest" => invalid}), expected: 400)
  end
  request(base, "/api/scaffolder/v2/dry-run", token: token,
          body: body.merge("values" => {"digest" => digest, "namespace" => "other"}), expected: 400)

  task = request(base, "/api/scaffolder/v2/tasks", token: token, expected: 201,
                 body: {"templateRef" => "template:default/#{name}", "values" => {"digest" => digest}})
  id = task.fetch("id")
  deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + 60
  loop do
    state = request(base, "/api/scaffolder/v2/tasks/#{id}", token: token)
    break if state.fetch("status") == "completed"
    if %w[failed cancelled].include?(state.fetch("status"))
      raise "#{name} task #{id} ended as #{state.fetch('status')}"
    end
    raise "#{name} task #{id} did not finish within 60 seconds" if
      Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline
    sleep 1
  end
  events = request(base, "/api/scaffolder/v2/tasks/#{id}/events", token: token)
  messages = events.map { |event| event.fetch("body").fetch("message", "") }.join("\n")
  raise "Task logs do not contain the actual rendered image" unless
    messages.include?("ghcr.io/yrw9281/it30-todo-api@sha256:#{digest}")
  if name == "todo-api-dev-pr-preview"
    raise "PR preview disclaimer missing" unless messages.include?("No GitHub action was executed")
    destination = YAML.load_file(File.join(root, "todo-api-dev/template.yaml")).dig(
      "spec", "steps", 1, "input")
    %w[repoUrl targetBranchName targetPath].each do |key|
      raise "PR destination not shown: #{key}" unless
        messages.include?("#{key}: #{destination.fetch(key)}")
    end
    raise "PR branch did not use the entered digest" unless
      messages.include?("branchName: backstage/todo-api/dev/#{digest}")
  end
  puts "#{name}: real rendering and input rejection verified; #{base}/create/tasks/#{id}"
end
puts "Preview tasks only: no GitHub PR action, Git write, or Kubernetes workload change."
