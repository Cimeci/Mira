terraform {
  required_providers {
    nebius = { source = "nebius/nebius" }
  }
}

# Auth: run `nebius init` (CLI) once — the provider reads those credentials.
provider "nebius" {}

resource "nebius_compute_v1_instance" "mira" {
  name      = "mira-backend"
  parent_id = var.project_id
  stopped   = false

  resources = {
    platform = var.platform
    preset   = var.preset
  }

  boot_disk = {
    attach_mode = "READ_WRITE"
    device_id   = "boot-disk"
    managed_disk = {
      name = "mira-backend-boot-disk"
      spec = {
        type             = "NETWORK_SSD"
        block_size_bytes = 4096
        size_bytes       = var.disk_gib * 1073741824 # GiB → bytes
        source_image_family = {
          image_family = var.image_family
        }
      }
    }
  }

  network_interfaces = [
    {
      name              = "eth0"
      subnet_id         = var.subnet_id
      ip_address        = {}
      public_ip_address = {} # reachable for SSH deploy from CI; drop if plan rejects it
    }
  ]

  # Installs Docker on first boot.
  cloud_init_user_data = base64encode(file("${path.module}/cloud-init.yaml"))

  recovery_policy    = "FAIL"
  reservation_policy = { policy = "AUTO" }
  # preemptible VMs can be reclaimed mid-demo — left off for reliability. Re-add for
  # the cheaper rate if you can tolerate the VM disappearing:
  # preemptible = { on_preemption = "1" }
}

output "instance_id" {
  value = nebius_compute_v1_instance.mira.id
}
