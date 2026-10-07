require "yaml"

root = File.expand_path(__dir__)
template = YAML.load_file(File.join(root, "todo-api-dev/template.yaml"))
catalog = YAML.load_file(File.join(root, "catalog-info.yaml"))
raise "Unexpected template type" unless template.values_at("apiVersion", "kind") == ["scaffolder.backstage.io/v1beta3", "Template"]
raise "Unexpected catalog type" unless catalog.values_at("apiVersion", "kind") == ["backstage.io/v1alpha1", "Component"]

form = template.fetch("spec").fetch("parameters").first
field = form.fetch("properties").fetch("digest")
raise "Digest must be required" unless form.fetch("required").include?("digest")
raise "Digest should be fixed length" unless field.values_at("minLength", "maxLength") == [64, 64]
pattern = Regexp.new(field.fetch("pattern"))
raise "Digest pattern is too broad" unless pattern.match?("a" * 64) && !pattern.match?("A" * 64) && !pattern.match?("g" * 64)

steps = template.fetch("spec").fetch("steps")
raise "Expected render and review steps" unless steps.map { |step| step.fetch("action") } == ["fetch:template", "publish:github:pull-request"]
destination = steps.last.fetch("input")
raise "Config destination is not explicitly scoped" unless destination.values_at("repoUrl", "targetBranchName", "targetPath") == ["github.com?owner=yrw9281&repo=repo-config", "main", "apps/todo-api/overlays/dev"]

image_file = File.join(root, "todo-api-dev/skeleton/microservice.yaml")
rendered = File.read(image_file).sub("${{ values.digest }}", "a" * 64)
raise "Missing digest substitution" if rendered.include?("{{")
resource = YAML.safe_load(rendered)
raise "Wrong image" unless resource.dig("spec", "image") == "ghcr.io/yrw9281/it30-todo-api@sha256:#{"a" * 64}"
raise "Unexpected destination" unless resource.dig("metadata", "namespace") == "todo"
raise "Catalog and template namespaces differ" unless catalog.dig("metadata", "annotations", "backstage.io/kubernetes-namespace") == resource.dig("metadata", "namespace")
raise "Unsupported CR field" unless (resource.fetch("spec").keys - %w[image port]).empty?
raise "Missing Kustomize resource" unless YAML.load_file(File.join(root, "todo-api-dev/skeleton/kustomization.yaml")).fetch("resources") == ["microservice.yaml"]

%w[preview-template.yaml pr-preview-template.yaml].each do |filename|
  preview = YAML.load_file(File.join(root, "todo-api-dev", filename))
  preview_form = preview.fetch("spec").fetch("parameters").first
  preview_field = preview_form.fetch("properties").fetch("digest")
  raise "Preview digest rules differ: #{filename}" unless preview_field.values_at(
    "type", "minLength", "maxLength", "pattern") == field.values_at(
      "type", "minLength", "maxLength", "pattern")
  raise "Preview must require only digest" unless preview_form.fetch("required") == ["digest"]
  raise "Preview permits extra parameters" unless preview_form.fetch("additionalProperties") == false
  actions = preview.fetch("spec").fetch("steps").map { |step| step.fetch("action") }
  raise "Preview can perform external writes" unless actions == ["fetch:template", "debug:log"]
  raise "Preview render differs" unless preview.dig("spec", "steps", 0, "input") == steps.first.fetch("input")
end
proposal = YAML.load_file(File.join(root, "todo-api-dev/pr-preview-template.yaml"))
message = proposal.dig("spec", "steps", 1, "input", "message")
%w[repoUrl branchName targetBranchName sourcePath targetPath title description].each do |key|
  raise "PR preview destination differs: #{key}" unless message.include?(
    "#{key}: #{destination.fetch(key)}")
end

puts "Template and preview structure verified locally; real Backstage rendering is checked separately."
