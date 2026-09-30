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
rendered = File.read(image_file).sub("{{ values.digest }}", "a" * 64)
raise "Missing digest substitution" if rendered.include?("{{")
resource = YAML.safe_load(rendered)
raise "Wrong image" unless resource.dig("spec", "image") == "ghcr.io/yrw9281/it30-todo-api@sha256:#{"a" * 64}"
raise "Unexpected destination" unless resource.dig("metadata", "namespace") == "todo-dev"
raise "Unsupported CR field" unless (resource.fetch("spec").keys - %w[image port]).empty?
raise "Missing Kustomize resource" unless YAML.load_file(File.join(root, "todo-api-dev/skeleton/kustomization.yaml")).fetch("resources") == ["microservice.yaml"]

puts "Template structure and rendered YAML verified locally; Backstage, Git and Kubernetes were not exercised."
