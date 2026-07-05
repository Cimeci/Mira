# Defaults are the values from your Nebius console — override per environment.
# CPU-only is cheaper and insightface runs fine on it: set platform="cpu-d3"-ish,
# preset without a gpu, image_family="ubuntu24.04". Check names with
# `nebius compute platform list` / `nebius compute image list`.

variable "project_id" {
  type    = string
  default = "project-e00ht643pr0021rf8y4g8r"
}

variable "subnet_id" {
  type    = string
  default = "vpcsubnet-e00eyybsbd400k3h43"
}

variable "platform" {
  type    = string
  default = "gpu-l40s-a"
}

variable "preset" {
  type    = string
  default = "1gpu-8vcpu-32gb"
}

variable "image_family" {
  type    = string
  default = "ubuntu24.04-cuda13.0"
}

variable "disk_gib" {
  type    = number
  default = 250
}
